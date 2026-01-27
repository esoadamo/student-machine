# Student Machine

A cross-platform QEMU VM manager that provides a unified Debian Linux virtual machine with LXQT desktop environment for students.

## Features

- **Cross-platform**: Works on Linux, macOS, and Windows
- **Debian 12 with LXQT**: Lightweight desktop environment
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
2. Installs LXQT desktop environment
3. Installs development tools (Python, Node.js, Docker)
4. Configures auto-login

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
