# File Upload Service

A simple file upload service that stores files and sends download links via email.

## Features

- File upload via REST API
- Email notifications with download links
- Automatic cleanup of files older than 1 day
- FTP server integration
- Secure credential storage
- Systemd service management

## Prerequisites

- Python 3.6+
- FTP server installed and configured
- Systemd
- UFW (Uncomplicated Firewall)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd send-myfile
```

2. Install Python dependencies:
```bash
pip3 install -r requirements.txt
```

3. Create the secrets file:
```bash
mkdir -p ~/.secrets
echo '{
    "smtp_username": "your-email@gmail.com",
    "smtp_password": "your-app-password"
}' > ~/.secrets/my_secret.txt
chmod 600 ~/.secrets/my_secret.txt
```

4. Install and start the service:
```bash
sudo chmod +x manage_service.sh
sudo ./manage_service.sh install
sudo ./manage_service.sh start
```

## Usage

### API Endpoint

POST /upload
- Content-Type: multipart/form-data
- Parameters:
  - file: The file to upload
  - email: Recipient's email address

### Service Management

```bash
# Start the service
sudo ./manage_service.sh start

# Stop the service
sudo ./manage_service.sh stop

# Restart the service
sudo ./manage_service.sh restart

# Check service status
sudo ./manage_service.sh status
```

## Security

- The service runs as user 'heroapp'
- Credentials are stored in ~/.secrets/my_secret.txt
- Firewall only allows SSH, FTP, and port 5000
- Files are automatically deleted after 1 day

## Directory Structure

- Upload directory: /var/ftp/upload (symlinked to /upload)
- Service configuration: /etc/systemd/system/fileupload.service
- Application logs: systemd journal

## Troubleshooting

1. Check service status:
```bash
sudo ./manage_service.sh status
```

2. View logs:
```bash
journalctl -u fileupload.service
```

3. Check permissions:
```bash
ls -la /upload
ls -la /home/heroapp/.secrets
``` 