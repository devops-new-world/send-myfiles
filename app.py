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