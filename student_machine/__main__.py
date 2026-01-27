"""Main CLI entry point for Student Machine."""

import argparse
import sys

from . import __version__


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
    setup_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force recreation of VM images"
    )
    
    # Start command
    start_parser = subparsers.add_parser(
        "start",
        help="Start the Student VM"
    )
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
    
    # Stop command
    stop_parser = subparsers.add_parser(
        "stop",
        help="Stop the Student VM"
    )
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
    subparsers.add_parser(
        "status",
        help="Show the Student VM status"
    )
    
    # Service command
    service_parser = subparsers.add_parser(
        "service",
        help="Manage Student VM system service"
    )
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
    run_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force recreation of VM images"
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
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    if args.command == "setup":
        from .setup import setup_vm
        success = setup_vm(force=args.force)
        return 0 if success else 1
    
    elif args.command == "start":
        from .start import start_vm
        from pathlib import Path
        shared_dir = Path(args.shared_dir) if args.shared_dir else None
        success = start_vm(
            gui=args.gui,
            console=args.console,
            shared_dir=shared_dir,
            port=args.port,
            memory=args.memory,
            cpus=args.cpus,
        )
        return 0 if success else 1
    
    elif args.command == "stop":
        from .stop import stop_vm
        success = stop_vm(force=args.force, timeout=args.timeout)
        return 0 if success else 1
    
    elif args.command == "status":
        from .status import status_vm
        is_running = status_vm()
        return 0 if is_running else 1
    
    elif args.command == "service":
        from .service import install_service, uninstall_service
        if args.action == "install":
            success = install_service()
        else:
            success = uninstall_service()
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
        from .run import run_vm
        from pathlib import Path
        shared_dir = Path(args.shared_dir) if args.shared_dir else None
        success = run_vm(
            force_setup=args.force,
            shared_dir=shared_dir,
            port=args.port,
            memory=args.memory,
            cpus=args.cpus,
        )
        return 0 if success else 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
