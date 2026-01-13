#!/usr/bin/env python3
"""
QCSC Intro Animation for RasQberry LED Matrix

Displays:
1. "IBM" in blue (2 seconds)
2. "HPC" in white (2 seconds)
3. "Q" in blue (2 seconds)
4. Scrolls "Quantum Centric Super Computing"
5. "QCSC" with QC in blue, SC in white (holds for 10 seconds)

Usage:
    sudo /home/rasqberry/RasQberry-Two/venv/RQB2/bin/python3 qcsc_intro.py
"""

import sys
import time

sys.path.insert(0, '/home/rasqberry/QCSC/RasQberry-Two/RQB2-bin')
from rq_led_utils import get_led_config, create_neopixel_strip, map_xy_to_pixel, create_text_bitmap

# Colors
BLUE = (0, 150, 255)
WHITE = (255, 255, 255)
OFF = (0, 0, 0)

# Initialize hardware
config = get_led_config()
pixels = create_neopixel_strip(config['led_count'], config['pixel_order'], brightness=0.5)


def clear():
    """Clear the display."""
    pixels.fill(OFF)
    pixels.show()


def display_text(text, color, x_offset=0):
    """Display text on the matrix at given offset."""
    text_columns = create_text_bitmap(text)
    width = config['matrix_width']
    height = config['matrix_height']
    layout = config['layout']

    for col_idx, col_data in enumerate(text_columns):
        x = x_offset + col_idx
        if x >= width or x < 0:
            continue
        for y in range(min(height, 7)):
            if col_data & (1 << y):
                led_index = map_xy_to_pixel(x, y, layout)
                if led_index is not None:
                    pixels[led_index] = color


def show_text(text, color, x_offset=0, duration=2.0):
    """Display text for a duration."""
    pixels.fill(OFF)
    display_text(text, color, x_offset)
    pixels.show()
    time.sleep(duration)


def scroll_text(text, color, speed=0.08):
    """Scroll text from right to left across the display."""
    text_columns = create_text_bitmap(text)
    text_width = len(text_columns)
    width = config['matrix_width']
    height = config['matrix_height']
    layout = config['layout']

    # Start from right edge, scroll until text is off left edge
    for offset in range(width, -text_width - 1, -1):
        pixels.fill(OFF)

        for col_idx, col_data in enumerate(text_columns):
            x = offset + col_idx
            if x >= width or x < 0:
                continue
            for y in range(min(height, 7)):
                if col_data & (1 << y):
                    led_index = map_xy_to_pixel(x, y, layout)
                    if led_index is not None:
                        pixels[led_index] = color

        pixels.show()
        time.sleep(speed)


def main():
    print("QCSC Intro Animation")
    print("=" * 40)

    try:
        # 1. Display "IBM" in blue
        print("Displaying IBM (blue)...")
        show_text("IBM", BLUE, x_offset=5, duration=2.0)

        # 2. Display "HPC" in white
        print("Displaying HPC (white)...")
        show_text("HPC", WHITE, x_offset=3, duration=2.0)

        # 3. Display "Q" in blue
        print("Displaying Q (blue)...")
        show_text("Q", BLUE, x_offset=9, duration=2.0)

        # 4. Scroll "Quantum Centric Super Computing"
        print("Scrolling 'Quantum Centric Super Computing'...")
        scroll_text("Quantum Centric Super Computing", BLUE, speed=0.06)

        # 5. Display "QCSC" - QC in blue, SC in white (hold for 10 seconds)
        print("Displaying QCSC (QC blue + SC white) for 10 seconds...")
        pixels.fill(OFF)
        display_text("QC", BLUE, x_offset=1)
        display_text("SC", WHITE, x_offset=13)
        pixels.show()
        time.sleep(10)

        # Clear and exit
        print("Done!")
        clear()

    except KeyboardInterrupt:
        print("\nInterrupted!")
        clear()


if __name__ == "__main__":
    main()
