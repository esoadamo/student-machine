"""Cloud-init configuration for Debian with XFCE desktop."""

import time
from typing import Optional


def get_user_data(locale: str = "en_US.UTF-8", keyboard: str = "us") -> str:
    """
    Generate cloud-init user-data for Debian with XFCE desktop.
    
    Args:
        locale: System locale (e.g., 'en_US.UTF-8', 'cs_CZ.UTF-8')
        keyboard: Keyboard layout (e.g., 'us', 'cz')
    
    Returns:
        Cloud-init user-data configuration.
    """
    # Extract language code for keyboard variant detection
    lang_code = locale.split("_")[0] if "_" in locale else locale.split(".")[0]
    
    return f"""#cloud-config
hostname: student-vm
fqdn: student-vm.local

# Locale and keyboard configuration
locale: {locale}
keyboard:
  layout: {keyboard}

users:
  - name: student
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    lock_passwd: false
    groups: [sudo, docker, audio, video, plugdev, netdev]

# Set password for student user
chpasswd:
  expire: false
  users:
    - name: student
      password: student
      type: text

# Install packages
packages:
  # Core system
  - curl
  - wget
  - git
  - htop
  - btop
  - nano
  - vim
  - openssh-server
  - locales
  
  # Terminal multiplexers
  - screen
  - byobu
  - tmux
  
  # XFCE Desktop Environment
  - xfce4
  - xfce4-goodies
  - lightdm
  - lightdm-gtk-greeter
  - xorg
  
  # Desktop applications
  - firefox-esr
  - thunar
  - xfce4-terminal
  - mousepad
  - thonny
  - kate
  
  # Development tools
  - build-essential
  - python3
  - python3-pip
  - python3-venv
  - python3-pytest
  - python3-flake8
  - pylint
  - nodejs
  - npm
  
  # Database
  - sqlite3
  
  # HTTP tools
  - httpie
  
  # Docker
  - docker.io
  - docker-compose
  
  # Flatpak
  - flatpak

# Grow root partition to use full disk
growpart:
  mode: auto
  devices: ["/"]

# System configuration files
write_files:
  # LightDM autologin configuration
  - path: /etc/lightdm/lightdm.conf
    content: |
      [Seat:*]
      autologin-user=student
      autologin-user-timeout=0
      user-session=xfce
      greeter-session=lightdm-gtk-greeter
    permissions: '0644'
  
  # Script to fix autologin after XFCE is installed
  - path: /usr/local/bin/fix-autologin.sh
    permissions: '0755'
    content: |
      #!/bin/bash
      # Find the actual XFCE session file name
      SESSION="xfce"
      for f in /usr/share/xsessions/xfce*.desktop; do
        if [ -f "$f" ]; then
          SESSION=$(basename "$f" .desktop)
          break
        fi
      done
      
      echo "Configuring LightDM autologin with session: $SESSION"
      
      # Create LightDM config
      mkdir -p /etc/lightdm/lightdm.conf.d
      cat > /etc/lightdm/lightdm.conf << EOF
      [Seat:*]
      autologin-user=student
      autologin-user-timeout=0
      user-session=$SESSION
      greeter-session=lightdm-gtk-greeter
      EOF
      
      # Also in conf.d
      cat > /etc/lightdm/lightdm.conf.d/autologin.conf << EOF
      [Seat:*]
      autologin-user=student
      autologin-user-timeout=0
      user-session=$SESSION
      EOF
      
      # Add student to autologin group
      groupadd -f autologin
      usermod -aG autologin student
      
      echo "Autologin configured for user 'student' with session '$SESSION'"
  
  # Desktop shortcut for terminal
  - path: /home/student/Desktop/terminal.desktop
    content: |
      [Desktop Entry]
      Type=Application
      Name=Terminal
      Exec=xfce4-terminal
      Icon=utilities-terminal
      Terminal=false
    permissions: '0755'
  
  # Desktop shortcut for file manager
  - path: /home/student/Desktop/filemanager.desktop
    content: |
      [Desktop Entry]
      Type=Application
      Name=File Manager
      Exec=thunar
      Icon=system-file-manager
      Terminal=false
    permissions: '0755'
    
  # Shared folder mount service
  - path: /etc/systemd/system/mnt-shared.mount
    content: |
      [Unit]
      Description=Mount shared folder from host
      
      [Mount]
      What=shared
      Where=/mnt/shared
      Type=9p
      Options=trans=virtio,version=9p2000.L,rw,msize=104857600
      
      [Install]
      WantedBy=multi-user.target
    permissions: '0644'

  # Memory monitor script - reports memory status to shared folder for balloon controller
  - path: /usr/local/bin/memory-monitor.py
    permissions: '0755'
    content: |
      #!/usr/bin/env python3
      \"\"\"Memory monitor for dynamic balloon control.\"\"\"
      import json
      import time
      from pathlib import Path
      
      SHARED_DIR = Path("/mnt/shared")
      STATUS_FILE = SHARED_DIR / ".vm-memory-status"
      INTERVAL = 3  # seconds
      
      def get_memory_info():
          \"\"\"Read memory info from /proc/meminfo.\"\"\"
          info = {{}}
          try:
              with open("/proc/meminfo") as f:
                  for line in f:
                      parts = line.split()
                      if len(parts) >= 2:
                          key = parts[0].rstrip(":")
                          value = int(parts[1])  # in kB
                          info[key] = value
          except Exception:
              pass
          return info
      
      def main():
          print("Memory monitor started")
          seq_id = 0  # Sequence ID to prevent duplicate processing
          while True:
              try:
                  if not SHARED_DIR.exists():
                      time.sleep(INTERVAL)
                      continue
                  
                  mem = get_memory_info()
                  total_kb = mem.get("MemTotal", 0)
                  available_kb = mem.get("MemAvailable", 0)
                  free_kb = mem.get("MemFree", 0)
                  buffers_kb = mem.get("Buffers", 0)
                  cached_kb = mem.get("Cached", 0)
                  
                  seq_id += 1
                  status = {{
                      "seq_id": seq_id,
                      "timestamp": time.time(),
                      "total_mb": total_kb // 1024,
                      "available_mb": available_kb // 1024,
                      "free_mb": free_kb // 1024,
                      "buffers_mb": buffers_kb // 1024,
                      "cached_mb": cached_kb // 1024,
                      "used_mb": (total_kb - available_kb) // 1024,
                  }}
                  
                  STATUS_FILE.write_text(json.dumps(status))
              except Exception as e:
                  print(f"Error: {{e}}")
              
              time.sleep(INTERVAL)
      
      if __name__ == "__main__":
          main()

  # Memory monitor systemd service
  - path: /etc/systemd/system/memory-monitor.service
    permissions: '0644'
    content: |
      [Unit]
      Description=Memory Monitor for Balloon Controller
      After=mnt-shared.mount
      Requires=mnt-shared.mount
      
      [Service]
      Type=simple
      ExecStart=/usr/bin/python3 /usr/local/bin/memory-monitor.py
      Restart=always
      RestartSec=5
      
      [Install]
      WantedBy=multi-user.target

  # Memory hotplug auto-online script - onlines new memory automatically
  - path: /usr/local/bin/memory-hotplug-online.sh
    permissions: '0755'
    content: |
      #!/bin/bash
      # Auto-online hotplugged memory
      for mem in /sys/devices/system/memory/memory*/state; do
        state=$(cat "$mem" 2>/dev/null)
        if [ "$state" = "offline" ]; then
          echo "Onlining $mem"
          echo online > "$mem" 2>/dev/null || true
        fi
      done

  # Udev rule to auto-online memory when hotplugged
  - path: /etc/udev/rules.d/99-memory-hotplug.rules
    permissions: '0644'
    content: |
      # Auto-online memory when hotplugged
      SUBSYSTEM=="memory", ACTION=="add", ATTR{{state}}=="offline", ATTR{{state}}="online"

  # Systemd service to online memory at boot and periodically
  - path: /etc/systemd/system/memory-hotplug.service
    permissions: '0644'
    content: |
      [Unit]
      Description=Auto-online hotplugged memory
      After=multi-user.target
      
      [Service]
      Type=oneshot
      ExecStart=/usr/local/bin/memory-hotplug-online.sh
      RemainAfterExit=yes
      
      [Install]
      WantedBy=multi-user.target

  # Timer to periodically check for offline memory
  - path: /etc/systemd/system/memory-hotplug.timer
    permissions: '0644'
    content: |
      [Unit]
      Description=Periodically online hotplugged memory
      
      [Timer]
      OnBootSec=10
      OnUnitActiveSec=5
      
      [Install]
      WantedBy=timers.target

  # First boot progress display script - runs as the main process on tty1
  - path: /usr/local/bin/first-boot-message.sh
    permissions: '0755'
    content: |
      #!/bin/bash
      
      # This script replaces getty on first boot to show progress
      
      # Clear screen and show banner
      clear
      
      show_banner() {{
        clear
        echo ""
        echo "╔═══════════════════════════════════════════════════════════════╗"
        echo "║                                                               ║"
        echo "║              🎓 STUDENT VM - FIRST BOOT SETUP 🎓              ║"
        echo "║                                                               ║"
        echo "╠═══════════════════════════════════════════════════════════════╣"
        echo "║                                                               ║"
        echo "║  Installing packages and configuring the system...           ║"
        echo "║                                                               ║"
        echo "║  This will take 5-10 minutes on first boot.                  ║"
        echo "║  The system will REBOOT AUTOMATICALLY when ready.            ║"
        echo "║                                                               ║"
        echo "║  After reboot, you will be logged in automatically           ║"
        echo "║  to the XFCE desktop environment.                            ║"
        echo "║                                                               ║"
        echo "║  Credentials (if needed):                                    ║"
        echo "║    Username: student                                         ║"
        echo "║    Password: student                                         ║"
        echo "║                                                               ║"
        echo "╚═══════════════════════════════════════════════════════════════╝"
        echo ""
      }}
      
      show_banner
      echo "Waiting for cloud-init to start..."
      echo ""
      
      # Wait for cloud-init log to exist
      while [ ! -f /var/log/cloud-init-output.log ]; do
        sleep 1
      done
      
      echo "Installing packages (this takes a few minutes)..."
      echo "─────────────────────────────────────────────────────────────────"
      echo ""
      
      # Show cloud-init output in real time
      tail -f /var/log/cloud-init-output.log &
      TAIL_PID=$!
      
      # Wait for cloud-init to finish
      while [ ! -f /var/lib/cloud/instance/boot-finished ]; do
        sleep 2
      done
      
      # Kill tail
      kill $TAIL_PID 2>/dev/null
      
      echo ""
      echo "─────────────────────────────────────────────────────────────────"
      echo ""
      echo "✓ Setup complete!"
      echo ""
      echo "The system will now reboot into the XFCE desktop..."
      echo ""
      sleep 3
      
      # The reboot is handled by cloud-init power_state, but just in case:
      # reboot

  # Console autologin config for after first boot (fallback if LightDM fails)
  - path: /etc/systemd/system/getty@tty1.service.d/autologin.conf
    permissions: '0644'
    content: |
      [Service]
      ExecStart=
      ExecStart=-/sbin/agetty --autologin student --noclear %I $TERM

# Bootcmd runs very early - stop getty and take over tty1
bootcmd:
  - |
    # Only run on first boot
    if [ ! -f /var/lib/student-vm-configured ]; then
      # Stop getty on tty1 so we can use it
      systemctl stop getty@tty1.service 2>/dev/null || true
      systemctl mask getty@tty1.service 2>/dev/null || true
      
      # Start our progress display in background
      (
        clear > /dev/tty1
        exec > /dev/tty1 2>&1
        
        echo ""
        echo "╔═══════════════════════════════════════════════════════════════╗"
        echo "║                                                               ║"
        echo "║              🎓 STUDENT VM - FIRST BOOT SETUP 🎓              ║"
        echo "║                                                               ║"
        echo "╠═══════════════════════════════════════════════════════════════╣"
        echo "║                                                               ║"
        echo "║  Installing packages and configuring the system...           ║"
        echo "║                                                               ║"
        echo "║  This will take 5-10 minutes on first boot.                  ║"
        echo "║  The system will REBOOT AUTOMATICALLY when ready.            ║"
        echo "║                                                               ║"
        echo "║  After reboot, you will be logged in automatically           ║"
        echo "║  to the XFCE desktop environment.                            ║"
        echo "║                                                               ║"
        echo "║  Credentials (if needed):                                    ║"
        echo "║    Username: student                                         ║"
        echo "║    Password: student                                         ║"
        echo "║                                                               ║"
        echo "╚═══════════════════════════════════════════════════════════════╝"
        echo ""
        echo "Waiting for package installation to begin..."
        echo ""
        
        # Wait for cloud-init output log
        while [ ! -f /var/log/cloud-init-output.log ]; do
          sleep 1
        done
        
        echo "───────────────────────────────────────────────────────────────"
        echo ""
        
        # Follow the log
        tail -f /var/log/cloud-init-output.log 2>/dev/null &
        TAIL_PID=$!
        
        # Wait for completion
        while [ ! -f /var/lib/cloud/instance/boot-finished ]; do
          sleep 2
        done
        
        kill $TAIL_PID 2>/dev/null || true
        
        echo ""
        echo "───────────────────────────────────────────────────────────────"
        echo ""
        echo "✓ Setup complete! Rebooting into desktop..."
        echo ""
        sleep 2
      ) &
    fi

# Commands to run at first boot
runcmd:
  # Create LightDM config directory
  - mkdir -p /etc/lightdm/lightdm.conf.d
  
  # Set up student user
  - mkdir -p /home/student/Desktop
  - chown -R student:student /home/student
  
  # Create shared folder mount point
  - mkdir -p /mnt/shared
  
  # Generate locale
  - sed -i 's/^# *{locale}/{locale}/' /etc/locale.gen || echo "{locale} UTF-8" >> /etc/locale.gen
  - locale-gen
  - update-locale LANG={locale}
  
  # Configure keyboard layout
  - |
    cat > /etc/default/keyboard << KBEOF
    XKBMODEL="pc105"
    XKBLAYOUT="{keyboard}"
    XKBVARIANT=""
    XKBOPTIONS=""
    BACKSPACE="guess"
    KBEOF
  - setupcon --save || true
  
  # Install VS Code
  - |
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/vscode stable main" > /etc/apt/sources.list.d/vscode.list
    apt-get update
    apt-get install -y code
  
  # Install VSCodium via Flatpak
  - flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
  - flatpak install -y flathub com.vscodium.codium
  
  # Install uv (Python package manager)
  - curl -LsSf https://astral.sh/uv/install.sh | sh
  - cp /root/.local/bin/uv /usr/local/bin/uv || true
  - cp /root/.local/bin/uvx /usr/local/bin/uvx || true
  
  # Enable and configure services
  - systemctl daemon-reload
  - systemctl enable lightdm
  - systemctl enable docker
  - systemctl enable mnt-shared.mount
  - systemctl enable memory-monitor.service
  - systemctl enable memory-hotplug.service
  - systemctl enable memory-hotplug.timer
  
  # Reload udev rules for memory hotplug
  - udevadm control --reload-rules
  - udevadm trigger
  
  # Add student to docker and autologin groups
  - usermod -aG docker student
  - groupadd -f autologin
  - usermod -aG autologin student
  
  # Start shared folder mount (will fail if not available, that's ok)
  - systemctl start mnt-shared.mount || true
  
  # Set default target to graphical
  - systemctl set-default graphical.target
  
  # Run the autologin fix script (detects correct session name)
  - /usr/local/bin/fix-autologin.sh
  
  # Clean up apt cache to save space
  - apt-get clean
  - rm -rf /var/lib/apt/lists/*
  
  # Mark as configured (so first-boot message doesn't show again)
  - touch /var/lib/student-vm-configured
  
  # Unmask getty (we masked it in bootcmd)
  - systemctl unmask getty@tty1.service
  
  # Create the autologin override directory
  - mkdir -p /etc/systemd/system/getty@tty1.service.d
  
  # Reboot to start fresh with XFCE desktop and autologin
  - echo "" > /dev/tty1 || true
  - echo "First boot complete. Rebooting into XFCE desktop..." > /dev/tty1 || true
  - sleep 2
  - reboot

# Power state: reboot after cloud-init finishes (backup method)
power_state:
  mode: reboot
  message: "First boot setup complete. Rebooting into XFCE desktop..."
  timeout: 30
  condition: true

# Final message
final_message: |
  Student VM setup complete!
  Login: student / student
  Shared folder: /mnt/shared
"""


def get_meta_data() -> str:
    """Generate cloud-init meta-data."""
    return f"""instance-id: student-vm-{int(time.time())}
local-hostname: student-vm
"""
