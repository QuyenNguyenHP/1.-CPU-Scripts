# Systemd Services Setup

## modbus.service

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

## zip.service

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

## encryptzip.service

```bash
sudo nano /etc/systemd/system/encrypt.service
```

```ini
[Unit]
Description=Encrypt Zip Files

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/drums/scripts/encrypt_zip.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

---

## send_asc_scp.service

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

## pulse.service

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

## hmi.service

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

## photo.service

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

## Install All Services (Automated)

Copy `install_services.sh` to the device, then run:

```bash
chmod +x install_services.sh
sudo ./install_services.sh
```

The script will write all service files, reload systemd, and enable + start every service automatically.

---

## Enable & Start All Services

After creating each service file, run the following to reload systemd and enable/start each service:

```bash
sudo systemctl daemon-reload

sudo systemctl enable modbus.service
sudo systemctl start modbus.service

sudo systemctl enable zip_csv_files.service
sudo systemctl start zip_csv_files.service

sudo systemctl enable encrypt.service
sudo systemctl start encrypt.service

sudo systemctl enable send_asc_scp.service
sudo systemctl start send_asc_scp.service

sudo systemctl enable pulse.service
sudo systemctl start pulse.service

sudo systemctl enable hmi.service
sudo systemctl start hmi.service

sudo systemctl enable photo.service
sudo systemctl start photo.service
```

## Check Service Status

```bash
sudo systemctl status modbus.service
sudo systemctl status zip_csv_files.service
sudo systemctl status encrypt.service
sudo systemctl status send_asc_scp.service
sudo systemctl status pulse.service
sudo systemctl status hmi.service
sudo systemctl status photo.service
```

## View Latest 100 Logs (journalctl)

```bash
journalctl -u modbus.service -n 100
journalctl -u zip_csv_files.service -n 100
journalctl -u encrypt.service -n 100
journalctl -u send_asc_scp.service -n 100
journalctl -u pulse.service -n 100
journalctl -u hmi.service -n 100
journalctl -u photo.service -n 100
```

> Add `-f` to follow logs in real time:
> ```bash
> journalctl -u modbus.service -n 100 -f
> ```
