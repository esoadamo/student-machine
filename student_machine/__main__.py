"""Main CLI entry point for Student Machine."""

import argparse
import sys

from . import __version__
from . import config


def add_name_argument(parser: argparse.ArgumentParser) -> None:
    """Add the --name argument to a parser."""
    parser.add_argument(
        "--name", "-n",
        type=str,
        default=config.DEFAULT_VM_NAME,
        help=f"VM name (default: {config.DEFAULT_VM_NAME})"
    )


def main() -> int:
    """Main entry point for the student-machine CLI."""
    parser = argparse.ArgumentParser(
        prog="student-machine",
        description="Student Machine - Cross-platform QEMU VM manager for students",
    )
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"student-machine {__version__}"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Setup command
    setup_parser = subparsers.add_parser(
        "setup",
        help="Set up the Student VM (download Debian image, create disk)"
    )
    add_name_argument(setup_parser)
    setup_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force recreation of VM images"
    )
    setup_parser.add_argument(
        "--locale", "-l",
        type=str,
        default="en_US.UTF-8",
        help="System locale (default: en_US.UTF-8, e.g., cs_CZ.UTF-8 for Czech)"
    )
    setup_parser.add_argument(
        "--keyboard", "-k",
        type=str,
        default="us",
        help="Keyboard layout (default: us, e.g., cz for Czech)"
    )
    
    # Start command
    start_parser = subparsers.add_parser(
        "start",
        help="Start the Student VM"
    )
    add_name_argument(start_parser)
    start_parser.add_argument(
        "--gui",
        action="store_true",
        help="Enable graphical display"
    )
    start_parser.add_argument(
        "--console",
        action="store_true",
        help="Enable serial console"
    )
    start_parser.add_argument(
        "--shared-dir",
        type=str,
        help="Directory to share with VM (default: ~/.vm/data)"
    )
    start_parser.add_argument(
        "--port", "-p",
        type=int,
        default=2222,
        help="SSH port forwarding (default: 2222)"
    )
    start_parser.add_argument(
        "--memory", "-m",
        type=str,
        help="Memory allocation (default: 2048M)"
    )
    start_parser.add_argument(
        "--cpus", "-c",
        type=int,
        help="Number of CPUs (default: 2)"
    )
    start_parser.add_argument(
        "--ssh",
        action="store_true",
        help="Enable SSH port forwarding"
    )
    start_parser.add_argument(
        "--vnc",
        action="store_true",
        help="Enable VNC port forwarding"
    )
    
    # Stop command
    stop_parser = subparsers.add_parser(
        "stop",
        help="Stop the Student VM"
    )
    add_name_argument(stop_parser)
    stop_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force kill the VM without graceful shutdown"
    )
    stop_parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=30,
        help="Seconds to wait for graceful shutdown (default: 30)"
    )
    
    # Status command
    status_parser = subparsers.add_parser(
        "status",
        help="Show the Student VM status"
    )
    add_name_argument(status_parser)
    
    # Service command
    service_parser = subparsers.add_parser(
        "service",
        help="Manage Student VM system service"
    )
    add_name_argument(service_parser)
    service_parser.add_argument(
        "action",
        choices=["install", "uninstall"],
        help="Action to perform"
    )
    
    # SSH command (convenience)
    ssh_parser = subparsers.add_parser(
        "ssh",
        help="SSH into the Student VM"
    )
    add_name_argument(ssh_parser)
    ssh_parser.add_argument(
        "--port", "-p",
        type=int,
        default=2222,
        help="SSH port (default: 2222)"
    )
    
    # Run command (auto-setup + auto-start with GUI)
    run_parser = subparsers.add_parser(
        "run",
        help="Auto-setup (if needed) and start VM with GUI (one-click mode)"
    )
    add_name_argument(run_parser)
    run_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force recreation of VM images"
    )
    run_parser.add_argument(
        "--from-url",
        type=str,
        help="Bootstrap VM from a backup URL"
    )
    run_parser.add_argument(
        "--shared-dir",
        type=str,
        help="Directory to share with VM (default: ~/.vm/data)"
    )
    run_parser.add_argument(
        "--port", "-p",
        type=int,
        default=2222,
        help="SSH port forwarding (default: 2222)"
    )
    run_parser.add_argument(
        "--memory", "-m",
        type=str,
        help="Memory allocation (default: 2048M)"
    )
    run_parser.add_argument(
        "--cpus", "-c",
        type=int,
        help="Number of CPUs (default: 2)"
    )
    run_parser.add_argument(
        "--locale", "-l",
        type=str,
        default="en_US.UTF-8",
        help="System locale (default: en_US.UTF-8, e.g., cs_CZ.UTF-8 for Czech)"
    )
    run_parser.add_argument(
        "--keyboard", "-k",
        type=str,
        default="us",
        help="Keyboard layout (default: us, e.g., cz for Czech)"
    )
    run_parser.add_argument(
        "--ssh",
        action="store_true",
        help="Enable SSH port forwarding"
    )
    run_parser.add_argument(
        "--vnc",
        action="store_true",
        help="Enable VNC port forwarding"
    )
    
    # Balloon command (memory management)
    balloon_parser = subparsers.add_parser(
        "balloon",
        help="Start memory balloon controller for dynamic memory management"
    )
    add_name_argument(balloon_parser)
    balloon_parser.add_argument(
        "--min-memory", "-min",
        type=int,
        default=1024,
        help="Minimum VM memory in MB (default: 1024)"
    )
    balloon_parser.add_argument(
        "--max-memory", "-max",
        type=int,
        default=0,
        help="Maximum VM memory in MB (default: host RAM - 1GB)"
    )
    balloon_parser.add_argument(
        "--shared-dir",
        type=str,
        help="Directory shared with VM (default: ~/.vm/data)"
    )
    balloon_parser.add_argument(
        "--foreground", "-fg",
        action="store_true",
        help="Run in foreground instead of background"
    )
    
    # Backup command
    backup_parser = subparsers.add_parser(
        "backup",
        help="Backup VM to a portable archive"
    )
    add_name_argument(backup_parser)
    backup_parser.add_argument(
        "output",
        type=str,
        help="Output path for backup archive (e.g., my-vm-backup.tar.gz)"
    )
    backup_parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Don't compress the archive"
    )
    
    # Restore command
    restore_parser = subparsers.add_parser(
        "restore",
        help="Restore VM from a backup archive"
    )
    restore_parser.add_argument(
        "backup",
        type=str,
        nargs="?",
        help="Path to backup archive"
    )
    restore_parser.add_argument(
        "--from-url",
        type=str,
        help="URL to download backup from"
    )
    restore_parser.add_argument(
        "--name", "-n",
        type=str,
        help="Name for restored VM (default: original name from backup)"
    )
    restore_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite existing VM"
    )
    
    # List command
    list_parser = subparsers.add_parser(
        "list",
        help="List all VMs"
    )
    
    # QEMU install command
    qemu_install_parser = subparsers.add_parser(
        "qemu-install",
        help="Install QEMU and prerequisites for current OS"
    )
    qemu_install_parser.add_argument(
        "--check",
        action="store_true",
        help="Only check prerequisites, don't install"
    )
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    if args.command == "setup":
        from .setup import setup_vm
        success = setup_vm(
            name=args.name,
            force=args.force,
            locale=args.locale,
            keyboard=args.keyboard,
        )
        return 0 if success else 1
    
    elif args.command == "start":
        from .start import start_vm
        from pathlib import Path
        shared_dir = Path(args.shared_dir) if args.shared_dir else None
        success = start_vm(
            name=args.name,
            gui=args.gui,
            console=args.console,
            shared_dir=shared_dir,
            port=args.port,
            memory=args.memory,
            cpus=args.cpus,
            ssh=args.ssh,
            vnc=args.vnc,
        )
        return 0 if success else 1
    
    elif args.command == "stop":
        from .stop import stop_vm
        success = stop_vm(name=args.name, force=args.force, timeout=args.timeout)
        return 0 if success else 1
    
    elif args.command == "status":
        from .status import status_vm
        is_running = status_vm(name=args.name)
        return 0 if is_running else 1
    
    elif args.command == "service":
        from .service import install_service, uninstall_service
        if args.action == "install":
            success = install_service(name=args.name)
        else:
            success = uninstall_service(name=args.name)
        return 0 if success else 1
    
    elif args.command == "ssh":
        import subprocess
        import shutil
        
        ssh_cmd = shutil.which("ssh")
        if not ssh_cmd:
            print("Error: ssh command not found")
            return 1
        
        try:
            subprocess.run([
                ssh_cmd,
                "-p", str(args.port),
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "student@localhost"
            ])
            return 0
        except KeyboardInterrupt:
            return 0
        except Exception as e:
            print(f"Error: {e}")
            return 1
    
    elif args.command == "run":
        from .qemu_install import check_and_prompt_install
        
        # Check prerequisites before running
        if not check_and_prompt_install():
            return 1
        
        from .run import run_vm
        from pathlib import Path
        shared_dir = Path(args.shared_dir) if args.shared_dir else None
        success = run_vm(
            name=args.name,
            force_setup=args.force,
            shared_dir=shared_dir,
            port=args.port,
            memory=args.memory,
            cpus=args.cpus,
            locale=args.locale,
            keyboard=args.keyboard,
            ssh=args.ssh,
            vnc=args.vnc,
            from_url=args.from_url,
        )
        return 0 if success else 1
    
    elif args.command == "balloon":
        from .balloon import (
            MemoryBalloonController, get_qmp_socket_path, 
            is_balloon_running, get_balloon_pid_file
        )
        from .start import get_host_memory_mb
        from pathlib import Path
        import os
        
        system = config.get_system()
        qmp_socket = config.get_monitor_socket(args.name)
        shared_dir = Path(args.shared_dir) if args.shared_dir else config.get_data_dir(args.name)
        qmp_host = None
        qmp_port = None
        
        if system == "windows":
            qmp_host = "127.0.0.1"
            qmp_port = config.get_monitor_port(args.name)
        else:
            if not qmp_socket.exists():
                print(f"Error: VM '{args.name}' is not running (QMP socket not found)")
                print("Start the VM first with: student-machine start")
                return 1
        
        # Check if balloon is already running
        running, existing_pid = is_balloon_running(args.name)
        if running:
            print(f"Balloon controller is already running (PID: {existing_pid})")
            print(f"  Log: {config.get_balloon_log_file(args.name)}")
            print()
            print(f"To stop: kill {existing_pid}")
            return 0
        
        # Use host memory - 1GB as default max
        max_memory = args.max_memory
        if max_memory == 0:  # Use default
            max_memory = get_host_memory_mb() - 1024
        
        # Run in background unless --foreground is specified
        if system == "windows" and not args.foreground:
            print("Background balloon controller is not supported on Windows. Running in foreground.")
            args.foreground = True

        if not args.foreground:
            # Fork to background
            pid = os.fork()
            if pid > 0:
                # Parent process - write PID and exit
                balloon_pid_file = get_balloon_pid_file(args.name)
                balloon_pid_file.write_text(str(pid), encoding="utf-8")
                print(f"Memory balloon controller started in background (PID: {pid})")
                print(f"  Min memory: {args.min_memory}MB")
                print(f"  Max memory: {max_memory}MB")
                print(f"  Log: {config.get_balloon_log_file(args.name)}")
                print()
                print(f"To stop: kill {pid}")
                return 0
            else:
                # Child process - detach and run
                os.setsid()
                # Redirect stdout/stderr to log file
                log_file = config.get_balloon_log_file(args.name)
                with open(log_file, "a", encoding="utf-8") as log:
                    os.dup2(log.fileno(), 1)
                    os.dup2(log.fileno(), 2)
        else:
            print("Starting memory balloon controller (foreground)...")
            print(f"  Min memory: {args.min_memory}MB")
            print(f"  Max memory: {max_memory}MB")
            print(f"  Shared dir: {shared_dir}")
            print()
            print("Press Ctrl+C to stop")
            print()
        
        controller = MemoryBalloonController(
            qmp_socket=qmp_socket,
            qmp_host=qmp_host,
            qmp_port=qmp_port,
            shared_dir=shared_dir,
            min_memory_mb=args.min_memory,
            max_memory_mb=max_memory,
            name=args.name,
        )
        
        try:
            controller._run_loop()
        except KeyboardInterrupt:
            if args.foreground:
                print("\nStopping balloon controller...")
        
        return 0
    
    elif args.command == "backup":
        from .backup import backup_vm
        from pathlib import Path
        success = backup_vm(
            output_path=Path(args.output),
            name=args.name,
            compress=not args.no_compress,
        )
        return 0 if success else 1
    
    elif args.command == "restore":
        from .backup import restore_vm
        from pathlib import Path
        
        # Check if we have either backup path or URL
        if not args.backup and not args.from_url:
            print("Error: Either provide a backup path or use --from-url")
            return 1
        
        backup_path = Path(args.backup) if args.backup else None
        success = restore_vm(
            backup_path=backup_path,
            backup_url=args.from_url,
            name=args.name,
            force=args.force,
        )
        return 0 if success else 1
    
    elif args.command == "list":
        from .backup import list_vms
        from . import utils
        
        vms = list_vms()
        if not vms:
            print("No VMs found.")
            print()
            print("Create a VM with: student-machine run")
            return 0
        
        print("=== Available VMs ===")
        print()
        for vm_name in vms:
            is_running, pid = utils.is_vm_running(vm_name)
            status = f"running (PID: {pid})" if is_running else "stopped"
            vm_image = config.get_image_path(vm_name)
            size_mb = vm_image.stat().st_size / (1024 * 1024)
            print(f"  {vm_name}: {status} ({size_mb:.1f} MB)")
        print()
        return 0
    
    elif args.command == "qemu-install":
        from .qemu_install import check_prerequisites, print_status, install_qemu
        
        status = check_prerequisites()
        
        if args.check:
            print()
            print_status(status)
            return 0 if status["all_ok"] else 1
        else:
            success = install_qemu()
            return 0 if success else 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
