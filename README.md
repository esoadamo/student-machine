# Student Machine

A cross-platform QEMU VM manager that provides a Debian Linux virtual machine with XFCE desktop environment for students.

## Features

- **Cross-platform**: Works on Linux, macOS, and Windows
- **Debian 12 with XFCE**: Lightweight desktop environment with auto-login
- **Hardware acceleration**: Automatic KVM (Linux), HVF (macOS), or WHPX (Windows)
- **Dynamic memory**: Memory hotplug automatically adds memory when VM needs it
- **Shared folders**: Easily share files between host and VM
- **SSH access**: Connect via SSH on port 2222
- **Backup & Restore**: Portable VM archives for easy migration between machines
- **Multiple VMs**: Run multiple named VMs simultaneously
- **Pre-installed tools**: Python, Node.js, Docker, VS Code, and more

## Prerequisites

QEMU is automatically checked when running `student-machine run`. If missing, you'll be prompted to install it.

### Automatic Installation

```bash
# Install QEMU and all prerequisites
student-machine qemu-install

# Just check if everything is installed
student-machine qemu-install --check
```

### Manual Installation

#### Linux (Ubuntu/Debian)

```bash
sudo apt install qemu-system-x86 qemu-utils cloud-image-utils

# For KVM acceleration (recommended)
sudo usermod -aG kvm $USER
# Log out and back in
```

### macOS

```bash
brew install qemu cdrtools
```

### Windows

1. Download QEMU from: https://www.qemu.org/download/#windows
2. Add QEMU to your PATH
3. Download cdrtools from: http://smithii.com/files/cdrtools-latest.zip
4. Extract and add to PATH

## Installation

```bash
# Install with uv (recommended)
uv tool install student-machine

# Or install with pip
pip install student-machine

# Or install from source
pip install -e .
```

## Quick Start

```bash
# One-click mode: auto-setup and start with GUI + autologin
student-machine run

# With Czech locale and keyboard layout
student-machine run --locale cs_CZ.UTF-8 --keyboard cz
```

The first boot takes 5-10 minutes to install the desktop environment. Subsequent boots are fast.

## VM Credentials

- **Username**: `student`
- **Password**: `student`

## Commands

| Command | Description |
|---------|-------------|
| `student-machine run` | **One-click mode**: auto-setup + start with GUI |
| `student-machine setup` | Download Debian image and create VM disk |
| `student-machine start` | Start the VM (headless by default) |
| `student-machine start --gui` | Start the VM with graphical display |
| `student-machine stop` | Stop the VM gracefully |
| `student-machine status` | Show VM status |
| `student-machine ssh` | SSH into the VM |
| `student-machine balloon` | Start memory controller (auto-started by `run`) |
| `student-machine backup` | Create portable backup archive |
| `student-machine restore` | Restore VM from backup archive |
| `student-machine list` | List all available VMs |
| `student-machine qemu-install` | Install QEMU and prerequisites |
| `student-machine service install` | Install as system service |
| `student-machine service uninstall` | Remove system service |

### Global Options

All commands support the `--name` option to work with multiple VMs:

```bash
# Default VM (backward compatible)
student-machine run

# Named VM (stored in ~/.vm/<name>/)
student-machine run --name work-vm
student-machine run --name school-vm

# All commands support --name
student-machine start --name work-vm --gui
student-machine stop --name work-vm
student-machine status --name work-vm
student-machine backup --name work-vm /path/to/backup.tar.gz
```

### Run Options

```bash
student-machine run [OPTIONS]

Options:
  --force, -f        Force recreation of VM images
  --shared-dir PATH  Directory to share with VM (default: ~/.vm/data)
  --port, -p PORT    SSH port forwarding (default: 2222)
  --memory, -m SIZE  Initial memory allocation (default: 2048M)
  --cpus, -c NUM     Number of CPUs (default: 2)
  --locale, -l LOC   System locale (default: en_US.UTF-8)
  --keyboard, -k KB  Keyboard layout (default: us)
```

### Locale and Keyboard Examples

```bash
# Czech locale and keyboard
student-machine run --locale cs_CZ.UTF-8 --keyboard cz

# German locale and keyboard
student-machine run --locale de_DE.UTF-8 --keyboard de

# French locale and keyboard
student-machine run --locale fr_FR.UTF-8 --keyboard fr

# Polish locale and keyboard
student-machine run --locale pl_PL.UTF-8 --keyboard pl
```

### Start Options

```bash
student-machine start [OPTIONS]

Options:
  --gui              Enable graphical display
  --console          Enable serial console
  --shared-dir PATH  Directory to share with VM (default: ~/.vm/data)
  --port, -p PORT    SSH port forwarding (default: 2222)
  --memory, -m SIZE  Initial memory allocation (default: 2048M)
  --cpus, -c NUM     Number of CPUs (default: 2)
```

### Dynamic Memory Management

The VM supports automatic memory scaling through memory hotplug:

- VM starts with initial memory (default 2GB)
- When VM memory runs low (<30% free), more memory is hotplugged (in 1GB chunks)
- When VM has excess memory (>50% free), memory is reclaimed via balloon
- Maximum memory is limited to host RAM - 1GB
- Up to 16 DIMM slots are available for memory expansion

The `run` command automatically starts the memory controller in the background.

```bash
# Manual control (if not using 'run')
student-machine balloon

# With custom limits
student-machine balloon --min-memory 1024 --max-memory 16384

# Run in foreground (for debugging)
student-machine balloon --foreground
```

