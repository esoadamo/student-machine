"""Cloud-init configuration for Debian with LXQT desktop."""

import time


def get_user_data() -> str:
    """Generate cloud-init user-data for Debian with LXQT desktop."""
    return """#cloud-config
hostname: student-vm
fqdn: student-vm.local

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
  - nano
  - vim
  - openssh-server
  
  # LXQT Desktop Environment
  - lxqt
  - sddm
  - xorg
  
  # Desktop applications
  - firefox-esr
  - pcmanfm-qt
  - qterminal
  - featherpad
  
  # Development tools
  - build-essential
  - python3
  - python3-pip
  - python3-venv
  - nodejs
  - npm
  
  # Docker
  - docker.io
  - docker-compose

# Grow root partition to use full disk
growpart:
  mode: auto
  devices: ["/"]

# System configuration files
write_files:
  # Main SDDM config for autologin
  # Note: Session must match filename in /usr/share/xsessions/ (without .desktop)
  - path: /etc/sddm.conf
    content: |
      [Autologin]
      User=student
      Session=lxqt
      
      [General]
      HaltCommand=/usr/bin/systemctl poweroff
      RebootCommand=/usr/bin/systemctl reboot
      
      [Users]
      MaximumUid=60000
      MinimumUid=1000
    permissions: '0644'
  
  # Script to fix autologin after LXQT is installed
  # This runs after packages are installed to get the correct session name
  - path: /usr/local/bin/fix-autologin.sh
    permissions: '0755'
    content: |
      #!/bin/bash
      # Find the actual LXQT session file name
      SESSION=""
      for f in /usr/share/xsessions/lxqt*.desktop; do
        if [ -f "$f" ]; then
          SESSION=$(basename "$f" .desktop)
          break
        fi
      done
      
      # Fallback to common names
      if [ -z "$SESSION" ]; then
        if [ -f /usr/share/xsessions/lxqt.desktop ]; then
          SESSION="lxqt"
        elif [ -f /usr/share/xsessions/LXQt.desktop ]; then
          SESSION="LXQt"
        else
          SESSION="lxqt"
        fi
      fi
      
      echo "Configuring SDDM autologin with session: $SESSION"
      
      # Create SDDM config
      mkdir -p /etc/sddm.conf.d
      cat > /etc/sddm.conf << EOF
      [Autologin]
      User=student
      Session=$SESSION
      
      [General]
      HaltCommand=/usr/bin/systemctl poweroff
      RebootCommand=/usr/bin/systemctl reboot
      
      [Users]
      MaximumUid=60000
      MinimumUid=1000
      EOF
      
      # Also set in conf.d
      cat > /etc/sddm.conf.d/autologin.conf << EOF
      [Autologin]
      User=student
      Session=$SESSION
      EOF
      
      # Enable autologin in PAM as well (some systems need this)
      if [ -f /etc/pam.d/sddm-autologin ]; then
        echo "PAM autologin already configured"
      else
        cat > /etc/pam.d/sddm-autologin << 'EOFPAM'
      auth     requisite pam_nologin.so
      auth     required  pam_succeed_if.so user ingroup nopasswdlogin quiet_success
      auth     optional  pam_permit.so
      account  include   sddm
      password include   sddm
      session  include   sddm
      EOFPAM
      fi
      
      # Create nopasswdlogin group and add student
      groupadd -f nopasswdlogin
      usermod -aG nopasswdlogin student
      
      echo "Autologin configured for user 'student' with session '$SESSION'"
  
  # Desktop shortcut for terminal
  - path: /home/student/Desktop/qterminal.desktop
    content: |
      [Desktop Entry]
      Type=Application
      Name=Terminal
      Exec=qterminal
      Icon=utilities-terminal
      Terminal=false
    permissions: '0755'
  
  # Desktop shortcut for file manager
  - path: /home/student/Desktop/pcmanfm-qt.desktop
    content: |
      [Desktop Entry]
      Type=Application
      Name=File Manager
      Exec=pcmanfm-qt
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

  # First boot progress display script - runs as the main process on tty1
  - path: /usr/local/bin/first-boot-message.sh
    permissions: '0755'
    content: |
      #!/bin/bash
      
      # This script replaces getty on first boot to show progress
      
      # Clear screen and show banner
      clear
      
      show_banner() {
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
        echo "║  to the LXQT desktop environment.                            ║"
        echo "║                                                               ║"
        echo "║  Credentials (if needed):                                    ║"
        echo "║    Username: student                                         ║"
        echo "║    Password: student                                         ║"
        echo "║                                                               ║"
        echo "╚═══════════════════════════════════════════════════════════════╝"
        echo ""
      }
      
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
      echo "The system will now reboot into the LXQT desktop..."
      echo ""
      sleep 3
      
      # The reboot is handled by cloud-init power_state, but just in case:
      # reboot

  # Console autologin config for after first boot (fallback if SDDM fails)
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
        echo "║  to the LXQT desktop environment.                            ║"
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
  # Create SDDM config directory
  - mkdir -p /etc/sddm.conf.d
  
  # Set up student user
  - mkdir -p /home/student/Desktop
  - chown -R student:student /home/student
  
  # Create shared folder mount point
  - mkdir -p /mnt/shared
  
  # Enable and configure services
  - systemctl daemon-reload
  - systemctl enable sddm
  - systemctl enable docker
  - systemctl enable mnt-shared.mount
  
  # Add student to docker group
  - usermod -aG docker student
  
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
  
  # Reboot to start fresh with LXQT desktop and autologin
  - echo "" > /dev/tty1 || true
  - echo "First boot complete. Rebooting into LXQT desktop..." > /dev/tty1 || true
  - sleep 2
  - reboot

# Power state: reboot after cloud-init finishes (backup method)
power_state:
  mode: reboot
  message: "First boot setup complete. Rebooting into LXQT desktop..."
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
