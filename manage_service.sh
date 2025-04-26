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

case "$1" in
    "install")
        check_heroapp_user
        setup_directories
        setup_firewall
        install_service
        echo "Installation completed successfully"
        ;;
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
        echo "Usage: $0 {install|start|stop|restart|status}"
        exit 1
        ;;
esac 