"""VM Run - One-click auto-setup and start with GUI."""

import sys
from pathlib import Path
from typing import Optional

from . import config
from . import utils


def run_vm(
    name: str = config.DEFAULT_VM_NAME,
    force_setup: bool = False,
    shared_dir: Optional[Path] = None,
    port: int = 2222,
    memory: Optional[str] = None,
    cpus: Optional[int] = None,
    locale: str = "en_US.UTF-8",
    keyboard: str = "us",
) -> bool:
    """
    Auto-setup (if needed) and start the Student VM with GUI.
    
    This is the one-click mode for students - it will:
    1. Check if setup is needed and run it automatically
    2. Start the VM with graphical display
    3. The VM will auto-login to XFCE desktop
    
    Args:
        name: Name of the VM to run.
        force_setup: If True, force recreation of VM images.
        shared_dir: Directory to share with VM (default: ~/.vm/data).
        port: SSH port forwarding (default: 2222).
        memory: Memory allocation (default from config).
        cpus: Number of CPUs (default from config).
        locale: System locale (e.g., 'en_US.UTF-8', 'cs_CZ.UTF-8').
        keyboard: Keyboard layout (e.g., 'us', 'cz').
    
    Returns:
        True if VM started successfully, False otherwise.
    """
    print("=" * 60)
    print(f"Student Machine - One-Click Mode: {name}")
    print("=" * 60)
    print()
    
    # Check if QEMU is installed
    if not utils.check_qemu_installed():
        print("Error: QEMU is not installed or not in PATH.")
        print(utils.get_installation_instructions())
        return False
    
    # Check if VM is already running
    is_running, pid = utils.is_vm_running(name)
    if is_running:
        if force_setup:
            print(f"VM is running (PID: {pid}). Stopping it for forced recreation...")
            from .stop import stop_vm
            if not stop_vm(name=name, force=True):
                print("Error: Failed to stop the running VM")
                return False
            print()
        else:
            print(f"VM is already running (PID: {pid})")
            print()
            print("Access information:")
            print(f"  SSH:      ssh student@localhost -p {port}")
            print(f"  Password: student")
            print()
            print("To stop the VM: student-machine stop")
            return True
    
    # Check if setup is needed
    vm_image = config.get_image_path(name)
    seed_image = config.get_seed_image_path(name)
    
    needs_setup = force_setup or not vm_image.exists() or not seed_image.exists()
    
    if needs_setup:
        print("VM not configured. Running setup...")
        print()
        
        from .setup import setup_vm
        if not setup_vm(name=name, force=force_setup, locale=locale, keyboard=keyboard):
            print("Error: Setup failed")
            return False
        print()
    else:
        print("VM already configured.")
        print(f"  Image: {vm_image}")
        print()
    
    # Start the VM with GUI
    print("Starting VM with graphical display...")
    print()
    
    # Set up shared directory
    if shared_dir is None:
        shared_dir = config.get_data_dir(name)
    
    from .start import start_vm
    success = start_vm(
        name=name,
        gui=True,  # Always GUI in run mode
        console=False,
        shared_dir=shared_dir,
        port=port,
        memory=memory,
        cpus=cpus,
    )
    
    if success:
        print()
        print("=" * 60)
        print("VM is starting!")
        print("=" * 60)
        print()
        print("The XFCE desktop will appear in the QEMU window.")
        print("Auto-login is enabled - no password needed.")
        print()
        print("First boot takes 5-10 minutes to install packages.")
        print("Subsequent boots are much faster.")
        print()
        print("Credentials (if needed):")
        print("  Username: student")
        print("  Password: student")
        print()
        
        # Start memory balloon controller
        from .balloon import start_balloon_controller, is_balloon_running
        from .start import get_host_memory_mb
        
        # Target memory = 2GB (or what was requested)
        # Max memory for balloon = host total - 1GB
        host_total_mb = get_host_memory_mb()
        max_memory_mb = host_total_mb - 1024
        target_memory_mb = config.VM_MEMORY_TARGET  # Default 2GB
        
        success = start_balloon_controller(
            name=name,
            shared_dir=shared_dir,
            min_memory_mb=target_memory_mb,  # This is the target to reclaim to
            max_memory_mb=max_memory_mb,     # This is the ceiling
        )
        if success:
            print(f"Memory balloon controller started (target: {target_memory_mb}MB, max: {max_memory_mb}MB)")
            print(f"  Log: {config.get_balloon_log_file(name)}")
            print()
    
    return success


def main() -> int:
    """Entry point for vm-run command."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Auto-setup and start the Student VM with GUI"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force recreation of VM images"
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
    parser.add_argument(
        "--locale", "-l",
        type=str,
        default="en_US.UTF-8",
        help="System locale (default: en_US.UTF-8, e.g., cs_CZ.UTF-8 for Czech)"
    )
    parser.add_argument(
        "--keyboard", "-k",
        type=str,
        default="us",
        help="Keyboard layout (default: us, e.g., cz for Czech)"
    )
    
    args = parser.parse_args()
    
    success = run_vm(
        force_setup=args.force,
        shared_dir=args.shared_dir,
        port=args.port,
        memory=args.memory,
        cpus=args.cpus,
        locale=args.locale,
        keyboard=args.keyboard,
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
