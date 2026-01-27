"""Service management for the Student VM (Linux systemd, macOS launchd, Windows Task Scheduler)."""

import os
import sys
from pathlib import Path
from typing import Optional

from . import config


# Systemd service template for Linux
SYSTEMD_SERVICE_TEMPLATE = """[Unit]
Description=Student VM QEMU Virtual Machine ({name})
After=network.target

[Service]
Type=forking
User={user}
Group={user}
WorkingDirectory={home}

# PID file for tracking
PIDFile={pid_file}

# Start/Stop commands
ExecStart={python} -m student_machine start --name {name}
ExecStop={python} -m student_machine stop --name {name}

# Restart policy
Restart=on-failure
RestartSec=10

# Timeout settings
TimeoutStartSec=300
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
"""

# launchd plist template for macOS
LAUNCHD_PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.student-machine.{name}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>-m</string>
        <string>student_machine</string>
        <string>start</string>
        <string>--name</string>
        <string>{name}</string>
    </array>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <false/>
    <key>WorkingDirectory</key>
    <string>{home}</string>
    <key>StandardOutPath</key>
    <string>{log_file}</string>
    <key>StandardErrorPath</key>
    <string>{log_file}</string>
</dict>
</plist>
"""


def install_service(name: str = config.DEFAULT_VM_NAME) -> bool:
    """
    Install the VM as a system service.
    
    Args:
        name: Name of the VM to install as service.
    
    Returns:
        True if successful, False otherwise.
    """
    system = config.get_system()
    
    if system == "linux":
        return install_systemd_service(name)
    elif system == "macos":
        return install_launchd_service(name)
    elif system == "windows":
        return install_windows_task(name)
    else:
        print(f"Error: Unsupported system: {system}")
        return False


def uninstall_service(name: str = config.DEFAULT_VM_NAME) -> bool:
    """
    Uninstall the VM system service.
    
    Args:
        name: Name of the VM service to uninstall.
    
    Returns:
        True if successful, False otherwise.
    """
    system = config.get_system()
    
    if system == "linux":
        return uninstall_systemd_service(name)
    elif system == "macos":
        return uninstall_launchd_service(name)
    elif system == "windows":
        return uninstall_windows_task(name)
    else:
        print(f"Error: Unsupported system: {system}")
        return False


def install_systemd_service(name: str = config.DEFAULT_VM_NAME) -> bool:
    """Install systemd service on Linux."""
    import subprocess
    
    # Check if running as root
    if os.geteuid() != 0:
        print("Error: Please run as root (sudo student-machine service install)")
        return False
    
    # Get the user who called sudo
    real_user = os.environ.get("SUDO_USER", os.environ.get("USER", ""))
    if not real_user:
        print("Error: Could not determine user")
        return False
    
    home_dir = Path(f"/home/{real_user}")
    if not home_dir.exists():
        home_dir = Path.home()
    
    python_path = sys.executable
    pid_file = config.get_pid_file(name)
    
    service_content = SYSTEMD_SERVICE_TEMPLATE.format(
        name=name,
        user=real_user,
        home=home_dir,
        python=python_path,
        pid_file=pid_file,
    )
    
    # Use VM name in service file name
    service_name = f"student-vm-{name}" if name != config.DEFAULT_VM_NAME else "student-vm"
    service_file = Path(f"/etc/systemd/system/{service_name}.service")
    
    print(f"Installing systemd service for VM: {name}...")
    print(f"  User: {real_user}")
    print(f"  Python: {python_path}")
    
    try:
        service_file.write_text(service_content, encoding="utf-8")
        service_file.chmod(0o644)
        
        # Reload systemd
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        
        print()
        print(f"✓ Service installed: {service_name}")
        print()
        print("Usage:")
        print(f"  sudo systemctl start {service_name}     # Start VM")
        print(f"  sudo systemctl stop {service_name}      # Stop VM")
        print(f"  sudo systemctl restart {service_name}   # Restart VM")
        print(f"  sudo systemctl status {service_name}    # Check status")
        print(f"  sudo systemctl enable {service_name}    # Start on boot")
        print(f"  sudo systemctl disable {service_name}   # Disable start on boot")
        print()
        print("View logs:")
        print(f"  journalctl -u {service_name} -f")
        
        return True
    except Exception as e:
        print(f"Error installing service: {e}")
        return False


def uninstall_systemd_service(name: str = config.DEFAULT_VM_NAME) -> bool:
    """Uninstall systemd service on Linux."""
    import subprocess
    
    if os.geteuid() != 0:
        print("Error: Please run as root (sudo student-machine service uninstall)")
        return False
    
    service_name = f"student-vm-{name}" if name != config.DEFAULT_VM_NAME else "student-vm"
    service_file = Path(f"/etc/systemd/system/{service_name}.service")
    
    print(f"Uninstalling systemd service for VM: {name}...")
    
    try:
        # Stop and disable if running
        subprocess.run(["systemctl", "stop", service_name], capture_output=True)
        subprocess.run(["systemctl", "disable", service_name], capture_output=True)
        
        if service_file.exists():
            service_file.unlink()
            print(f"✓ Removed {service_file}")
        
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        
        print("✓ Service uninstalled")
        return True
    except Exception as e:
        print(f"Error uninstalling service: {e}")
        return False


def install_launchd_service(name: str = config.DEFAULT_VM_NAME) -> bool:
    """Install launchd service on macOS."""
    python_path = sys.executable
    home_dir = Path.home()
    log_file = config.get_log_file(name)
    
    plist_content = LAUNCHD_PLIST_TEMPLATE.format(
        name=name,
        python=python_path,
        home=home_dir,
        log_file=log_file,
    )
    
    label = f"com.student-machine.{name}"
    plist_file = home_dir / f"Library/LaunchAgents/{label}.plist"
    plist_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Installing launchd service for VM: {name}...")
    
    try:
        plist_file.write_text(plist_content, encoding="utf-8")
        
        print()
        print(f"✓ Service installed: {label}")
        print()
        print("Usage:")
        print(f"  launchctl load ~/{plist_file.relative_to(home_dir)}")
        print(f"  launchctl start {label}")
        print(f"  launchctl stop {label}")
        print(f"  launchctl unload ~/{plist_file.relative_to(home_dir)}")
        print()
        print("Or simply use:")
        print(f"  student-machine start --name {name}")
        print(f"  student-machine stop --name {name}")
        
        return True
    except Exception as e:
        print(f"Error installing service: {e}")
        return False


def uninstall_launchd_service(name: str = config.DEFAULT_VM_NAME) -> bool:
    """Uninstall launchd service on macOS."""
    import subprocess
    
    home_dir = Path.home()
    label = f"com.student-machine.{name}"
    plist_file = home_dir / f"Library/LaunchAgents/{label}.plist"
    
    print(f"Uninstalling launchd service for VM: {name}...")
    
    try:
        # Unload if loaded
        subprocess.run(
            ["launchctl", "unload", str(plist_file)],
            capture_output=True
        )
        
        if plist_file.exists():
            plist_file.unlink()
            print(f"✓ Removed {plist_file}")
        
        print("✓ Service uninstalled")
        return True
    except Exception as e:
        print(f"Error uninstalling service: {e}")
        return False


def install_windows_task(name: str = config.DEFAULT_VM_NAME) -> bool:
    """Install scheduled task on Windows."""
    import subprocess
    
    python_path = sys.executable
    task_name = f"StudentVM-{name}" if name != config.DEFAULT_VM_NAME else "StudentVM"
    
    print(f"Installing Windows scheduled task for VM: {name}...")
    
    # Create a batch script to start the VM
    vm_dir = config.get_vm_subdir(name)
    vm_dir.mkdir(parents=True, exist_ok=True)
    
    start_script = vm_dir / "start-vm.bat"
    start_script.write_text(
        f'@echo off\n"{python_path}" -m student_machine start --name {name}\n',
        encoding="utf-8"
    )
    
    try:
        # Create scheduled task (manual trigger, not automatic)
        subprocess.run([
            "schtasks", "/create",
            "/tn", task_name,
            "/tr", str(start_script),
            "/sc", "ONLOGON",
            "/rl", "HIGHEST",
            "/f"
        ], check=True)
        
        # Disable automatic start (user can enable if wanted)
        subprocess.run([
            "schtasks", "/change",
            "/tn", task_name,
            "/disable"
        ], check=True)
        
        print()
        print(f"✓ Task installed: {task_name}")
        print()
        print("Usage:")
        print(f"  schtasks /run /tn {task_name}     # Start VM")
        print(f"  schtasks /end /tn {task_name}     # Stop task")
        print(f"  schtasks /change /tn {task_name} /enable   # Enable auto-start")
        print(f"  schtasks /change /tn {task_name} /disable  # Disable auto-start")
        print()
        print("Or simply use:")
        if name != config.DEFAULT_VM_NAME:
            print(f"  student-machine start --name {name}")
            print(f"  student-machine stop --name {name}")
        else:
            print("  student-machine start")
            print("  student-machine stop")
        
        return True
    except Exception as e:
        print(f"Error installing task: {e}")
        return False


def uninstall_windows_task(name: str = config.DEFAULT_VM_NAME) -> bool:
    """Uninstall scheduled task on Windows."""
    import subprocess
    
    task_name = f"StudentVM-{name}" if name != config.DEFAULT_VM_NAME else "StudentVM"
    
    print(f"Uninstalling Windows scheduled task for VM: {name}...")
    
    try:
        subprocess.run([
            "schtasks", "/delete",
            "/tn", task_name,
            "/f"
        ], check=True)
        
        # Remove batch script
        vm_dir = config.get_vm_subdir(name)
        start_script = vm_dir / "start-vm.bat"
        if start_script.exists():
            start_script.unlink()
        
        print("✓ Task uninstalled")
        return True
    except subprocess.CalledProcessError:
        print("Task not found or already removed")
        return True
    except Exception as e:
        print(f"Error uninstalling task: {e}")
        return False


def main() -> int:
    """Entry point for service command."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Manage Student VM system service"
    )
    parser.add_argument(
        "action",
        choices=["install", "uninstall"],
        help="Action to perform"
    )
    
    args = parser.parse_args()
    
    if args.action == "install":
        success = install_service()
    else:
        success = uninstall_service()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
