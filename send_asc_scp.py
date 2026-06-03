#!/usr/bin/python3
'''
Created by: Romel
Version: 2.0
Date: 17.Feb.2024
Python script that monitors a directory for new .asc files and sends them to a remote server using scp, 
that uses the watchdog library for monitoring directory changes and the subprocess module to execute 
the scp command.
V2.0 - 24.Aug.2024 - optimize for deleting the asc file when successul transfer only
V5 - 24.Aug.2024 - To make sure it will send all .asc files
                 - Continuous Checking: The transfer_pending_files() method now runs in a loop, continuously 
                 checking the directory for any .asc files that need to be transferred, even after the initial 
                 transfer and while monitoring for new files.
                 - Retry Logic: If the internet connection is lost, the script will keep checking every check_interval 
                 seconds (default is 60 seconds) and will attempt to transfer any remaining .asc files once the connection 
                 is restored.
                 - Non-Blocking Monitoring: The loop for transferring pending files runs concurrently with the file monitoring, 
                 so new files are still detected and processed as usual.

Dependencies:
pip3 install watchdog

How It Works:

1. Initial Transfer: When an instance of AscFileHandler is created, the initial_transfer method is called. 
   This method scans the specified directory for any .asc files that already exist and sends them to the 
   remote server. After this initial transfer, the script continues to monitor the directory for new .asc files.
2. On Creation: The on_created method handles the event of a new .asc file being created in the directory. 
   It calls transfer_file to send the new file.
3. File Transfer: The transfer_file method is responsible for transferring a file using scp and then deleting 
   the file upon successful transfer.
This script ensures that all existing .asc files in the directory are transferred when the script is first 
started, and it continues to monitor and transfer new .asc files as they are created.
'''
import os
import subprocess
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class AscFileHandler(FileSystemEventHandler):
    def __init__(self, directory, remote_paths, ports, check_interval=60):
        self.directory = directory
        self.remote_paths = remote_paths
        self.ports = ports
        self.check_interval = check_interval
        self.transfer_pending_files()
        
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.asc'):
            self.transfer_file(event.src_path)

    def transfer_file(self, file_path):
        print(f"Detected new file for transfer: {file_path}")
        success = True  # Flag to check if all transfers were successful
        for remote_path, port in zip(self.remote_paths, self.ports):
            print(f"Attempting to transfer {file_path} to {remote_path} using port {port if port else 'default'}")
            if port:
                result = subprocess.run(["scp", "-P", str(port), file_path, remote_path], capture_output=True)
            else:
                result = subprocess.run(["scp", file_path, remote_path], capture_output=True)
            if result.returncode == 0:
                print(f"Transfer to {remote_path} successful: {file_path}")
            else:
                success = False  # Mark as failed if any transfer fails
                print(f"Transfer to {remote_path} failed: {file_path}\n{result.stderr.decode()}")

        if success:
            os.remove(file_path)
            print(f"File {file_path} deleted after successful transfer.")
        else:
            print(f"File {file_path} not deleted due to failed transfer.")

    def transfer_pending_files(self):
        while True:
            files = [f for f in os.listdir(self.directory) if f.endswith('.asc')]
            if files:
                print(f"Found {len(files)} pending .asc files for transfer.")
            for file_name in sorted(files):
                file_path = os.path.join(self.directory, file_name)
                print(f"Transferring pending file: {file_path}")
                self.transfer_file(file_path)
            time.sleep(self.check_interval)

if __name__ == "__main__":
    directory_to_monitor = "/home/drums/asc/"
    remote_server_paths = [
        #"devdb@dsing.softether.net:/home/devdb/incoming/",
        "opc@129.150.37.135:/input/DB4502"
    ]
    ports = [None]  # Specify ports corresponding to each remote path, None for default port
    check_interval = 60  # Check for unsent files every 60 seconds

    event_handler = AscFileHandler(directory_to_monitor, remote_server_paths, ports, check_interval)
    observer = Observer()
    observer.schedule(event_handler, directory_to_monitor, recursive=False)
    observer.start()

    try:
        while True:
            pass  # Keep the script running
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

