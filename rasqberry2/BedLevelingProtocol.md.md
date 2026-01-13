# Bulletproof Bed Leveling Protocol for Ender 3 Pro with CR Touch

Your first layer problems stem from a calibration chain where any weak link causes inconsistency. This protocol establishes a systematic approach: mechanically stable bed first, then precise firmware configuration, followed by Z-offset calibration and mesh creation. With silicon spacers providing stability and CR Touch handling compensation, you can achieve reliable **±0.01mm** first layer consistency.

## Phase 1: Marlin firmware configuration

Before any physical calibration, your firmware must be correctly configured. These settings go in `Configuration.h` and `Configuration_adv.h` when compiling from the latest Marlin bugfix branch for your Creality 4.2.2 board.

### Core probe settings in Configuration.h

```cpp
// Board and probe type
#define MOTHERBOARD BOARD_CREALITY_V4
#define BLTOUCH                              // Works for CR Touch
#define USE_PROBE_FOR_Z_HOMING

// Probe offsets - MEASURE YOUR SPECIFIC MOUNT
// Standard Creality metal bracket: probe left and forward of nozzle
#define NOZZLE_TO_PROBE_OFFSET { -42, -10, 0 }

// Z-safe homing prevents probing outside bed
#define Z_SAFE_HOMING
#define Z_SAFE_HOMING_X_POINT 117            // Bed center
#define Z_SAFE_HOMING_Y_POINT 117

// Probing margins - keeps probe on bed surface
#define PROBING_MARGIN 10                    // 10mm from edges

// Critical: allows probe to go below 0 during setup
#define Z_PROBE_LOW_POINT -5                 // Use -10 for initial setup

// Multiple probing for accuracy
#define MULTIPLE_PROBING 2                   // Probe twice per point

// Probing speeds (mm/min)
#define Z_PROBE_FEEDRATE_FAST (10*60)        // 10mm/s first approach
#define Z_PROBE_FEEDRATE_SLOW (5*60)         // 5mm/s final approach
#define XY_PROBE_FEEDRATE (133*60)           // Travel speed between points

// Clearance settings
#define Z_CLEARANCE_DEPLOY_PROBE 10          // Height before deploy
#define Z_CLEARANCE_BETWEEN_PROBES 5         // Height between points
#define Z_CLEARANCE_MULTI_PROBE 5            // Height between same-point probes

// Enable M48 repeatability test
#define Z_MIN_PROBE_REPEATABILITY_TEST

// Bed leveling type
#define AUTO_BED_LEVELING_BILINEAR           // Simpler, works well
#define RESTORE_LEVELING_AFTER_G28           // CRITICAL: keeps mesh after homing
#define ENABLE_LEVELING_FADE_HEIGHT
#define G26_MESH_VALIDATION

// Grid configuration (5x5 is optimal balance)
#define GRID_MAX_POINTS_X 5
#define GRID_MAX_POINTS_Y GRID_MAX_POINTS_X

// EEPROM for saving settings
#define EEPROM_SETTINGS
#define EEPROM_AUTO_INIT
```

### Advanced settings in Configuration_adv.h

```cpp
// BLTouch/CR Touch optimizations
#define BLTOUCH_DELAY 300                    // Reduced from 500
#define BLTOUCH_HS_MODE true                 // High-speed mode

// Fade height configuration
#define DEFAULT_LEVELING_FADE_HEIGHT 10.0    // Fade compensation over 10mm

// Probe offset wizard (highly recommended)
#define PROBE_OFFSET_WIZARD
#define PROBE_OFFSET_WIZARD_START_Z -4.0

// Baby stepping for live adjustment
#define BABYSTEPPING
#define BABYSTEP_MULTIPLICATOR_Z 1
#define BABYSTEP_ZPROBE_OFFSET               // Baby steps modify Z-offset

// Settling time after moves
#define DELAY_BEFORE_PROBING 200             // 200ms for vibration settling
```

The **RESTORE_LEVELING_AFTER_G28** setting is particularly critical—without it, G28 disables your mesh compensation, causing the exact inconsistency you're experiencing.

## Phase 2: Silicon spacer installation and zeroing

Silicon spacers provide more stability than springs because they maintain consistent compression without losing tension over time. Your planned zeroing approach is correct with one modification.

