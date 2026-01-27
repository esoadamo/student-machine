"""VM Start - Start the Student VM."""

import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from . import config
from . import utils


def start_vm(
    gui: bool = False,
    console: bool = False,
    shared_dir: Optional[Path] = None,
    port: int = 2222,
    memory: Optional[str] = None,
    cpus: Optional[int] = None,
) -> bool:
    """
    Start the Student VM.
    
    Args:
        gui: If True, show graphical display.
        console: If True, enable serial console.
        shared_dir: Directory to share with VM (default: ~/.vm/data).
        port: SSH port forwarding (default: 2222).
        memory: Memory allocation (default from config).
        cpus: Number of CPUs (default from config).
    
    Returns:
        True if VM started successfully, False otherwise.
    """
    print("=== Starting Student VM ===")
    print()
    
    # Check if QEMU is installed
    if not utils.check_qemu_installed():
        print("Error: QEMU is not installed or not in PATH.")
        print(utils.get_installation_instructions())
        return False
    
    # Check if VM images exist
    vm_image = config.get_image_path()
    seed_image = config.get_seed_image_path()
    
    if not vm_image.exists():
        print(f"Error: VM image not found: {vm_image}")
        print("Run 'student-machine setup' first.")
        return False
    
    if not seed_image.exists():
        print(f"Error: Seed image not found: {seed_image}")
        print("Run 'student-machine setup' first.")
        return False
    
    # Check if VM is already running
    is_running, pid = utils.is_vm_running()
    if is_running:
        print(f"VM is already running (PID: {pid})")
        print("To stop it, run: student-machine stop")
        return True
    
    # Clean up stale PID file
    pid_file = config.get_pid_file()
    if pid_file.exists():
        pid_file.unlink()
    
    # Get configuration
    qemu_binary = config.get_qemu_binary()
    accel_opts = config.get_qemu_accel()
    system = config.get_system()
    
    vm_memory = memory or config.VM_MEMORY
    vm_cpus = cpus or config.VM_CPUS
    
    # Set up shared directory
    if shared_dir is None:
        shared_dir = config.get_data_dir()
    shared_dir.mkdir(parents=True, exist_ok=True)
    
    # Build QEMU command
    cmd = [qemu_binary]
    cmd.extend(["-name", config.VM_NAME])
    
    # Acceleration
    cmd.extend(accel_opts)
    
    # Machine type
    if config.get_arch() == "arm64":
        cmd.extend(["-machine", "virt"])
    else:
        cmd.extend(["-machine", "type=q35"])
    
    # Resources
    cmd.extend(["-smp", f"cpus={vm_cpus}"])
    cmd.extend(["-m", vm_memory])
    
    # Drives
    cmd.extend([
        "-drive", f"file={vm_image},format=qcow2,if=virtio,cache=writeback",
        "-drive", f"file={seed_image},format=raw,if=virtio",
    ])
    
    # Network with SSH and VNC port forwarding
    # Port 22 -> SSH, Port 5900 -> VNC (for XFCE)
    cmd.extend([
        "-nic", f"user,hostfwd=tcp:127.0.0.1:{port}-:22,hostfwd=tcp:127.0.0.1:5900-:5900"
    ])
    
    # Shared folder (9p virtfs - works on Linux and macOS with proper QEMU build)
    if system in ("linux", "macos"):
        cmd.extend([
            "-virtfs", f"local,path={shared_dir},mount_tag=shared,security_model=mapped-xattr,id=shared"
        ])
    elif system == "windows":
        # On Windows, use SMB sharing instead (not implemented here, could use built-in Windows sharing)
        print(f"Note: Shared folder not available on Windows. Use SSH/SCP instead.")
    
    # Display
    if gui:
        if system == "macos":
            cmd.extend(["-display", "cocoa"])
        elif system == "windows":
            cmd.extend(["-display", "sdl"])
        else:
            cmd.extend(["-display", "gtk"])
    else:
        cmd.extend(["-display", "none"])
    
    # Console
    console_sock = config.get_console_socket()
    if console:
        if system != "windows":
            cmd.extend(["-serial", f"unix:{console_sock},server,nowait"])
        else:
            # On Windows, use a different approach
            cmd.extend(["-serial", "stdio"])
    
    # QMP Monitor socket (for graceful shutdown)
    monitor_sock = config.get_monitor_socket()
    if system != "windows":
        cmd.extend(["-qmp", f"unix:{monitor_sock},server,nowait"])
    
    # PID file
    cmd.extend(["-pidfile", str(pid_file)])
    
    # USB for mouse input
    cmd.extend([
        "-device", "qemu-xhci",
        "-device", "usb-tablet",
    ])
    
    # Audio (for desktop experience)
    if gui:
        if system == "linux":
            cmd.extend(["-audiodev", "pa,id=audio0", "-device", "intel-hda", "-device", "hda-duplex,audiodev=audio0"])
        elif system == "macos":
            cmd.extend(["-audiodev", "coreaudio,id=audio0", "-device", "intel-hda", "-device", "hda-duplex,audiodev=audio0"])
    
    # Memory ballooning
    cmd.extend(["-device", "virtio-balloon"])
    
    # Log file
    log_file = config.get_log_file()
    
    print(f"Starting QEMU with command:")
    print(f"  {' '.join(cmd[:5])}...")
    print()
    
    # Start QEMU
    try:
        if system == "windows" and console:
            # On Windows with console, run in foreground
            process = subprocess.Popen(cmd)
        else:
            # Run in background
            with open(log_file, "a") as log:
                if system == "windows":
                    # On Windows, use CREATE_NEW_PROCESS_GROUP
                    process = subprocess.Popen(
                        cmd,
                        stdout=log,
                        stderr=log,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    # On Unix, daemonize
                    process = subprocess.Popen(
                        cmd,
                        stdout=log,
                        stderr=log,
                        start_new_session=True
                    )
        
        # Wait a moment for QEMU to start
        time.sleep(2)
        
        # Check if it started
        is_running, pid = utils.is_vm_running()
        if is_running:
            print(f"✓ VM started with PID: {pid}")
            print()
            print("Access information:")
            print(f"  SSH:          ssh student@localhost -p {port}")
            print(f"  Password:     student")
            print(f"  Shared Dir:   {shared_dir}")
            print(f"  Guest Mount:  /mnt/shared")
            print()
            if console and system != "windows":
                print(f"Console socket: {console_sock}")
                print(f"  Connect with: socat - UNIX-CONNECT:{console_sock}")
                print()
            print("Cloud-init is provisioning the VM (first boot takes 5-10 minutes)...")
            print("The desktop environment will be available after reboot.")
            print()
            print(f"Monitor progress: tail -f {log_file}")
            return True
        else:
            print("Error: Failed to start VM")
            print(f"Check logs: {log_file}")
            return False
            
    except Exception as e:
        print(f"Error starting VM: {e}")
        return False


def main() -> int:
    """Entry point for vm-start command."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Start the Student VM"
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Enable graphical display"
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Enable serial console"
    )
    parser.add_argument(
        "--shared-dir",
        type=Path,
        help="Directory to share with VM (default: ~/.vm/data)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=2222,
        help="SSH port forwarding (default: 2222)"
    )
    parser.add_argument(
        "--memory", "-m",
        type=str,
        help=f"Memory allocation (default: {config.VM_MEMORY})"
    )
    parser.add_argument(
        "--cpus", "-c",
        type=int,
        help=f"Number of CPUs (default: {config.VM_CPUS})"
    )
    
    args = parser.parse_args()
    
    success = start_vm(
        gui=args.gui,
        console=args.console,
        shared_dir=args.shared_dir,
        port=args.port,
        memory=args.memory,
        cpus=args.cpus,
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
