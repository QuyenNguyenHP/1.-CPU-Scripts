#!/usr/bin/python3
'''
Created By: Romel
Version: 1.6
Date: 21.09.2023
V1.6: 18.12.2025
Encrypts .zip files in /home/drums/zip/ into .asc in /home/drums/asc/
and archives original zips after success.
Adds max ZIP size limit + logging.
'''
import os
import subprocess
import shutil
import time
from datetime import datetime

ZIP_DIR = '/home/drums/zip/'
ASC_DIR = '/home/drums/asc/'
ARCHIVE_DIR = '/home/drums/archive/'
LOGFILE = '/home/drums/logs/encrypt01.log'

ZIP_MAX_BYTES = 50 * 1024 * 1024  # 50MB
SLEEP_SECONDS = 180

RECIPIENT = 'romel@daikai.com'

def log(msg: str):
    os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} {msg}"
    print(line)
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def encrypt_zip_files():
    if not os.path.exists(ZIP_DIR):
        log(f"[ERROR] ZIP_DIR missing: {ZIP_DIR}")
        return

    os.makedirs(ASC_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    zip_files = [f for f in os.listdir(ZIP_DIR) if f.endswith('.zip')]

    for zip_file in sorted(zip_files):
        zip_path = os.path.join(ZIP_DIR, zip_file)

        # Skip empty
        try:
            size = os.path.getsize(zip_path)
        except FileNotFoundError:
            continue

        if size == 0:
            log(f"[SKIP] Empty zip: {zip_file} (deleting)")
            try:
                os.remove(zip_path)
            except Exception as e:
                log(f"[WARN] Failed delete empty zip {zip_file}: {e}")
            continue

        # Enforce size limit
        if size > ZIP_MAX_BYTES:
            log(f"[REJECT] Zip too large ({size} bytes > 50MB): {zip_file} (moving to archive/rejected)")
            reject_dir = os.path.join(ARCHIVE_DIR, "rejected")
            os.makedirs(reject_dir, exist_ok=True)
            try:
                shutil.move(zip_path, os.path.join(reject_dir, zip_file))
            except Exception as e:
                log(f"[ERROR] Failed to move oversize zip {zip_file}: {e}")
            continue

        asc_file = zip_file + '.asc'
        asc_path = os.path.join(ASC_DIR, asc_file)

        # More predictable automation flags:
        gpg_command = [
            'gpg',
            '--batch', '--yes',
            '--encrypt',
            '--sign',
            '--armor',
            '--trust-model', 'always',
            '-r', RECIPIENT,
            '-o', asc_path,
            zip_path
        ]

        try:
            subprocess.run(gpg_command, check=True)
            log(f"[OK] Encrypted {zip_file} -> {asc_file}")

            # Move original zip to archive
            shutil.move(zip_path, os.path.join(ARCHIVE_DIR, zip_file))
            log(f"[OK] Archived zip: {zip_file}")

        except subprocess.CalledProcessError as e:
            log(f"[FAIL] Encrypt failed for {zip_file}: {e}. Deleting zip to prevent retries.")
            try:
                os.remove(zip_path)
                log(f"[OK] Deleted failed zip: {zip_file}")
            except Exception as delete_error:
                log(f"[ERROR] Failed delete {zip_file}: {delete_error}")

if __name__ == '__main__':
    while True:
        encrypt_zip_files()
        time.sleep(SLEEP_SECONDS)
