import sys
import logging
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_socketio import SocketIO, emit
import subprocess
import os

app = Flask(__name__)
socketio = SocketIO(app)

# Function to get the directory of the current Python script
def get_script_directory():
    return os.path.dirname(os.path.realpath(__file__))

# Function to get a list of files in the directory
def get_files(directory):
    return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

# Configure logging
log_file = os.path.join(get_script_directory(), 'flask.log')
logging.basicConfig(filename=log_file, level=logging.DEBUG)

# Define a route to the home page
@app.route('/')
def index():
    directory = get_script_directory()
    files = get_files(directory)
    return render_template('index.html', files=files)

# Define a route to view logs
@app.route('/view-logs')
def view_logs():
    # Read log file content
    with open(log_file, 'r') as file:
        logs = file.readlines()
    return render_template('logs.html', logs=logs)

# Define a route to restart the server
@app.route('/restart-server', methods=['POST'])
def restart_server():
    # Command to restart the server (adjust this based on your server setup)
    restart_command = 'sudo systemctl restart your_server_name.service'
    
    # Execute the restart command
    subprocess.run(restart_command, shell=True)
    
    return redirect(url_for('index'))

# Define a route to edit files
@app.route('/edit-file', methods=['POST'])
def edit_file():
    # Get the file path and content from the form
    file_path = request.form['file_path']
    file_content = request.form['file_content']
    
    # Write the content to the file
    with open(file_path, 'w') as file:
        file.write(file_content)
    
    return redirect(url_for('index'))

# Define a route to handle file uploads
@app.route('/upload-file', methods=['POST'])
def upload_file():
    # Get the uploaded file
    uploaded_file = request.files['file']
    
    # Save the file to the uploads directory
    uploads_dir = os.path.join(get_script_directory(), 'uploads')
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
    
    uploaded_file.save(os.path.join(uploads_dir, uploaded_file.filename))
    
    return redirect(url_for('index'))

# Serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(os.path.join(get_script_directory(), 'uploads'), filename)

# Start a background process to run the command and emit output to the client
@socketio.on('connect')
def handle_connect():
    # Command to run (example)
    command = 'ls -l'
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    for line in iter(process.stdout.readline, b''):
        emit('terminal_output', {'data': line.decode()}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=80, debug=False, allow_unsafe_werkzeug=True)

