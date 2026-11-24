import os, re, uuid, math

PROJ_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "kicad"))
SYM_DIR = "/app/extensions/Library/Symbols/symbols"
FP_DIR = "/app/extensions/Library/Footprints/footprints"

def uid():
    return str(uuid.uuid4())

def extract_symbol(lib, name):
    txt = open(f"{SYM_DIR}/{lib}.kicad_sym", "r", encoding="utf-8").read()
    target = f'\n\t(symbol "{name}"'
    idx = txt.find(target)
    if idx == -1:
        raise ValueError(f"Symbol {lib}:{name} not found")
    depth = 0
    i = idx + 2
    in_str = False
    esc = False
    while i < len(txt):
        ch = txt[i]
        if esc:
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == '"':
            in_str = not in_str
        elif not in_str:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    block = txt[idx+2:i+1]
                    block = block.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)
                    if lib == "Regulator_Linear" and name == "AMS1117-3.3":
                        block = block.replace('(extends "AP1117-15")', '(extends "Regulator_Linear:AP1117-15")')
                    return block
        i += 1
    raise ValueError(f"Unclosed symbol {lib}:{name}")

needed_syms = [
    ("Connector_Generic", "Conn_01x02"),
    ("Device", "D_Schottky"),
    ("Device", "D_Schottky_Dual_CommonCathode_AKA_Parallel"),
    ("Transistor_FET", "Q_PMOS_GDS"),
    ("Device", "R"),
    ("Device", "C"),
    ("Device", "C_Polarized"),
    ("Mechanical", "MountingHole"),
    ("power", "GND"),
    ("power", "PWR_FLAG"),
]

# Extract AP1117-15 and make it a fully self-contained AMS1117-3.3 with embedded pins
ap_sym = extract_symbol("Regulator_Linear", "AP1117-15")
ams_sym = ap_sym.replace('"Regulator_Linear:AP1117-15"', '"Regulator_Linear:AMS1117-3.3"')
ams_sym = ams_sym.replace('"AP1117-15_', '"AMS1117-3.3_')
ams_sym = ams_sym.replace('(property "Value" "AP1117-15"', '(property "Value" "AMS1117-3.3"')

lib_blocks = "\n".join("\t\t" + extract_symbol(l, n).replace("\n", "\n\t\t") for l, n in needed_syms)
lib_blocks += "\n\t\t" + ams_sym.replace("\n", "\n\t\t")

def make_sym(lib_id, ref, val, fp, x, y, angle=0, mirror=None, pins=("1", "2"), ref_pos=(0, -3.81), val_pos=(0, 3.81)):
    m_str = f"\n\t\t(mirror {mirror})" if mirror else ""
    pin_lines = "\n".join(f'\t\t(pin "{p}" (uuid "{uid()}"))' for p in pins)
    return f'''\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x:.2f} {y:.2f} {angle}){m_str}
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid "{uid()}")
\t\t(property "Reference" "{ref}"
\t\t\t(at {x + ref_pos[0]:.2f} {y + ref_pos[1]:.2f} 0)
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)
\t\t(property "Value" "{val}"
\t\t\t(at {x + val_pos[0]:.2f} {y + val_pos[1]:.2f} 0)
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)
\t\t(property "Footprint" "{fp}"
\t\t\t(at {x:.2f} {y:.2f} 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(property "Datasheet" "~"
\t\t\t(at {x:.2f} {y:.2f} 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
{pin_lines}
\t\t(instances
\t\t\t(project "DC_UPS_IoT"
\t\t\t\t(path "/{ROOT_UUID}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)'''

def make_pwr(lib_id, ref, val, x, y, angle=0):
    return f'''\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x:.2f} {y:.2f} {angle})
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid "{uid()}")
\t\t(property "Reference" "{ref}"
\t\t\t(at {x:.2f} {y+2.54:.2f} 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(property "Value" "{val}"
\t\t\t(at {x:.2f} {y+2.54:.2f} 0)
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)
\t\t(property "Footprint" "" (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "Datasheet" "" (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(pin "1" (uuid "{uid()}"))
\t\t(instances
\t\t\t(project "DC_UPS_IoT"
\t\t\t\t(path "/{ROOT_UUID}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)'''

