"""VM Stop - Stop the Student VM."""

import sys
import time

from . import config
from . import utils


def stop_vm(
    name: str = config.DEFAULT_VM_NAME,
    force: bool = False,
    timeout: int = 30,
) -> bool:
    """
    Stop the Student VM.
    
    Args:
        name: Name of the VM to stop.
        force: If True, force kill the VM without graceful shutdown.
        timeout: Seconds to wait for graceful shutdown before forcing.
    
    Returns:
        True if VM was stopped, False otherwise.
    """
    print(f"=== Stopping VM: {name} ===")
    print()
    
    # Check if VM is running
    is_running, pid = utils.is_vm_running(name)
    
    if not is_running:
        print("VM is not running.")
        # Clean up stale files
        pid_file = config.get_pid_file(name)
        if pid_file.exists():
            pid_file.unlink()
        return True
    
    print(f"Stopping VM (PID: {pid})...")
    
    system = config.get_system()
    
    # Try graceful shutdown via QMP (not on Windows with no unix sockets easily)
    if not force and system != "windows":
        print("Attempting graceful shutdown...")
        if utils.graceful_shutdown(name):
            # Wait for VM to shut down
            for i in range(timeout):
                time.sleep(1)
                is_running, _ = utils.is_vm_running(name)
                if not is_running:
                    print("✓ VM stopped gracefully")
                    cleanup_files(name)
                    return True
                if i % 5 == 4:
                    print(f"  Waiting... ({i + 1}/{timeout}s)")
            
            print("Graceful shutdown timed out.")
    
    # Force kill
    print("Forcing VM shutdown...")
    if pid and utils.kill_process(pid, force=True):
        time.sleep(1)
        is_running, _ = utils.is_vm_running(name)
        if not is_running:
            print("✓ VM stopped")
            cleanup_files(name)
            return True
    
    print("Error: Failed to stop VM")
    return False


def cleanup_files(name: str = config.DEFAULT_VM_NAME) -> None:
    """Clean up runtime files after VM stops."""
    pid_file = config.get_pid_file(name)
    monitor_sock = config.get_monitor_socket(name)
    console_sock = config.get_console_socket(name)
    
    for f in [pid_file, monitor_sock, console_sock]:
        if f.exists():
            try:
                f.unlink()
            except Exception:
                pass


def main() -> int:
    """Entry point for vm-stop command."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Stop the Student VM"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force kill the VM without graceful shutdown"
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=30,
        help="Seconds to wait for graceful shutdown (default: 30)"
    )
    
    args = parser.parse_args()
    
    success = stop_vm(force=args.force, timeout=args.timeout)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
