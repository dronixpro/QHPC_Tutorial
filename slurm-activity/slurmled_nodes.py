#!/usr/bin/env python3
"""
SLURM Container LED Monitor for Raspberry Pi (rasqberry2)

Monitors SLURM node states and controls:
- 6 Individual LEDs for each container node (c1-c4 green, q1-q2 blue)
- WS2812B LED strip with comet effects based on partition activity

Each individual LED lights up when its corresponding node has a job running.
The LED strip shows animated comet effects:
- Green comet: Normal partition has running jobs
- Blue comet: Quantum partition has running jobs
- Both comets: Both partitions have running jobs (comets in opposite directions)

Requirements:
    pip install lgpio adafruit-circuitpython-neopixel

===============================================================================
HARDWARE SETUP (BCM GPIO numbering)
===============================================================================

Individual Node LEDs:
---------------------
    Classical Nodes (Green LEDs):
    - C1: GPIO 17 (pin 11) -> 330 ohm resistor -> LED -> GND
    - C2: GPIO 27 (pin 13) -> 330 ohm resistor -> LED -> GND
    - C3: GPIO 22 (pin 15) -> 330 ohm resistor -> LED -> GND
    - C4: GPIO 23 (pin 16) -> 330 ohm resistor -> LED -> GND

    Quantum Nodes (Blue LEDs):
    - Q1: GPIO 24 (pin 18) -> 330 ohm resistor -> LED -> GND
    - Q2: GPIO 25 (pin 22) -> 330 ohm resistor -> LED -> GND

WS2812B LED Strip (Partition Status):
-------------------------------------
    - Data: GPIO 19 (pin 35) - Uses PCM for signal timing
    - 5V:   External 5V power supply (or pin 2/4 for short strips <10 LEDs)
    - GND:  Common ground with Pi (pin 6, 9, 14, 20, 25, 30, 34, or 39)

    Ground connections:
    - Pin 6, 9, 14, 20, 25, 30, 34, 39 (any GND pin)

===============================================================================
WIRING DIAGRAM
===============================================================================

Raspberry Pi 5 GPIO Header (40-pin)
===================================
Looking at the Pi with USB ports facing down, GPIO header on the right:

                    +-----+-----+
               3.3V | 1   | 2   | 5V ─────────── LED Strip VCC (short strips)
              GPIO2 | 3   | 4   | 5V
              GPIO3 | 5   | 6   | GND  <─── Ground bus / LED Strip GND
              GPIO4 | 7   | 8   | GPIO14
                GND | 9   | 10  | GPIO15
    C1 ──────GPIO17 | 11  | 12  | GPIO18
    C2 ──────GPIO27 | 13  | 14  | GND  <─── Ground bus
    C3 ──────GPIO22 | 15  | 16  | GPIO23 ────── C4
               3.3V | 17  | 18  | GPIO24 ────── Q1
             GPIO10 | 19  | 20  | GND  <─── Ground bus
              GPIO9 | 21  | 22  | GPIO25 ────── Q2
             GPIO11 | 23  | 24  | GPIO8
                GND | 25  | 26  | GPIO7
              GPIO0 | 27  | 28  | GPIO1
              GPIO5 | 29  | 30  | GND
              GPIO6 | 31  | 32  | GPIO12
             GPIO13 | 33  | 34  | GND
  STRIP ─────GPIO19 | 35  | 36  | GPIO16
             GPIO26 | 37  | 38  | GPIO20
                GND | 39  | 40  | GPIO21
                    +-----+-----+


Individual LED Wiring Detail:
=============================

    GPIO Pin ────[####]────┤>├──── GND
                 330Ω      LED
                resistor   (long leg = anode, short leg = cathode)

    Example for C1 (GPIO 17, Pin 11):

        Pin 11 (GPIO17) ────[####]────┤>├──── Pin 6 (GND)
                            330Ω     Green
                                     LED


WS2812B LED Strip Wiring:
=========================

    For short strips (< 10 LEDs, < 600mA):

        Pin 35 (GPIO19) ────────────── DIN (Data In)
        Pin 2 or 4 (5V) ────────────── VCC (5V)
        Pin 6 (GND) ────────────────── GND

    For longer strips (use external 5V power supply):

                              ┌─────────────────┐
        Pin 35 (GPIO19) ──────┤ DIN             │
                              │   WS2812B       │
        External 5V ──────────┤ VCC    Strip    │
                              │                 │
        Pin 6 (GND) ──┬───────┤ GND             │
                      │       └─────────────────┘
        External GND ─┘

    IMPORTANT: Connect Pi GND and external power supply GND together!


Complete Wiring Table:
======================

    Component │ Color │ GPIO │ Pin │ Connection
    ──────────┼───────┼──────┼─────┼──────────────────────────────────
     C1 LED   │ Green │  17  │ 11  │ GPIO -> 330Ω -> LED -> GND (pin 6)
     C2 LED   │ Green │  27  │ 13  │ GPIO -> 330Ω -> LED -> GND (pin 14)
     C3 LED   │ Green │  22  │ 15  │ GPIO -> 330Ω -> LED -> GND (pin 20)
     C4 LED   │ Green │  23  │ 16  │ GPIO -> 330Ω -> LED -> GND (pin 20)
     Q1 LED   │ Blue  │  24  │ 18  │ GPIO -> 330Ω -> LED -> GND (pin 20)
     Q2 LED   │ Blue  │  25  │ 22  │ GPIO -> 330Ω -> LED -> GND (pin 25)
     Strip    │ RGB   │  19  │ 35  │ GPIO -> DIN, 5V -> VCC, GND -> GND


Physical Layout Suggestion:
===========================

    Individual LEDs in a row to match cluster layout:

        [C1] [C2] [C3] [C4]    [Q1] [Q2]
        GREEN LEDs             BLUE LEDs
        (classical nodes)      (quantum nodes)

    LED Strip mounted separately showing partition activity:

        ════════════════════════════════════════
        │  Comet animation shows job activity  │
        │  Green = Normal, Blue = Quantum      │
        ════════════════════════════════════════


Parts List:
===========
    Individual Node LEDs:
    - 4x Green 5mm LEDs (for C1-C4)
    - 2x Blue 5mm LEDs (for Q1-Q2)
    - 6x 330 ohm resistors (1/4 watt)

    LED Strip:
    - 1x WS2812B LED strip (60 LEDs recommended, adjustable via --strip-leds)
    - 1x 5V power supply (for strips > 10 LEDs, ~60mA per LED at full white)
    - Capacitor 1000uF 6.3V (optional, across power supply for stability)

    General:
    - Jumper wires (male-to-female for GPIO header)
    - Breadboard (optional, for prototyping)

===============================================================================

Usage:
    # Run on rasqberry2 (connects to slurmctld on rasqberry via SSH)
    python3 slurmled_nodes.py

    # Simulation mode (no GPIO hardware)
    python3 slurmled_nodes.py --simulate

    # Custom polling interval
    python3 slurmled_nodes.py --interval 2

    # Test mode (light all LEDs for 5 seconds)
    python3 slurmled_nodes.py --test

    # Disable LED strip (only use individual node LEDs)
    python3 slurmled_nodes.py --no-strip

    # Custom LED strip configuration
    python3 slurmled_nodes.py --strip-leds 30 --strip-brightness 0.5
"""