def wire(x1, y1, x2, y2):
    if abs(x1 - x2) < 1e-4 and abs(y1 - y2) < 1e-4:
        return ""
    return f'\t(wire (pts (xy {x1:.2f} {y1:.2f}) (xy {x2:.2f} {y2:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))'

def junc(x, y):
    return f'\t(junction (at {x:.2f} {y:.2f}) (diameter 0) (color 0 0 0 0) (uuid "{uid()}"))'

def label(txt, x, y, angle=0):
    return f'\t(label "{txt}" (at {x:.2f} {y:.2f} {angle}) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "{uid()}"))'

def note(txt, x, y, size=1.5):
    return f'\t(text "{txt}" (exclude_from_sim no) (at {x:.2f} {y:.2f} 0) (effects (font (size {size} {size}) (bold yes)) (justify left)) (uuid "{uid()}"))'

ROOT_UUID = "9b21e801-334a-4b11-8891-000000000001"

# Footprints
FP_TB2 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal"
FP_HDR = "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
FP_TO220 = "Package_TO_SOT_THT:TO-220-3_Vertical"
FP_SOT223 = "Package_TO_SOT_SMD:SOT-223-3_TabPin2"
FP_DIODE = "Diode_THT:D_DO-201AD_P15.24mm_Horizontal"
FP_RES = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"
FP_C1000 = "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm"
FP_C220 = "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm"
FP_C100 = "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm"
FP_C10 = "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm"
FP_C104 = "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm"
FP_MH = "MountingHole:MountingHole_3.2mm_M3"

items = []
wires = []
juncs = []
labels = []
texts = []

# ==============================================================================
# SECTION 1: WIDE DC INPUT (6.5V - 24V) & BUCK CONVERTER INTERFACE
# ==============================================================================
texts.append(note("1. WIDE DC INPUT (6.5V - 24V) & BUCK CONVERTER (STEP-DOWN TO 5.0V)", 25, 25))

# J1: Screw Terminal 2-Pin (Input 6.5V - 24V)
items.append(make_sym("Connector_Generic:Conn_01x02", "J1", "DC_IN_6.5V-24V", FP_TB2, 35.56, 45.72, mirror="y", ref_pos=(-5, -3), val_pos=(-5, 5.5)))
# J1.1 = (40.64, 45.72) [+VIN_RAW], J1.2 = (40.64, 48.26) [GND]
wires.append(wire(40.64, 45.72, 45.72, 45.72))
items.append(make_pwr("power:PWR_FLAG", "#FLG01", "PWR_FLAG", 45.72, 40.64))
wires.append(wire(45.72, 40.64, 45.72, 45.72))
juncs.append(junc(45.72, 45.72))

# D_REV: Reverse Polarity Protection Diode at (54.61, 45.72), angle=180
# Pin 2 (A) = (54.61 - 3.81, 45.72) = (50.80, 45.72)
# Pin 1 (K) = (54.61 + 3.81, 45.72) = (58.42, 45.72)
items.append(make_sym("Device:D_Schottky", "D_REV", "1N5822", FP_DIODE, 54.61, 45.72, angle=180, ref_pos=(0, -3.5), val_pos=(0, 3.5)))
wires.append(wire(45.72, 45.72, 50.80, 45.72))
wires.append(wire(58.42, 45.72, 63.50, 45.72))
labels.append(label("+VIN_FILT", 63.50, 45.72))

# J1.2 GND
wires.append(wire(40.64, 48.26, 45.72, 48.26))
wires.append(wire(45.72, 48.26, 45.72, 53.34))
items.append(make_pwr("power:GND", "#PWR01", "GND", 45.72, 53.34))
items.append(make_pwr("power:PWR_FLAG", "#FLG02", "PWR_FLAG", 45.72, 50.80))
juncs.append(junc(45.72, 50.80))

