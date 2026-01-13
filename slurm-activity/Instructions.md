# SLURM LED Monitor - Quick Start Guide

## Architecture Overview

The SLURM LED monitoring system is split across two Raspberry Pi 5s:

- **rasqberry** (`slurmled.py`): Controls individual LEDs (GPIO 17, 27) and LED matrix (GPIO 19)
- **rasqberry2** (`slurmled_nodes.py`): Controls individual LEDs per container node (GPIO 17, 27, 22, 23, 24, 25)

---

## 1. Start the LED Monitor (rasqberry)

```bash
cd /home/rasqberry/QCSC/QHPC_Tutorial/slurm-activity
sudo /home/rasqberry/RasQberry-Two/venv/RQB2/bin/python3 slurmled.py --container login --interval 2 -v
```

Press Ctrl+C to stop.

To run in the background:

```bash
sudo /home/rasqberry/RasQberry-Two/venv/RQB2/bin/python3 slurmled.py --container login --interval 3 &
```

## 2. Start the Node LED Monitor (rasqberry2)

SSH into rasqberry2 and run:

```bash
python3 ~/slurmled_nodes.py -v -i 1
```

The rasqberry2 monitors Slurm node states via SSH to rasqberry and lights up individual LEDs for each container:
- **Green LEDs** (C1-C4): Classical compute nodes
- **Blue LEDs** (Q1-Q2): Quantum compute nodes

---

## 3. Submit Your Workloads

From any terminal, submit jobs as normal:

```bash
docker exec -it login bash
```
Then from the login container terminal:
```bash
cd /shared/chapters/ch3/workflows
MAPPING_JOB=$(sbatch --parsable mapping.sh)
OPTIMIZE_JOB=$(sbatch --parsable --dependency=afterok:$MAPPING_JOB optimization.sh)
EXECUTE_JOB=$(sbatch --parsable --dependency=afterok:$OPTIMIZE_JOB execution.sh)
```

---

## 4. LED Behavior

### Individual LEDs - rasqberry (Job-based)
The green and blue LEDs indicate whether jobs are **running** in each partition:

| Green LED (GPIO 17) | Blue LED (GPIO 27) | Meaning |
|---------------------|-------------------|---------|
| OFF | OFF | No jobs running |
| ON | OFF | Normal partition jobs running |
| OFF | ON | Quantum partition jobs running |
| ON | ON | Both types running |

### LED Matrix - rasqberry (Job-based Text)
The 24x8 LED matrix displays text indicating which partition types have running jobs:

| Matrix Display | Meaning |
|----------------|---------|
| OFF | No jobs running (idle) |
| **HPC** (green) | Normal partition jobs running |
| **Q** (blue) | Quantum partition jobs running |
| **QCSC** | Both types running (QC blue + SC green) |

### Node LEDs - rasqberry2 (Per-Container)
Individual LEDs light up when each container node has a running job:

| LED | GPIO | Pin | Color | Node |
|-----|------|-----|-------|------|
| C1 | 17 | 11 | Green | Classical node c1 |
| C2 | 27 | 13 | Green | Classical node c2 |
| C3 | 22 | 15 | Green | Classical node c3 |
| C4 | 23 | 16 | Green | Classical node c4 |
| Q1 | 24 | 18 | Blue | Quantum node q1 |
| Q2 | 25 | 22 | Blue | Quantum node q2 |

---

## 5. Stop the Monitors

**rasqberry (foreground):** Press Ctrl+C

**rasqberry (background):**
```bash
sudo pkill -f slurmled.py
```

**rasqberry2:** Press Ctrl+C or:
```bash
pkill -f slurmled_nodes.py
```

---

## Hardware Setup

### rasqberry
- **Green LED**: GPIO 17 (pin 11) -> 330Ω resistor -> GND
- **Blue LED**: GPIO 27 (pin 13) -> 330Ω resistor -> GND
- **LED Matrix (24x8)**: GPIO 19 (configured in RasQberry utilities)

```
Raspberry Pi 5 GPIO Header (40-pin)
===================================

                    +-----+-----+
               3.3V | 1   | 2   | 5V
              GPIO2 | 3   | 4   | 5V
              GPIO3 | 5   | 6   | GND  <─── Ground bus
              GPIO4 | 7   | 8   | GPIO14
                GND | 9   | 10  | GPIO15
  GREEN ────GPIO17  | 11  | 12  | GPIO18
  BLUE  ────GPIO27  | 13  | 14  | GND  <─── Ground bus
             GPIO22 | 15  | 16  | GPIO23
               3.3V | 17  | 18  | GPIO24
  MATRIX ───GPIO19  | 19  | 20  | GND  <─── Ground bus
              GPIO9 | 21  | 22  | GPIO25
             GPIO11 | 23  | 24  | GPIO8
                GND | 25  | 26  | GPIO7
                    +-----+-----+
```