import argparse
import logging
import signal
import subprocess
import time
import sys
import threading
from dataclasses import dataclass, field
from typing import Optional, Dict, Set, Tuple

try:
    import lgpio
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("Warning: lgpio not available. Running in simulation mode.")

try:
    import board
    import neopixel
    NEOPIXEL_AVAILABLE = True
except ImportError:
    NEOPIXEL_AVAILABLE = False
    print("Warning: neopixel not available. LED strip features disabled.")


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class Config:
    """Configuration for the SLURM LED monitor."""
    # Remote Slurm access (via SSH to rasqberry)
    slurm_host: str = "192.168.4.160"  # rasqberry IP address
    slurm_user: str = "rasqberry"  # SSH username on rasqberry
    docker_container: str = "login"

    # GPIO pins for each node (BCM numbering)
    node_pins: Dict[str, int] = field(default_factory=lambda: {
        # Classical nodes (Green LEDs)
        'c1': 17,  # Pin 11
        'c2': 27,  # Pin 13
        'c3': 22,  # Pin 15
        'c4': 23,  # Pin 16
        # Quantum nodes (Blue LEDs)
        'q1': 24,  # Pin 18
        'q2': 25,  # Pin 22
    })

    # Polling interval in seconds
    poll_interval: int = 5

    # LED Strip configuration
    strip_led_count: int = 60
    strip_brightness: float = 1.0
    strip_comet_speed: float = 0.03  # seconds between frames
    strip_comet_length: int = 10  # length of comet tail