**How it works:**
1. VM runs a memory monitor that reports stats to `/mnt/shared/.vm-memory-status`
2. Host-side controller reads these stats every 5 seconds
3. If VM free memory < 30%, controller hotplugs more memory (up to max)
4. If VM free memory > 50%, controller reclaims memory via balloon (down to initial)

## Backup & Restore

Create portable VM backups that can be restored on any machine with student-machine installed:

### Create Backup

```bash
# Backup to file (VM must be stopped)
student-machine backup /path/to/my-vm-backup.tar.gz

# Backup named VM
student-machine backup --name work-vm /backups/work-vm-backup.tar.gz
```

The backup archive contains:
- VM disk image (qcow2)
- Cloud-init configuration (seed.iso)
- Shared data folder contents
- VM metadata (name, architecture, creation date)

### Restore Backup

```bash
# Restore on a new machine (downloads will happen automatically)
student-machine restore /path/to/my-vm-backup.tar.gz

# Restore as a different VM name
student-machine restore --name restored-vm /path/to/backup.tar.gz

# Force overwrite existing VM
student-machine restore --force /path/to/backup.tar.gz
```

### List VMs

```bash
# List all available VMs
student-machine list
```

### Migration Workflow

```bash
# On source machine
student-machine stop
student-machine backup /tmp/my-work-vm.tar.gz
# Copy backup to USB/cloud/etc.

# On target machine (after installing student-machine)
student-machine restore /path/to/my-work-vm.tar.gz
student-machine run
# VM starts exactly as it was!
```

## File Locations

All VM files are stored in `~/.vm/`:

| File | Description |
|------|-------------|
| `~/.vm/student-vm.qcow2` | VM disk image |
| `~/.vm/debian-12-base.qcow2` | Base Debian cloud image (shared by all VMs) |
| `~/.vm/seed.iso` | Cloud-init configuration |
| `~/.vm/data/` | Shared folder (mounted as `/mnt/shared` in VM) |
| `~/.vm/student-vm.log` | QEMU log file |
| `~/.vm/balloon.log` | Memory controller log |
| `~/.vm/student-vm.pid` | VM PID file |
| `~/.vm/balloon.pid` | Memory controller PID file |

### Named VMs

When using `--name`, files are stored in subdirectories:

| File | Description |
|------|-------------|
| `~/.vm/<name>/vm.qcow2` | Named VM disk image |
| `~/.vm/<name>/seed.iso` | VM's cloud-init configuration |
| `~/.vm/<name>/data/` | VM's shared folder |
| `~/.vm/<name>/vm.log` | VM's QEMU log |
| `~/.vm/<name>/balloon.log` | VM's memory controller log |

```bash
# Example: "work-vm" files are in ~/.vm/work-vm/
student-machine run --name work-vm
ls ~/.vm/work-vm/
# vm.qcow2  seed.iso  data/  vm.log  vm.pid  ...
```

## Shared Folders

Files in `~/.vm/data/` on your host are available at `/mnt/shared` inside the VM.

```bash
# On host
echo "Hello from host" > ~/.vm/data/test.txt

# In VM
cat /mnt/shared/test.txt
```

## SSH Access

```bash
# Using the built-in command
student-machine ssh

# Or manually
ssh student@localhost -p 2222
```

## Pre-installed Software

The first boot installs a complete development environment:

**Development:**
- Python 3, pip, venv
- Node.js, npm
- Docker, docker-compose
- Git

**Editors:**
- VS Code
- VSCodium (via Flatpak)
- Thonny (Python IDE)
- Kate

**Tools:**
- uv (fast Python package manager)
- httpie (HTTP client)
- pytest, flake8, pylint
- btop (system monitor)
- tmux, screen, byobu (terminal multiplexers)
- sqlite3

## System Service

### Linux (systemd)

```bash
# Install service (requires sudo)
sudo student-machine service install

# Manage service
sudo systemctl start student-vm
sudo systemctl stop student-vm
sudo systemctl enable student-vm   # Start on boot
sudo systemctl disable student-vm  # Disable auto-start
```

### macOS (launchd)

```bash
# Install service
student-machine service install

# Load and start
launchctl load ~/Library/LaunchAgents/com.student-machine.vm.plist
launchctl start com.student-machine.vm
```

### Windows (Task Scheduler)

```bash
# Install scheduled task (may require admin)
student-machine service install
```

## Troubleshooting

### VM won't start

Check if QEMU is installed:
```bash
qemu-system-x86_64 --version
```

### No KVM acceleration

On Linux, add yourself to the kvm group:
```bash
sudo usermod -aG kvm $USER
# Log out and back in
```

### Shared folder not mounting

The 9p filesystem requires QEMU to be built with virtfs support. On macOS, you may need to install QEMU from source or use a different sharing method.

### Memory not increasing

Check the balloon controller log:
```bash
tail -f ~/.vm/balloon.log
```

Ensure the memory monitor is running inside the VM:
```bash
# Inside VM
systemctl status memory-monitor
```

### View logs

```bash
# QEMU log
tail -f ~/.vm/student-vm.log

# Memory controller log
tail -f ~/.vm/balloon.log
```

## Development

```bash
# Clone the repository
git clone https://github.com/yourusername/student-machine.git
cd student-machine

# Install in development mode with uv
uv sync
uv run student-machine --help

# Or with pip
pip install -e .
```
