#!/usr/bin/python3
'''
Created By: Romel
Version: 2.21
Date: 19.09.2023
v2.21: 18.12.2025
Zips CSV files from /home/drums/csv/ into /home/drums/zip/
with a max ZIP size limit (default 50MB).
'''
import os
import zipfile
from datetime import datetime
import time

csv_dir = '/home/drums/csv/'
zip_dir = '/home/drums/zip/'
os.makedirs(zip_dir, exist_ok=True)

ZIP_MAX_BYTES = 50 * 1024 * 1024  # 50MB
SLEEP_SECONDS = 180

def zip_and_delete_csv_files():
    timestamp = datetime.now().strftime("%m-%d-%Y-%H-%M-%S")
    zip_filename = os.path.join(zip_dir, f'H429-{timestamp}.zip')

    csv_files = [f for f in os.listdir(csv_dir) if f.endswith('.csv')]
    if not csv_files:
        print('No CSV files found. Doing nothing.')
        return

    files_added = 0
    bytes_estimated = 0  # estimate using source file sizes (good enough for limit control)

    with zipfile.ZipFile(zip_filename, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
        for file in sorted(csv_files):
            file_path = os.path.join(csv_dir, file)

            # Skip non-existent
            if not os.path.exists(file_path):
                continue

            # Delete empty files
            if os.path.getsize(file_path) == 0:
                try:
                    os.remove(file_path)
                    print(f'Deleted empty file: {file}')
                except Exception as e:
                    print(f"Error deleting {file}: {e}")
                continue

            file_size = os.path.getsize(file_path)

            # If adding this file will exceed limit, stop
            if bytes_estimated + file_size > ZIP_MAX_BYTES:
                print(f"[LIMIT] Reached ~50MB limit. Stopping zip creation: {zip_filename}")
                break

            try:
                zipf.write(file_path, arcname=file)
                bytes_estimated += file_size
                files_added += 1
                print(f'Added {file} ({file_size} bytes) to {zip_filename}')
                os.remove(file_path)
                print(f'Deleted {file} after zipping')
            except Exception as e:
                print(f"Error processing {file}: {e}")

    # If nothing added, remove empty zip
    if files_added == 0:
        try:
            os.remove(zip_filename)
        except FileNotFoundError:
            pass
        print('No non-empty CSV files zipped. No zip created.')
    else:
        # Optional: verify zip is readable
        try:
            with zipfile.ZipFile(zip_filename, 'r') as z:
                bad = z.testzip()
                if bad is not None:
                    print(f"[WARN] ZIP integrity test failed on file: {bad}. Deleting zip.")
                    os.remove(zip_filename)
        except Exception as e:
            print(f"[WARN] ZIP integrity check failed: {e}. Deleting zip.")
            try:
                os.remove(zip_filename)
            except Exception:
                pass
        else:
            print(f'Created zip file: {zip_filename} (estimated bytes added={bytes_estimated})')

while True:
    zip_and_delete_csv_files()
    time.sleep(SLEEP_SECONDS)