# =============================================================================
# LED Controller
# =============================================================================

class NodeLEDController:
    """Controls individual LEDs for each Slurm node."""

    def __init__(self, node_pins: Dict[str, int], simulate: bool = False):
        self.node_pins = node_pins
        self.simulation_mode = simulate or not GPIO_AVAILABLE
        self.current_states: Dict[str, bool] = {node: False for node in node_pins}
        self.handle = None

        if not self.simulation_mode:
            try:
                self.handle = lgpio.gpiochip_open(0)
                for node, pin in node_pins.items():
                    lgpio.gpio_claim_output(self.handle, pin)
                    lgpio.gpio_write(self.handle, pin, 0)
                logging.info(f"GPIO initialized for nodes: {list(node_pins.keys())}")
            except Exception as e:
                logging.error(f"Failed to initialize GPIO: {e}")
                self.simulation_mode = True
        else:
            logging.info("Running in simulation mode")

    def set_node(self, node: str, state: bool):
        """Set LED state for a specific node."""
        if node not in self.node_pins:
            return

        if self.current_states.get(node) == state:
            return  # No change needed

        self.current_states[node] = state
        pin = self.node_pins[node]

        if self.simulation_mode:
            status = "ON " if state else "OFF"
            color = "BLUE " if node.startswith('q') else "GREEN"
            logging.debug(f"[SIM] {node.upper()} ({color}): {status}")
        else:
            lgpio.gpio_write(self.handle, pin, 1 if state else 0)

    def update(self, active_nodes: Set[str]):
        """Update all LEDs based on which nodes have running jobs."""
        changes = []
        for node in self.node_pins:
            new_state = node in active_nodes
            if new_state != self.current_states.get(node, False):
                self.set_node(node, new_state)
                color = "blue" if node.startswith('q') else "green"
                changes.append(f"{node.upper()}({'ON' if new_state else 'OFF'}/{color})")

        if changes:
            logging.info(f"LED changes: {', '.join(changes)}")

        # Log current state summary
        classical = [n.upper() for n in ['c1', 'c2', 'c3', 'c4'] if self.current_states.get(n)]
        quantum = [n.upper() for n in ['q1', 'q2'] if self.current_states.get(n)]

        if classical or quantum:
            parts = []
            if classical:
                parts.append(f"Classical: {', '.join(classical)}")
            if quantum:
                parts.append(f"Quantum: {', '.join(quantum)}")
            logging.info(f"Active: {' | '.join(parts)}")
        else:
            logging.debug("All nodes idle")

    def all_on(self):
        """Turn on all LEDs (for testing)."""
        for node in self.node_pins:
            self.set_node(node, True)

    def all_off(self):
        """Turn off all LEDs."""
        for node in self.node_pins:
            self.set_node(node, False)

    def test_sequence(self):
        """Run a test sequence lighting each LED in order."""
        logging.info("Running LED test sequence...")

        # Light each LED in sequence
        for node in ['c1', 'c2', 'c3', 'c4', 'q1', 'q2']:
            color = "BLUE" if node.startswith('q') else "GREEN"
            logging.info(f"  {node.upper()} ({color}) ON")
            self.set_node(node, True)
            time.sleep(0.3)

        time.sleep(0.5)

        # Turn off in reverse order
        for node in ['q2', 'q1', 'c4', 'c3', 'c2', 'c1']:
            self.set_node(node, False)
            time.sleep(0.2)

        # Flash all twice
        for _ in range(2):
            self.all_on()
            time.sleep(0.3)
            self.all_off()
            time.sleep(0.3)

        logging.info("Test sequence complete")

    def cleanup(self):
        """Clean up GPIO resources."""
        self.all_off()
        if self.handle is not None and not self.simulation_mode:
            lgpio.gpiochip_close(self.handle)
        logging.info("GPIO cleanup complete")


# =============================================================================
# LED Strip Controller with Comet Effect
# =============================================================================

