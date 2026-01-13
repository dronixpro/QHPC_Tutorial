#!/usr/bin/env python3
"""
SLURM Queue LED Monitor for Raspberry Pi 5
Docker Cluster Edition (with QRMI/QPU support)

Monitors a SLURM queue and controls LEDs based on job type:

Individual LEDs (GPIO 17, 27) - Job-based:
- Green LED on: Normal partition jobs running
- Blue LED on: Quantum partition jobs running

LED Matrix (GPIO 19) - Job-based:
- "HPC" in green: Normal partition jobs running
- "Q" in blue: Quantum partition jobs running
- "QCSC" displayed when both job types are running (QC blue + SC green)

Requirements:
    pip install lgpio

Hardware Setup:
    - Green LED: GPIO 17 (pin 11) -> 330Ω resistor -> GND
    - Blue LED:  GPIO 27 (pin 13) -> 330Ω resistor -> GND
    - LED Matrix: GPIO 19 (directly connected via RasQberry utilities)
"""

import argparse
import logging
import signal
import subprocess
import time
import sys
from dataclasses import dataclass
from typing import Optional, List, Dict

try:
    import lgpio
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("Warning: lgpio not available. Running in simulation mode for LEDs.")

# Try to import RasQberry LED utilities for matrix display
try:
    sys.path.insert(0, '/home/rasqberry/QCSC/RasQberry-Two/RQB2-bin')
    from rq_led_utils import get_led_config, create_neopixel_strip, map_xy_to_pixel, create_text_bitmap
    MATRIX_AVAILABLE = True
except ImportError:
    MATRIX_AVAILABLE = False
    print("Warning: RasQberry LED utilities not available. Matrix display disabled.")


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class Config:
    """Configuration for the SLURM LED monitor."""
    # Docker settings
    docker_container: str = "login"
    docker_command: str = "docker"

    # SLURM settings
    slurm_user: Optional[str] = None

    # QPU detection patterns
    quantum_job_patterns: tuple = ("qiskit", "pasqal", "quantum", "qpu", "ibm_")
    qpu_resources: tuple = ("test_eagle", "ibm_sherbrooke", "ibm_brisbane", "FRESNEL")
    quantum_partitions: tuple = ("quantum",)

    # GPIO pins (BCM numbering)
    normal_led_pin: int = 17   # Green LED
    quantum_led_pin: int = 27  # Blue LED

    # LED matrix settings (24x8 RasQberry matrix)
    matrix_brightness: float = 0.5
    matrix_enabled: bool = True

    # Polling interval in seconds
    poll_interval: int = 30


# =============================================================================
# LED Controller
# =============================================================================

class LEDController:
    """Controls LEDs on Raspberry Pi 5 using lgpio."""

    def __init__(self, normal_pin: int, quantum_pin: int):
        self.simulation_mode = not GPIO_AVAILABLE
        self.normal_pin = normal_pin
        self.quantum_pin = quantum_pin

        if not self.simulation_mode:
            # Pi 5 uses gpiochip0 for the main GPIO header
            self.handle = lgpio.gpiochip_open(0)
            lgpio.gpio_claim_output(self.handle, normal_pin)
            lgpio.gpio_claim_output(self.handle, quantum_pin)
        else:
            self.normal_state = False
            self.quantum_state = False

    def set_normal(self, state: bool):
        if self.simulation_mode:
            self.normal_state = state
            logging.debug(f"[SIM] Normal LED: {'ON' if state else 'OFF'}")
        else:
            lgpio.gpio_write(self.handle, self.normal_pin, 1 if state else 0)

    def set_quantum(self, state: bool):
        if self.simulation_mode:
            self.quantum_state = state
            logging.debug(f"[SIM] Quantum LED: {'ON' if state else 'OFF'}")
        else:
            lgpio.gpio_write(self.handle, self.quantum_pin, 1 if state else 0)

    def update(self, normal_running: bool, quantum_running: bool):
        self.set_normal(normal_running)
        self.set_quantum(quantum_running)

        status = []
        if normal_running:
            status.append("NORMAL")
            logging.info(f"LED Status: {' + '.join(status)}")
        if quantum_running:
            status.append("QUANTUM/QPU")
            logging.info(f"LED Status: {' + '.join(status)}")
        if not status:
            status.append("IDLE")
            logging.debug(f"LED Status: {' + '.join(status)}")

    def cleanup(self):
        self.set_normal(False)
        self.set_quantum(False)
        if not self.simulation_mode:
            lgpio.gpiochip_close(self.handle)


