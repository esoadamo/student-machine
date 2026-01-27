"""VM Backup and Restore - Backup/restore complete VM state."""

import json
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import config


# Backup format version for future compatibility
BACKUP_VERSION = 1


def backup_vm(
    output_path: Path,
    name: str = config.DEFAULT_VM_NAME,
    compress: bool = True,
) -> bool:
    """
    Backup a VM to a portable archive.
    
    Creates a tarball containing:
    - VM disk image (qcow2)
    - Cloud-init seed image
    - Metadata (config, version info)
    
    Args:
        output_path: Path for the backup archive
        name: Name of the VM to backup
        compress: Whether to compress the archive (gzip)
    
    Returns:
        True if backup was successful, False otherwise.
    """
    from . import utils
    
    print("=== Backing up VM ===")
    print()
    
    vm_dir = config.get_vm_subdir(name)
    vm_image = config.get_image_path(name)
    seed_image = config.get_seed_image_path(name)
    data_dir = config.get_data_dir(name)
    
    # Check if VM exists
    if not vm_image.exists():
        print(f"Error: VM image not found: {vm_image}")
        print(f"No VM named '{name}' exists.")
        return False
    
    # Check if VM is running
    is_running, pid = utils.is_vm_running(name)
    if is_running:
        print(f"Warning: VM '{name}' is running (PID: {pid})")
        print("For a consistent backup, consider stopping the VM first.")
        print("Continuing with backup of potentially inconsistent state...")
        print()
    
    # Gather files to backup
    files_to_backup = []
    
    if vm_image.exists():
        files_to_backup.append(("vm.qcow2", vm_image))
        print(f"  VM Image:   {vm_image} ({vm_image.stat().st_size / (1024*1024):.1f} MB)")
    
    if seed_image.exists():
        files_to_backup.append(("seed.iso", seed_image))
        print(f"  Seed Image: {seed_image} ({seed_image.stat().st_size / 1024:.1f} KB)")
    
    # Include data directory if it exists and has content
    if data_dir.exists() and any(data_dir.iterdir()):
        print(f"  Data Dir:   {data_dir}")
    
    print()
    
    # Create metadata
    metadata = {
        "version": BACKUP_VERSION,
        "created": datetime.now().isoformat(),
        "vm_name": name,
        "arch": config.get_arch(),
        "files": [f[0] for f in files_to_backup],
        "has_data": data_dir.exists() and any(data_dir.iterdir()),
    }
    
    # Create the backup archive
    mode = "w:gz" if compress else "w"
    if not output_path.suffix:
        output_path = output_path.with_suffix(".tar.gz" if compress else ".tar")
    
    print(f"Creating backup: {output_path}")
    
    try:
        with tarfile.open(output_path, mode) as tar:
            # Add metadata
            metadata_json = json.dumps(metadata, indent=2).encode()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
                tmp.write(metadata_json)
                tmp.flush()
                tar.add(tmp.name, arcname="metadata.json")
                Path(tmp.name).unlink()
            
            # Add VM files
            for arcname, filepath in files_to_backup:
                print(f"  Adding: {arcname}...")
                tar.add(filepath, arcname=arcname)
            
            # Add data directory contents if present
            if data_dir.exists() and any(data_dir.iterdir()):
                print("  Adding: data/...")
                for item in data_dir.iterdir():
                    # Skip hidden status files
                    if item.name.startswith(".vm-"):
                        continue
                    tar.add(item, arcname=f"data/{item.name}")
        
        final_size = output_path.stat().st_size / (1024 * 1024)
        print()
        print(f"✓ Backup complete: {output_path} ({final_size:.1f} MB)")
        return True
        
    except Exception as e:
        print(f"Error creating backup: {e}")
        if output_path.exists():
            output_path.unlink()
        return False