# Input Filter Caps: C_IN1 (100uF 35V), C_IN2 (100nF 50V) on +VIN_FILT
for idx, (sym, ref, val, fp, cx) in enumerate([
    ("Device:C_Polarized", "C_IN1", "100uF 35V", FP_C100, 68.58),
    ("Device:C", "C_IN2", "100nF", FP_C104, 78.74),
]):
    items.append(make_sym(sym, ref, val, fp, cx, 55.88, ref_pos=(2.5, -1.5), val_pos=(2.5, 1.5)))
    wires.append(wire(63.50, 45.72, cx, 45.72))
    wires.append(wire(cx, 45.72, cx, 52.07))
    juncs.append(junc(cx, 45.72))
    wires.append(wire(cx, 59.69, cx, 66.04))
    items.append(make_pwr("power:GND", f"#PWR_IN_{idx}", "GND", cx, 66.04))

# J_B_IN: Connects to Buck Converter Module Input (VIN+, GND)
items.append(make_sym("Connector_Generic:Conn_01x02", "J_B_IN", "TO_BUCK_IN", FP_HDR, 91.44, 45.72, ref_pos=(-2, -3.5), val_pos=(-2, 5.5)))
wires.append(wire(78.74, 45.72, 86.36, 45.72))
wires.append(wire(86.36, 48.26, 81.28, 48.26))
wires.append(wire(81.28, 48.26, 81.28, 53.34))
items.append(make_pwr("power:GND", "#PWR_BIN", "GND", 81.28, 53.34))

# J_B_OUT: Receives 5.0V from Buck Converter Module (OUT+, GND)
items.append(make_sym("Connector_Generic:Conn_01x02", "J_B_OUT", "FROM_BUCK_OUT", FP_HDR, 106.68, 45.72, mirror="y", ref_pos=(-4, -3.5), val_pos=(-4, 5.5)))
wires.append(wire(111.76, 45.72, 124.46, 45.72))
labels.append(label("+5V_IN", 114.30, 45.72))
items.append(make_pwr("power:PWR_FLAG", "#FLG03", "PWR_FLAG", 119.38, 40.64))
wires.append(wire(119.38, 40.64, 119.38, 45.72))
juncs.append(junc(119.38, 45.72))

wires.append(wire(111.76, 48.26, 114.30, 48.26))
wires.append(wire(114.30, 48.26, 114.30, 53.34))
items.append(make_pwr("power:GND", "#PWR_BOUT", "GND", 114.30, 53.34))

# Buck Output Smoothing Cap: C_B1 (220uF 16V), C_B2 (100nF)
for idx, (sym, ref, val, fp, cx) in enumerate([
    ("Device:C_Polarized", "C_B1", "220uF 16V", FP_C220, 127.00),
    ("Device:C", "C_B2", "100nF", FP_C104, 137.16),
]):
    items.append(make_sym(sym, ref, val, fp, cx, 55.88, ref_pos=(2.5, -1.5), val_pos=(2.5, 1.5)))
    wires.append(wire(124.46, 45.72, cx, 45.72))
    wires.append(wire(cx, 45.72, cx, 52.07))
    juncs.append(junc(cx, 45.72))
    wires.append(wire(cx, 59.69, cx, 66.04))
    items.append(make_pwr("power:GND", f"#PWR_BO_{idx}", "GND", cx, 66.04))

# ==============================================================================
# SECTION 2: TP4056 CHARGER INTERFACE
# ==============================================================================
texts.append(note("2. TP4056 CHARGER & PROTECTED BATTERY INTERFACE", 25, 80))

# J2: To TP4056 IN+ / IN-
items.append(make_sym("Connector_Generic:Conn_01x02", "J2", "TO_TP4056_IN", FP_HDR, 35.56, 96.52, mirror="y", ref_pos=(-5, -3), val_pos=(-5, 5.5)))
wires.append(wire(40.64, 96.52, 50.80, 96.52))
labels.append(label("+5V_IN", 50.80, 96.52))
wires.append(wire(40.64, 99.06, 45.72, 99.06))
wires.append(wire(45.72, 99.06, 45.72, 104.14))
items.append(make_pwr("power:GND", "#PWR02", "GND", 45.72, 104.14))

