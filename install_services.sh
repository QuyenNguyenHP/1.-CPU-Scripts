#!/bin/bash

set -e

SYSTEMD_DIR="/etc/systemd/system"

echo "=== Creating systemd service files ==="

# modbus.service
cat > "$SYSTEMD_DIR/modbus.service" <<EOF
[Unit]
Description=Modbus

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/drums/scripts/modbus.py
Restart=always

[Install]
WantedBy=default.target
EOF

# zip_csv_files.service
cat > "$SYSTEMD_DIR/zip_csv_files.service" <<EOF
[Unit]
Description=Zip CSV File

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/drums/scripts/zip_csv_files.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

# encrypt.service
cat > "$SYSTEMD_DIR/encrypt.service" <<EOF
[Unit]
Description=Encrypt Zip Files

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/drums/scripts/encrypt_zip_file.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

# send_asc_scp.service
cat > "$SYSTEMD_DIR/send_asc_scp.service" <<EOF
[Unit]
Description=Send ASC Files Service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/drums/scripts/send_asc_scp.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

# pulse.service
cat > "$SYSTEMD_DIR/pulse.service" <<EOF
[Unit]
Description=Pulse

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/drums/scripts/pulse.py
Restart=always

[Install]
WantedBy=default.target
EOF

# hmi.service
cat > "$SYSTEMD_DIR/hmi.service" <<EOF
[Unit]
Description=HMI to DGS

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/drums/scripts/hmi_to_dgs.py
Restart=always

[Install]
WantedBy=default.target
EOF

# photo.service
cat > "$SYSTEMD_DIR/photo.service" <<EOF
[Unit]
Description=Perimeter_Breach01

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/drums/scripts/photo_capture.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

# autossh-tunnel.service
cat > "$SYSTEMD_DIR/autossh-tunnel.service" <<EOF
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
EOF

echo "=== Reloading systemd daemon ==="
systemctl daemon-reload

SERVICES=(
    modbus.service
    zip_csv_files.service
    encrypt.service
    send_asc_scp.service
    pulse.service
    hmi.service
    photo.service
    autossh-tunnel.service
)

echo "=== Enabling and starting services ==="
for SERVICE in "${SERVICES[@]}"; do
    echo "  -> $SERVICE"
    systemctl enable "$SERVICE"
    systemctl start "$SERVICE"
done

echo ""
echo "=== Service Status ==="
for SERVICE in "${SERVICES[@]}"; do
    STATUS=$(systemctl is-active "$SERVICE")
    echo "  $SERVICE: $STATUS"
done

echo ""
echo "Done."
