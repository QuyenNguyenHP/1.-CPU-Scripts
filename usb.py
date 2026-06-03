#!/usr/bin/python3
# -*- coding: utf-8 -*-

# pymodbus 3.6.8 / python 3.9.2
# Modbus - Multiple register query (Function 02 and Function 04)
# Client3 - HMI Panel addresses are offset by -1, Slave ID: 03
# Date: May 31, 2024
# By: Romel Mendoza


import asyncio
import logging
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.exceptions import ModbusIOException
from time import strftime
import datetime
#import schedule  # For scheduling tasks like data logging
import threading

import os
import shutil
import random

# Global storage for DG#1 Repose values
TP_VALUES = {}


async def is_usb_connected(device_name):
    """Check if a USB device is connected asynchronously."""
    try:
        process = await asyncio.create_subprocess_shell(
            "lsblk -o NAME --json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            print(f"Error running 'lsblk': {stderr.decode()}")
            return False
        devices = eval(stdout.decode())["blockdevices"]
        return any(device["name"].startswith(device_name) for device in devices)
    except Exception as e:
        print(f"Error in is_usb_connected: {e}")
        return False

async def mount_usb_flash_drive(device_path, mount_path):
    """Mount a USB drive asynchronously."""
    cmd = f"sudo mount {device_path} {mount_path}"
    process = await asyncio.create_subprocess_shell(cmd)
    await process.communicate()
    return process.returncode == 0

async def is_mounted(device, mount_point):
    """Check if a device is mounted at the specified mount point asynchronously."""
    try:
        process = await asyncio.create_subprocess_shell(
            "mount",  # Run the 'mount' command to get a list of mounted filesystems
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            print(f"Error running 'mount' command: {stderr.decode().strip()}")
            return False

        # Check if the specified device and mount point exist in the 'mount' output
        return f"{device} on {mount_point}" in stdout.decode()

    except Exception as e:
        print(f"Error in is_mounted: {e}")
        return False


async def delete_files_in_directory(directory_path):
    """Delete all files in a directory asynchronously."""
    try:
        files = os.listdir(directory_path)
        for file in files:
            file_path = os.path.join(directory_path, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        print("All files deleted successfully.")
    except OSError:
        print("Error occurred while deleting files.")

async def copy_asc_files(source_dir, destination_dir, client3):
    """Copy all `.asc` files asynchronously."""
    if not os.path.exists(source_dir):
        print(f"Source directory {source_dir} does not exist.")
        await client3.write_coil(104, True, slave=0x03)  # Error copying
        await asyncio.sleep(0.5)
        await client3.write_coil(104, False, slave=0x03)
        return

    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)

    for file in os.listdir(source_dir):
        if file.endswith('.asc'):
            src = os.path.join(source_dir, file)
            dst = os.path.join(destination_dir, file)
            shutil.copy2(src, dst)
            print(f"Copied {file} to {destination_dir}.")
            await client3.write_coil(102, True, slave=0x03)
            await asyncio.sleep(0.5)
            await client3.write_coil(102, False, slave=0x03)

async def usb_copy_handler(client3):
    """Monitor and handle USB file copy requests asynchronously."""
    usb_mount_path = "/mnt/usb"
    os.makedirs(usb_mount_path, exist_ok=True)
    device_list = ["/dev/sda1", "/dev/sdb1", "/dev/sdc1"]

    while True:
        try:
            response = await client3.read_discrete_inputs(0x85, 10, slave=0x03)
            if response.isError():
                pass  # Continue without blocking

            input_readings = response.bits  # Extract boolean values

            # Match the correct Modbus register address (0x8D = 10142)
            copy_request = False
            for i, value in enumerate(input_readings):
                register_address = 0x85 + i
                if register_address == 0x8D:  # If Modbus register 10142 is triggered
                    copy_request = value
                    break  # Stop looping once we find the match

            if copy_request:  # If 10142 is True (Copy Files Request)
                print("Copy Files Requested.")

                # Delete existing files in USB directory
                await delete_files_in_directory(usb_mount_path)

                # Check if USB is mounted and perform copy
                for device in device_list:
                    if await is_mounted(device, usb_mount_path):
                        print(f"{device} is mounted on {usb_mount_path}. Copying files...")
                        await copy_asc_files("/home/drums/asc", usb_mount_path, client3)
                        break  # Stop checking once a valid device is found
                    else:
                        print(f"{device} is not mounted on {usb_mount_path}.")
                        await client3.write_coil(104, True, slave=0x03)
                        await asyncio.sleep(0.5)
                        await client3.write_coil(104, False, slave=0x03)

        except Exception as e:
            print(f"Error in usb_copy_handler: {e}")

        await asyncio.sleep(5)  # Reduce polling frequency

async def usb_handler(client3):
    """Monitor and handle USB mount requests asynchronously."""
    usb_mount_path = "/mnt/usb"
    usb_device_names = ["sda", "sdb", "sdc"]
    os.makedirs(usb_mount_path, exist_ok=True)

    while True:
        try:
            response = await client3.read_discrete_inputs(0x90, 10, slave=0x03)
            if response.isError():
                pass  # Avoid blocking if there's an error

            input_readings = response.bits  # Extract boolean values

            # Correctly map Modbus register address (0x93 = 10148)
            usb_mount_signal = False
            for i, value in enumerate(input_readings):
                register_address = 0x90 + i
                if register_address == 0x93:  # If Modbus register 10148 is triggered
                    usb_mount_signal = value
                    break  # Stop looping once we find the match

            if usb_mount_signal:  # If 10148 is True (USB Mount Request)
                print("USB Mount Requested.")

                # Randomly select a USB device name
                random_device_name = random.choice(usb_device_names)

                # Check if the USB flash drive is connected
                if await is_usb_connected(random_device_name):
                    usb_device_path = f"/dev/{random_device_name}1"

                    # Try to mount USB
                    mount_success = await mount_usb_flash_drive(usb_device_path, usb_mount_path)

                    # Update Modbus HMI status
                    await client3.write_coil(99, False, slave=0x03)  # Remove unmounted message
                    await client3.write_coil(98, True, slave=0x03)   # Give mounted message

                    if not mount_success:
                        print("Failed to mount USB flash drive.")
                        await client3.write_coil(103, True, slave=0x03)
                        await asyncio.sleep(0.05)
                        await client3.write_coil(103, False, slave=0x03)
                    else:
                        print(f"USB mounted at {usb_mount_path}")

                else:
                    print("No USB flash drive connected.")
                    await client3.write_coil(103, True, slave=0x03)
                    await asyncio.sleep(0.2)
                    await client3.write_coil(103, False, slave=0x03)

        except Exception as e:
            print(f"Error in usb_handler: {e}")

        await asyncio.sleep(5)  # Reduce polling frequency

async def unmount_usb_handler(client3):
    """Monitor and handle USB unmount requests asynchronously."""
    mount_point = "/mnt/usb"

    while True:
        try:
            response = await client3.read_discrete_inputs(0x90, 10, slave=0x03)
            if response.isError():
                print("Modbus Error: F02 input USB UMOUNT", response)
                continue

            input_readings = response.bits  # Extract boolean values

            # Check for the specific register (0x94 = 10149)
            unmount_request = False
            for i, value in enumerate(input_readings):
                register_address = 0x90 + i
                if register_address == 0x94:  # If Modbus register 10149 is triggered
                    unmount_request = value
                    break  # Stop looping once we find the match

            if unmount_request:  # If 10149 is True (Unmount Request)
                print("Unmount USB Requested.")

                # Perform the unmount operation
                cmd = f"sudo umount -l {mount_point}"
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    print(f"Successfully unmounted {mount_point}.")
                    await client3.write_coil(99, True, slave=0x03)  # Indicate unmounted
                    await client3.write_coil(98, False, slave=0x03)  # Clear mounted status
                else:
                    print(f"Failed to unmount {mount_point}: {stderr.decode()}")

        except Exception as e:
            print(f"Error in unmount_usb_handler: {e}")

        await asyncio.sleep(5)  # Reduce polling frequency

async def shutdown_handler(client3):
    """Monitor and handle system shutdown/reboot actions asynchronously."""
    while True:
        try:
            response = await client3.read_discrete_inputs(0x89, 10, slave=0x03)
            if response.isError():
                pass  # Continue without blocking if Modbus read fails

            input_readings = response.bits  # Extract boolean values

            # Match the correct Modbus registers for shutdown and reboot
            shutdown_signal = input_readings[2] if len(input_readings) > 2 else False  # 0x8B (Shutdown)
            reboot_signal = input_readings[3] if len(input_readings) > 3 else False  # 0x8C (Reboot)

            if shutdown_signal:
                print("Shutting Down System...")
                await client3.write_coil(601, True, slave=0x03)  # Show shutdown message
                await client3.write_coil(600, False, slave=0x03)  # Remove "In Operation" status
                await asyncio.sleep(1)
                os.system("sudo shutdown -h now")
                return  # Stop async loop after shutdown command

            if reboot_signal:
                print("Rebooting System...")
                await client3.write_coil(602, True, slave=0x03)  # Show restart message
                await client3.write_coil(600, False, slave=0x03)  # Remove "In Operation" status
                await asyncio.sleep(1)
                os.system("sudo reboot")
                return  # Stop async loop after reboot command

        except Exception:
            pass  # Continue loop without blocking

        await asyncio.sleep(5)  # Reduce frequency of checking to prevent delays

async def connect_client(client, address):
    """Connects to the Modbus client and ensures reconnection when disconnected."""
    while not client.connected:
        print(f"Attempting to connect to {address}...")
        await client.connect()
        if client.connected:
            print(f"Connected to {address}")
            return client
        await asyncio.sleep(0.5)  # Short delay to avoid excessive CPU usage

async def monitor_connection(client, address):
    """Monitors the client connection and reconnects if lost."""
    while True:
        if not client.connected:
            print(f"Lost connection to {address}, reconnecting...")
            await connect_client(client, address)
        await asyncio.sleep(0.1)  # Allow frequent reconnection checks
        
async def main():

    """Main function that initializes Modbus and starts tasks."""
    while True:

        try:
            client3 = AsyncModbusTcpClient('192.168.100.14', timeout=5)
            # Ensure both clients connect before starting tasks
            await asyncio.gather(
                connect_client(client3, '192.168.100.14'),
            )

            # Start a background task to monitor connection status
            asyncio.create_task(monitor_connection(client3, '192.168.100.14'))
            # Run the initialization function **only once** before entering the main loop
            # Run all tasks concurrently with actual client objects
            await asyncio.gather(
                usb_handler(client3),  # Handles USB mounting
                usb_copy_handler(client3),  # Handles file copy requests
                unmount_usb_handler(client3), # Handles USB unmount
                shutdown_handler(client3) # Handles shutdown and reboot
            )
        except Exception as e:
            print(f"Error in main: {e}")
        finally:
            # Ensure clients are closed properly
            print("Closing clients...")
            await asyncio.gather(
                client3.close()
            )
            print("Clients closed. Restarting immediately.")

if __name__ == "__main__":
    asyncio.run(main())