**Complete Wiring Table:**
```
    LED    │ Color │ GPIO │ Pin │ LED Anode (+) │ LED Cathode (-) │ Resistor
    ───────┼───────┼──────┼─────┼───────────────┼─────────────────┼──────────
    Normal │ Green │  17  │ 11  │ After 330Ω    │ GND (pin 6)     │ 330Ω
    Quantum│ Blue  │  27  │ 13  │ After 330Ω    │ GND (pin 14)    │ 330Ω
    Matrix │  -    │  19  │ 19  │ Direct to matrix data pin       │ -
```

Parts list for rasqberry:
- 1x Green 5mm LED (normal partition indicator)
- 1x Blue 5mm LED (quantum partition indicator)
- 2x 330 ohm resistors (1/4 watt)
- 1x 24x8 LED Matrix (WS2812B, configured via RasQberry utilities)
- Jumper wires

### rasqberry2
Individual LEDs for each node:

```
Raspberry Pi 5 GPIO Header (40-pin)
===================================

                    +-----+-----+
               3.3V | 1   | 2   | 5V
              GPIO2 | 3   | 4   | 5V
              GPIO3 | 5   | 6   | GND  <─── Ground bus
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
                    +-----+-----+

LED Wiring: GPIO -> 330Ω resistor -> LED (anode) -> GND (cathode)
```

**LED Wiring Detail:**
```
    GPIO Pin ────[####]────┤>├──── GND
                 330Ω      LED
                resistor   (long leg = anode, short leg = cathode)
```

**Complete Wiring Table:**
```
    Node │ Color │ GPIO │ Pin │ LED Anode (+) │ LED Cathode (-) │ Resistor
    ─────┼───────┼──────┼─────┼───────────────┼─────────────────┼──────────
     C1  │ Green │  17  │ 11  │ After 330Ω    │ GND (pin 6)     │ 330Ω
     C2  │ Green │  27  │ 13  │ After 330Ω    │ GND (pin 14)    │ 330Ω
     C3  │ Green │  22  │ 15  │ After 330Ω    │ GND (pin 20)    │ 330Ω
     C4  │ Green │  23  │ 16  │ After 330Ω    │ GND (pin 20)    │ 330Ω
     Q1  │ Blue  │  24  │ 18  │ After 330Ω    │ GND (pin 20)    │ 330Ω
     Q2  │ Blue  │  25  │ 22  │ After 330Ω    │ GND (pin 25)    │ 330Ω
```

**Physical Layout Suggestion:**
```
    Arrange LEDs in a row to match cluster layout:

        [C1] [C2] [C3] [C4]    [Q1] [Q2]
        GREEN LEDs             BLUE LEDs
        (classical nodes)      (quantum nodes)
```

Parts list for rasqberry2:
- 4x Green 5mm LEDs (for C1-C4)
- 2x Blue 5mm LEDs (for Q1-Q2)
- 6x 330 ohm resistors (1/4 watt)
- Jumper wires

### Network
- rasqberry IP: 192.168.4.160
- rasqberry2 IP: 192.168.4.161

---

## Requirements

### rasqberry
```bash
pip install lgpio
```

### rasqberry2
```bash
pip install lgpio
```

SSH key setup (run on rasqberry2):
```bash
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519
ssh-copy-id rasqberry@192.168.4.160
```

---

## Optional Flags

### rasqberry (slurmled.py)

| Flag | Description |
|------|-------------|
| `--container NAME` | Docker container name (default: login) |
| `--interval 5` | Poll every 5 seconds for jobs (default: 30) |
| `-v` | Verbose logging |
| `--slurm-user USERNAME` | Only monitor one user's jobs |
| `--matrix-brightness 0.5` | Matrix brightness 0.0-1.0 (default: 0.5) |
| `--no-matrix` | Disable LED matrix display |

### rasqberry2 (slurmled_nodes.py)

| Flag | Description |
|------|-------------|
| `--host IP` | IP of rasqberry (default: 192.168.4.160) |
| `--user USER` | SSH username (default: rasqberry) |
| `--container NAME` | Docker container name (default: login) |
| `--interval 1` | Poll every N seconds (default: 5) |
| `--simulate` | Run in simulation mode (no GPIO) |
| `--test` | Run LED test sequence and exit |
| `-v` | Verbose logging |

---

## Example Commands

### rasqberry - Basic usage:
```bash
sudo /home/rasqberry/RasQberry-Two/venv/RQB2/bin/python3 slurmled.py --container login -v --interval 2
```

### rasqberry - With brighter matrix:
```bash
sudo /home/rasqberry/RasQberry-Two/venv/RQB2/bin/python3 slurmled.py --container login -v --interval 2 --matrix-brightness 0.8
```

### rasqberry2 - Basic usage:
```bash
python3 ~/slurmled_nodes.py -v -i 1
```

### rasqberry2 - Test LEDs:
```bash
python3 ~/slurmled_nodes.py --test
```

### rasqberry2 - Simulation mode (no hardware):
```bash
python3 ~/slurmled_nodes.py --simulate -v -i 1
```

---

