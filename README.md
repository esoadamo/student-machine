# Student Machine

A cross-platform QEMU VM manager that provides a unified Debian Linux virtual machine with XFCE desktop environment for students.

## Features

- **Cross-platform**: Works on Linux, macOS, and Windows
- **Debian 12 with XFCE**: Lightweight desktop environment
- **Hardware acceleration**: Automatic KVM (Linux), HVF (macOS), or WHPX (Windows)
- **Shared folders**: Easily share files between host and VM
- **SSH access**: Connect via SSH on port 2222
- **Simple CLI**: Easy-to-use command line interface

## Prerequisites

### Linux (Ubuntu/Debian)

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
# Install from source
pip install -e .

# Or install directly
pip install student-machine
```

## Quick Start

```bash
# One-click mode: auto-setup and start with GUI + autologin
student-machine run

# With Czech locale and keyboard layout
student-machine run --locale cs_CZ.UTF-8 --keyboard cz

# Or step by step:
# 1. Set up the VM (downloads Debian image, ~5-10 minutes first time)
student-machine setup

# 2. Start the VM with GUI
student-machine start --gui

# 3. Or start headless and use SSH
student-machine start
student-machine ssh
```

## VM Credentials

- **Username**: `student`
- **Password**: `student`

## Commands

| Command | Description |
|---------|-------------|
| `student-machine run` | **One-click mode**: auto-setup + start with GUI + autologin |
| `student-machine setup` | Download Debian image and create VM disk |
| `student-machine start` | Start the VM (headless) |
| `student-machine start --gui` | Start the VM with graphical display |
| `student-machine stop` | Stop the VM gracefully |
| `student-machine status` | Show VM status |
| `student-machine ssh` | SSH into the VM |
| `student-machine balloon` | Start memory balloon controller (dynamic memory) |
| `student-machine service install` | Install as system service |
| `student-machine service uninstall` | Remove system service |

### Run Options (One-Click Mode)

```bash
student-machine run [OPTIONS]

Options:
  --force, -f        Force recreation of VM images
  --shared-dir PATH  Directory to share with VM (default: ~/.vm/data)
  --port, -p PORT    SSH port forwarding (default: 2222)
  --memory, -m SIZE  Memory allocation (default: 2048M)
  --cpus, -c NUM     Number of CPUs (default: 2)
  --locale, -l LOC   System locale (default: en_US.UTF-8)
  --keyboard, -k KB  Keyboard layout (default: us)
```

#### Locale and Keyboard Examples

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
  --memory, -m SIZE  Memory allocation (default: 2048M)
  --cpus, -c NUM     Number of CPUs (default: 2)
```

### Memory Balloon Controller

The VM supports dynamic memory management through a balloon controller. The VM is started with a configurable maximum memory limit, and the balloon controller can:
- **Increase** guest memory when VM is running low (up to the max limit)
- **Decrease** guest memory when VM has excess free memory (reclaim for host)

```bash
# Start balloon controller (runs in background)
student-machine balloon

# With custom limits
student-machine balloon --min-memory 1024 --max-memory 8192

Options:
  --min-memory, -min  Minimum VM memory in MB (default: 1024)
  --max-memory, -max  Maximum VM memory in MB (default: 8192)
  --shared-dir PATH   Directory shared with VM (default: ~/.vm/data)
```

**How it works:**
1. VM runs a memory monitor that reports stats to `/mnt/shared/.vm-memory-status`
2. Host-side balloon controller reads these stats every 5 seconds
3. If VM free memory < 30%, controller increases memory (up to max)
4. If VM free memory > 40%, controller reclaims memory (down to min)

**Note:** The `run` command automatically starts the balloon controller in the background. To use balloon with higher max memory, restart the VM with `--force`.

## File Locations

All VM files are stored in `~/.vm/`:

| File | Description |
|------|-------------|
| `~/.vm/student-vm.qcow2` | VM disk image |
| `~/.vm/debian-12-base.qcow2` | Base Debian cloud image |
| `~/.vm/seed.iso` | Cloud-init configuration |
| `~/.vm/data/` | Shared folder (mounted as `/mnt/shared` in VM) |
| `~/.vm/student-vm.log` | QEMU log file |
| `~/.vm/student-vm.pid` | PID file when running |

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

## First Boot

The first boot takes 5-10 minutes as cloud-init:

1. Resizes the disk
2. Installs XFCE desktop environment
3. Configures locale and keyboard layout
4. Installs development tools:
   - Python 3, pip, venv
   - Node.js, npm
   - Docker, docker-compose
   - VS Code (code editor)
   - Thonny (Python IDE for beginners)
   - uv (fast Python package manager)
5. Installs terminal tools:
   - btop (system monitor)
   - tmux, screen, byobu (terminal multiplexers)
6. Configures auto-login

After the first boot completes, the VM will have a full graphical desktop.

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

### View logs

```bash
tail -f ~/.vm/student-vm.log
```

## Development

```bash
# Clone the repository
git clone https://github.com/yourusername/student-machine.git
cd student-machine

# Install in development mode
pip install -e .

# Run directly
python -m student_machine --help
```

## License

MIT License