### Installation procedure

Replace your existing springs with silicon spacers: use three **18mm** spacers for standard corners and one **16mm** spacer at the cable strain relief bracket corner (typically rear-left on Ender 3 Pro) where the extra bracket creates additional height.

**Zeroing method:**

1. Remove the magnetic build plate
2. Loosen all four knobs completely (counter-clockwise until very loose)
3. Hand-tighten each knob until you feel the silicone just begin to compress—roughly **1-2mm of compression** from relaxed state
4. All knobs should have identical resistance; don't overtighten
5. The target is approximately **50% compression**—solid but not rock-hard

The "tighten until just getting resistance" approach works, but you want slight compression beyond first contact. If knobs are too tight, your Z-offset becomes excessively negative (beyond -3.5mm), and if too loose, the bed wobbles during printing.

### Why mechanical tramming still matters

Even with CR Touch, manual tramming is essential. ABL compensation works optimally within **±0.2mm** of level (half your 0.4mm nozzle diameter). Beyond this range, compensation degrades first layer quality. Think of ABL as polish, not a fix.

**Mechanical tramming procedure:**

1. Heat bed to 60°C (thermal expansion affects measurements)
2. Home all axes: `G28`
3. Disable steppers: `M84`
4. Move nozzle manually to each corner
5. Use standard office paper (0.1mm thick) between nozzle and bed
6. Adjust each corner knob until paper slides with slight resistance
7. Repeat the full cycle 2-3 times—adjusting one corner affects others
8. Target: consistent drag at all four corners and center

## Phase 3: Verify probe accuracy with M48

Before trusting your probe for mesh creation, verify its repeatability. The M48 test probes the same point multiple times and reports statistical accuracy.

**Run the test:**
```gcode
G28                      ; Home all axes
M140 S60                 ; Heat bed to printing temp
M190 S60                 ; Wait for bed
M48 P10 V4               ; 10 probes, verbose output
```

### Interpreting results

| Standard Deviation | Assessment | Action |
|-------------------|------------|--------|
| ≤0.005mm | Excellent | Probe working optimally |
| ≤0.01mm | Good | Acceptable for reliable printing |
| 0.01-0.02mm | Marginal | Check mount rigidity |
| >0.02mm | Poor | Troubleshooting required |

**If results are poor:**
- Check probe mount for any wobble—even 0.5mm of play degrades accuracy significantly
- Verify all screws are tight on the mount bracket
- Clean the probe pin and probing area
- Check for loose Z-axis components or gantry sag
- Run test at different bed positions to rule out localized issues

The CR Touch pin tip should be **2-3mm below the nozzle** when retracted. Too high or too low affects trigger consistency.

## Phase 4: Z-offset calibration

Z-offset is the distance between where the probe triggers and where the nozzle should actually be for proper first layer squish. This is the most common source of "too close/too far" problems.

### Calibration procedure

**Preparation:**
1. Heat bed to 60°C
2. Heat nozzle to 150°C (prevents ooze but accounts for thermal expansion)
3. Have standard office paper ready

**Paper method:**
```gcode
G28                      ; Home all axes
G1 Z0 F300               ; Move to Z0 (nozzle won't touch bed yet)
```

Using the LCD menu (Control → Motion → Probe Z Offset) or baby stepping:
1. Decrease Z-offset in 0.1mm increments until nozzle approaches bed
2. Switch to 0.01mm increments for fine adjustment
3. Slide paper between nozzle and bed
4. **Target feel:** Paper slides with light resistance—you feel a gentle grab but can still move the paper without tearing

**Save the offset:**
```gcode
M851 Z-2.50              ; Replace with YOUR measured value
M500                     ; Save to EEPROM
M503                     ; Verify saved settings
```

### Typical values and troubleshooting

CR Touch on Ender 3 Pro typically requires Z-offset between **-2.0 and -3.0mm**, with -2.4 to -2.6mm being most common. If your offset exceeds -3.5mm, your spacers may be overtightened or your mount is positioned unusually high.

**Understanding offset direction:**
- More negative = nozzle closer to bed
- Less negative = nozzle farther from bed
- `M851 Z-2.50` → `M851 Z-2.70` moves nozzle **0.2mm closer**
- `M851 Z-2.50` → `M851 Z-2.30` moves nozzle **0.2mm farther**

