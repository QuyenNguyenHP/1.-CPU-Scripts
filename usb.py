#!/usr/bin/python3
# -*- coding: utf-8 -*-

# pymodbus 3.6.8 / python 3.9.2
# USB Handler - Mount, Copy, Unmount, Shutdown via Modbus HMI
# Date: May 31, 2024
# By: Romel Mendoza

import asyncio
import os
import shutil
from pymodbus.client import AsyncModbusTcpClient

# ------------------- Configuration -------------------
HMI_IP      = '192.168.100.14'
HMI_SLAVE   = 0x03
MODBUS_TIMEOUT = 5          # seconds
POLL_INTERVAL  = 5          # seconds between each handler loop

# Paths
USB_MOUNT_PATH = "/mnt/usb"
ASC_SOURCE_DIR = "/home/drums/asc"

# USB devices to scan (in order)
USB_DEVICE_NAMES = ["sda", "sdb", "sdc"]
USB_DEVICE_PATHS = ["/dev/sda1", "/dev/sdb1", "/dev/sdc1"]

# ---- Input Registers (Discrete Inputs - Function 02) ----
#  Modbus register = address + 10001  (e.g. 0x85 + 10001 = 10134)
REG_COPY_BASE       = 0x85   # 10134 — base address for usb_copy_handler read
REG_COPY_REQUEST    = 0x8D   # 10142 — HMI requests file copy to USB

REG_SHUTDOWN_BASE   = 0x89   # 10138 — base address for shutdown_handler read
REG_SHUTDOWN        = 0x8B   # 10140 — shutdown signal  (index 2 from base)
REG_REBOOT          = 0x8C   # 10141 — reboot signal    (index 3 from base)

REG_MOUNT_BASE      = 0x90   # 10145 — base address for mount/unmount handler read
REG_USB_MOUNT       = 0x93   # 10148 — HMI requests USB mount
REG_USB_UNMOUNT     = 0x94   # 10149 — HMI requests USB unmount

# ---- Output Coils (Function 01 write) ----
COIL_IN_OPERATION   = 600    # system in operation
COIL_SHUTTING_DOWN  = 601    # shutdown in progress
COIL_RESTARTING     = 602    # reboot in progress
COIL_USB_MOUNTED    = 604    # USB is mounted
COIL_USB_UNMOUNTED  = 99     # USB is unmounted
COIL_FILE_COPIED    = 102    # file copy confirmation pulse
COIL_USB_ERROR      = 103    # mount / no-USB error
COIL_COPY_ERROR     = 104    # 0x068 — copy error

# -------------------------------------------------------


async def is_usb_connected(device_name):
    """Return True if a block device starting with device_name exists."""
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
    """Mount a USB drive and return True on success."""
    process = await asyncio.create_subprocess_shell(
        f"sudo mount {device_path} {mount_path}"
    )
    await process.communicate()
    return process.returncode == 0


