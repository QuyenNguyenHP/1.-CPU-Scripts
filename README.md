# 🥁 DRUMS CPU Configuration Tutorial

---

## 🚢 Project Information

| Field                    | Details                                           |
| ------------------------ | ------------------------------------------------- |
| 🏭 Customer              | Dongbac Shipbuilding Industry Joint Stock Company |
| 🔖 Shipyard Code         | DEC-EMVN879AO                                     |
| 🛳️ Hull No.            | DB45-02                                           |
| 🆔 IMO No.               | 9976991                                           |
| 📐 Project Name          | 45,000 DWT Bulk Carrier                           |
| ⚓ Vessel Name           | Truong Minh Dream 06                              |
| 🔧 Equipment             | Daihatsu 6DE-18 × 3                              |
| 🔩 Engine Serial Numbers | DE618Z4755 / DE618Z4756 / DE618Z4757              |

---

## 📋 Table of Contents

1. [🖥️ OS Install &amp; Base Setup](#1-os-install--base-setup)
2. [⚡ CPU Performance Mode](#2-cpu-performance-mode)
3. [🔐 SSH Hardening (Key-Only Login)](#3-ssh-hardening-key-only-login)
4. [🔑 GPG Key Import](#4-gpg-key-import)
5. [🔒 Zymbit Configuration](#5-zymbit-configuration)
6. [🔗 SSH Key Setup (Pi → VM)](#6-ssh-key-setup-pi--vm)
7. [📁 Create Folders &amp; Scripts](#7-create-folders--scripts)
8. [⚙️ Systemd Services](#8-systemd-services)
9. [🛡️ Firewall (UFW)](#9-firewall-ufw)
10. [🚫 Fail2Ban](#10-fail2ban)
11. [🌐 Static IP](#11-static-ip)
12. [📡 Remote.IT Setup](#12-remoteit-setup)

---

## 1. 🖥️ OS Install & Base Setup

### 1.1 Install Raspberry Pi OS

- **OS:** Debian 11 Bullseye (32-bit)
- **Download:** [raspios_oldstable_armhf-2024-10-28](https://downloads.raspberrypi.org/raspios_oldstable_armhf/images/raspios_oldstable_armhf-2024-10-28/)
- ✅ Enable **I2C** and configure **Wi-Fi / hostname** during setup
- ✅ Boot into **CLI mode** (no desktop)

### 1.2 Disable 64-bit Mode

```bash
sudo nano /boot/config.txt
```

Add the following line:

```
arm_64bit=0
```

💾 Save and reboot.

### 1.3 Update & Install Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install curl autossh -y
sudo pip3 install schedule
sudo pip3 install watchdog
sudo pip3 install pymodbus==3.6.8
```

> ⚠️ `pymodbus` must be version **3.6.8** — other versions may be incompatible.

---

## 2. ⚡ CPU Performance Mode

Setting the CPU governor to `performance` keeps the CPU at maximum frequency, ensuring stable communication with ZYMKEY.

### Step 1 — Create the service file

```bash
sudo nano /etc/systemd/system/cpu-governor.service
```

Paste the following:

```ini
[Unit]
Description=Set scaling governor to performance
After=multi-user.target
Before=zkbootrtc.service

[Service]
Type=oneshot
ExecStart=/bin/sh -c "echo performance > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor"

[Install]
WantedBy=multi-user.target
```

### Step 2 — Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable cpu-governor.service
sudo systemctl start cpu-governor.service
```

### Step 3 — ✅ Verify

```bash
# Should show: active (exited)
sudo systemctl status cpu-governor.service

# Should return: performance
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
```

---

## 3. 🔐 SSH Hardening (Key-Only Login)

### Step 1 — Create `.ssh` directory (if it doesn't exist)

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### Step 2 — Add authorized public keys

```bash
sudo nano ~/.ssh/authorized_keys
# 📋 Paste each user's public key on a new line
```

### Step 3 — Disable password authentication

```bash
sudo nano /etc/ssh/sshd_config
```

Find and set the following values:

```
PasswordAuthentication no
ChallengeResponseAuthentication no
UsePAM no
PubkeyAuthentication yes
```

### Step 4 — Restart SSH

```bash
sudo systemctl restart ssh
```

---

## 4. 🔑 GPG Key Import

Used by `encrypt_zip.py` to encrypt `.zip` files into `.asc` format.

### Import public key 🔓

```bash
gpg --import romel-public.key
```

### Import private key 🔒 (as root)

```bash
sudo gpg --import romel-private.key
```

### ✅ Verify

```bash
sudo gpg --list-secret-keys
```

---

## 5. 🔒 Zymbit Configuration

📖 Reference: [https://docs.zymbit.com/getting-started/zymkey4/quickstart](https://docs.zymbit.com/getting-started/zymkey4/quickstart/)

### Step 1 — 🔌 Hardware installation

1. Power off the Pi
2. Install the Zymkey hardware
3. Power on the Pi

### Step 2 — Enable I2C

```bash
sudo raspi-config
# Navigate to: Interface Options > I2C > Enable

# ✅ Verify I2C is enabled:
ls /dev/i2c-1
```

### Step 3 — Install Zymbit software

```bash
curl -G https://s3.amazonaws.com/zk-sw-repo/install_zk_sw.sh | sudo bash
```

### Step 4 — 🧪 Test installation

```bash
python3 /usr/local/share/zymkey/examples/zk_crypto_test.py
```

✅ If the script runs successfully, Zymkey 4 encryption is working correctly.

### Step 5 — 💾 Encrypt the filesystem on USB

> ⚠️ **Note:** The first run on a new USB drive can take a long time. **Two reboots** are required before the script completes.

🔌 Plug in the USB drive (format: exFAT or FAT32), then verify it is detected:

```bash
lsblk -f
```

Disable unattended upgrades before proceeding:

```bash
sudo systemctl stop unattended-upgrades
sudo systemctl disable unattended-upgrades
sudo apt remove unattended-upgrades -y
```

Run the encryption script:

```bash
curl -G https://s3.amazonaws.com/zk-sw-repo/mk_encr_sd_rfs.sh | sudo bash
```

✅ Verify after reboot:

```bash
df
```

---

## 6. 🔗 SSH Key Setup (Pi → VM)

This allows the Pi to authenticate to remote VMs without a password (required for `send_asc_scp.py`).

### 🥧 On the Pi — Generate key pairs

```bash
# drums user keypair
ssh-keygen -t rsa -b 4096
cat /home/drums/.ssh/id_rsa.pub

# root keypair
sudo ssh-keygen -t rsa -b 4096
sudo cat /root/.ssh/id_rsa.pub
```

### 🖥️ On the VM — Add Pi's public key

```bash
# Connect to VM
ssh opc@213.35.115.98    # VM01
# or
ssh opc@129.150.37.135   # VM02

# 📋 Add the Pi's public key
sudo nano ~/.ssh/authorized_keys
# Paste the public key from the Pi
```

---

## 7. 📁 Create Folders & Scripts

### Create working directories

```bash
mkdir -p /home/drums/asc \
         /home/drums/zip \
         /home/drums/csv \
         /home/drums/archive \
         /home/drums/scripts \
         /home/drums/logs \
         /home/drums/breach_photos
```

### 📝 Scripts checklist

| Script                | Status      |
| --------------------- | ----------- |
| `pulse.py`          | ✅ Required |
| `modbus.py`         | ✅ Required |
| `zip_csv_files.py`  | ✅ Required |
| `encrypt_zip.py`    | ✅ Required |
| `send_asc_scp.py`   | ✅ Required |
| `hmi_to_dgs.py`     | ✅ Required |
| `photo_capture.py`  | ✅ Required |
| `send_photo_scp.py` | 🔲 Optional |
| `modbus_to_HMI.py`  | 🔲 Optional |

📂 Copy all scripts to `/home/drums/scripts/`.

---

## 8. ⚙️ Systemd Services

### 8.1 Create service files

#### 📊 modbus.service

```bash
sudo nano /etc/systemd/system/modbus.service
```

```ini
[Unit]
Description=Modbus

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/drums/scripts/modbus.py
Restart=always

[Install]
WantedBy=default.target
```

---

#### 🗜️ zip_csv_files.service

```bash
sudo nano /etc/systemd/system/zip_csv_files.service
```

```ini
[Unit]
Description=Zip CSV File

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/drums/scripts/zip_csv_files.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

---

#### 🔐 encrypt.service

```bash
sudo nano /etc/systemd/system/encrypt.service
```

```ini
[Unit]
Description=Encrypt Zip Files

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/drums/scripts/encrypt_zip_file.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

---

#### 📤 send_asc_scp.service

```bash
sudo nano /etc/systemd/system/send_asc_scp.service
```

```ini
[Unit]
Description=Send ASC Files Service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/drums/scripts/send_asc_scp.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

---

#### 💓 pulse.service

```bash
sudo nano /etc/systemd/system/pulse.service
```

```ini
[Unit]
Description=Pulse

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/drums/scripts/pulse.py
Restart=always

[Install]
WantedBy=default.target
```

---

#### 🖥️ hmi.service

```bash
sudo nano /etc/systemd/system/hmi.service
```

```ini
[Unit]
Description=HMI to DGS

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/drums/scripts/hmi_to_dgs.py
Restart=always

[Install]
WantedBy=default.target
```

---

#### 📷 photo.service

```bash
sudo nano /etc/systemd/system/photo.service
```

```ini
[Unit]
Description=Perimeter_Breach01

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/drums/scripts/photo_capture.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

---

#### 🚇 autossh-tunnel.service

```bash
sudo nano /etc/systemd/system/autossh-tunnel.service
```

```ini
[Unit]
Description=AutoSSH tunnel service
After=network.target

[Service]
User=drums
ExecStart=/usr/bin/autossh -M 20000 -N -R 19999:localhost:22 daikai@146.190.88.223
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

### 8.2 🤖 Automated Install (Recommended)

Copy `install_services.sh` to the device, then run:

```bash
chmod +x install_services.sh
sudo ./install_services.sh
```

The script writes all service files, reloads systemd, and enables + starts every service automatically.

---

### 8.3 🚀 Manual: Reload, enable, and start all services

```bash
sudo systemctl daemon-reload

sudo systemctl enable modbus.service zip_csv_files.service encrypt.service \
    send_asc_scp.service pulse.service hmi.service photo.service autossh-tunnel.service

sudo systemctl start modbus.service zip_csv_files.service encrypt.service \
    send_asc_scp.service pulse.service hmi.service photo.service autossh-tunnel.service
```

### 8.4 ✅ Check all service statuses

```bash
sudo systemctl status modbus.service
sudo systemctl status zip_csv_files.service
sudo systemctl status encrypt.service
sudo systemctl status send_asc_scp.service
sudo systemctl status pulse.service
sudo systemctl status hmi.service
sudo systemctl status photo.service
sudo systemctl status autossh-tunnel.service
```

### 8.5 📋 View latest 100 logs

```bash
journalctl -u modbus.service -n 100
journalctl -u zip_csv_files.service -n 100
journalctl -u encrypt.service -n 100
journalctl -u send_asc_scp.service -n 100
journalctl -u pulse.service -n 100
journalctl -u hmi.service -n 100
journalctl -u photo.service -n 100
journalctl -u autossh-tunnel.service -n 100
```

> 💡 Add `-f` to follow logs in real time, e.g. `journalctl -u modbus.service -n 100 -f`

---

## 9. 🛡️ Firewall (UFW)

### Step 1 — Install UFW

```bash
sudo apt install ufw -y
```

### Step 2 — Set port limits

```bash
sudo ufw limit 22/tcp    # 🔐 SSH — rate-limit to prevent brute force
sudo ufw limit 443/tcp   # 🌐 HTTPS
```

### Step 3 — Enable firewall

```bash
sudo ufw enable
```

### Step 4 — ✅ Check status

```bash
sudo ufw status
```

---

## 10. 🚫 Fail2Ban

Fail2Ban blocks IP addresses that have too many failed SSH login attempts.

### Step 1 — Install

```bash
sudo apt install fail2ban -y
```

### Step 2 — Create local config

```bash
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
```

### Step 3 — Configure SSH jail

```bash
sudo nano /etc/fail2ban/jail.local
```

Find and set:

```
bantime  = 600
findtime = 600
maxretry = 3
```

### Step 4 — Restart Fail2Ban

```bash
sudo service fail2ban restart
```

### Step 5 — ✅ Verify

```bash
# Check overall status
sudo fail2ban-client status

# Check SSH jail specifically
sudo fail2ban-client status sshd
```

---

## 11. 🌐 Static IP

### Step 1 — Edit DHCP config

```bash
sudo nano /etc/dhcpcd.conf
```

Add the following at the end of the file:

```
interface eth0
static ip_address=192.168.100.10/24
metric 200

interface eth1
metric 100
```

### Step 2 — Apply changes

```bash
sudo systemctl restart dhcpcd
```

### Step 3 — ✅ Verify

```bash
ip addr show eth0
```

---

## 12. 📡 Remote.IT Setup

### Method 1 — 📦 Package install

```bash
sudo dpkg -i /tmp/remoteit.deb
```

This generates a **claim code**. Copy it and paste it into the Remote.IT dashboard to register the device.

### Method 2 — 🖱️ Dashboard claim

Log in to [remote.it](https://remote.it), go to **Add Device**, and follow the on-screen instructions for Raspberry Pi.
