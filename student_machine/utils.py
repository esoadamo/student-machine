"""Utility functions for the Student Machine VM manager."""

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
from pathlib import Path
from typing import Optional

import pycdlib

from . import config


def check_qemu_installed() -> bool:
    """Check if QEMU is installed and available."""
    qemu_binary = config.get_qemu_binary()
    return shutil.which(qemu_binary) is not None


def check_qemu_img_installed() -> bool:
    """Check if qemu-img is installed and available."""
    return shutil.which("qemu-img") is not None


def get_installation_instructions() -> str:
    """Get QEMU installation instructions for the current system."""
    system = config.get_system()
    
    if system == "linux":
        return """
Install QEMU on Linux:
    Ubuntu/Debian: sudo apt install qemu-system-x86 qemu-utils
    Fedora:        sudo dnf install qemu-system-x86 qemu-img
    Arch:          sudo pacman -S qemu-full

For KVM acceleration:
  sudo usermod -aG kvm $USER
  # Log out and back in
"""
    elif system == "macos":
        return """
Install QEMU on macOS:
    brew install qemu
"""
    elif system == "windows":
        return """
Install QEMU on Windows:
  1. Download from: https://www.qemu.org/download/#windows
  2. Add QEMU to your PATH
"""
    return "Please install QEMU for your system: https://www.qemu.org/download/"


def run_command(
    cmd: list[str],
    check: bool = True,
    capture_output: bool = False,
    cwd: Optional[Path] = None,
    env: Optional[dict] = None,
) -> subprocess.CompletedProcess:
    """Run a command and handle errors."""
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True,
            cwd=cwd,
            env=env,
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(cmd)}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        raise


def download_file(url: str, dest: Path, show_progress: bool = True) -> bool:
    """Download a file from URL to destination."""
    import urllib.request
    import urllib.error
    
    print(f"Downloading: {url}")
    print(f"Destination: {dest}")
    
    try:
        def report_progress(block_num: int, block_size: int, total_size: int) -> None:
            if total_size > 0 and show_progress:
                downloaded = block_num * block_size
                percent = min(100, (downloaded / total_size) * 100)
                bar_length = 40
                filled = int(bar_length * percent / 100)
                bar = "=" * filled + "-" * (bar_length - filled)
                sys.stdout.write(f"\r[{bar}] {percent:.1f}%")
                sys.stdout.flush()
                if downloaded >= total_size:
                    print()
        
        # Create opener with custom user agent
        opener = urllib.request.build_opener()
        opener.addheaders = [("User-Agent", "student-machine/0.1.0")]
        urllib.request.install_opener(opener)
        
        urllib.request.urlretrieve(
            url, 
            dest, 
            reporthook=report_progress if show_progress else None
        )
        return True
    except urllib.error.URLError as e:
        print(f"Error downloading file: {e}")
        return False


def create_cloud_init_iso(dest: Path, user_data: str, meta_data: str) -> bool:
    """Create a cloud-init seed ISO image."""
    vm_dir = config.get_vm_dir()
    
    user_data_file = vm_dir / "user-data"
    meta_data_file = vm_dir / "meta-data"
    
    # Write cloud-init files
    user_data_file.write_text(user_data, encoding="utf-8")
    meta_data_file.write_text(meta_data, encoding="utf-8")
    
    try:
        iso = pycdlib.PyCdlib()
        iso.new(
            interchange_level=3,
            joliet=True,
            rock_ridge="1.09",
            vol_ident="cidata",
        )
        iso.add_file(
            str(user_data_file),
            iso_path="/USERDATA.;1",
            joliet_path="/user-data",
            rr_name="user-data",
        )
        iso.add_file(
            str(meta_data_file),
            iso_path="/METADATA.;1",
            joliet_path="/meta-data",
            rr_name="meta-data",
        )
        iso.write(str(dest))
        iso.close()

        return True
    finally:
        # Cleanup temp files
        user_data_file.unlink(missing_ok=True)
        meta_data_file.unlink(missing_ok=True)


def is_vm_running(name: str = config.DEFAULT_VM_NAME) -> tuple[bool, Optional[int]]:
    """Check if the VM is running. Returns (is_running, pid)."""
    pid_file = config.get_pid_file(name)
    
    if not pid_file.exists():
        return False, None
    
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return False, None
    
    # Check if process is running
    if process_exists(pid):
        return True, pid
    
    return False, None


def process_exists(pid: int) -> bool:
    """Check if a process with given PID exists."""
    system = config.get_system()
    
    if system == "windows":
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True
            )
            return str(pid) in result.stdout
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def kill_process(pid: int, force: bool = False) -> bool:
    """Kill a process by PID."""
    system = config.get_system()
    
    if system == "windows":
        try:
            if force:
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True)
            else:
                subprocess.run(["taskkill", "/PID", str(pid)], check=True)
            return True
        except Exception:
            return False
    else:
        try:
            sig = signal.SIGKILL if force else signal.SIGTERM
            os.kill(pid, sig)
            return True
        except OSError:
            return False


def send_qmp_command(command: dict, name: str = config.DEFAULT_VM_NAME) -> Optional[dict]:
    """Send a QMP command to the VM monitor socket."""
    monitor_sock = config.get_monitor_socket(name)
    
    if not monitor_sock.exists():
        return None
    
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(str(monitor_sock))
        
        # Read greeting
        sock.recv(4096)
        
        # Send capabilities negotiation
        sock.send(json.dumps({"execute": "qmp_capabilities"}).encode() + b"\n")
        sock.recv(4096)
        
        # Send actual command
        sock.send(json.dumps(command).encode() + b"\n")
        response = sock.recv(4096).decode()
        
        sock.close()
        return json.loads(response)
    except Exception as e:
        return None


def graceful_shutdown(name: str = config.DEFAULT_VM_NAME) -> bool:
    """Try to gracefully shutdown the VM via QMP."""
    response = send_qmp_command({"execute": "system_powerdown"}, name)
    return response is not None