## Testing

### Test Matrix Display (rasqberry)

```bash
sudo /home/rasqberry/RasQberry-Two/venv/RQB2/bin/python3 -c "
import sys
sys.path.insert(0, '/home/rasqberry/QCSC/RasQberry-Two/RQB2-bin')
from rq_led_utils import get_led_config, create_neopixel_strip, map_xy_to_pixel, create_text_bitmap
import time

config = get_led_config()
pixels = create_neopixel_strip(config['led_count'], config['pixel_order'], brightness=0.5)

def display_text(text, color, x_offset=0):
    text_columns = create_text_bitmap(text)
    for col_idx, col_data in enumerate(text_columns):
        x = x_offset + col_idx
        if x >= config['matrix_width'] or x < 0:
            continue
        for y in range(min(config['matrix_height'], 7)):
            if col_data & (1 << y):
                led_index = map_xy_to_pixel(x, y, config['layout'])
                if led_index is not None:
                    pixels[led_index] = color

print('Displaying HPC (green)...')
pixels.fill((0,0,0))
display_text('HPC', (0, 255, 0), x_offset=3)
pixels.show()
time.sleep(2)

print('Displaying Q (blue)...')
pixels.fill((0,0,0))
display_text('Q', (0, 150, 255), x_offset=9)
pixels.show()
time.sleep(2)

print('Displaying QCSC (QC blue + SC green)...')
pixels.fill((0,0,0))
display_text('QC', (0, 150, 255), x_offset=1)
display_text('SC', (0, 255, 0), x_offset=13)
pixels.show()
time.sleep(2)

print('Done!')
pixels.fill((0,0,0))
pixels.show()
"
```

### Test Node LEDs (rasqberry2)

```bash
python3 ~/slurmled_nodes.py --test
```

### Test Individual LEDs (rasqberry)

```bash
sudo /home/rasqberry/RasQberry-Two/venv/RQB2/bin/python3 -c "
import lgpio
import time

chip = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(chip, 17)
lgpio.gpio_claim_output(chip, 27)

print('Green LED on...')
lgpio.gpio_write(chip, 17, 1)
time.sleep(1)

print('Blue LED on...')
lgpio.gpio_write(chip, 27, 1)
time.sleep(1)

print('Both off...')
lgpio.gpio_write(chip, 17, 0)
lgpio.gpio_write(chip, 27, 0)

lgpio.gpiochip_close(chip)
print('Done!')
"
```

---

## Troubleshooting

### GPIO Busy Error
If you see `lgpio.error: 'GPIO busy'`, a previous instance is still running:
```bash
# On rasqberry
sudo pkill -9 -f slurmled.py

# On rasqberry2
pkill -9 -f slurmled_nodes.py
```

### LEDs Not Lighting Up
1. Verify hardware connections (check for loose pins!)
2. Run the test commands above

### Wrong LED Colors (rasqberry)
The script determines job type by partition name:
- Jobs in `quantum` partition → Blue LED
- Jobs in other partitions → Green LED

Check which partition your job is running on:
```bash
docker exec login squeue -o "%.10i %.12P %.15j"
```

### Node LEDs Not Responding (rasqberry2)
Check if sinfo command works via SSH:
```bash
ssh rasqberry@192.168.4.160 "docker exec login sinfo -N -h -o \"%N %T\""
```

Should return node states like:
```
c1 idle
c2 mixed
c3 allocated
...
```

### SSH Permission Denied (rasqberry2)
Re-setup SSH keys:
```bash
# On rasqberry2
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519
ssh-copy-id rasqberry@192.168.4.160
```

---

## Run on Boot (Optional)

### rasqberry
Add to root's crontab:
```bash
sudo crontab -e
```

Add:
```
@reboot cd /home/rasqberry/QCSC/QHPC_Tutorial/slurm-activity && /home/rasqberry/RasQberry-Two/venv/RQB2/bin/python3 slurmled.py --container login --interval 5 >> /tmp/slurmled.log 2>&1 &
```

### rasqberry2
Add to user's crontab:
```bash
crontab -e
```

Add:
```
@reboot /usr/bin/python3 /home/rasqberry2/slurmled_nodes.py -i 1 >> /tmp/slurmled_nodes.log 2>&1 &
```

---

## Cluster Node Configuration Summary

| Node | Partition | Location | Container | LEDs |
|------|-----------|----------|-----------|------|
| c1 | normal | rasqberry | Docker | rasqberry2 GPIO 17 (Green) |
| c2 | normal | rasqberry | Docker | rasqberry2 GPIO 27 (Green) |
| c3 | normal | rasqberry2 | Docker | rasqberry2 GPIO 22 (Green) |
| c4 | normal | rasqberry2 | Docker | rasqberry2 GPIO 23 (Green) |
| q1 | quantum | rasqberry | Docker | rasqberry2 GPIO 24 (Blue) |
| q2 | quantum | rasqberry2 | Docker | rasqberry2 GPIO 25 (Blue) |