# =============================================================================
# LED Matrix Display Controller (HPC + Container Status)
# =============================================================================

class MatrixDisplayController:
    """Controls the 24x8 LED matrix to display HPC cluster status.

    Display modes:
    - "HPC" in green: Normal partition jobs running
    - "Q" in blue: Quantum partition jobs running
    - "QCSC" displayed when both job types are running (QC blue + SC green)

    Colors:
    - Green: Normal/HPC partition
    - Blue: Quantum partition
    """

    # Colors
    GREEN = (0, 255, 0)
    BLUE = (0, 150, 255)
    OFF = (0, 0, 0)

    def __init__(self, brightness: float = 0.5, enabled: bool = True):
        """Initialize the matrix display controller.

        Args:
            brightness: LED brightness 0.0-1.0
            enabled: If False, run in simulation mode
        """
        self.simulation_mode = not MATRIX_AVAILABLE or not enabled
        self.brightness = brightness
        self.pixels = None
        self.config = None
        self.current_state = (False, False)  # (normal, quantum)

        if not enabled:
            logging.info("LED matrix disabled via --no-matrix")
        elif not MATRIX_AVAILABLE:
            logging.warning("LED matrix not available (RasQberry utilities not found)")
        else:
            self._init_hardware()

    def _init_hardware(self):
        """Initialize the NeoPixel hardware."""
        try:
            logging.info("Initializing LED matrix on GPIO 19...")
            self.config = get_led_config()
            self.pixels = create_neopixel_strip(
                self.config['led_count'],
                self.config['pixel_order'],
                brightness=self.brightness
            )
            logging.info(f"Matrix display initialized: {self.config['matrix_width']}x{self.config['matrix_height']}")
        except Exception as e:
            logging.error(f"Failed to initialize matrix display: {e}")
            self.simulation_mode = True

    def _display_text(self, text: str, color: tuple, x_offset: int = 0):
        """Display text on the matrix using the built-in font.

        Args:
            text: Text to display
            color: RGB color tuple
            x_offset: Starting x position
        """
        if self.simulation_mode or self.pixels is None:
            return

        text_columns = create_text_bitmap(text)
        layout = self.config['layout']
        height = self.config['matrix_height']
        width = self.config['matrix_width']

        for col_idx, col_data in enumerate(text_columns):
            x = x_offset + col_idx
            if x >= width or x < 0:
                continue

            for y in range(min(height, 7)):
                if col_data & (1 << y):
                    led_index = map_xy_to_pixel(x, y, layout)
                    if led_index is not None:
                        self.pixels[led_index] = color

    def _display_normal_partition(self):
        """Display 'HPC' in green for normal partition."""
        self._display_text("HPC", self.GREEN, x_offset=3)

    def _display_quantum_partition(self):
        """Display 'Q' in blue for quantum partition."""
        self._display_text("Q", self.BLUE, x_offset=9)

    def _display_both_partitions(self):
        """Display 'QCSC' when both partitions are running."""
        # QC in blue, SC in green
        self._display_text("QC", self.BLUE, x_offset=1)
        self._display_text("SC", self.GREEN, x_offset=13)

    def update(self, normal_running: bool, quantum_running: bool):
        """Update the matrix display based on job status."""
        new_state = (normal_running, quantum_running)

        # Only update if state changed
        if new_state == self.current_state:
            return
        self.current_state = new_state

        if self.simulation_mode:
            if normal_running and quantum_running:
                logging.info("[MATRIX] Displaying: QCSC (QC blue + SC green)")
            elif normal_running:
                logging.info("[MATRIX] Displaying: HPC (green)")
            elif quantum_running:
                logging.info("[MATRIX] Displaying: Q (blue)")
            else:
                logging.info("[MATRIX] Display: OFF (idle)")
            return

        if self.pixels is None:
            return

        try:
            # Clear the display
            self.pixels.fill(self.OFF)

            if normal_running and quantum_running:
                self._display_both_partitions()
                logging.info("Matrix: QCSC")
            elif normal_running:
                self._display_normal_partition()
                logging.info("Matrix: HPC")
            elif quantum_running:
                self._display_quantum_partition()
                logging.info("Matrix: Q")
            else:
                # Idle - display off
                logging.debug("Matrix: idle")

            self.pixels.show()
        except Exception as e:
            logging.debug(f"Matrix update error: {e}")

    def cleanup(self):
        """Turn off the matrix display."""
        if not self.simulation_mode and self.pixels is not None:
            try:
                self.pixels.fill(self.OFF)
                self.pixels.show()
            except Exception as e:
                logging.debug(f"Matrix cleanup error: {e}")
        logging.info("Matrix display stopped")


