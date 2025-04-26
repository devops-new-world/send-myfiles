# Hands-On Lab: Setting Up a File Upload Service

## Prerequisites
- A Linux system with sudo privileges
- Basic understanding of terminal commands

## Step 1: Create the `heroapp` User

```bash
# Create the heroapp user with home directory
sudo useradd -m -s /bin/bash heroapp

# Verify the user was created
id heroapp
```

## Step 2: Set Password for the `heroapp` User

```bash
# Set password for heroapp user
sudo passwd heroapp

# You'll be prompted to enter and confirm the password
```

## Step 3: Create Required Directories and Set Permissions

```bash
# Create the upload directory
sudo mkdir -p /upload

# Create the secrets directory
sudo mkdir -p /home/heroapp/.secrets

# Set proper permissions
sudo chmod 755 /upload
sudo chmod 700 /home/heroapp/.secrets

# Change ownership to heroapp user
sudo chown -R heroapp:heroapp /upload
sudo chown -R heroapp:heroapp /home/heroapp/.secrets
```

## Step 4: Create the Secrets File

```bash
# Create the secrets file with Gmail credentials
sudo tee /home/heroapp/.secrets/my_secret.txt << EOF
{
    "smtp_username": "your-email@gmail.com",
    "smtp_password": "your-app-password"
}
EOF

# Set proper permissions
sudo chmod 600 /home/heroapp/.secrets/my_secret.txt
sudo chown heroapp:heroapp /home/heroapp/.secrets/my_secret.txt
```

## Step 5: Create the Application Files

```bash
# Create the application directory
sudo mkdir -p /home/heroapp/send-myfile

# Create the app.py file
sudo tee /home/heroapp/send-myfile/app.py << 'EOF'
import os
import shutil
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = '/var/ftp/upload'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_secrets():
    try:
        with open(os.path.expanduser('~/.secrets/my_secret.txt'), 'r') as f:
            secrets = json.load(f)
            return secrets
    except Exception as e:
        logger.error(f"Error loading secrets: {e}")
        return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_email(recipient_email, file_url):
    secrets = load_secrets()
    if not secrets:
        logger.error("Could not load email credentials")
        return False

    sender_email = secrets['smtp_username']
    password = secrets['smtp_password']

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = "Your File Upload Link"

    body = f"Your file has been uploaded successfully. You can download it from: {file_url}"
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False

def cleanup_old_files():
    try:
        current_time = datetime.now()
        for filename in os.listdir(UPLOAD_FOLDER):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(filepath):
                file_modified = datetime.fromtimestamp(os.path.getmtime(filepath))
                if current_time - file_modified > timedelta(days=1):
                    os.remove(filepath)
                    logger.info(f"Deleted old file: {filename}")
    except Exception as e:
        logger.error(f"Error cleaning up old files: {e}")

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    email = request.form.get('email')
    
    if not email:
        return jsonify({'error': 'No email provided'}), 400
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    try:
        # Save the file
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Generate download URL
        file_url = f"ftp://your-server-address/{filename}"
        
        # Send email
        if send_email(email, file_url):
            return jsonify({
                'message': 'File uploaded successfully',
                'download_url': file_url
            }), 200
        else:
            return jsonify({
                'message': 'File uploaded but email sending failed',
                'download_url': file_url
            }), 200
            
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return jsonify({'error': 'Error uploading file'}), 500

if __name__ == '__main__':
    # Ensure upload directory exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Clean up old files on startup
    cleanup_old_files()
    
    # Start the Flask app
    app.run(host='0.0.0.0', port=5000)
EOF

# Create the requirements.txt file
sudo tee /home/heroapp/send-myfile/requirements.txt << EOF
Flask==2.0.1
Werkzeug==2.0.1
python-dotenv==0.19.0
EOF

# Set proper ownership
sudo chown -R heroapp:heroapp /home/heroapp/send-myfile
```

## Step 6: Create the Systemd Service File

```bash
# Create the systemd service file
sudo tee /etc/systemd/system/fileupload.service << EOF
[Unit]
Description=File Upload Service
After=network.target

[Service]
Type=simple
User=heroapp
WorkingDirectory=/home/heroapp/send-myfile
Environment=PYTHONUNBUFFERED=1
ExecStart=/usr/bin/python3 /home/heroapp/send-myfile/app.py
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
EOF
```

## Step 7: Install and Configure FTP Server

