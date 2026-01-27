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
    
    # Balloon command (memory management)
    balloon_parser = subparsers.add_parser(
        "balloon",
        help="Start memory balloon controller for dynamic memory management"
    )
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
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    if args.command == "setup":
        from .setup import setup_vm
        success = setup_vm(
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
            locale=args.locale,
            keyboard=args.keyboard,
        )
        return 0 if success else 1
    
    elif args.command == "balloon":
        from .balloon import (
            MemoryBalloonController, get_qmp_socket_path, 
            is_balloon_running, get_balloon_pid_file
        )
        from .start import get_host_memory_mb
        from . import config
        from pathlib import Path
        import os
        
        qmp_socket = get_qmp_socket_path()
        shared_dir = Path(args.shared_dir) if args.shared_dir else config.get_data_dir()
        
        if not qmp_socket.exists():
            print("Error: VM is not running (QMP socket not found)")
            print("Start the VM first with: student-machine start")
            return 1
        
        # Check if balloon is already running
        running, existing_pid = is_balloon_running()
        if running:
            print(f"Balloon controller is already running (PID: {existing_pid})")
            print(f"  Log: ~/.vm/balloon.log")
            print()
            print(f"To stop: kill {existing_pid}")
            return 0
        
        # Use host memory - 1GB as default max
        max_memory = args.max_memory
        if max_memory == 0:  # Use default
            max_memory = get_host_memory_mb() - 1024
        
        # Run in background unless --foreground is specified
        if not args.foreground:
            # Fork to background
            pid = os.fork()
            if pid > 0:
                # Parent process - write PID and exit
                balloon_pid_file = get_balloon_pid_file()
                balloon_pid_file.write_text(str(pid))
                print(f"Memory balloon controller started in background (PID: {pid})")
                print(f"  Min memory: {args.min_memory}MB")
                print(f"  Max memory: {max_memory}MB")
                print(f"  Log: ~/.vm/balloon.log")
                print()
                print(f"To stop: kill {pid}")
                return 0
            else:
                # Child process - detach and run
                os.setsid()
                # Redirect stdout/stderr to log file
                log_file = config.get_vm_dir() / "balloon.log"
                with open(log_file, "a") as log:
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
            shared_dir=shared_dir,
            min_memory_mb=args.min_memory,
            max_memory_mb=max_memory,
        )
        
        try:
            controller._run_loop()
        except KeyboardInterrupt:
            if args.foreground:
                print("\nStopping balloon controller...")
        
        return 0
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
