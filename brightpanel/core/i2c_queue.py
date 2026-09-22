"""Thread-safe asynchronous command queue and debouncer for I2C and DDC/CI communication."""

from __future__ import annotations
import os
import time
import shutil
import logging
import threading
import subprocess
from queue import Queue, Empty
from dataclasses import dataclass
from typing import Dict, Optional, Callable, Any, List

from brightpanel.core.vcp_manager import VCPCode, VCPValue
from brightpanel.core.detector import DisplayInfo

logger = logging.getLogger("brightpanel.i2c_queue")


@dataclass
class I2CTask:
    """Represents an I2C command to execute on a monitor."""
    display_num: int
    bus_num: int
    vcp_code: int
    value: int
    is_mock: bool = False
    callback: Optional[Callable[[bool, int], None]] = None
    timestamp: float = 0.0


class I2CCommandQueue:
    """Serializes and debounces hardware DDC/CI calls to prevent I2C bus lockup and GUI freezing."""

    def __init__(self, ddcutil_bin: Optional[str] = None, debounce_interval: float = 0.10):
        self.ddcutil_bin = ddcutil_bin or shutil.which("ddcutil") or "ddcutil"
        self.debounce_interval = debounce_interval  # 100ms
        self._pending_tasks: Dict[str, I2CTask] = {}  # key: f"{display_num}:{vcp_code}"
        self._queue: Queue[str] = Queue()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        # Value cache: key: f"{display_num}:{vcp_code}" -> current int value
        self._cached_values: Dict[str, int] = {}
        self._listeners: List[Callable[[int, int, int], None]] = []  # (display_num, vcp_code, value)

    def start(self) -> None:
        """Starts background worker thread."""
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, name="BrightPanel-I2CWorker", daemon=True)
        self._worker_thread.start()
        logger.debug("I2C worker thread started.")

    def stop(self) -> None:
        """Stops background worker thread."""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
        logger.debug("I2C worker thread stopped.")

    def add_listener(self, callback: Callable[[int, int, int], None]) -> None:
        """Registers a listener for value change events."""
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[int, int, int], None]) -> None:
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def get_cached_value(self, display_num: int, vcp_code: int, fallback: int = 50) -> int:
        key = f"{display_num}:{vcp_code}"
        with self._lock:
            return self._cached_values.get(key, fallback)

    def set_cached_value(self, display_num: int, vcp_code: int, value: int) -> None:
        key = f"{display_num}:{vcp_code}"
        with self._lock:
            self._cached_values[key] = value

    def enqueue_set_vcp(
        self,
        display: DisplayInfo,
        vcp_code: int,
        value: int,
        callback: Optional[Callable[[bool, int], None]] = None
    ) -> None:
        """Queues a setvcp request with automatic debouncing.

        Updates local cache immediately for responsive UI, and schedules physical write.
        """
        clamped_value = VCPValue.clamp(value)
        key = f"{display.display_num}:{vcp_code}"

        with self._lock:
            # Update cache immediately
            self._cached_values[key] = clamped_value

            task = I2CTask(
                display_num=display.display_num,
                bus_num=display.bus_num,
                vcp_code=vcp_code,
                value=clamped_value,
                is_mock=display.is_mock,
                callback=callback,
                timestamp=time.time()
            )
            is_new = key not in self._pending_tasks
            self._pending_tasks[key] = task
            if is_new:
                self._queue.put(key)

        # Notify in-process listeners immediately
        self._notify_listeners(display.display_num, vcp_code, clamped_value)

        # Ensure worker is running
        self.start()

    def set_brightness(self, display: DisplayInfo, value: int, callback: Optional[Callable[[bool, int], None]] = None) -> None:
        self.enqueue_set_vcp(display, VCPCode.BRIGHTNESS, value, callback)

    def set_contrast(self, display: DisplayInfo, value: int, callback: Optional[Callable[[bool, int], None]] = None) -> None:
        self.enqueue_set_vcp(display, VCPCode.CONTRAST, value, callback)

    def set_volume(self, display: DisplayInfo, value: int, callback: Optional[Callable[[bool, int], None]] = None) -> None:
        self.enqueue_set_vcp(display, VCPCode.AUDIO_VOLUME, value, callback)

    def set_input_source(self, display: DisplayInfo, source_code: int, callback: Optional[Callable[[bool, int], None]] = None) -> None:
        self.enqueue_set_vcp(display, VCPCode.INPUT_SOURCE, source_code, callback)

    def _worker_loop(self) -> None:
        """Continuously pulls tasks from queue and executes them with rate limiting."""
        while not self._stop_event.is_set():
            try:
                key = self._queue.get(timeout=0.2)
            except Empty:
                continue

            # Sleep brief debounce interval to let rapid dragging settle
            time.sleep(self.debounce_interval)

            task: Optional[I2CTask] = None
            with self._lock:
                if key in self._pending_tasks:
                    task = self._pending_tasks.pop(key)

            if not task:
                self._queue.task_done()
                continue

            success = self._execute_task(task)
            if task.callback:
                try:
                    task.callback(success, task.value)
                except Exception as e:
                    logger.debug("Task callback exception: %s", e)

            self._queue.task_done()

    def _execute_task(self, task: I2CTask) -> bool:
        """Executes a single hardware or mock I2C task."""
        if task.is_mock or os.environ.get("MOCK_DDC", "0") in ("1", "true", "yes"):
            # Mock execution simulates slight hardware delay
            time.sleep(0.015)
            logger.debug(
                "Mock execute: Display %d (bus %d) VCP 0x%02X = %d",
                task.display_num, task.bus_num, task.vcp_code, task.value
            )
            return True

        if task.display_num <= 0:
            # Internal display handling
            return self._execute_internal_backlight(task)

        # Physical DDC/CI write via ddcutil
        try:
            cmd = [
                self.ddcutil_bin,
                "setvcp",
                f"{task.vcp_code:#x}",
                str(task.value),
                "--display", str(task.display_num),
                "--sleep-multiplier", "0.5"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
            if res.returncode == 0:
                logger.debug("Successfully applied VCP 0x%02X=%d to display %d", task.vcp_code, task.value, task.display_num)
                return True
            else:
                logger.warning(
                    "ddcutil setvcp failed (code %d) for display %d: %s",
                    res.returncode, task.display_num, res.stderr.strip()
                )
        except subprocess.TimeoutExpired:
            logger.error("ddcutil setvcp timed out on display %d", task.display_num)
        except Exception as e:
            logger.error("Error executing setvcp: %s", e)

        return False

    def _execute_internal_backlight(self, task: I2CTask) -> bool:
        """Sets internal laptop backlight via sysfs if permitted."""
        backlight_dir = "/sys/class/backlight"
        if not os.path.exists(backlight_dir):
            return False
        try:
            entries = os.listdir(backlight_dir)
            if not entries:
                return False
            dev_path = os.path.join(backlight_dir, entries[0])
            max_file = os.path.join(dev_path, "max_brightness")
            bright_file = os.path.join(dev_path, "brightness")
            if os.path.exists(max_file) and os.path.exists(bright_file):
                with open(max_file, "r") as f:
                    max_raw = int(f.read().strip())
                target_raw = int((task.value / 100.0) * max_raw)
                with open(bright_file, "w") as f:
                    f.write(str(target_raw))
                return True
        except Exception as e:
            logger.debug("Failed writing internal backlight sysfs: %s", e)
        return False

    def _notify_listeners(self, display_num: int, vcp_code: int, value: int) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(display_num, vcp_code, value)
            except Exception as e:
                logger.debug("Error in listener callback: %s", e)