class LEDStripController:
    """Controls WS2812B LED strip with comet effects based on partition activity."""

    # Color definitions
    GREEN = (0, 255, 0)   # Normal/classical partition
    BLUE = (0, 0, 255)    # Quantum partition
    OFF = (0, 0, 0)

    def __init__(self, config: Config, simulate: bool = False):
        self.config = config
        self.simulation_mode = simulate or not NEOPIXEL_AVAILABLE
        self.pixels = None
        self.running = False
        self.animation_thread = None
        self.lock = threading.Lock()

        # Current state
        self.normal_active = False
        self.quantum_active = False

        # Comet positions (for dual comet mode)
        self.green_pos = 0
        self.blue_pos = 0

        if not self.simulation_mode:
            try:
                # Use GPIO 19 (PCM) for LED strip data signal
                self.pixels = neopixel.NeoPixel(
                    board.D19,
                    config.strip_led_count,
                    brightness=config.strip_brightness,
                    auto_write=False,
                    pixel_order=neopixel.GRB
                )
                self.pixels.fill(self.OFF)
                self.pixels.show()
                logging.info(f"LED strip initialized on GPIO19: {config.strip_led_count} LEDs")
            except Exception as e:
                logging.error(f"Failed to initialize LED strip: {e}")
                self.simulation_mode = True
        else:
            logging.info("LED strip running in simulation mode")

    def _blend_colors(self, color1: Tuple[int, int, int], color2: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """Blend two colors together (additive)."""
        return (
            min(255, color1[0] + color2[0]),
            min(255, color1[1] + color2[1]),
            min(255, color1[2] + color2[2])
        )

    def _comet_brightness(self, distance: int, length: int) -> float:
        """Calculate brightness for comet tail based on distance from head."""
        if distance < 0 or distance >= length:
            return 0.0
        # Exponential falloff for comet tail
        return (1.0 - (distance / length)) ** 2

    def _render_comet(self, position: int, color: Tuple[int, int, int], buffer: list):
        """Render a single comet into the buffer."""
        length = self.config.strip_comet_length
        num_leds = self.config.strip_led_count

        for i in range(length):
            led_pos = (position - i) % num_leds
            brightness = self._comet_brightness(i, length)
            scaled_color = (
                int(color[0] * brightness),
                int(color[1] * brightness),
                int(color[2] * brightness)
            )
            buffer[led_pos] = self._blend_colors(buffer[led_pos], scaled_color)

    def _animation_loop(self):
        """Background thread for running comet animations."""
        num_leds = self.config.strip_led_count

        while self.running:
            with self.lock:
                normal = self.normal_active
                quantum = self.quantum_active

            if not normal and not quantum:
                # No activity - turn off strip
                if not self.simulation_mode and self.pixels:
                    self.pixels.fill(self.OFF)
                    self.pixels.show()
                time.sleep(0.1)
                continue

            # Create buffer for blending
            buffer = [self.OFF] * num_leds

            if normal and quantum:
                # Both active - two comets going opposite directions
                self._render_comet(self.green_pos, self.GREEN, buffer)
                self._render_comet(num_leds - 1 - self.blue_pos, self.BLUE, buffer)
                self.green_pos = (self.green_pos + 1) % num_leds
                self.blue_pos = (self.blue_pos + 1) % num_leds
            elif normal:
                # Only normal - green comet
                self._render_comet(self.green_pos, self.GREEN, buffer)
                self.green_pos = (self.green_pos + 1) % num_leds
            elif quantum:
                # Only quantum - blue comet
                self._render_comet(self.blue_pos, self.BLUE, buffer)
                self.blue_pos = (self.blue_pos + 1) % num_leds

            # Update strip
            if not self.simulation_mode and self.pixels:
                for i, color in enumerate(buffer):
                    self.pixels[i] = color
                self.pixels.show()

            time.sleep(self.config.strip_comet_speed)

    def update_state(self, normal_active: bool, quantum_active: bool):
        """Update which partitions are active."""
        with self.lock:
            old_normal = self.normal_active
            old_quantum = self.quantum_active
            self.normal_active = normal_active
            self.quantum_active = quantum_active

        if (normal_active != old_normal) or (quantum_active != old_quantum):
            states = []
            if normal_active:
                states.append("NORMAL(green)")
            if quantum_active:
                states.append("QUANTUM(blue)")
            if states:
                logging.info(f"LED strip: {' + '.join(states)} comet")
            else:
                logging.info("LED strip: OFF (no partition activity)")

    def start(self):
        """Start the animation thread."""
        if self.running:
            return
        self.running = True
        self.animation_thread = threading.Thread(target=self._animation_loop, daemon=True)
        self.animation_thread.start()
        logging.info("LED strip animation started")

    def stop(self):
        """Stop the animation thread."""
        self.running = False
        if self.animation_thread:
            self.animation_thread.join(timeout=1.0)
        if not self.simulation_mode and self.pixels:
            self.pixels.fill(self.OFF)
            self.pixels.show()
        logging.info("LED strip animation stopped")

    def cleanup(self):
        """Clean up resources."""
        self.stop()
        if not self.simulation_mode and self.pixels:
            self.pixels.deinit()
        logging.info("LED strip cleanup complete")


# =============================================================================
# Slurm Monitor
# =============================================================================

class SlurmNodeMonitor:
    """Monitors Slurm node states via SSH to the main cluster."""

    def __init__(self, config: Config):
        self.config = config

    def get_active_nodes(self) -> Set[str]:
        """Get set of nodes that have running jobs."""
        try:
            # SSH to rasqberry and run sinfo to get node states
            # Use shell=True to preserve quote handling exactly as command line
            ssh_target = f"{self.config.slurm_user}@{self.config.slurm_host}"
            cmd = f'ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {ssh_target} "docker exec {self.config.docker_container} sinfo -N -h -o \\"%N %T\\""'
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logging.warning(f"sinfo failed (rc={result.returncode}): {result.stderr}")
                logging.debug(f"stdout was: {result.stdout}")
                return set()

            logging.debug(f"sinfo output: {result.stdout.strip()}")
            active_nodes = set()
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    node = parts[0].lower()
                    state = parts[1].lower()
                    # Node is active if it's NOT idle (and not down/drain/etc)
                    # This catches: mixed, allocated, completing, etc.
                    if 'idle' not in state and 'down' not in state and 'drain' not in state:
                        active_nodes.add(node)
                        logging.debug(f"  {node} is active (state: {state})")

            return active_nodes

        except subprocess.TimeoutExpired:
            logging.warning("Timeout getting node states")
            return set()
        except Exception as e:
            logging.error(f"Error getting node states: {e}")
            return set()

    def get_active_partitions(self) -> Tuple[bool, bool]:
        """Get which partitions have running jobs.

        Returns:
            Tuple of (normal_active, quantum_active)
        """
        try:
            ssh_target = f"{self.config.slurm_user}@{self.config.slurm_host}"
            # Get running jobs with their partitions
            cmd = f'ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {ssh_target} "docker exec {self.config.docker_container} squeue -h -t RUNNING -o \\"%P\\""'
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logging.warning(f"squeue failed (rc={result.returncode}): {result.stderr}")
                return (False, False)

            partitions = set()
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    partitions.add(line.strip().lower())

            logging.debug(f"Active partitions: {partitions}")

            normal_active = 'normal' in partitions
            quantum_active = 'quantum' in partitions

            return (normal_active, quantum_active)

        except subprocess.TimeoutExpired:
            logging.warning("Timeout getting partition states")
            return (False, False)
        except Exception as e:
            logging.error(f"Error getting partition states: {e}")
            return (False, False)


# =============================================================================
# Main Application
# =============================================================================

class SlurmLEDMonitor:
    """Main application that monitors Slurm and controls LEDs."""

    def __init__(self, config: Config, simulate: bool = False, enable_strip: bool = True):
        self.config = config
        self.running = True
        self.led_controller = NodeLEDController(config.node_pins, simulate)
        self.slurm_monitor = SlurmNodeMonitor(config)

        # LED strip controller for partition-based comet effects
        self.strip_controller = None
        if enable_strip:
            self.strip_controller = LEDStripController(config, simulate)

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        logging.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def run(self):
        """Main monitoring loop."""
        logging.info("=" * 60)
        logging.info("SLURM Node LED Monitor")
        logging.info("=" * 60)
        logging.info(f"Slurm host: {self.config.slurm_host}")
        logging.info(f"Container: {self.config.docker_container}")
        logging.info(f"Nodes: {list(self.config.node_pins.keys())}")
        logging.info(f"LED strip: {'enabled' if self.strip_controller else 'disabled'}")
        logging.info(f"Polling: every {self.config.poll_interval}s")
        logging.info("-" * 60)

        # Startup test sequence
        self.led_controller.test_sequence()

        # Start LED strip animation thread
        if self.strip_controller:
            self.strip_controller.start()

        logging.info("Monitoring started. Press Ctrl+C to stop.")
        logging.info("-" * 60)

        try:
            while self.running:
                # Update individual node LEDs
                active_nodes = self.slurm_monitor.get_active_nodes()
                self.led_controller.update(active_nodes)

                # Update LED strip based on partition activity
                if self.strip_controller:
                    normal_active, quantum_active = self.slurm_monitor.get_active_partitions()
                    self.strip_controller.update_state(normal_active, quantum_active)

                time.sleep(self.config.poll_interval)
        finally:
            if self.strip_controller:
                self.strip_controller.cleanup()
            self.led_controller.cleanup()
            logging.info("Monitor stopped")


# =============================================================================
# Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='SLURM Node LED Monitor - Individual LEDs per container + LED strip',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
GPIO Pin Assignments (BCM numbering):
  Individual Node LEDs:
    C1: GPIO 17 (pin 11) - Green LED
    C2: GPIO 27 (pin 13) - Green LED
    C3: GPIO 22 (pin 15) - Green LED
    C4: GPIO 23 (pin 16) - Green LED
    Q1: GPIO 24 (pin 18) - Blue LED
    Q2: GPIO 25 (pin 22) - Blue LED

  LED Strip (WS2812B):
    Data: GPIO 19 (pin 35) - Uses PCM for signal timing
    - Green comet: Normal partition has running jobs
    - Blue comet: Quantum partition has running jobs
    - Both comets: Both partitions have running jobs

Wiring:
  LEDs: GPIO -> 330 ohm resistor -> LED (anode) -> LED (cathode) -> GND
  Strip: GPIO19 -> DIN, 5V -> VCC, GND -> GND (use external power for long strips)

Examples:
  python3 slurmled_nodes.py              # Normal operation
  python3 slurmled_nodes.py --simulate   # Simulation mode (no hardware)
  python3 slurmled_nodes.py --interval 2 # Poll every 2 seconds
  python3 slurmled_nodes.py --test       # Test LEDs and exit
  python3 slurmled_nodes.py --no-strip   # Disable LED strip
  python3 slurmled_nodes.py --strip-leds 30 --strip-brightness 0.5
        """
    )
    parser.add_argument(
        '--simulate', '-s',
        action='store_true',
        help='Run in simulation mode (no GPIO hardware)'
    )
    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=5,
        help='Polling interval in seconds (default: 5)'
    )
    parser.add_argument(
        '--host',
        default='192.168.4.160',
        help='Hostname/IP of main Slurm controller (default: 192.168.4.160)'
    )
    parser.add_argument(
        '--user', '-u',
        default='rasqberry',
        help='SSH username on Slurm controller (default: rasqberry)'
    )
    parser.add_argument(
        '--container',
        default='login',
        help='Docker container name (default: login)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--test', '-t',
        action='store_true',
        help='Test mode: run LED test sequence then exit'
    )
    parser.add_argument(
        '--no-strip',
        action='store_true',
        help='Disable LED strip (only use individual node LEDs)'
    )
    parser.add_argument(
        '--strip-leds',
        type=int,
        default=60,
        help='Number of LEDs in the strip (default: 60)'
    )
    parser.add_argument(
        '--strip-brightness',
        type=float,
        default=1.0,
        help='LED strip brightness 0.0-1.0 (default: 1.0)'
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # Create configuration
    config = Config(
        slurm_host=args.host,
        slurm_user=args.user,
        docker_container=args.container,
        poll_interval=args.interval,
        strip_led_count=args.strip_leds,
        strip_brightness=args.strip_brightness
    )

    # Test mode
    if args.test:
        logging.info("Test mode: running LED test sequence...")
        controller = NodeLEDController(config.node_pins, args.simulate)
        controller.test_sequence()
        time.sleep(1)
        controller.cleanup()
        logging.info("Test complete")
        return

    # Run the monitor
    monitor = SlurmLEDMonitor(config, simulate=args.simulate, enable_strip=not args.no_strip)
    monitor.run()


if __name__ == '__main__':
    main()