# J3: From TP4056 OUT+ / OUT- (Protected Battery)
items.append(make_sym("Connector_Generic:Conn_01x02", "J3", "FROM_TP4056_OUT", FP_HDR, 35.56, 116.84, mirror="y", ref_pos=(-5, -3), val_pos=(-5, 5.5)))
wires.append(wire(40.64, 116.84, 55.88, 116.84))
labels.append(label("V_BAT_PROT", 55.88, 116.84))
items.append(make_pwr("power:PWR_FLAG", "#FLG04", "PWR_FLAG", 48.26, 111.76))
wires.append(wire(48.26, 111.76, 48.26, 116.84))
juncs.append(junc(48.26, 116.84))
wires.append(wire(40.64, 119.38, 45.72, 119.38))
wires.append(wire(45.72, 119.38, 45.72, 124.46))
items.append(make_pwr("power:GND", "#PWR03", "GND", 45.72, 124.46))

# ==============================================================================
# SECTION 3: AUTOMATIC POWER-PATH SWITCH (MBR460CT + NDP6020P + 10k)
# ==============================================================================
texts.append(note("3. AUTOMATIC ZERO-DELAY POWER-PATH SWITCH (AN1149)", 85, 80))

# D1: MBR460CT
items.append(make_sym("Device:D_Schottky_Dual_CommonCathode_AKA_Parallel", "D1", "MBR460CT", FP_TO220, 93.98, 96.52, pins=("1","2","3"), ref_pos=(0, -6), val_pos=(0, 6)))
wires.append(wire(88.90, 93.98, 88.90, 99.06))
wires.append(wire(83.82, 96.52, 88.90, 96.52))
juncs.append(junc(88.90, 96.52))
labels.append(label("+5V_IN", 83.82, 96.52))
wires.append(wire(99.06, 96.52, 119.38, 96.52))
labels.append(label("V_SW", 104.14, 96.52))

# Q1: NDP6020P P-MOSFET
items.append(make_sym("Transistor_FET:Q_PMOS_GDS", "Q1", "NDP6020P", FP_TO220, 99.06, 129.54, mirror="x", pins=("1","2","3"), ref_pos=(5, -2), val_pos=(5, 2)))
wires.append(wire(81.28, 129.54, 93.98, 129.54))
labels.append(label("+5V_IN", 81.28, 129.54))

# R1 Gate Pull-Down (10k)
items.append(make_sym("Device:R", "R1", "10k", FP_RES, 86.36, 139.70, ref_pos=(3, -1), val_pos=(3, 1.5)))
wires.append(wire(86.36, 129.54, 86.36, 135.89))
juncs.append(junc(86.36, 129.54))
wires.append(wire(86.36, 143.51, 86.36, 147.32))
items.append(make_pwr("power:GND", "#PWR04", "GND", 86.36, 147.32))

# Pin 2 (D) = (101.60, 134.62) -> V_BAT_PROT
wires.append(wire(101.60, 134.62, 101.60, 142.24))
wires.append(wire(101.60, 142.24, 111.76, 142.24))
labels.append(label("V_BAT_PROT", 111.76, 142.24))

# Pin 3 (S) = (101.60, 124.46) -> V_SW
wires.append(wire(101.60, 124.46, 101.60, 111.76))
wires.append(wire(101.60, 111.76, 119.38, 111.76))
wires.append(wire(119.38, 96.52, 119.38, 111.76))
juncs.append(junc(119.38, 96.52))

# ==============================================================================
# SECTION 4: SWITCHED RAIL BUFFER & MT3608 BOOST INTERFACE
# ==============================================================================
texts.append(note("4. SWITCHED RAIL BUFFER & MT3608 BOOST TO 5.1V", 130, 80))

for idx, (sym, ref, val, fp, cx) in enumerate([
    ("Device:C_Polarized", "C1", "220uF 16V", FP_C220, 127.00),
    ("Device:C_Polarized", "C2", "10uF 16V", FP_C10, 137.16),
    ("Device:C", "C3", "100nF", FP_C104, 147.32),
]):
    items.append(make_sym(sym, ref, val, fp, cx, 106.68, ref_pos=(2.5, -1.5), val_pos=(2.5, 1.5)))
    wires.append(wire(119.38, 96.52, cx, 96.52))
    wires.append(wire(cx, 96.52, cx, 102.87))
    juncs.append(junc(cx, 96.52))
    wires.append(wire(cx, 110.49, cx, 116.84))
    items.append(make_pwr("power:GND", f"#PWR0{5+idx}", "GND", cx, 116.84))