# =============================================================================
# Command Executor
# =============================================================================

class CommandExecutor:
    """Executes commands via Docker."""

    def __init__(self, config: Config):
        self.config = config

    def execute(self, command: str) -> tuple[str, str]:
        """Execute a command and return (stdout, stderr)."""
        try:
            full_cmd = [
                self.config.docker_command, "exec",
                self.config.docker_container,
                "bash", "-c", command
            ]
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            logging.error("Docker exec timed out")
            return "", "timeout"
        except Exception as e:
            logging.error(f"Docker exec failed: {e}")
            return "", str(e)

    def cleanup(self):
        pass


# =============================================================================
# SLURM Monitor
# =============================================================================

class SLURMMonitor:
    """Monitors SLURM queue for running jobs."""

    def __init__(self, config: Config, executor: CommandExecutor):
        self.config = config
        self.executor = executor

    def get_running_jobs(self) -> Dict[str, List[Dict]]:
        """Query SLURM for running jobs and categorize them."""
        result = {"normal": [], "quantum": []}

        user_filter = f"-u {self.config.slurm_user}" if self.config.slurm_user else ""
        cmd = f'squeue {user_filter} -t RUNNING -h -o "%i|%P|%t|%j|%u|%k"'

        stdout, stderr = self.executor.execute(cmd)

        if stderr and "error" in stderr.lower():
            logging.warning(f"squeue stderr: {stderr}")

        if not stdout:
            logging.debug("No running jobs found")
            return result

        jobs = []
        for line in stdout.split('\n'):
            if not line.strip():
                continue
            parts = line.split('|')
            if len(parts) < 5:
                continue

            job_id, partition, state, name, user = parts[:5]
            comment = parts[5] if len(parts) > 5 else ""

            jobs.append({
                "id": job_id,
                "partition": partition,
                "name": name,
                "user": user,
                "comment": comment
            })

        for job in jobs:
            is_quantum = self._is_quantum_job(job)

            if is_quantum:
                result["quantum"].append(job)
                logging.debug(f"Quantum job: {job['id']} - {job['name']}")
            else:
                result["normal"].append(job)
                logging.debug(f"Normal job: {job['id']} - {job['name']}")

        return result

    def _is_quantum_job(self, job: Dict) -> bool:
        """Determine if a job is a quantum/QPU job."""
        job_name = job["name"].lower()
        job_comment = job.get("comment", "").lower()
        job_partition = job.get("partition", "").lower()

        # Method 1: Check partition (most reliable)
        for partition in self.config.quantum_partitions:
            if partition.lower() == job_partition:
                return True

        # Method 2: Check job name patterns
        for pattern in self.config.quantum_job_patterns:
            if pattern.lower() in job_name:
                return True

        # Method 3: Check comment for QPU resources
        for qpu in self.config.qpu_resources:
            if qpu.lower() in job_comment:
                return True

        # Method 4: Query scontrol for more details
        return self._check_job_details(job["id"])

    def _check_job_details(self, job_id: str) -> bool:
        """Use scontrol to get detailed job info and check for QPU usage."""
        cmd = f"scontrol show job {job_id}"
        stdout, stderr = self.executor.execute(cmd)

        if not stdout:
            return False

        stdout_lower = stdout.lower()

        for qpu in self.config.qpu_resources:
            if qpu.lower() in stdout_lower:
                return True

        if "--qpu" in stdout_lower or "qpu=" in stdout_lower:
            return True

        if "qrmi_" in stdout_lower:
            return True

        return False


