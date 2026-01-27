"""Configuration constants for the Student Machine VM."""

import os
from pathlib import Path
import platform

# Default VM Configuration
DEFAULT_VM_NAME = "student-vm"
IMAGE_SIZE = "20G"  # Disk size for Debian with XFCE desktop
VM_MEMORY = "2048M"  # Initial memory allocation (can grow via hotplug)
VM_MEMORY_TARGET = 2048  # Initial memory in MB (used as floor for balloon reclaim)
VM_CPUS = 2

# Debian 12 cloud image URLs based on architecture
DEBIAN_IMAGE_URLS = {
    "amd64": "https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-generic-amd64.qcow2",
    "arm64": "https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-generic-arm64.qcow2",
}

# Paths
def get_vm_dir() -> Path:
    """Get the VM directory path (~/.vm)."""
    return Path.home() / ".vm"


def get_vm_subdir(name: str = DEFAULT_VM_NAME) -> Path:
    """Get the directory for a specific VM."""
    if name == DEFAULT_VM_NAME:
        # For backwards compatibility, default VM uses ~/.vm directly
        return get_vm_dir()
    return get_vm_dir() / name


def get_image_path(name: str = DEFAULT_VM_NAME) -> Path:
    """Get the main VM image path."""
    return get_vm_subdir(name) / f"{name}.qcow2"


def get_base_image_path() -> Path:
    """Get the base Debian image path (shared across all VMs)."""
    return get_vm_dir() / "debian-12-base.qcow2"


def get_seed_image_path(name: str = DEFAULT_VM_NAME) -> Path:
    """Get the cloud-init seed image path."""
    return get_vm_subdir(name) / "seed.iso"


def get_pid_file(name: str = DEFAULT_VM_NAME) -> Path:
    """Get the PID file path."""
    return get_vm_subdir(name) / f"{name}.pid"


def get_monitor_socket(name: str = DEFAULT_VM_NAME) -> Path:
    """Get the QMP monitor socket path."""
    return get_vm_subdir(name) / f"{name}-monitor.sock"


def get_console_socket(name: str = DEFAULT_VM_NAME) -> Path:
    """Get the serial console socket path."""
    return get_vm_subdir(name) / f"{name}-console.sock"


def get_log_file(name: str = DEFAULT_VM_NAME) -> Path:
    """Get the QEMU log file path."""
    return get_vm_subdir(name) / f"{name}.log"


def get_balloon_log_file(name: str = DEFAULT_VM_NAME) -> Path:
    """Get the balloon controller log file path."""
    return get_vm_subdir(name) / "balloon.log"


def get_balloon_pid_file(name: str = DEFAULT_VM_NAME) -> Path:
    """Get the balloon controller PID file path."""
    return get_vm_subdir(name) / "balloon.pid"


def get_data_dir(name: str = DEFAULT_VM_NAME) -> Path:
    """Get the data directory for shared folders."""
    return get_vm_subdir(name) / "data"


def get_system() -> str:
    """Get the current operating system."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    return system


def get_arch() -> str:
    """Get the current architecture."""
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        return "amd64"
    elif machine in ("aarch64", "arm64"):
        return "arm64"
    return machine


def get_qemu_binary() -> str:
    """Get the appropriate QEMU binary name for the current system."""
    arch = get_arch()
    system = get_system()
    
    if arch == "amd64":
        return "qemu-system-x86_64"
    elif arch == "arm64":
        return "qemu-system-aarch64"
    return "qemu-system-x86_64"


def get_qemu_accel() -> list[str]:
    """Get QEMU acceleration options for the current system."""
    system = get_system()
    arch = get_arch()
    
    if system == "linux":
        # Check if KVM is available
        if Path("/dev/kvm").exists():
            if os.access("/dev/kvm", os.R_OK | os.W_OK):
                return ["-enable-kvm", "-cpu", "host"]
            else:
                print("Warning: No permission to access /dev/kvm")
                print("Add yourself to the kvm group: sudo usermod -aG kvm $USER")
        else:
            print("Warning: /dev/kvm not found. KVM acceleration not available.")
    elif system == "macos":
        # Use Hypervisor.framework on macOS
        if arch == "arm64":
            return ["-accel", "hvf", "-cpu", "host"]
        else:
            return ["-accel", "hvf", "-cpu", "host"]
    elif system == "windows":
        # Use WHPX on Windows if available
        return ["-accel", "whpx", "-cpu", "max"]
    
    # Fallback to TCG (software emulation)
    print("Warning: No hardware acceleration available. VM will run slower.")
    return ["-accel", "tcg", "-cpu", "max"]