## Phase 5: Create and validate mesh

With probe verified and Z-offset calibrated, create your compensation mesh.

### Mesh creation

```gcode
G28                      ; Home all axes
M140 S60                 ; Heat bed (probe at printing temperature)
M190 S60                 ; Wait for bed temp
M104 S150                ; Warm nozzle to prevent ooze
G29                      ; Probe the bed (creates 5x5 mesh)
M500                     ; Save mesh to EEPROM
```

### Validate mesh quality

```gcode
G29 T                    ; Print mesh to terminal
```

The output shows Z-deviation at each point in millimeters. Positive values indicate high spots; negative values indicate low spots.

**Acceptable deviation ranges:**

| Max Deviation | Assessment |
|--------------|------------|
| <0.3mm | Excellent—well-trammed bed |
| 0.3-0.5mm | Good—compensation handles this |
| 0.5-1.0mm | Marginal—consider re-tramming |
| >1.0mm | Re-tram mechanically before relying on mesh |

If corners show large deviations, adjust those spacer knobs based on mesh data: tighten knobs at high corners (positive values), loosen at low corners (negative values), then re-probe.

## Phase 6: First layer calibration prints

Test your calibration with a dedicated first layer pattern before printing real parts.

### Recommended test print

Print a single-layer **60x60mm square** at 0.2mm layer height. The Teaching Tech calibration generator at teachingtechyt.github.io/calibration.html#firstlayer creates customized test G-code including squares at each corner and center.

### Visual diagnosis guide

**Perfect first layer indicators:**
- Lines slightly wider than 0.4mm nozzle (approximately 0.45-0.5mm)
- Flat, pancake-shaped cross-section when viewed from the side
- Adjacent lines touch or slightly overlap without gaps
- Smooth surface when running finger across
- Good adhesion but removable after cooling

**Too close (Z-offset too negative):**
- Lines appear thin, transparent, or rough
- Ridges between passes from excess squished material
- Scratchy texture you can feel
- Nozzle scraping sounds
- Extruder clicking from back pressure
- Very difficult to remove print

**Too far (Z-offset not negative enough):**
- Visible gaps between lines
- Round cross-section instead of flat squish
- Lines barely touching bed surface
- Poor adhesion—print peels easily
- Warping and corner lifting

### Live adjustment with baby stepping

During the first layer of any print, access Tune → Babystep Z on your LCD:
- Turn encoder counter-clockwise to lower nozzle (closer)
- Turn encoder clockwise to raise nozzle (farther)

Increments of 0.01-0.02mm are typical. Once perfect, with `BABYSTEP_ZPROBE_OFFSET` enabled, your baby step adjustments automatically update the Z-offset. After the print, run `M500` to save permanently.

## Phase 7: Optimized start G-code

This start sequence ensures consistent first layers every print:

```gcode
; Ender 3 Pro + CR Touch Start G-code
G90                                          ; Absolute positioning
M82                                          ; Extruder absolute mode

; Heat bed first (probe at temperature)
M140 S{material_bed_temperature_layer_0}     ; Start bed heating
M190 S{material_bed_temperature_layer_0}     ; Wait for bed temp

; Warm nozzle (prevents ooze during probing)
M104 S150                                    ; Preheat to 150°C

; Home and probe
G28                                          ; Home all axes
G29                                          ; Probe bed mesh (or use M420 S1 for saved mesh)

; Move to prime position
G1 X0.1 Y20 Z5 F3000

; Now heat nozzle fully
M109 S{material_print_temperature_layer_0}   ; Wait for nozzle temp

; Prime line
G1 Z0.28 F240
G92 E0
G1 Y200 E15 F1500.0                          ; First prime line
G1 X0.4 F5000
G1 Y20 E30 F1200.0                           ; Second prime line
G92 E0
G1 Z2.0 F3000                                ; Raise nozzle

M117 Printing...
```

### When to use G29 vs M420 S1

| Scenario | Command | Reason |
|----------|---------|--------|
| Every print (recommended) | G29 | Maximum accuracy, accounts for any bed shifts |
| Quick consecutive prints | M420 S1 | Loads saved mesh, faster startup |
| After moving printer | G29 | Bed position may have changed |
| Different bed surface | G29 | New mesh required |