# =============================================================================
# Main Monitor Loop
# =============================================================================

def run_monitor(config: Config):
    """Main monitoring loop."""
    led = LEDController(config.normal_led_pin, config.quantum_led_pin)

    if config.matrix_enabled:
        matrix = MatrixDisplayController(
            brightness=config.matrix_brightness,
            enabled=config.matrix_enabled
        )
    else:
        matrix = MatrixDisplayController(enabled=False)

    executor = CommandExecutor(config)
    slurm = SLURMMonitor(config, executor)
    running = True

    def signal_handler(signum, frame):
        nonlocal running
        logging.info(f"Received signal {signum}, shutting down...")
        running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logging.info("Starting SLURM LED Monitor")
    logging.info(f"Docker container: {config.docker_container}")
    logging.info(f"Polling interval: {config.poll_interval}s")
    logging.info("Press Ctrl+C to stop")

    try:
        while running:
            jobs = slurm.get_running_jobs()

            normal_running = len(jobs["normal"]) > 0
            quantum_running = len(jobs["quantum"]) > 0

            if jobs["normal"]:
                names = [f"{j['name']}({j['id']})" for j in jobs["normal"]]
                logging.info(f"Normal jobs ({len(jobs['normal'])}): {', '.join(names)}")
            if jobs["quantum"]:
                names = [f"{j['name']}({j['id']})" for j in jobs["quantum"]]
                logging.info(f"Quantum jobs ({len(jobs['quantum'])}): {', '.join(names)}")

            led.update(normal_running, quantum_running)
            matrix.update(normal_running, quantum_running)

            for _ in range(config.poll_interval * 10):
                if not running:
                    break
                time.sleep(0.1)

    except KeyboardInterrupt:
        logging.info("Shutting down...")
    finally:
        led.cleanup()
        matrix.cleanup()
        executor.cleanup()
        logging.info("Cleanup complete. Goodbye!")


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Monitor SLURM queue and control LEDs on Raspberry Pi 5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --container login
  %(prog)s --container login --interval 5 -v
        """
    )

    # Docker options
    parser.add_argument(
        "--container", "-c",
        default="login",
        help="Docker container name (default: login)"
    )
    parser.add_argument(
        "--docker-cmd",
        default="docker",
        help="Docker command: 'docker' or 'podman' (default: docker)"
    )

    # SLURM options
    parser.add_argument(
        "--slurm-user", "-s",
        default=None,
        help="Filter jobs by SLURM username (default: all users)"
    )
    parser.add_argument(
        "--qpu-patterns",
        default="qiskit,pasqal,quantum,qpu,ibm_",
        help="Comma-separated job name patterns indicating quantum jobs"
    )
    parser.add_argument(
        "--qpu-resources",
        default="ibm_torino,ibm_fez,ibm_sherbrooke,ibm_brisbane,FRESNEL",
        help="Comma-separated QPU resource names"
    )

    # Hardware options
    parser.add_argument(
        "--normal-pin", type=int, default=17,
        help="GPIO pin for normal LED (default: 17)"
    )
    parser.add_argument(
        "--quantum-pin", type=int, default=27,
        help="GPIO pin for quantum LED (default: 27)"
    )
    parser.add_argument(
        "--matrix-brightness", type=float, default=0.5,
        help="LED matrix brightness 0.0-1.0 (default: 0.5)"
    )
    parser.add_argument(
        "--no-matrix", action="store_true",
        help="Disable LED matrix display"
    )

    # General options
    parser.add_argument(
        "--interval", "-i",
        type=int, default=30,
        help="Polling interval in seconds (default: 30)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    config = Config(
        docker_container=args.container,
        docker_command=args.docker_cmd,
        slurm_user=args.slurm_user,
        quantum_job_patterns=tuple(args.qpu_patterns.split(",")),
        qpu_resources=tuple(args.qpu_resources.split(",")),
        normal_led_pin=args.normal_pin,
        quantum_led_pin=args.quantum_pin,
        matrix_brightness=args.matrix_brightness,
        matrix_enabled=not args.no_matrix,
        poll_interval=args.interval
    )

    run_monitor(config)


if __name__ == "__main__":
    main()
