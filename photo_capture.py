#!/usr/bin/python3
'''
Created By: Romel
Version:1.6
Date: 10.10.2023
This script is for taking photo when the panel door is breached detected by GPIO27.
'''
import RPi.GPIO as GPIO
import time
import os
import subprocess
from datetime import datetime, timezone
import schedule  # Import the schedule library

# Set up GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Define the directories for saving files
csv_save_directory = '/home/drums/csv/'
photos_save_directory = '/home/drums/breach_photos/'

# Ensure the directories exist
os.makedirs(csv_save_directory, exist_ok=True)
os.makedirs(photos_save_directory, exist_ok=True)

def log_state_and_maybe_take_photo():
    # Original timestamp in UTC, for general use
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    # New timestamp format for the CSV filename
    timestamp1 = datetime.now(timezone.utc).strftime("%m-%d-%Y-%H-%M-%S")
    # Create a new CSV filename with the new timestamp format
    csv_filename = os.path.join(csv_save_directory, f'perimeter_breach_{timestamp1}.csv')
    
    # Check the GPIO input state
    input_state = GPIO.input(27)
    state = '1.0' if input_state else '0.0'
    print(f"GPIO 27 input is {state}.")

    # Define the log content
    log_content = f"9812664,DB66_01,10193,Panel Perimeter Breach,{timestamp},{state},High/Low\n"

    # Log the input state to the newly created CSV file
    with open(csv_filename, 'w') as log_file:
        log_file.write(log_content)
    
    # If the input is LOW, take a photo
    if input_state == GPIO.LOW:
        print("Taking a photo...")
        # Change the save directory for the photo
        photo_filename = os.path.join(photos_save_directory, f"photo_{timestamp}_{state}.jpg")
        capture_command = f'libcamera-still -o "{photo_filename}" --shutter 200000 --awb auto --hdr 1'
        subprocess.run(capture_command, shell=True)
        print(f"Photo captured: {photo_filename}")

# Schedule the function to run every 1 minute
schedule.every(1).minute.do(log_state_and_maybe_take_photo)

try:
    # Kick off the first log immediately
    log_state_and_maybe_take_photo()
    while True:
        schedule.run_pending()
        time.sleep(1)  # Sleep for a short time to prevent high CPU usage

except KeyboardInterrupt:
    print("Script terminated by the user.")
finally:
    GPIO.cleanup()
