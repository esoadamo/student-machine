"""Memory balloon controller for dynamic VM memory management."""

import json
import socket
import time
from pathlib import Path
from typing import Optional, Tuple

from . import config


class QMPClient:
    """Client for QEMU Machine Protocol (QMP)."""
    
    def __init__(self, socket_path: Path):
        self.socket_path = socket_path
        self.sock: Optional[socket.socket] = None
    
    def connect(self) -> bool:
        """Connect to QMP socket."""
        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.connect(str(self.socket_path))
            self.sock.settimeout(5.0)
            
            # Read greeting
            self._recv()
            
            # Send qmp_capabilities to enter command mode
            self._send({"execute": "qmp_capabilities"})
            response = self._recv()
            
            return "return" in response
        except Exception as e:
            print(f"QMP connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from QMP socket."""
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None
    
    def _send(self, cmd: dict):
        """Send a QMP command."""
        if not self.sock:
            raise RuntimeError("Not connected")
        data = json.dumps(cmd).encode() + b"\n"
        self.sock.sendall(data)
    
    def _recv(self) -> dict:
        """Receive a QMP response."""
        if not self.sock:
            raise RuntimeError("Not connected")
        
        data = b""
        while True:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            data += chunk
            try:
                return json.loads(data.decode())
            except json.JSONDecodeError:
                continue
        
        return {}
    
    def query_balloon(self) -> Optional[int]:
        """Query current balloon size in bytes."""
        try:
            self._send({"execute": "query-balloon"})
            response = self._recv()
            if "return" in response:
                return response["return"].get("actual")
        except Exception as e:
            print(f"Query balloon error: {e}")
        return None
    
    def set_balloon(self, size_bytes: int) -> bool:
        """Set balloon target size in bytes."""
        try:
            self._send({
                "execute": "balloon",
                "arguments": {"value": size_bytes}
            })
            response = self._recv()
            return "return" in response
        except Exception as e:
            print(f"Set balloon error: {e}")
            return False
    
    def query_memory_size_summary(self) -> Optional[dict]:
        """Query memory size summary including hotpluggable memory."""
        try:
            self._send({"execute": "query-memory-size-summary"})
            response = self._recv()
            if "return" in response:
                return response["return"]
        except Exception as e:
            print(f"Query memory size error: {e}")
        return None
    
    def hotplug_memory(self, size_mb: int, slot_id: str) -> bool:
        """Hotplug memory using pc-dimm device."""
        try:
            # First create the memory backend
            self._send({
                "execute": "object-add",
                "arguments": {
                    "qom-type": "memory-backend-ram",
                    "id": f"mem-{slot_id}",
                    "size": size_mb * 1024 * 1024
                }
            })
            response = self._recv()
            if "error" in response:
                print(f"Memory backend error: {response['error']}")
                return False
            
            # Then add the DIMM device
            self._send({
                "execute": "device_add",
                "arguments": {
                    "driver": "pc-dimm",
                    "id": f"dimm-{slot_id}",
                    "memdev": f"mem-{slot_id}"
                }
            })
            response = self._recv()
            if "error" in response:
                print(f"DIMM add error: {response['error']}")
                return False
            
            return True
        except Exception as e:
            print(f"Hotplug memory error: {e}")
            return False
    
    def query_hotplugged_memory(self) -> list:
        """Query list of hotplugged memory devices."""
        try:
            self._send({"execute": "query-memory-devices"})
            response = self._recv()
            if "return" in response:
                return response["return"]
        except Exception as e:
            print(f"Query memory devices error: {e}")
        return []


def get_balloon_pid_file(name: str = config.DEFAULT_VM_NAME) -> Path:
    """Get the balloon PID file path."""
    return config.get_balloon_pid_file(name)


def get_balloon_lock_file(name: str = config.DEFAULT_VM_NAME) -> Path:
    """Get the balloon lock file path."""
    return config.get_vm_subdir(name) / "balloon.lock"


def is_balloon_running(name: str = config.DEFAULT_VM_NAME) -> Tuple[bool, Optional[int]]:
    """Check if balloon controller is already running."""
    pid_file = get_balloon_pid_file(name)
    if not pid_file.exists():
        return False, None
    
    try:
        pid = int(pid_file.read_text().strip())
        # Check if process is still running
        import os
        os.kill(pid, 0)  # Signal 0 just checks if process exists
        return True, pid
    except (ValueError, ProcessLookupError, PermissionError):
        # PID file exists but process is dead - clean up
        try:
            pid_file.unlink()
        except:
            pass
        return False, None


def is_vm_running(name: str = config.DEFAULT_VM_NAME) -> bool:
    """Check if the VM is still running by checking QEMU PID."""
    from . import utils
    running, _ = utils.is_vm_running(name)
    return running


class MemoryBalloonController:
    """
    Controls VM memory dynamically based on guest memory pressure.
    
    Memory management strategy:
    - To ADD memory beyond initial allocation: Use memory hotplug (pc-dimm devices)
    - To RECLAIM memory back to host: Use balloon inflation
    - To RELEASE reclaimed memory back to VM: Use balloon deflation (up to initial)
    
    The virtio-balloon can only reclaim/release memory within the initial allocation.
    Memory hotplug is needed to actually increase total VM memory.
    
    The VM runs a monitor that writes memory stats to a shared file.
    This controller reads those stats and adjusts memory accordingly.
    """
    
    def __init__(
        self,
        qmp_socket: Path,
        shared_dir: Path,
        min_memory_mb: int = 1024,
        max_memory_mb: int = 8192,
        check_interval: float = 5.0,
        low_memory_threshold: float = 0.30,  # 30% free = low, release balloon
        high_memory_threshold: float = 0.50,  # 50% free = can reclaim some
        adjustment_step_mb: int = 256,
        name: str = config.DEFAULT_VM_NAME,
    ):
        self.qmp_socket = qmp_socket
        self.shared_dir = shared_dir
        self.min_memory_mb = min_memory_mb
        self.max_memory_mb = max_memory_mb  # This is the ceiling (initial allocation)
        self.check_interval = check_interval
        self.low_memory_threshold = low_memory_threshold
        self.high_memory_threshold = high_memory_threshold
        self.adjustment_step_mb = adjustment_step_mb
        self.name = name
        
        self.status_file = shared_dir / ".vm-memory-status"
        self.qmp = QMPClient(qmp_socket)
        self._running = False
        self._last_processed_seq_id: int = 0  # Track last processed record
        self._initial_balloon_mb: Optional[int] = None  # Initial balloon (floor for reclaim)
        self._hotplug_slot_counter: int = 0  # Counter for hotplug slot IDs
        self._total_hotplugged_mb: int = 0  # Track total hotplugged memory
        self._max_slots: int = 16  # Maximum number of DIMM slots available
    
    def get_vm_memory_status(self) -> Optional[dict]:
        """Read memory status from VM's shared file."""
        try:
            if not self.status_file.exists():
                return None
            
            content = self.status_file.read_text()
            return json.loads(content)
        except Exception:
            return None
    
    def get_host_available_memory_mb(self) -> int:
        """Get available memory on host system."""
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        # Value is in kB
                        kb = int(line.split()[1])
                        return kb // 1024
        except:
            pass
        return 0
    
    def adjust_memory(self) -> bool:
        """Check VM memory and adjust balloon if needed."""
        vm_status = self.get_vm_memory_status()
        if not vm_status:
            print("  [DEBUG] No VM memory status file found")
            return False
        
        # Check if this is a new record (prevent duplicate processing)
        # Only compare equality - seq_id resets to 0 on VM reboot
        seq_id = vm_status.get("seq_id", 0)
        if seq_id == self._last_processed_seq_id:
            print(f"  [SKIP] Already processed seq_id={seq_id}")
            return True
        
        total_mb = vm_status.get("total_mb", 0)
        available_mb = vm_status.get("available_mb", 0)
        
        if total_mb == 0:
            print("  [DEBUG] Total memory is 0")
            return False
        
        free_ratio = available_mb / total_mb
        current_balloon = self.qmp.query_balloon()
        
        if current_balloon is None:
            print("  [DEBUG] Could not query balloon")
            return False
        
        current_mb = current_balloon // (1024 * 1024)
        used_mb = total_mb - available_mb
        
        # Track initial balloon size (this is the floor - minimum memory)
        if self._initial_balloon_mb is None:
            self._initial_balloon_mb = current_mb
            print(f"  [INIT] Initial balloon size (floor): {self._initial_balloon_mb}MB")
        
        print(f"  [STATUS] seq={seq_id} VM: {available_mb}MB free / {total_mb}MB total ({free_ratio:.1%}), Balloon: {current_mb}MB, Used: {used_mb}MB")
        
        # Mark this record as processed
        self._last_processed_seq_id = seq_id
        
        # Balloon value = target memory size for guest
        # Higher balloon = more memory for VM
        # Lower balloon = less memory for VM
        
        floor_mb = self._initial_balloon_mb  # Minimum memory (1GB)
        ceiling_mb = self.max_memory_mb       # Maximum memory (host - 1GB)
        
        # Check if VM needs more memory (use memory HOTPLUG to add memory)
        if free_ratio < self.low_memory_threshold:
            # VM is low on memory - hotplug more memory
            total_possible_mb = self._initial_balloon_mb + self._total_hotplugged_mb
            
            if total_possible_mb >= ceiling_mb:
                print(f"  [INFO] Already at maximum ({ceiling_mb}MB). Cannot add more memory.")
                return True
            
            if self._hotplug_slot_counter >= self._max_slots:
                print(f"  [INFO] All {self._max_slots} DIMM slots used. Cannot add more memory.")
                return True
            
            # Calculate 50% increase, but at least adjustment_step_mb
            desired_increase = max(int(total_mb * 0.50), self.adjustment_step_mb)
            
            # Round up to nearest 1GB for better DIMM sizing (fewer slots used)
            desired_increase = ((desired_increase + 1023) // 1024) * 1024
            
            # Limit to what we can add
            max_increase = ceiling_mb - total_possible_mb
            actual_increase = min(desired_increase, max_increase)
            
            # Ensure at least 256MB DIMM size
            if actual_increase < 256:
                print(f"  [INFO] Cannot add more memory (need at least 256MB, max available: {max_increase}MB)")
                return True
            
            self._hotplug_slot_counter += 1
            slot_id = f"slot{self._hotplug_slot_counter}"
            
            print(f"  [ACTION] VM low on memory ({free_ratio:.1%} free). "
                  f"Hotplugging {actual_increase}MB (slot: {slot_id}, {self._hotplug_slot_counter}/{self._max_slots} used)")
            
            result = self.qmp.hotplug_memory(actual_increase, slot_id)
            if result:
                self._total_hotplugged_mb += actual_increase
                print(f"  [RESULT] Memory hotplug successful. Total hotplugged: {self._total_hotplugged_mb}MB")
            else:
                print(f"  [RESULT] Memory hotplug failed")
                self._hotplug_slot_counter -= 1  # Revert counter on failure
            return result
        
        # Check if we can reclaim memory (use BALLOON to take memory from VM)
        # Note: We can only balloon within the current total allocation, not un-hotplug
        elif free_ratio > self.high_memory_threshold:
            # VM has excess memory - inflate balloon (reclaim memory from VM)
            # Balloon can reclaim memory, but we keep at least floor_mb available
            
            if current_mb <= floor_mb:
                print(f"  [INFO] Already at minimum balloon ({floor_mb}MB). Cannot reclaim more memory.")
                return True
            
            # Calculate 30% decrease, but at least adjustment_step_mb
            desired_decrease = max(int(current_mb * 0.30), self.adjustment_step_mb)
            
            new_size_mb = max(
                current_mb - desired_decrease,
                floor_mb,  # Cannot go below initial allocation
            )
            
            if new_size_mb < current_mb:
                print(f"  [ACTION] VM has excess memory ({free_ratio:.1%} free). "
                      f"Ballooning from {current_mb}MB to {new_size_mb}MB (-{current_mb - new_size_mb}MB)")
                result = self.qmp.set_balloon(new_size_mb * 1024 * 1024)
                print(f"  [RESULT] Balloon set: {result}")
                return result
        else:
            print(f"  [INFO] Memory OK, no adjustment needed")
        
        return True
    
    def _run_loop(self, run_once: bool = False):
        """Main control loop."""
        if not self.qmp.connect():
            print("Failed to connect to QMP socket")
            return
        
        print(f"Memory balloon controller started for VM: {self.name}")
        print(f"  Target memory: {self.min_memory_mb}MB")
        print(f"  Max memory (ceiling): {self.max_memory_mb}MB")
        print(f"  Low threshold: {self.low_memory_threshold:.0%}")
        print(f"  High threshold: {self.high_memory_threshold:.0%}")
        print(f"  Check interval: {self.check_interval}s")
        print()
        
        # Get current balloon size (this is the ceiling we can release back to)
        current_balloon = self.qmp.query_balloon()
        if current_balloon:
            current_mb = current_balloon // (1024 * 1024)
            self._initial_balloon_mb = current_mb
            print(f"[INIT] Current balloon: {current_mb}MB (ceiling: {self._initial_balloon_mb}MB)")
        
        # For direct calls (not from thread), run until interrupted
        if not self._running:
            self._running = True
        
        vm_check_counter = 0
        try:
            while self._running:
                # Check if VM is still running every 3rd iteration
                vm_check_counter += 1
                if vm_check_counter >= 3:
                    vm_check_counter = 0
                    if not is_vm_running(self.name):
                        print(f"[{time.strftime('%H:%M:%S')}] VM has stopped, exiting balloon controller")
                        break
                
                print(f"[{time.strftime('%H:%M:%S')}] Checking memory...")
                self.adjust_memory()
                if run_once:
                    break
                time.sleep(self.check_interval)
        finally:
            self.qmp.disconnect()
            # Clean up PID file
            pid_file = get_balloon_pid_file(self.name)
            if pid_file.exists():
                try:
                    pid_file.unlink()
                except:
                    pass


def get_qmp_socket_path(name: str = config.DEFAULT_VM_NAME) -> Path:
    """Get the QMP socket path."""
    return config.get_monitor_socket(name)


def start_balloon_controller(
    name: str = config.DEFAULT_VM_NAME,
    shared_dir: Optional[Path] = None,
    min_memory_mb: int = 1024,
    max_memory_mb: int = 8192,
) -> bool:
    """
    Start the memory balloon controller as a background process.
    
    Returns True if started successfully, False otherwise.
    """
    import os
    import sys
    
    qmp_socket = get_qmp_socket_path(name)
    if not qmp_socket.exists():
        print(f"Cannot start balloon: VM '{name}' is not running (QMP socket not found)")
        return False
    
    # Check if balloon is already running
    running, pid = is_balloon_running(name)
    if running:
        print(f"Balloon controller already running (PID: {pid})")
        return True
    
    if shared_dir is None:
        shared_dir = config.get_data_dir(name)
    
    # Fork to background
    pid = os.fork()
    if pid > 0:
        # Parent process - write PID and return
        pid_file = get_balloon_pid_file(name)
        pid_file.write_text(str(pid))
        return True
    else:
        # Child process - detach and run
        os.setsid()
        
        # Redirect stdout/stderr to log file
        log_file = config.get_balloon_log_file(name)
        with open(log_file, "a") as log:
            os.dup2(log.fileno(), 1)
            os.dup2(log.fileno(), 2)
        
        controller = MemoryBalloonController(
            qmp_socket=qmp_socket,
            shared_dir=shared_dir,
            min_memory_mb=min_memory_mb,
            max_memory_mb=max_memory_mb,
            name=name,
        )
        
        try:
            controller._run_loop()
        except Exception as e:
            print(f"Balloon controller error: {e}")
        finally:
            # Clean up PID file on exit
            pid_file = get_balloon_pid_file(name)
            if pid_file.exists():
                try:
                    pid_file.unlink()
                except:
                    pass
        
        os._exit(0)
