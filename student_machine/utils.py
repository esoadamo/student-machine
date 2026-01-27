"""Utility functions for the Student Machine VM manager."""

import json
import os
import platform
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

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
  Ubuntu/Debian: sudo apt install qemu-system-x86 qemu-utils cloud-image-utils
  Fedora:        sudo dnf install qemu-system-x86 qemu-img cloud-utils
  Arch:          sudo pacman -S qemu-full cloud-utils

For KVM acceleration:
  sudo usermod -aG kvm $USER
  # Log out and back in
"""
    elif system == "macos":
        return """
Install QEMU on macOS:
  brew install qemu cdrtools
  
Note: cdrtools provides 'mkisofs' for creating cloud-init images.
"""
    elif system == "windows":
        return """
Install QEMU on Windows:
  1. Download from: https://www.qemu.org/download/#windows
  2. Add QEMU to your PATH
  3. Install genisoimage from: http://smithii.com/files/cdrtools-latest.zip
     (extract and add to PATH)
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
    system = config.get_system()
    vm_dir = config.get_vm_dir()
    
    user_data_file = vm_dir / "user-data"
    meta_data_file = vm_dir / "meta-data"
    
    # Write cloud-init files
    user_data_file.write_text(user_data, encoding="utf-8")
    meta_data_file.write_text(meta_data, encoding="utf-8")
    
    def create_with_pycdlib() -> bool:
        try:
            import pycdlib
        except Exception:
            print("Error: pycdlib is not installed.")
            print("Install it with: pip install pycdlib")
            return False

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
        except Exception as e:
            print(f"Error creating ISO with pycdlib: {e}")
            return False

    try:
        # Try different tools based on platform
        if system == "linux":
            # Try cloud-localds first (from cloud-image-utils)
            if shutil.which("cloud-localds"):
                run_command([
                    "cloud-localds", str(dest), 
                    str(user_data_file), str(meta_data_file)
                ])
            elif shutil.which("genisoimage"):
                run_command([
                    "genisoimage", "-output", str(dest),
                    "-volid", "cidata", "-joliet", "-rock",
                    str(user_data_file), str(meta_data_file)
                ])
            elif shutil.which("mkisofs"):
                run_command([
                    "mkisofs", "-output", str(dest),
                    "-volid", "cidata", "-joliet", "-rock",
                    str(user_data_file), str(meta_data_file)
                ])
            else:
                print("Error: No ISO creation tool found.")
                print("Install cloud-image-utils: sudo apt install cloud-image-utils")
                return False
                
        elif system == "macos":
            if shutil.which("mkisofs"):
                run_command([
                    "mkisofs", "-output", str(dest),
                    "-volid", "cidata", "-joliet", "-rock",
                    str(user_data_file), str(meta_data_file)
                ])
            elif shutil.which("hdiutil"):
                # Create a temporary directory structure
                temp_dir = vm_dir / "cidata_temp"
                temp_dir.mkdir(exist_ok=True)
                shutil.copy(user_data_file, temp_dir / "user-data")
                shutil.copy(meta_data_file, temp_dir / "meta-data")
                run_command([
                    "hdiutil", "makehybrid", "-iso", "-joliet",
                    "-o", str(dest), str(temp_dir)
                ])
                shutil.rmtree(temp_dir)
            else:
                print("Error: No ISO creation tool found.")
                print("Install cdrtools: brew install cdrtools")
                return False
                
        elif system == "windows":
            mkisofs_path = shutil.which("mkisofs")
            genisoimage_path = shutil.which("genisoimage")
            if mkisofs_path:
                mkisofs_dir = Path(mkisofs_path).parent
                env = os.environ.copy()
                env["PATH"] = f"{mkisofs_dir};{env.get('PATH', '')}"
                try:
                    run_command([
                        mkisofs_path, "-o", str(dest),
                        "-volid", "cidata", "-joliet", "-rock",
                        str(user_data_file), str(meta_data_file)
                    ], cwd=mkisofs_dir, env=env)
                except Exception:
                    print("mkisofs failed. Trying pycdlib fallback...")
                    return create_with_pycdlib()
            elif genisoimage_path:
                genisoimage_dir = Path(genisoimage_path).parent
                env = os.environ.copy()
                env["PATH"] = f"{genisoimage_dir};{env.get('PATH', '')}"
                try:
                    run_command([
                        genisoimage_path, "-o", str(dest),
                        "-volid", "cidata", "-joliet", "-rock",
                        str(user_data_file), str(meta_data_file)
                    ], cwd=genisoimage_dir, env=env)
                except Exception:
                    print("genisoimage failed. Trying pycdlib fallback...")
                    return create_with_pycdlib()
            else:
                print("No ISO creation tool found. Trying pycdlib fallback...")
                return create_with_pycdlib()
        
        return True
    except Exception as e:
        print(f"Error creating cloud-init ISO: {e}")
        return False
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
