#!/usr/bin/env python3
"""
Marlin Bed Mesh Analyzer
Parses mesh leveling output and evaluates bed skew/levelness.
"""

import re
import sys


def parse_mesh(input_text: str) -> list[list[float]]:
    """Parse Marlin mesh output into a 2D array of values."""
    mesh = []
    for line in input_text.strip().split('\n'):
        # Look for lines with row data (start with "Recv:  N" where N is a digit)
        match = re.search(r'Recv:\s+\d+\s+([-+]?\d+\.\d+.*)', line)
        if match:
            values_str = match.group(1)
            values = [float(v) for v in re.findall(r'[-+]?\d+\.\d+', values_str)]
            if values:
                mesh.append(values)
    return mesh


def analyze_mesh(mesh: list[list[float]]) -> dict:
    """Analyze mesh for skew and levelness."""
    if not mesh:
        return {"error": "No mesh data found"}
    
    rows = len(mesh)
    cols = len(mesh[0])
    
    # Flatten for stats
    all_values = [v for row in mesh for v in row]
    min_val = min(all_values)
    max_val = max(all_values)
    avg_val = sum(all_values) / len(all_values)
    total_range = max_val - min_val
    
    # Corner analysis (assuming standard orientation)
    # Row 0 = front, Row -1 = back
    # Col 0 = left, Col -1 = right
    corners = {
        "front_left": mesh[0][0],
        "front_right": mesh[0][-1],
        "back_left": mesh[-1][0],
        "back_right": mesh[-1][-1],
    }
    
    # Find min/max positions
    min_pos = None
    max_pos = None
    for i, row in enumerate(mesh):
        for j, val in enumerate(row):
            if val == min_val:
                min_pos = (i, j)
            if val == max_val:
                max_pos = (i, j)
    
    # Calculate tilts
    front_avg = sum(mesh[0]) / len(mesh[0])
    back_avg = sum(mesh[-1]) / len(mesh[-1])
    left_avg = sum(row[0] for row in mesh) / rows
    right_avg = sum(row[-1] for row in mesh) / rows
    
    front_back_tilt = back_avg - front_avg  # Positive = back is higher
    left_right_tilt = right_avg - left_avg  # Positive = right is higher
    
    return {
        "dimensions": f"{rows}x{cols}",
        "min": min_val,
        "max": max_val,
        "range": total_range,
        "average": avg_val,
        "corners": corners,
        "min_position": min_pos,
        "max_position": max_pos,
        "front_back_tilt": front_back_tilt,
        "left_right_tilt": left_right_tilt,
    }


def position_to_label(pos: tuple[int, int], rows: int, cols: int) -> str:
    """Convert grid position to human-readable location."""
    row, col = pos
    
    if row == 0:
        y_label = "front"
    elif row == rows - 1:
        y_label = "back"
    else:
        y_label = "middle"
    
    if col == 0:
        x_label = "left"
    elif col == cols - 1:
        x_label = "right"
    else:
        x_label = "center"
    
    if y_label == "middle" and x_label == "center":
        return "center"
    elif y_label == "middle":
        return x_label
    elif x_label == "center":
        return y_label
    else:
        return f"{y_label}-{x_label}"


def generate_report(analysis: dict) -> str:
    """Generate human-readable analysis report."""
    if "error" in analysis:
        return f"Error: {analysis['error']}"
    
    rows, cols = map(int, analysis["dimensions"].split("x"))
    
    lines = [
        "=" * 50,
        "BED MESH ANALYSIS",
        "=" * 50,
        "",
        f"Grid Size: {analysis['dimensions']}",
        f"Min Value: {analysis['min']:+.3f}mm at {position_to_label(analysis['min_position'], rows, cols)}",
        f"Max Value: {analysis['max']:+.3f}mm at {position_to_label(analysis['max_position'], rows, cols)}",
        f"Total Range: {analysis['range']:.3f}mm",
        f"Average: {analysis['average']:+.3f}mm",
        "",
        "-" * 50,
        "CORNER VALUES",
        "-" * 50,
    ]
    
    for corner, value in analysis["corners"].items():
        label = corner.replace("_", "-").title()
        lines.append(f"  {label}: {value:+.3f}mm")
    
    lines.extend([
        "",
        "-" * 50,
        "TILT ANALYSIS",
        "-" * 50,
        f"  Front-to-Back: {analysis['front_back_tilt']:+.3f}mm",
    ])
    
    if analysis["front_back_tilt"] > 0.1:
        lines.append("    → Back is HIGHER than front")
    elif analysis["front_back_tilt"] < -0.1:
        lines.append("    → Front is HIGHER than back")
    else:
        lines.append("    → Level front-to-back ✓")
    
    lines.append(f"  Left-to-Right: {analysis['left_right_tilt']:+.3f}mm")
    
    if analysis["left_right_tilt"] > 0.1:
        lines.append("    → Right side is HIGHER than left")
    elif analysis["left_right_tilt"] < -0.1:
        lines.append("    → Left side is HIGHER than right")
    else:
        lines.append("    → Level left-to-right ✓")
    
    lines.extend([
        "",
        "-" * 50,
        "ASSESSMENT",
        "-" * 50,
    ])
    
    range_val = analysis["range"]
    if range_val <= 0.3:
        lines.append("  ★ Excellent - Bed is very well trammed")
    elif range_val <= 0.6:
        lines.append("  ✓ Good - Mesh compensation will handle this easily")
    elif range_val <= 1.0:
        lines.append("  ⚠ Acceptable - Consider minor tramming adjustments")
    elif range_val <= 2.0:
        lines.append("  ✗ Poor - Tramming adjustments recommended")
    else:
        lines.append("  ✗✗ Bad - Significant tramming needed before relying on mesh")
    
    # Generate recommendations
    lines.extend([
        "",
        "-" * 50,
        "RECOMMENDATIONS",
        "-" * 50,
    ])
    
    recommendations = []
    corners = analysis["corners"]
    avg = analysis["average"]
    
    # Check each corner deviation from average
    corner_wheel_map = {
        "front_left": "front-left",
        "front_right": "front-right",
        "back_left": "back-left",
        "back_right": "back-right",
    }
    
    for corner, value in corners.items():
        diff = value - avg
        wheel = corner_wheel_map[corner]
        if diff > 0.15:
            recommendations.append(f"  • Lower {wheel} wheel (currently {diff:+.2f}mm high)")
        elif diff < -0.15:
            recommendations.append(f"  • Raise {wheel} wheel (currently {diff:+.2f}mm low)")
    
    if recommendations:
        lines.extend(recommendations)
    else:
        lines.append("  None - bed is well trammed!")
    
    lines.extend(["", "=" * 50])
    
    return "\n".join(lines)


def main():
    if len(sys.argv) > 1:
        # Read from file
        with open(sys.argv[1], 'r') as f:
            input_text = f.read()
    else:
        # Read from stdin
        print("Paste mesh data (Ctrl+D or Ctrl+Z when done):")
        input_text = sys.stdin.read()
    
    mesh = parse_mesh(input_text)
    
    if not mesh:
        print("Error: Could not parse mesh data")
        print("Expected format:")
        print("Recv:  0 -0.402 +0.083 -0.027 +0.026 -0.062")
        sys.exit(1)
    
    analysis = analyze_mesh(mesh)
    report = generate_report(analysis)
    print(report)


if __name__ == "__main__":
    main()