"""VM Status - Show the Student VM status."""

import sys

from . import config
from . import utils


def status_vm() -> bool:
    """
    Show the Student VM status.
    
    Returns:
        True if VM is running, False otherwise.
    """
    print("=== Student VM Status ===")
    print()
    
    # Check if VM is running
    is_running, pid = utils.is_vm_running()
    
    vm_dir = config.get_vm_dir()
    vm_image = config.get_image_path()
    seed_image = config.get_seed_image_path()
    data_dir = config.get_data_dir()
    log_file = config.get_log_file()
    
    # Show VM directory info
    print(f"VM Directory: {vm_dir}")
    print()
    
    # Show image status
    print("Images:")
    if vm_image.exists():
        size_mb = vm_image.stat().st_size / (1024 * 1024)
        print(f"  ✓ VM Image:   {vm_image} ({size_mb:.1f} MB)")
    else:
        print(f"  ✗ VM Image:   Not found (run 'student-machine setup')")
    
    if seed_image.exists():
        size_kb = seed_image.stat().st_size / 1024
        print(f"  ✓ Seed Image: {seed_image} ({size_kb:.1f} KB)")
    else:
        print(f"  ✗ Seed Image: Not found (run 'student-machine setup')")
    print()
    
    # Show running status
    print("Status:")
    if is_running:
        print(f"  ✓ VM is running (PID: {pid})")
        print()
        print("Access:")
        print("  SSH:         ssh student@localhost -p 2222")
        print("  Password:    student")
        print(f"  Shared Dir:  {data_dir}")
        print("  Guest Mount: /mnt/shared")
    else:
        print("  ✗ VM is not running")
        print()
        print("To start the VM:")
        print("  student-machine start       # Headless")
        print("  student-machine start --gui # With display")
    print()
    
    # Show log file info
    if log_file.exists():
        print(f"Log file: {log_file}")
        print("  View with: tail -f " + str(log_file))
    
    return is_running


def main() -> int:
    """Entry point for vm-status command."""
    is_running = status_vm()
    return 0 if is_running else 1


if __name__ == "__main__":
    sys.exit(main())
