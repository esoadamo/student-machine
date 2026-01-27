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
  # Enable autologin for student user
  - path: /etc/sddm.conf.d/autologin.conf
    content: |
      [Autologin]
      User=student
      Session=lxqt
    permissions: '0644'
  
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

# Commands to run at first boot
runcmd:
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
  
  # Clean up apt cache to save space
  - apt-get clean
  - rm -rf /var/lib/apt/lists/*

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