def restore_vm(
    backup_path: Path,
    name: Optional[str] = None,
    force: bool = False,
) -> bool:
    """
    Restore a VM from a backup archive.
    
    Args:
        backup_path: Path to the backup archive
        name: Name for the restored VM (default: original name from backup)
        force: Overwrite existing VM if it exists
    
    Returns:
        True if restore was successful, False otherwise.
    """
    from . import utils
    
    print("=== Restoring VM ===")
    print()
    
    if not backup_path.exists():
        print(f"Error: Backup file not found: {backup_path}")
        return False
    
    # Determine archive mode
    if backup_path.suffix == ".gz" or str(backup_path).endswith(".tar.gz"):
        mode = "r:gz"
    else:
        mode = "r"
    
    try:
        with tarfile.open(backup_path, mode) as tar:
            # Read metadata
            try:
                metadata_file = tar.extractfile("metadata.json")
                if metadata_file:
                    metadata = json.loads(metadata_file.read().decode())
                else:
                    print("Warning: No metadata found in backup, using defaults")
                    metadata = {"vm_name": config.DEFAULT_VM_NAME, "version": 1}
            except KeyError:
                print("Warning: No metadata found in backup, using defaults")
                metadata = {"vm_name": config.DEFAULT_VM_NAME, "version": 1}
            
            # Determine VM name
            original_name = metadata.get("vm_name", config.DEFAULT_VM_NAME)
            vm_name = name if name else original_name
            
            print(f"Backup info:")
            print(f"  Version:  {metadata.get('version', 'unknown')}")
            print(f"  Created:  {metadata.get('created', 'unknown')}")
            print(f"  Original: {original_name}")
            print(f"  Arch:     {metadata.get('arch', 'unknown')}")
            print()
            
            # Check architecture compatibility
            current_arch = config.get_arch()
            backup_arch = metadata.get("arch", current_arch)
            if backup_arch != current_arch:
                print(f"Warning: Architecture mismatch!")
                print(f"  Backup: {backup_arch}, Current: {current_arch}")
                print("  The VM may not run correctly.")
                print()
            
            # Check if VM already exists
            vm_dir = config.get_vm_subdir(vm_name)
            vm_image = config.get_image_path(vm_name)
            
            if vm_image.exists():
                if not force:
                    print(f"Error: VM '{vm_name}' already exists.")
                    print("Use --force to overwrite, or specify a different --name")
                    return False
                
                # Check if running
                is_running, pid = utils.is_vm_running(vm_name)
                if is_running:
                    print(f"Error: VM '{vm_name}' is currently running (PID: {pid})")
                    print("Stop the VM first with: student-machine stop")
                    return False
                
                print(f"Overwriting existing VM: {vm_name}")
            
            # Create VM directory
            vm_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract files
            print(f"Restoring to: {vm_dir}")
            
            for member in tar.getmembers():
                if member.name == "metadata.json":
                    continue
                
                if member.name == "vm.qcow2":
                    dest = config.get_image_path(vm_name)
                    print(f"  Extracting: {member.name} -> {dest}")
                    src = tar.extractfile(member)
                    if src:
                        with open(dest, "wb") as dst:
                            while chunk := src.read(1024 * 1024):
                                dst.write(chunk)
                        src.close()
                
                elif member.name == "seed.iso":
                    dest = config.get_seed_image_path(vm_name)
                    print(f"  Extracting: {member.name} -> {dest}")
                    src = tar.extractfile(member)
                    if src:
                        with open(dest, "wb") as dst:
                            dst.write(src.read())
                        src.close()
                
                elif member.name.startswith("data/"):
                    data_dir = config.get_data_dir(vm_name)
                    data_dir.mkdir(parents=True, exist_ok=True)
                    rel_path = member.name[5:]  # Remove "data/" prefix
                    if rel_path:  # Skip the data/ directory entry itself
                        dest = data_dir / rel_path
                        print(f"  Extracting: {member.name} -> {dest}")
                        if member.isdir():
                            dest.mkdir(parents=True, exist_ok=True)
                        else:
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            src = tar.extractfile(member)
                            if src:
                                with open(dest, "wb") as dst:
                                    dst.write(src.read())
                                src.close()
            
            print()
            print(f"✓ VM '{vm_name}' restored successfully!")
            print()
            print("To start the VM:")
            if vm_name != config.DEFAULT_VM_NAME:
                print(f"  student-machine start --name {vm_name}")
            else:
                print("  student-machine start")
            
            return True
            
    except tarfile.TarError as e:
        print(f"Error reading backup archive: {e}")
        return False
    except Exception as e:
        print(f"Error during restore: {e}")
        return False


def list_vms() -> list[str]:
    """List all VMs in the VM directory."""
    vm_dir = config.get_vm_dir()
    vms = []
    
    if not vm_dir.exists():
        return vms
    
    # Check for default VM
    default_image = config.get_image_path(config.DEFAULT_VM_NAME)
    if default_image.exists():
        vms.append(config.DEFAULT_VM_NAME)
    
    # Check subdirectories for other VMs
    for subdir in vm_dir.iterdir():
        if subdir.is_dir() and subdir.name != "data":
            potential_image = subdir / f"{subdir.name}.qcow2"
            if potential_image.exists():
                vms.append(subdir.name)
    
    return sorted(vms)