```bash
# Install vsftpd (Very Secure FTP Daemon)
sudo apt update
sudo apt install -y vsftpd

# Backup the original configuration
sudo cp /etc/vsftpd.conf /etc/vsftpd.conf.bak

# Configure vsftpd
sudo tee /etc/vsftpd.conf << EOF
listen=YES
listen_ipv6=NO
anonymous_enable=NO
local_enable=YES
write_enable=YES
local_umask=022
dirmessage_enable=YES
use_localtime=YES
xferlog_enable=YES
connect_from_port_20=YES
chroot_local_user=YES
secure_chroot_dir=/var/run/vsftpd/empty
pam_service_name=vsftpd
force_local_logins_ssl=NO
force_local_data_ssl=NO
pasv_enable=YES
pasv_min_port=40000
pasv_max_port=50000
user_sub_token=\$USER
local_root=/var/ftp/\$USER
userlist_enable=YES
userlist_file=/etc/vsftpd.userlist
userlist_deny=NO
EOF

# Create the userlist file
sudo tee /etc/vsftpd.userlist << EOF
heroapp
EOF

# Create the FTP directory structure
sudo mkdir -p /var/ftp/heroapp
sudo ln -sf /upload /var/ftp/upload
sudo chown -R heroapp:heroapp /var/ftp/heroapp
sudo chmod 755 /var/ftp/heroapp

# Restart the FTP service
sudo systemctl restart vsftpd
```

## Step 8: Configure Firewall

```bash
# Install UFW if not already installed
sudo apt install -y ufw

# Allow SSH, FTP, and port 5000
sudo ufw allow ssh
sudo ufw allow ftp
sudo ufw allow 5000/tcp

# Enable the firewall
sudo ufw --force enable

# Check the status
sudo ufw status
```

## Step 9: Install Python Dependencies

```bash
# Switch to heroapp user
sudo -u heroapp bash -c "cd /home/heroapp/send-myfile && pip3 install -r requirements.txt"
```

## Step 10: Start and Enable the Service

```bash
# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable fileupload.service

# Start the service
sudo systemctl start fileupload.service

# Check the status
sudo systemctl status fileupload.service
```

## Step 11: Check Service Logs

```bash
# View the service logs
sudo journalctl -u fileupload.service

# Follow the logs in real-time
sudo journalctl -u fileupload.service -f
```

## Step 12: Create a Management Script

```bash
# Create the management script
sudo tee /home/heroapp/send-myfile/manage_service.sh << 'EOF'
#!/bin/bash

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root"
    exit 1
fi

case "$1" in
    "start")
        systemctl start fileupload.service
        echo "Service started"
        ;;
    "stop")
        systemctl stop fileupload.service
        echo "Service stopped"
        ;;
    "restart")
        systemctl restart fileupload.service
        echo "Service restarted"
        ;;
    "status")
        systemctl status fileupload.service
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
EOF

# Make the script executable
sudo chmod +x /home/heroapp/send-myfile/manage_service.sh
```

## Step 13: Create a Makefile for Maintainability

```bash
# Create the Makefile
sudo tee /home/heroapp/send-myfile/Makefile << 'EOF'
.PHONY: install start stop restart status logs clean

install:
	@echo "Installing dependencies..."
	pip3 install -r requirements.txt

start:
	@echo "Starting service..."
	sudo systemctl start fileupload.service

stop:
	@echo "Stopping service..."
	sudo systemctl stop fileupload.service

restart:
	@echo "Restarting service..."
	sudo systemctl restart fileupload.service

status:
	@echo "Checking service status..."
	sudo systemctl status fileupload.service

logs:
	@echo "Viewing service logs..."
	sudo journalctl -u fileupload.service

clean:
	@echo "Cleaning up old files..."
	find /upload -type f -mtime +1 -delete

setup:
	@echo "Setting up the service..."
	sudo systemctl daemon-reload
	sudo systemctl enable fileupload.service
	sudo systemctl start fileupload.service
EOF

# Set proper ownership
sudo chown heroapp:heroapp /home/heroapp/send-myfile/Makefile
```

## Step 14: Test the Service

```bash
# Create a test file
echo "This is a test file" > test.txt

# Upload the file using curl
curl -X POST -F "file=@test.txt" -F "email=your-email@example.com" http://localhost:5000/upload
```

## Step 15: Create an Automation Script

