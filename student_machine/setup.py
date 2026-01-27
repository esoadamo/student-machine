"""VM Setup - Download and configure the Student VM."""

import sys
from pathlib import Path
from typing import Optional

from . import config
from . import utils
from . import cloud_init


def setup_vm(
    force: bool = False,
    locale: str = "en_US.UTF-8",
    keyboard: str = "us",
) -> bool:
    """
    Set up the Student VM.
    
    Downloads Debian cloud image and creates the VM disk with cloud-init.
    
    Args:
        force: If True, recreate the VM even if it exists.
        locale: System locale (e.g., 'en_US.UTF-8', 'cs_CZ.UTF-8').
        keyboard: Keyboard layout (e.g., 'us', 'cz').
    
    Returns:
        True if setup was successful, False otherwise.
    """
    print("=" * 60)
    print("Student VM Setup")
    print("=" * 60)
    print()
    
    # Check QEMU installation
    if not utils.check_qemu_installed():
        print("Error: QEMU is not installed or not in PATH.")
        print(utils.get_installation_instructions())
        return False
    
    if not utils.check_qemu_img_installed():
        print("Error: qemu-img is not installed or not in PATH.")
        print(utils.get_installation_instructions())
        return False
    
    # Create VM directory
    vm_dir = config.get_vm_dir()
    vm_dir.mkdir(parents=True, exist_ok=True)
    print(f"VM directory: {vm_dir}")
    print()
    
    # Get paths
    base_image = config.get_base_image_path()
    vm_image = config.get_image_path()
    seed_image = config.get_seed_image_path()
    arch = config.get_arch()
    
    # Download Debian cloud image
    print("=== Downloading Debian 12 cloud image ===")
    if base_image.exists() and not force:
        print(f"Base image already exists: {base_image}")
    else:
        if arch not in config.DEBIAN_IMAGE_URLS:
            print(f"Error: Unsupported architecture: {arch}")
            return False
        
        url = config.DEBIAN_IMAGE_URLS[arch]
        if not utils.download_file(url, base_image):
            return False
        print(f"Downloaded: {base_image}")
    print()
    
    # Create VM disk image
    print("=== Creating VM disk image ===")
    if vm_image.exists() and not force:
        print(f"VM image already exists: {vm_image}")
    else:
        if vm_image.exists():
            vm_image.unlink()
        
        utils.run_command([
            "qemu-img", "create",
            "-f", "qcow2",
            "-b", str(base_image),
            "-F", "qcow2",
            str(vm_image),
            config.IMAGE_SIZE
        ])
        print(f"Created VM image: {vm_image}")
    print()
    
    # Create cloud-init seed image
    print("=== Creating cloud-init seed image ===")
    print(f"Locale: {locale}, Keyboard: {keyboard}")
    if seed_image.exists() and not force:
        print(f"Seed image already exists: {seed_image}")
    else:
        if seed_image.exists():
            seed_image.unlink()
        
        user_data = cloud_init.get_user_data(locale=locale, keyboard=keyboard)
        meta_data = cloud_init.get_meta_data()
        
        if not utils.create_cloud_init_iso(seed_image, user_data, meta_data):
            return False
        print(f"Created seed image: {seed_image}")
    print()
    
    # Create data directory for shared folders
    data_dir = config.get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    print(f"Shared folder: {data_dir}")
    print()
    
    print("=" * 60)
    print("VM setup complete!")
    print("=" * 60)
    print()
    print(f"  VM Image:     {vm_image}")
    print(f"  Seed Image:   {seed_image}")
    print(f"  Shared Dir:   {data_dir}")
    print()
    print("To start the VM, run:")
    print("  student-machine start")
    print()
    print("Or with GUI:")
    print("  student-machine start --gui")
    print()
    
    return True


def main() -> int:
    """Entry point for vm-setup command."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Set up the Student VM"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force recreation of VM images"
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
    
    success = setup_vm(
        force=args.force,
        locale=args.locale,
        keyboard=args.keyboard,
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