**Critical:** If using `M420 S1` instead of `G29`, you must have previously run `G29` followed by `M500` to have a saved mesh.

## First layer speed and temperature considerations

Slow first layers adhere better. These settings in your slicer work well with the calibration above:

| Setting | Recommended Value |
|---------|------------------|
| First layer speed | 20-30 mm/s |
| First layer height | 0.2mm (can use up to 0.28mm) |
| First layer line width | 100-120% of nozzle width |
| First layer flow | 100% (increase to 105% if gaps persist) |
| First layer fan | 0% (no cooling) |
| Bed temperature (PLA) | 60°C |
| Nozzle temperature (PLA) | 200-215°C (5-10°C higher than other layers) |

If first layers look wrong despite correct Z-offset, verify these slicer settings—excessive speed or cold temperatures create symptoms identical to incorrect Z-offset.

## Troubleshooting common issues

### Z-offset drift causes and solutions

| Cause | Symptom | Solution |
|-------|---------|----------|
| Springs losing tension | Gradual Z-offset change over weeks | Silicon spacers solve this |
| Nozzle changes | Z-offset wrong after swap | Recalibrate offset after any nozzle work |
| Loose probe mount | Inconsistent first layer | Tighten all mount screws |
| EEPROM not saving | Settings reset after power cycle | Verify `M500` saves, check EEPROM health with `M501` |
| G28 disabling mesh | First layer varies between prints | Enable `RESTORE_LEVELING_AFTER_G28` or add `M420 S1` after G28 |

### Inconsistent first layers despite leveling

If first layers vary across the bed despite calibration:

1. Run `G29 T` and check mesh deviation—values over 0.5mm suggest mechanical issues
2. Test probe repeatability with `M48 P10 V4` at different bed locations
3. Check X-gantry level (measure distance from gantry to frame at both ends)
4. Verify bed surface is clean (oils cause localized adhesion issues)
5. For glass beds, ensure 10+ minutes heat soak for thermal stability

### Thermal expansion considerations

Temperature affects all measurements:
- Always probe with bed at printing temperature
- Heat nozzle to 150-180°C during calibration (full temp causes ooze)
- Glass beds need 10-15 minutes to stabilize shape after reaching temperature
- First print after cold start may need slight baby step adjustment

## Pre-print checklist and maintenance schedule

### Before every print

- [ ] Nozzle clean (no filament blob)
- [ ] Bed surface clean (IPA wipe if fingerprints present)
- [ ] Correct filament loaded and dry
- [ ] Start G-code includes G29 or M420 S1 after G28

### Weekly/monthly maintenance

- [ ] Run `M48 P10 V4` to verify probe accuracy
- [ ] Check mesh with `G29 T`—re-tram if deviation exceeds 0.3mm
- [ ] Inspect probe mount tightness
- [ ] Verify silicon spacers have consistent compression
- [ ] Clean bed thoroughly with dish soap and water (for PEI surfaces)

### After moving printer or maintenance

1. Re-tram bed mechanically
2. Verify Z-offset with paper test
3. Create fresh mesh with G29
4. Save with M500

## Quick command reference

```
CALIBRATION:
M851 Z-2.5         Set Z-offset
M851               Show current Z-offset
M48 P10 V4         Probe repeatability test
G29                Create new mesh
G29 T              Display mesh values
M500               Save all settings to EEPROM
M501               Load settings from EEPROM
M503               Display all current settings

LIVE ADJUSTMENT:
M290 Z-0.05        Baby step closer (during print)
M290 Z0.05         Baby step farther (during print)

MESH CONTROL:
M420 S1            Enable saved mesh
M420 S0            Disable mesh compensation
M420 V             Display mesh (same as G29 T)

PROBE TESTING:
M401               Deploy probe
M402               Stow probe
M119               Show endstop/probe states
```

This protocol transforms the multi-variable bed leveling problem into a systematic process. With silicon spacers eliminating spring drift, proper firmware settings ensuring mesh persistence, and a verified Z-offset, your first layers will become consistently reliable. The key is treating this as a calibration chain where each phase builds on the previous—skip nothing, verify each step, and your CR Touch will deliver the precision it's capable of.