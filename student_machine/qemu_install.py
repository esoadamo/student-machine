"""QEMU installation and prerequisite checking."""

import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

# QEMU installer URLs
QEMU_WINDOWS_URL = "https://cdn.adamhlavacek.com/qemu-windows.zip"
QEMU_WINDOWS_ARCHIVE = "qemu-windows.zip"


def get_qemu_binary() -> str:
    """Get the QEMU binary name for current architecture."""
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        return "qemu-system-x86_64"
    elif machine in ("aarch64", "arm64"):
        return "qemu-system-aarch64"
    else:
        return "qemu-system-x86_64"


def is_qemu_installed() -> bool:
    """Check if QEMU is installed and accessible."""
    qemu_bin = get_qemu_binary()
    return shutil.which(qemu_bin) is not None


def get_qemu_version() -> str | None:
    """Get installed QEMU version."""
    qemu_bin = get_qemu_binary()
    try:
        result = subprocess.run(
            [qemu_bin, "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            # First line usually contains version
            return result.stdout.split("\n")[0]
    except Exception:
        pass
    return None


def check_prerequisites() -> dict:
    """Check all prerequisites and return status."""
    system = platform.system()
    
    status = {
        "system": system,
        "qemu_installed": is_qemu_installed(),
        "qemu_version": get_qemu_version(),
        "all_ok": False,
    }
    
    # Check KVM on Linux
    if system == "Linux":
        status["kvm_available"] = Path("/dev/kvm").exists()
        kvm_access = False
        if status["kvm_available"]:
            try:
                with open("/dev/kvm", "r", encoding="utf-8"):
                    kvm_access = True
            except PermissionError:
                kvm_access = False
            except Exception:
                kvm_access = False
        status["kvm_accessible"] = kvm_access
    
    status["all_ok"] = status["qemu_installed"]
    
    return status


def print_status(status: dict) -> None:
    """Print prerequisite status."""
    print("Prerequisite Status")
    print("=" * 40)
    print(f"Operating System: {status['system']}")
    print()
    
    # QEMU
    if status["qemu_installed"]:
        print(f"✓ QEMU: Installed")
        if status["qemu_version"]:
            print(f"  {status['qemu_version']}")
    else:
        print("✗ QEMU: Not installed")
    
    # KVM on Linux
    if status["system"] == "Linux":
        if status.get("kvm_available"):
            if status.get("kvm_accessible"):
                print("✓ KVM: Available and accessible")
            else:
                print("⚠ KVM: Available but not accessible (add user to kvm group)")
        else:
            print("⚠ KVM: Not available (will use software emulation)")
    
    print()


def install_linux() -> bool:
    """Install QEMU on Linux."""
    print("Installing QEMU on Linux...")
    print()
    
    # Detect package manager
    if shutil.which("apt"):
        # Debian/Ubuntu
        print("Detected: Debian/Ubuntu (apt)")
        print()
        print("Run the following command:")
        print()
        print("  sudo apt update && sudo apt install -y qemu-system-x86 qemu-utils")
        print()
        
        response = input("Run this command now? [y/N]: ").strip().lower()
        if response == "y":
            try:
                subprocess.run(["sudo", "apt", "update"], check=True)
                subprocess.run([
                    "sudo", "apt", "install", "-y",
                    "qemu-system-x86", "qemu-utils"
                ], check=True)
                print()
                print("✓ Installation complete!")
                
                # Check KVM access
                if Path("/dev/kvm").exists():
                    try:
                        with open("/dev/kvm", "r", encoding="utf-8"):
                            pass
                    except PermissionError:
                        print()
                        print("Note: To enable KVM acceleration, run:")
                        print("  sudo usermod -aG kvm $USER")
                        print("Then log out and back in.")
                
                return True
            except subprocess.CalledProcessError as e:
                print(f"Installation failed: {e}")
                return False
        else:
            print("Skipped.")
            return False
    
    elif shutil.which("dnf"):
        # Fedora/RHEL
        print("Detected: Fedora/RHEL (dnf)")
        print()
        print("Run the following command:")
        print()
        print("  sudo dnf install -y qemu-system-x86 qemu-img")
        print()
        
        response = input("Run this command now? [y/N]: ").strip().lower()
        if response == "y":
            try:
                subprocess.run([
                    "sudo", "dnf", "install", "-y",
                    "qemu-system-x86", "qemu-img"
                ], check=True)
                print()
                print("✓ Installation complete!")
                return True
            except subprocess.CalledProcessError as e:
                print(f"Installation failed: {e}")
                return False
        else:
            print("Skipped.")
            return False
    
    elif shutil.which("pacman"):
        # Arch Linux
        print("Detected: Arch Linux (pacman)")
        print()
        print("Run the following command:")
        print()
        print("  sudo pacman -S qemu-full")
        print()
        
        response = input("Run this command now? [y/N]: ").strip().lower()
        if response == "y":
            try:
                subprocess.run([
                    "sudo", "pacman", "-S", "--noconfirm",
                    "qemu-full"
                ], check=True)
                print()
                print("✓ Installation complete!")
                return True
            except subprocess.CalledProcessError as e:
                print(f"Installation failed: {e}")
                return False
        else:
            print("Skipped.")
            return False
    
    elif shutil.which("zypper"):
        # openSUSE
        print("Detected: openSUSE (zypper)")
        print()
        print("Run the following command:")
        print()
        print("  sudo zypper install qemu-x86 qemu-tools")
        print()
        
        response = input("Run this command now? [y/N]: ").strip().lower()
        if response == "y":
            try:
                subprocess.run([
                    "sudo", "zypper", "install", "-y",
                    "qemu-x86", "qemu-tools"
                ], check=True)
                print()
                print("✓ Installation complete!")
                return True
            except subprocess.CalledProcessError as e:
                print(f"Installation failed: {e}")
                return False
        else:
            print("Skipped.")
            return False
    
    else:
        print("Could not detect package manager.")
        print()
        print("Please install QEMU manually:")
        print("  - qemu-system-x86_64 (or qemu-system-aarch64 for ARM)")
        print("  - qemu-img")
        return False


def install_macos() -> bool:
    """Install QEMU on macOS."""
    print("Installing QEMU on macOS...")
    print()
    
    if not shutil.which("brew"):
        print("Homebrew is not installed.")
        print()
        print("Install Homebrew first:")
        print('  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')
        print()
        print("Then run this command again.")
        return False
    
    print("Detected: Homebrew")
    print()
    print("Run the following command:")
    print()
    print("  brew install qemu")
    print()
    
    response = input("Run this command now? [y/N]: ").strip().lower()
    if response == "y":
        try:
            subprocess.run(["brew", "install", "qemu"], check=True)
            print()
            print("✓ Installation complete!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Installation failed: {e}")
            return False
    else:
        print("Skipped.")
        return False


def install_windows() -> bool:
    """Install QEMU on Windows."""
    print("Installing QEMU on Windows...")
    print()

    def find_qemu_bin_dir(search_paths: list[Path]) -> Path | None:
        for qemu_path in search_paths:
            for candidate in [
                qemu_path / "qemu-system-x86_64.exe",
                qemu_path / "qemu-system-aarch64.exe",
                qemu_path / "bin" / "qemu-system-x86_64.exe",
                qemu_path / "bin" / "qemu-system-aarch64.exe",
            ]:
                if candidate.exists():
                    return candidate.parent
        return None

    def add_to_user_path(paths: list[Path]) -> bool:
        current_path = os.environ.get("PATH", "")
        current_entries = [entry for entry in current_path.split(";") if entry]
        current_set = {entry.lower() for entry in current_entries}
        to_add = [str(path) for path in paths if str(path).lower() not in current_set]
        if not to_add:
            return False
        new_path = ";".join(current_entries + to_add)
        subprocess.run(["setx", "PATH", new_path], check=True)
        return True

    qemu_in_path = is_qemu_installed()
    if qemu_in_path:
        print("✓ QEMU is already installed!")
        if get_qemu_version():
            print(f"  {get_qemu_version()}")

    # Check common installation paths
    common_paths = [
        Path("C:/Program Files/qemu"),
        Path("C:/Program Files (x86)/qemu"),
        Path.home() / "qemu",
        Path(os.environ.get("LOCALAPPDATA", "")) / "qemu-windows",
    ]

    localappdata = os.environ.get("LOCALAPPDATA")
    qemu_bin_dir = find_qemu_bin_dir(common_paths)
    paths_to_add = []
    if qemu_bin_dir and not qemu_in_path:
        print(f"Found QEMU at: {qemu_bin_dir}")
        paths_to_add.append(qemu_bin_dir)

    if paths_to_add:
        print()
        print("Adding existing installs to PATH...")
        add_to_user_path(paths_to_add)
        print("✓ PATH updated.")
        print("Restart your terminal/command prompt to pick up PATH changes.")

    qemu_ready = qemu_in_path or qemu_bin_dir is not None
    if qemu_ready:
        return True
    
    # Download and install missing components
    need_qemu_download = not qemu_ready

    print("Downloading archive from:")
    if need_qemu_download:
        print(f"  {QEMU_WINDOWS_URL}")
    print()

    response = input("Download and install now? [y/N]: ").strip().lower()
    if response != "y":
        print("Skipped.")
        print()
        print("Manual installation:")
        step = 1
        if need_qemu_download:
            print(f"  {step}. Download: {QEMU_WINDOWS_URL}")
            step += 1
        if need_qemu_download:
            print(f"  {step}. Unpack qemu-windows into %LOCALAPPDATA%")
            step += 1
        if need_qemu_download:
            print(f"  {step}. Add %LOCALAPPDATA%\\qemu-windows to your user PATH")
        return False
    
    # Download to temp directory
    temp_dir = Path(tempfile.gettempdir())
    archive_path = temp_dir / QEMU_WINDOWS_ARCHIVE
    
    try:
        print("Downloading...")
        
        def download_with_progress(url: str, target_path: Path) -> None:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"}
            )

            with urllib.request.urlopen(req) as response, open(target_path, "wb") as out_file:
                total_size = int(response.headers.get("Content-Length", "0"))
                downloaded = 0
                block_size = 8192
                while True:
                    chunk = response.read(block_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    if total_size:
                        percent = int(downloaded * 100 / total_size)
                        print(f"\r  Progress: {percent}%", end="", flush=True)

            if total_size:
                print("\r  Progress: 100%", end="", flush=True)

        if need_qemu_download:
            print("Downloading QEMU...")
            download_with_progress(QEMU_WINDOWS_URL, archive_path)
            print()
        print()
        if need_qemu_download:
            print(f"Downloaded to: {archive_path}")
        print()
        print("Extracting archives...")

        if not localappdata:
            print("Error: LOCALAPPDATA is not set.")
            return False

        target_root = Path(localappdata)
        qemu_target_dir = target_root / "qemu-windows"

        if need_qemu_download:
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                zip_ref.extractall(target_root)
            if not qemu_target_dir.exists():
                print(f"Error: {qemu_target_dir} was not found after extraction.")
                return False

        # Find QEMU binary directory to add to PATH
        qemu_bin_dir = None
        if need_qemu_download:
            qemu_bin_dir = find_qemu_bin_dir([qemu_target_dir])
            if not qemu_bin_dir:
                print("Error: QEMU executable not found in extracted folder.")
                return False

        paths_to_add = []
        if qemu_bin_dir and not qemu_in_path:
            paths_to_add.append(qemu_bin_dir)

        if paths_to_add:
            add_to_user_path(paths_to_add)

        print()
        print("✓ Installation complete!")
        if need_qemu_download:
            print(f"  Installed to: {qemu_target_dir}")
        if qemu_bin_dir and not qemu_in_path:
            print(f"  Added to user PATH: {qemu_bin_dir}")
        print()
        print("Restart your terminal/command prompt to pick up PATH changes.")

        return True
        
    except Exception as e:
        print(f"Error: {e}")
        print()
        print("Manual installation:")
        step = 1
        if need_qemu_download:
            print(f"  {step}. Download: {QEMU_WINDOWS_URL}")
            step += 1
        if need_qemu_download:
            print(f"  {step}. Unpack qemu-windows into %LOCALAPPDATA%")
            step += 1
        if need_qemu_download:
            print(f"  {step}. Add %LOCALAPPDATA%\\qemu-windows to your user PATH")
        return False


def install_qemu(auto: bool = False) -> bool:
    """Install QEMU for the current operating system.
    
    Args:
        auto: If True, skip confirmation prompts (for CI/automation)
    """
    status = check_prerequisites()
    
    print()
    print_status(status)
    
    if status["all_ok"]:
        print("All prerequisites are already installed!")
        return True
    
    print("Missing prerequisites will be installed.")
    print()
    
    system = platform.system()
    
    if system == "Linux":
        return install_linux()
    elif system == "Darwin":
        return install_macos()
    elif system == "Windows":
        return install_windows()
    else:
        print(f"Unsupported operating system: {system}")
        return False


def check_and_prompt_install() -> bool:
    """Check prerequisites and prompt to install if missing.
    
    Returns True if all prerequisites are met (or were installed).
    Returns False if prerequisites are missing and user declined to install.
    """
    status = check_prerequisites()
    
    if status["all_ok"]:
        return True
    
    print()
    print("=" * 50)
    print("Missing Prerequisites")
    print("=" * 50)
    print()
    
    if not status["qemu_installed"]:
        print("✗ QEMU is not installed")
    print()
    print("The VM requires QEMU to run.")
    print()
    
    response = input("Install prerequisites now? [Y/n]: ").strip().lower()
    if response in ("", "y", "yes"):
        print()
        result = install_qemu()
        print()
        
        # Re-check after installation
        new_status = check_prerequisites()
        if new_status["all_ok"]:
            return True
        else:
            print("Some prerequisites are still missing.")
            print("Please install them manually and try again.")
            return False
    else:
        print()
        print("Prerequisites are required to run the VM.")
        print("Run 'student-machine qemu-install' to install them.")
        return False