async def is_mounted(device, mount_point):
    """Return True if device is mounted at mount_point."""
    try:
        process = await asyncio.create_subprocess_shell(
            "mount",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            print(f"Error running 'mount': {stderr.decode().strip()}")
            return False
        return f"{device} on {mount_point}" in stdout.decode()
    except Exception as e:
        print(f"Error in is_mounted: {e}")
        return False


async def delete_files_in_directory(directory_path):
    """Delete all files in a directory."""
    try:
        for file in os.listdir(directory_path):
            file_path = os.path.join(directory_path, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        print("All files deleted successfully.")
    except OSError:
        print("Error occurred while deleting files.")


async def copy_asc_files(source_dir, destination_dir, client):
    """Copy all .asc files from source_dir to destination_dir."""
    if not os.path.exists(source_dir):
        print(f"Source directory {source_dir} does not exist.")
        await client.write_coil(COIL_COPY_ERROR, True, slave=HMI_SLAVE)
        await asyncio.sleep(0.5)
        await client.write_coil(COIL_COPY_ERROR, False, slave=HMI_SLAVE)
        return

    os.makedirs(destination_dir, exist_ok=True)

    for file in os.listdir(source_dir):
        if file.endswith('.asc'):
            shutil.copy2(os.path.join(source_dir, file), os.path.join(destination_dir, file))
            print(f"Copied {file} to {destination_dir}.")
            await client.write_coil(COIL_FILE_COPIED, True, slave=HMI_SLAVE)
            await asyncio.sleep(0.5)
            await client.write_coil(COIL_FILE_COPIED, False, slave=HMI_SLAVE)


async def usb_copy_handler(client):
    """Monitor REG_COPY_REQUEST and copy .asc files to USB when triggered."""
    os.makedirs(USB_MOUNT_PATH, exist_ok=True)

    while True:
        try:
            response = await client.read_discrete_inputs(REG_COPY_BASE, 10, slave=HMI_SLAVE)
            if not response.isError():
                copy_request = False
                for i, value in enumerate(response.bits):
                    if (REG_COPY_BASE + i) == REG_COPY_REQUEST:
                        copy_request = value
                        break

                if copy_request:
                    print("Copy Files Requested.")
                    await delete_files_in_directory(USB_MOUNT_PATH)

                    copied = False
                    for device in USB_DEVICE_PATHS:
                        if await is_mounted(device, USB_MOUNT_PATH):
                            print(f"{device} is mounted. Copying files...")
                            await copy_asc_files(ASC_SOURCE_DIR, USB_MOUNT_PATH, client)
                            copied = True
                            break

                    if not copied:
                        print("No USB device mounted — cannot copy.")
                        await client.write_coil(COIL_COPY_ERROR, True, slave=HMI_SLAVE)
                        await asyncio.sleep(0.5)
                        await client.write_coil(COIL_COPY_ERROR, False, slave=HMI_SLAVE)

        except Exception as e:
            print(f"Error in usb_copy_handler: {e}")

        await asyncio.sleep(POLL_INTERVAL)


async def usb_handler(client):
    """Monitor REG_USB_MOUNT and mount the first detected USB device."""
    os.makedirs(USB_MOUNT_PATH, exist_ok=True)

    while True:
        try:
            response = await client.read_discrete_inputs(REG_MOUNT_BASE, 10, slave=HMI_SLAVE)
            if not response.isError():
                usb_mount_signal = False
                for i, value in enumerate(response.bits):
                    if (REG_MOUNT_BASE + i) == REG_USB_MOUNT:
                        usb_mount_signal = value
                        break

                if usb_mount_signal:
                    print("USB Mount Requested.")
                    found = False
                    for device_name in USB_DEVICE_NAMES:
                        if await is_usb_connected(device_name):
                            device_path = f"/dev/{device_name}1"
                            print(f"Found USB device: {device_path}")
                            mount_success = await mount_usb_flash_drive(device_path, USB_MOUNT_PATH)
                            await client.write_coil(COIL_USB_UNMOUNTED, False, slave=HMI_SLAVE)
                            await client.write_coil(COIL_USB_MOUNTED, True, slave=HMI_SLAVE)
                            if not mount_success:
                                print("Failed to mount USB.")
                                await client.write_coil(COIL_USB_ERROR, True, slave=HMI_SLAVE)
                                await asyncio.sleep(0.05)
                                await client.write_coil(COIL_USB_ERROR, False, slave=HMI_SLAVE)
                            else:
                                print(f"USB mounted at {USB_MOUNT_PATH}")
                            found = True
                            break

                    if not found:
                        print("No USB flash drive connected.")
                        await client.write_coil(COIL_USB_ERROR, True, slave=HMI_SLAVE)
                        await asyncio.sleep(0.2)
                        await client.write_coil(COIL_USB_ERROR, False, slave=HMI_SLAVE)

        except Exception as e:
            print(f"Error in usb_handler: {e}")

        await asyncio.sleep(POLL_INTERVAL)


async def unmount_usb_handler(client):
    """Monitor REG_USB_UNMOUNT and unmount USB when triggered."""
    while True:
        try:
            response = await client.read_discrete_inputs(REG_MOUNT_BASE, 10, slave=HMI_SLAVE)
            if response.isError():
                print("Modbus Error: F02 input USB UNMOUNT", response)
                await asyncio.sleep(POLL_INTERVAL)
                continue

            unmount_request = False
            for i, value in enumerate(response.bits):
                if (REG_MOUNT_BASE + i) == REG_USB_UNMOUNT:
                    unmount_request = value
                    break

            if unmount_request:
                print("Unmount USB Requested.")
                process = await asyncio.create_subprocess_shell(
                    f"sudo umount -l {USB_MOUNT_PATH}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    print(f"Successfully unmounted {USB_MOUNT_PATH}.")
                    await client.write_coil(COIL_USB_UNMOUNTED, True, slave=HMI_SLAVE)
                    await client.write_coil(COIL_USB_MOUNTED, False, slave=HMI_SLAVE)
                else:
                    print(f"Failed to unmount {USB_MOUNT_PATH}: {stderr.decode()}")

        except Exception as e:
            print(f"Error in unmount_usb_handler: {e}")

        await asyncio.sleep(POLL_INTERVAL)


async def shutdown_handler(client):
    """Monitor REG_SHUTDOWN / REG_REBOOT and act accordingly."""
    while True:
        try:
            response = await client.read_discrete_inputs(REG_SHUTDOWN_BASE, 10, slave=HMI_SLAVE)
            if not response.isError():
                shutdown_signal = response.bits[REG_SHUTDOWN - REG_SHUTDOWN_BASE] if len(response.bits) > (REG_SHUTDOWN - REG_SHUTDOWN_BASE) else False
                reboot_signal   = response.bits[REG_REBOOT   - REG_SHUTDOWN_BASE] if len(response.bits) > (REG_REBOOT   - REG_SHUTDOWN_BASE) else False

                if shutdown_signal:
                    print("Shutting Down System...")
                    await client.write_coil(COIL_SHUTTING_DOWN, True, slave=HMI_SLAVE)
                    await client.write_coil(COIL_IN_OPERATION, False, slave=HMI_SLAVE)
                    await asyncio.sleep(1)
                    await asyncio.create_subprocess_shell("sudo shutdown -h now")
                    return

                if reboot_signal:
                    print("Rebooting System...")
                    await client.write_coil(COIL_RESTARTING, True, slave=HMI_SLAVE)
                    await client.write_coil(COIL_IN_OPERATION, False, slave=HMI_SLAVE)
                    await asyncio.sleep(1)
                    await asyncio.create_subprocess_shell("sudo reboot")
                    return

        except Exception:
            pass

        await asyncio.sleep(POLL_INTERVAL)


async def connect_client(client, address):
    while not client.connected:
        print(f"Attempting to connect to {address}...")
        await client.connect()
        if client.connected:
            print(f"Connected to {address}")
            return client
        await asyncio.sleep(0.5)


async def monitor_connection(client, address):
    while True:
        if not client.connected:
            print(f"Lost connection to {address}, reconnecting...")
            await connect_client(client, address)
        await asyncio.sleep(0.1)


async def main():
    while True:
        try:
            client = AsyncModbusTcpClient(HMI_IP, timeout=MODBUS_TIMEOUT)
            await connect_client(client, HMI_IP)
            asyncio.create_task(monitor_connection(client, HMI_IP))

            await asyncio.gather(
                usb_handler(client),
                usb_copy_handler(client),
                unmount_usb_handler(client),
                shutdown_handler(client),
            )
        except Exception as e:
            print(f"Error in main: {e}")
        finally:
            print("Closing client...")
            await client.close()
            print("Client closed. Restarting...")


if __name__ == "__main__":
    asyncio.run(main())