```bash
# Create the automation script
sudo tee /home/heroapp/send-myfile/setup.sh << 'EOF'
#!/bin/bash

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root"
    exit 1
fi

# Function to check if heroapp user exists
check_heroapp_user() {
    if ! id "heroapp" &>/dev/null; then
        echo "Creating heroapp user..."
        useradd -m -s /bin/bash heroapp
    fi
}

# Function to setup directories and permissions
setup_directories() {
    # Create upload directory and symlink
    mkdir -p /upload
    ln -sf /upload /var/ftp/upload
    chown -R heroapp:heroapp /upload
    
    # Create secrets directory
    mkdir -p /home/heroapp/.secrets
    chmod 700 /home/heroapp/.secrets
}

# Function to setup firewall
setup_firewall() {
    # Allow SSH, FTP, and port 5000
    ufw allow ssh
    ufw allow ftp
    ufw allow 5000/tcp
    ufw --force enable
}

# Function to install service
install_service() {
    cp fileupload.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable fileupload.service
}

# Main installation process
echo "Starting installation..."

# Check and create heroapp user
check_heroapp_user

# Setup directories and permissions
setup_directories

# Setup firewall
setup_firewall

# Install service
install_service

echo "Installation completed successfully"
echo "Please set the password for heroapp user:"
passwd heroapp

echo "Please create the secrets file with your Gmail credentials:"
echo "mkdir -p /home/heroapp/.secrets"
echo "echo '{\"smtp_username\": \"your-email@gmail.com\", \"smtp_password\": \"your-app-password\"}' > /home/heroapp/.secrets/my_secret.txt"
echo "chmod 600 /home/heroapp/.secrets/my_secret.txt"
echo "chown heroapp:heroapp /home/heroapp/.secrets/my_secret.txt"

echo "After setting up the secrets file, start the service with:"
echo "sudo systemctl start fileupload.service"
EOF

# Make the script executable
sudo chmod +x /home/heroapp/send-myfile/setup.sh
```

## Additional Steps: Verification and Monitoring

### Step 16: Verify Network Status and Port Binding

```bash
# Check if the service is listening on port 5000
sudo netstat -tuln | grep 5000

# Alternative using ss command
sudo ss -tuln | grep 5000

# Check if the FTP service is running
sudo netstat -tuln | grep 21

# Check all listening ports
sudo lsof -i -P -n | grep LISTEN

# Check network connections for the Python process
sudo lsof -i -P -n | grep python
```

### Step 17: Monitor Process, CPU, and RAM Usage

```bash
# Check process status
ps aux | grep python

# Monitor process in real-time
top -p $(pgrep -f "python.*app.py")

# Check memory usage
free -h

# Check CPU usage
mpstat 1 5

# Check system load
uptime

# Monitor system resources in real-time
htop
```

### Step 18: Monitor Disk Usage

```bash
# Check disk usage
df -h

# Check directory size
du -sh /upload

# Check file count in upload directory
find /upload -type f | wc -l

# Check largest files in upload directory
find /upload -type f -exec du -h {} \; | sort -rh | head -10

# Monitor disk I/O
iostat -x 1 5
```

### Step 19: Create a Monitoring Script

```bash
# Create a monitoring script
sudo tee /home/heroapp/send-myfile/monitor.sh << 'EOF'
#!/bin/bash

echo "=== System Status ==="
echo "Uptime: $(uptime)"
echo "Load Average: $(cat /proc/loadavg | awk '{print $1, $2, $3}')"
echo ""

echo "=== Memory Usage ==="
free -h
echo ""

echo "=== Disk Usage ==="
df -h /upload
echo ""

echo "=== Process Status ==="
ps aux | grep python | grep -v grep
echo ""

echo "=== Network Connections ==="
netstat -tuln | grep -E '5000|21'
echo ""

echo "=== Service Status ==="
systemctl status fileupload.service | grep Active
systemctl status vsftpd | grep Active
echo ""

echo "=== Recent Logs ==="
journalctl -u fileupload.service -n 10 --no-pager
EOF

# Make the script executable
sudo chmod +x /home/heroapp/send-myfile/monitor.sh
```

## Learning Points

Throughout this lab, you've learned several important Linux commands and concepts:

1. **User Management**:
   - `useradd`: Create a new user
   - `passwd`: Set or change a user's password
   - `id`: Display user and group information

2. **File and Directory Operations**:
   - `mkdir`: Create directories
   - `chmod`: Change file permissions
   - `chown`: Change file ownership
   - `ln`: Create symbolic links
   - `tee`: Write output to a file and display it

3. **Service Management**:
   - `systemctl`: Control the systemd system and service manager
   - `journalctl`: Query and display messages from the systemd journal

4. **Package Management**:
   - `apt update`: Update package lists
   - `apt install`: Install packages

5. **Firewall Configuration**:
   - `ufw allow`: Allow specific traffic
   - `ufw enable`: Enable the firewall

6. **Process Management**:
   - `ps`: Display information about running processes
   - `kill`: Send signals to processes

7. **Network Monitoring**:
   - `netstat`: Display network connections
   - `ss`: Display socket statistics
   - `lsof`: List open files

8. **System Resource Monitoring**:
   - `top`: Display system processes
   - `htop`: Interactive process viewer
   - `free`: Display memory usage
   - `df`: Display disk space usage
   - `du`: Display directory space usage
   - `iostat`: Report I/O statistics

9. **Automation**:
   - Shell scripting
   - Makefiles for build automation

This hands-on lab provides a practical way to learn Linux commands while setting up a useful service. You can now use these skills to manage other services and automate system administration tasks. 