# J4: To MT3608 VIN+ / VIN-
items.append(make_sym("Connector_Generic:Conn_01x02", "J4", "TO_MT3608_IN", FP_HDR, 162.56, 96.52, ref_pos=(-2, -3.5), val_pos=(-2, 5.5)))
wires.append(wire(147.32, 96.52, 157.48, 96.52))
wires.append(wire(157.48, 99.06, 152.40, 99.06))
wires.append(wire(152.40, 99.06, 152.40, 104.14))
items.append(make_pwr("power:GND", "#PWR08", "GND", 152.40, 104.14))

# J5: From MT3608 VOUT+ / VOUT-
items.append(make_sym("Connector_Generic:Conn_01x02", "J5", "FROM_MT3608_OUT", FP_HDR, 177.80, 96.52, mirror="y", ref_pos=(-4, -3.5), val_pos=(-4, 5.5)))
wires.append(wire(182.88, 96.52, 195.58, 96.52))
labels.append(label("+5V_OUT", 185.42, 96.52))
items.append(make_pwr("power:PWR_FLAG", "#FLG05", "PWR_FLAG", 190.50, 91.44))
wires.append(wire(190.50, 91.44, 190.50, 96.52))
juncs.append(junc(190.50, 96.52))
wires.append(wire(182.88, 99.06, 185.42, 99.06))
wires.append(wire(185.42, 99.06, 185.42, 104.14))
items.append(make_pwr("power:GND", "#PWR09", "GND", 185.42, 104.14))

# Output Filter Caps: C4 (1000uF 25V), C5 (10uF 16V), C6 (100nF)
for idx, (sym, ref, val, fp, cx) in enumerate([
    ("Device:C_Polarized", "C4", "1000uF 25V", FP_C1000, 198.12),
    ("Device:C_Polarized", "C5", "10uF 16V", FP_C10, 208.28),
    ("Device:C", "C6", "100nF", FP_C104, 218.44),
]):
    items.append(make_sym(sym, ref, val, fp, cx, 106.68, ref_pos=(2.5, -1.5), val_pos=(2.5, 1.5)))
    wires.append(wire(195.58, 96.52, cx, 96.52))
    wires.append(wire(cx, 96.52, cx, 102.87))
    juncs.append(junc(cx, 96.52))
    wires.append(wire(cx, 110.49, cx, 116.84))
    items.append(make_pwr("power:GND", f"#PWR{10+idx}", "GND", cx, 116.84))

# ==============================================================================
# SECTION 5: 3.3V LDO REGULATOR (AMS1117-3.3)
# ==============================================================================
texts.append(note("5. 3.3V LDO REGULATOR (AMS1117-3.3)", 130, 135))

# U1: AMS1117-3.3 at (165.10, 152.40)
# Pin 3 (VI) at (165.10 - 7.62, 152.40) = (157.48, 152.40)
# Pin 1 (GND) at (165.10, 152.40 + 7.62) = (165.10, 160.02)
# Pin 2 (VO) at (165.10 + 7.62, 152.40) = (172.72, 152.40)
items.append(make_sym("Regulator_Linear:AMS1117-3.3", "U1", "AMS1117-3.3", FP_SOT223, 165.10, 152.40, pins=("1","2","3"), ref_pos=(0, -5), val_pos=(0, 5)))

# Feed +5V_OUT into U1 Pin 3
wires.append(wire(147.32, 152.40, 157.48, 152.40))
labels.append(label("+5V_OUT", 147.32, 152.40))

# U1 Pin 1 GND
wires.append(wire(165.10, 160.02, 165.10, 165.10))
items.append(make_pwr("power:GND", "#PWR_LDO1", "GND", 165.10, 165.10))

# Decoupling Caps for LDO: C7 (10uF In), C8 (22uF Out), C9 (100nF Out)
items.append(make_sym("Device:C_Polarized", "C7", "10uF 16V", FP_C10, 152.40, 162.56, ref_pos=(2.5, -1.5), val_pos=(2.5, 1.5)))
wires.append(wire(152.40, 152.40, 152.40, 158.75))
juncs.append(junc(152.40, 152.40))
wires.append(wire(152.40, 166.37, 152.40, 172.72))
items.append(make_pwr("power:GND", "#PWR_LDO2", "GND", 152.40, 172.72))

wires.append(wire(172.72, 152.40, 195.58, 152.40))
labels.append(label("+3V3_OUT", 175.26, 152.40))

for idx, (sym, ref, val, fp, cx) in enumerate([
    ("Device:C_Polarized", "C8", "22uF 10V", FP_C10, 185.42),
    ("Device:C", "C9", "100nF", FP_C104, 195.58),
]):
    items.append(make_sym(sym, ref, val, fp, cx, 162.56, ref_pos=(2.5, -1.5), val_pos=(2.5, 1.5)))
    wires.append(wire(cx, 152.40, cx, 158.75))
    juncs.append(junc(cx, 152.40))
    wires.append(wire(cx, 166.37, cx, 172.72))
    items.append(make_pwr("power:GND", f"#PWR_LDO_{idx+3}", "GND", cx, 172.72))

# ==============================================================================
# SECTION 6: DUAL OUTPUT SCREW TERMINALS (5V & 3.3V)
# ==============================================================================
texts.append(note("6. DUAL POWER OUTPUT SCREW TERMINALS (5V & 3.3V)", 210, 80))

# J6: Screw Terminal 2-Pin (5V Output & GND)
items.append(make_sym("Connector_Generic:Conn_01x02", "J6", "5V_OUT", FP_TB2, 238.76, 96.52, ref_pos=(-2, -3.5), val_pos=(-2, 5.5)))
wires.append(wire(218.44, 96.52, 233.68, 96.52))
wires.append(wire(233.68, 99.06, 228.60, 99.06))
wires.append(wire(228.60, 99.06, 228.60, 104.14))
items.append(make_pwr("power:GND", "#PWR13", "GND", 228.60, 104.14))

# J7: Screw Terminal 2-Pin (3.3V Output & GND)
items.append(make_sym("Connector_Generic:Conn_01x02", "J7", "3V3_OUT", FP_TB2, 238.76, 152.40, ref_pos=(-2, -3.5), val_pos=(-2, 5.5)))
wires.append(wire(195.58, 152.40, 233.68, 152.40))
wires.append(wire(233.68, 154.94, 228.60, 154.94))
wires.append(wire(228.60, 154.94, 228.60, 160.02))
items.append(make_pwr("power:GND", "#PWR14", "GND", 228.60, 160.02))

# Mounting Holes (H1..H4)
for idx, mx in enumerate([45.72, 55.88, 66.04, 76.20], start=1):
    items.append(make_sym("Mechanical:MountingHole", f"H{idx}", "M3", FP_MH, mx, 185.42, pins=(), ref_pos=(0, -3), val_pos=(0, 3)))

texts.append(note("NOTE: Wide Input 6.5V - 24V DC. Reverse Polarity Protected by D_REV.", 25, 195, size=1.3))
texts.append(note("NOTE: Set MT3608 Boost Trimpot to 5.10V before powering loads.", 25, 200, size=1.3))
texts.append(note("NOTE: Dual Regulated Outputs: 5.0V on J6, 3.3V on J7.", 25, 205, size=1.3))

sch_content = f'''(kicad_sch
\t(version 20250114)
\t(generator "eeschema")
\t(generator_version "10.0")
\t(uuid "{ROOT_UUID}")
\t(paper "A3")
\t(title_block
\t\t(title "Universal IoT DC UPS (Wide 6.5V-24V In, 5V & 3.3V Dual Out)")
\t\t(date "2026-11-25")
\t\t(rev "2.0")
\t\t(comment 1 "Buck Converter Step-Down + AN1149 Zero-Delay Power-Path + MT3608 Boost + AMS1117-3.3")
\t\t(comment 2 "Screw Terminals for Input & Dual Outputs - Zero Brownout ESP32 Backup")
\t)
\t(lib_symbols
{lib_blocks}
\t)
{chr(10).join(texts)}
{chr(10).join(items)}
{chr(10).join(wires)}
{chr(10).join(juncs)}
{chr(10).join(labels)}
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
)
'''

sch_path = os.path.join(PROJ_DIR, "DC_UPS_IoT.kicad_sch")
with open(sch_path, "w", encoding="utf-8") as f:
    f.write(sch_content)
print("Schematic written to:", sch_path)
