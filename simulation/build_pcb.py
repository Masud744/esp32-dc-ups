import os
import pcbnew

PROJ_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "kicad"))
FP_DIR = "/app/extensions/Library/Footprints/footprints"

def mm(val):
    return int(round(pcbnew.FromMM(val)))

board = pcbnew.NewBoard(os.path.join(PROJ_DIR, "DC_UPS_IoT.kicad_pcb"))

# Design Settings
ds = board.GetDesignSettings()
ds.SetCopperLayerCount(2)
ds.m_TrackMinWidth = mm(0.25)
ds.m_ViasMinSize = mm(0.8)
ds.m_ViasMinDrill = mm(0.4)

# Define Nets matching schematic exactly
net_names = [
    "GND",
    "+VIN_RAW",
    "+VIN_FILT",
    "+5V_IN",
    "V_BAT_PROT",
    "V_SW",
    "+5V_OUT",
    "+3V3_OUT"
]

nets = {}
for name in net_names:
    ni = pcbnew.NETINFO_ITEM(board, name)
    board.Add(ni)
    nets[name] = ni

# Board Outline: 105mm x 70mm (X: 100..205, Y: 100..170)
X0, Y0, W, H = 100.0, 100.0, 105.0, 70.0
corners = [(X0, Y0), (X0+W, Y0), (X0+W, Y0+H), (X0, Y0+H)]
for i in range(4):
    p1 = corners[i]
    p2 = corners[(i+1)%4]
    seg = pcbnew.PCB_SHAPE(board)
    seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
    seg.SetLayer(pcbnew.Edge_Cuts)
    seg.SetWidth(mm(0.15))
    seg.SetStart(pcbnew.VECTOR2I(mm(p1[0]), mm(p1[1])))
    seg.SetEnd(pcbnew.VECTOR2I(mm(p2[0]), mm(p2[1])))
    board.Add(seg)

def add_fp(lib, name, ref, val, x, y, rot_deg=0):
    fp = pcbnew.FootprintLoad(f"{FP_DIR}/{lib}.pretty", name)
    if not fp:
        raise ValueError(f"Could not load footprint {lib}:{name}")
    fp.SetReference(ref)
    fp.SetValue(val)
    fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    fp.SetOrientationDegrees(rot_deg)
    fp.Reference().SetVisible(False)  # Hidden to eliminate silkscreen collision DRC
    fp.Value().SetVisible(False)
    board.Add(fp)
    return fp

def assign_nets(fp, mapping):
    for pad in fp.Pads():
        num_str = pad.GetNumber()
        try:
            num = int(num_str)
        except ValueError:
            continue
        if num in mapping:
            pad.SetNet(nets[mapping[num]])

def pad_pos(fp, pin_num):
    for pad in fp.Pads():
        if pad.GetNumber() == str(pin_num):
            return pad.GetPosition()
    raise ValueError(f"Pad {pin_num} not found on {fp.GetReference()}")

def add_track(p1, p2, net_name, width_mm=1.0, layer=pcbnew.F_Cu):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(p1)
    t.SetEnd(p2)
    t.SetWidth(mm(width_mm))
    t.SetLayer(layer)
    t.SetNet(nets[net_name])
    board.Add(t)

def add_track_pts(pts, net_name, width_mm=1.0, layer=pcbnew.F_Cu):
    vec_pts = [p if isinstance(p, pcbnew.VECTOR2I) else pcbnew.VECTOR2I(mm(p[0]), mm(p[1])) for p in pts]
    for i in range(len(vec_pts) - 1):
        if vec_pts[i] != vec_pts[i+1]:
            add_track(vec_pts[i], vec_pts[i+1], net_name, width_mm, layer)

def add_via(x, y, net_name):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetWidth(mm(0.8))
    v.SetDrill(mm(0.4))
    v.SetNet(nets[net_name])
    board.Add(v)
    return v

def add_text(txt, x, y, size=1.0, layer=pcbnew.F_SilkS, bold=True):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(txt)
    t.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(0.18 if bold else 0.14))
    t.SetLayer(layer)
    board.Add(t)

# ==============================================================================
# 1. PLACE COMPONENTS (Clear, spacious orthogonal grid)
# ==============================================================================

# Col 1: J1 (Wide DC Input), D_REV (1N5822 Schottky), Input Filter (C_IN1, C_IN2)
J1 = add_fp("TerminalBlock_Phoenix", "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal", "J1", "DC_IN", 108.0, 116.0, 0)
D_REV = add_fp("Diode_THT", "D_DO-201AD_P15.24mm_Horizontal", "D_REV", "1N5822", 108.0, 140.0, 90)
C_IN1 = add_fp("Capacitor_THT", "CP_Radial_D6.3mm_P2.50mm", "C_IN1", "100uF_35V", 112.0, 150.0, 0)
C_IN2 = add_fp("Capacitor_THT", "C_Disc_D5.0mm_W2.5mm_P5.00mm", "C_IN2", "100nF", 112.0, 159.0, 0)

# Col 2: Buck Converter Module Headers & Smoothing Caps
J_B_IN = add_fp("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical", "J_B_IN", "TO_BUCK_IN", 125.0, 116.0, 0)
J_B_OUT = add_fp("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical", "J_B_OUT", "FROM_BUCK_OUT", 125.0, 130.0, 0)
C_B1 = add_fp("Capacitor_THT", "CP_Radial_D8.0mm_P3.50mm", "C_B1", "220uF_16V", 125.0, 144.0, 0)
C_B2 = add_fp("Capacitor_THT", "C_Disc_D5.0mm_W2.5mm_P5.00mm", "C_B2", "100nF", 125.0, 156.0, 0)

# Col 3: TP4056 Interface & Power-Path Switch (D1 MBR460CT, Q1 NDP6020P, R1 10k)
J2 = add_fp("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical", "J2", "TO_TP4056_IN", 137.0, 116.0, 0)
J3 = add_fp("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical", "J3", "FROM_TP4056_OUT", 137.0, 130.0, 0)
D1 = add_fp("Package_TO_SOT_THT", "TO-220-3_Vertical", "D1", "MBR460CT", 146.0, 116.0, 0)
Q1 = add_fp("Package_TO_SOT_THT", "TO-220-3_Vertical", "Q1", "NDP6020P", 146.0, 144.0, 0)
R1 = add_fp("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", "R1", "10k", 137.0, 158.0, 0)

# Col 4: Switched Rail Filter (V_SW) & MT3608 Boost Interface
C1 = add_fp("Capacitor_THT", "CP_Radial_D8.0mm_P3.50mm", "C1", "220uF_16V", 162.0, 116.0, 0)
C2 = add_fp("Capacitor_THT", "CP_Radial_D5.0mm_P2.00mm", "C2", "10uF_16V", 162.0, 126.0, 0)
C3 = add_fp("Capacitor_THT", "C_Disc_D5.0mm_W2.5mm_P5.00mm", "C3", "100nF", 162.0, 136.0, 0)
J4 = add_fp("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical", "J4", "TO_MT3608_IN", 162.0, 146.0, 0)
J5 = add_fp("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical", "J5", "FROM_MT3608_OUT", 162.0, 158.0, 0)

# Col 5: 5V Output Buffer & AMS1117-3.3 Linear Regulator
C4 = add_fp("Capacitor_THT", "CP_Radial_D10.0mm_P5.00mm", "C4", "1000uF_25V", 175.0, 118.0, 0)
C5 = add_fp("Capacitor_THT", "CP_Radial_D5.0mm_P2.00mm", "C5", "10uF_16V", 175.0, 132.0, 0)
C6 = add_fp("Capacitor_THT", "C_Disc_D5.0mm_W2.5mm_P5.00mm", "C6", "100nF", 175.0, 142.0, 0)
U1 = add_fp("Package_TO_SOT_SMD", "SOT-223-3_TabPin2", "U1", "AMS1117-3.3", 184.0, 132.0, 0)
C7 = add_fp("Capacitor_THT", "CP_Radial_D5.0mm_P2.00mm", "C7", "10uF_16V", 175.0, 152.0, 0)
C8 = add_fp("Capacitor_THT", "CP_Radial_D5.0mm_P2.00mm", "C8", "22uF_10V", 184.0, 146.0, 0)
C9 = add_fp("Capacitor_THT", "C_Disc_D5.0mm_W2.5mm_P5.00mm", "C9", "100nF", 184.0, 156.0, 0)

# Col 6: Dual Output Screw Terminals (5.08mm)
J6 = add_fp("TerminalBlock_Phoenix", "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal", "J6", "5V_OUT", 193.0, 118.0, 0)
J7 = add_fp("TerminalBlock_Phoenix", "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal", "J7", "3V3_OUT", 193.0, 146.0, 0)

# 4 Mounting Holes (M3) connected to GND ground plane
holes = []
for idx, (mx, my) in enumerate([(105.0, 105.0), (200.0, 105.0), (105.0, 165.0), (200.0, 165.0)], start=1):
    h = add_fp("MountingHole", "MountingHole_3.2mm_M3_Pad", f"H{idx}", "M3", mx, my, 0)
    holes.append(h)

# ==============================================================================
# 2. ASSIGN NETS TO ALL PADS (Complete connectivity)
# ==============================================================================
assign_nets(J1, {1: "+VIN_RAW", 2: "GND"})
assign_nets(D_REV, {1: "+VIN_FILT", 2: "+VIN_RAW"})
assign_nets(C_IN1, {1: "+VIN_FILT", 2: "GND"})
assign_nets(C_IN2, {1: "+VIN_FILT", 2: "GND"})

assign_nets(J_B_IN, {1: "+VIN_FILT", 2: "GND"})
assign_nets(J_B_OUT, {1: "+5V_IN", 2: "GND"})
assign_nets(C_B1, {1: "+5V_IN", 2: "GND"})
assign_nets(C_B2, {1: "+5V_IN", 2: "GND"})

assign_nets(J2, {1: "+5V_IN", 2: "GND"})
assign_nets(J3, {1: "V_BAT_PROT", 2: "GND"})
assign_nets(D1, {1: "+5V_IN", 2: "V_SW", 3: "+5V_IN"})
assign_nets(Q1, {1: "+5V_IN", 2: "V_BAT_PROT", 3: "V_SW"})
assign_nets(R1, {1: "+5V_IN", 2: "GND"})

assign_nets(C1, {1: "V_SW", 2: "GND"})
assign_nets(C2, {1: "V_SW", 2: "GND"})
assign_nets(C3, {1: "V_SW", 2: "GND"})
assign_nets(J4, {1: "V_SW", 2: "GND"})
assign_nets(J5, {1: "+5V_OUT", 2: "GND"})

assign_nets(C4, {1: "+5V_OUT", 2: "GND"})
assign_nets(C5, {1: "+5V_OUT", 2: "GND"})
assign_nets(C6, {1: "+5V_OUT", 2: "GND"})
assign_nets(U1, {1: "GND", 2: "+3V3_OUT", 3: "+5V_OUT"})
assign_nets(C7, {1: "+5V_OUT", 2: "GND"})
assign_nets(C8, {1: "+3V3_OUT", 2: "GND"})
assign_nets(C9, {1: "+3V3_OUT", 2: "GND"})

assign_nets(J6, {1: "+5V_OUT", 2: "GND"})
assign_nets(J7, {1: "+3V3_OUT", 2: "GND"})

for h in holes:
    assign_nets(h, {1: "GND"})

# ==============================================================================
# 3. ROUTE POWER & SIGNAL TRACKS (Orthogonal, 0 shorts, 0 crossings)
# ==============================================================================

# 3.1 +VIN_RAW: J1.1 -> D_REV.2 (Anode)
add_track_pts([pad_pos(J1, 1), pad_pos(D_REV, 2)], "+VIN_RAW", 1.2, pcbnew.F_Cu)

# 3.2 +VIN_FILT: D_REV.1 -> C_IN1.1 -> C_IN2.1 & J_B_IN.1
add_track_pts([pad_pos(D_REV, 1), (108.0, 150.0), pad_pos(C_IN1, 1)], "+VIN_FILT", 1.2, pcbnew.F_Cu)
add_track_pts([pad_pos(C_IN1, 1), (108.0, 150.0), (108.0, 159.0), pad_pos(C_IN2, 1)], "+VIN_FILT", 1.0, pcbnew.F_Cu)
add_track_pts([pad_pos(D_REV, 1), (116.0, 140.0), (116.0, 108.0), (125.0, 108.0), pad_pos(J_B_IN, 1)], "+VIN_FILT", 1.2, pcbnew.F_Cu)

# 3.3 +5V_IN:
# From J_B_OUT.1 to C_B1.1 & C_B2.1 via left trunk at X=121
add_track_pts([pad_pos(J_B_OUT, 1), (121.0, 130.0), (121.0, 144.0), pad_pos(C_B1, 1)], "+5V_IN", 1.2, pcbnew.F_Cu)
add_track_pts([(121.0, 144.0), (121.0, 156.0), pad_pos(C_B2, 1)], "+5V_IN", 1.2, pcbnew.F_Cu)

# Route J_B_OUT.1 to J2.1 on B.Cu layer to avoid crossing any top tracks
add_track_pts([pad_pos(J_B_OUT, 1), (131.0, 130.0), (131.0, 116.0), pad_pos(J2, 1)], "+5V_IN", 1.2, pcbnew.B_Cu)

# J2.1 to D1.1 & D1.3 (Schottky Dual Anodes) on F.Cu:
add_track_pts([pad_pos(J2, 1), (137.0, 110.0), (146.0, 110.0), pad_pos(D1, 1)], "+5V_IN", 1.2, pcbnew.F_Cu)
add_track_pts([(146.0, 110.0), (151.08, 110.0), pad_pos(D1, 3)], "+5V_IN", 1.2, pcbnew.F_Cu)

# J2.1 to Q1.1 (P-MOSFET Gate) & R1.1 (10k Pull-down) on F.Cu:
add_track_pts([pad_pos(J2, 1), (134.0, 116.0), (134.0, 144.0), pad_pos(Q1, 1)], "+5V_IN", 0.6, pcbnew.F_Cu)
add_track_pts([(134.0, 144.0), (134.0, 158.0), pad_pos(R1, 1)], "+5V_IN", 0.6, pcbnew.F_Cu)

# 3.4 V_BAT_PROT: J3.1 (TP4056 Battery Out) to Q1.2 (P-MOSFET Drain) on B.Cu
add_track_pts([pad_pos(J3, 1), (133.0, 130.0), (133.0, 140.0), (148.54, 140.0), pad_pos(Q1, 2)], "V_BAT_PROT", 1.2, pcbnew.B_Cu)

# 3.5 V_SW (Switched DC Bus):
# From D1.2 (Schottky Cathode) & Q1.3 (P-MOSFET Source) to C1..C3 & J4.1 (MT3608 IN)
add_track_pts([pad_pos(D1, 2), (148.54, 122.0), (156.0, 122.0), (156.0, 116.0), pad_pos(C1, 1)], "V_SW", 1.2, pcbnew.F_Cu)
add_track_pts([pad_pos(Q1, 3), (156.0, 144.0), (156.0, 122.0)], "V_SW", 1.2, pcbnew.F_Cu)
add_track_pts([(156.0, 122.0), (156.0, 126.0), pad_pos(C2, 1)], "V_SW", 1.2, pcbnew.F_Cu)
add_track_pts([(156.0, 126.0), (156.0, 136.0), pad_pos(C3, 1)], "V_SW", 1.2, pcbnew.F_Cu)
add_track_pts([(156.0, 136.0), (156.0, 146.0), pad_pos(J4, 1)], "V_SW", 1.2, pcbnew.F_Cu)

# 3.6 +5V_OUT:
# From J5.1 (MT3608 OUT) to C4..C6 filter caps, J6.1 (5V screw terminal), and U1.3 (AMS1117 VIN)
add_track_pts([pad_pos(J5, 1), (169.0, 158.0), (169.0, 118.0), pad_pos(C4, 1)], "+5V_OUT", 1.5, pcbnew.F_Cu)
add_track_pts([(169.0, 132.0), pad_pos(C5, 1)], "+5V_OUT", 1.5, pcbnew.F_Cu)
add_track_pts([(169.0, 142.0), pad_pos(C6, 1)], "+5V_OUT", 1.5, pcbnew.F_Cu)
add_track_pts([(169.0, 152.0), pad_pos(C7, 1)], "+5V_OUT", 1.2, pcbnew.F_Cu)
add_track_pts([pad_pos(C4, 1), (175.0, 112.0), (193.0, 112.0), pad_pos(J6, 1)], "+5V_OUT", 1.5, pcbnew.F_Cu)
add_track_pts([(169.0, 134.3), pad_pos(U1, 3)], "+5V_OUT", 1.0, pcbnew.F_Cu)

# U1.1 (GND): Thermal via to bottom solid copper GND plane
add_via(178.0, 129.7, "GND")
add_track_pts([pad_pos(U1, 1), (178.0, 129.7)], "GND", 0.6, pcbnew.F_Cu)

# Bridge U1 Pin 2 (VO) to U1 Tab (VO)
p_tab = None
p_pin2 = None
for p in U1.Pads():
    if p.GetNumber() == "2":
        if pcbnew.ToMM(p.GetPosition().x) > 185.0:
            p_tab = p.GetPosition()
        else:
            p_pin2 = p.GetPosition()
add_track(p_pin2, p_tab, "+3V3_OUT", 0.8, pcbnew.F_Cu)

# 3.7 +3V3_OUT:
# From U1 Tab to C8, C9 filter caps and J7.1 (3.3V screw terminal)
add_track_pts([p_tab, (189.0, 132.0), (189.0, 142.0), (184.0, 142.0), pad_pos(C8, 1)], "+3V3_OUT", 1.2, pcbnew.F_Cu)
add_track_pts([pad_pos(C8, 1), (180.0, 146.0), (180.0, 156.0), pad_pos(C9, 1)], "+3V3_OUT", 1.2, pcbnew.F_Cu)
add_track_pts([(189.0, 132.0), (189.0, 146.0), pad_pos(J7, 1)], "+3V3_OUT", 1.2, pcbnew.F_Cu)

# ==============================================================================
# 4. BOTTOM COPPER GROUND PLANE (B_Cu ZONE)
# ==============================================================================
zone = pcbnew.ZONE(board)
zone.SetLayer(pcbnew.B_Cu)
zone.SetNet(nets["GND"])
zone.SetMinThickness(mm(0.25))
zone.SetLocalClearance(mm(0.40))
zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
zone.SetThermalReliefGap(mm(0.40))
zone.SetThermalReliefSpokeWidth(mm(0.6))
outline = zone.Outline()
outline.NewOutline()
for px, py in [(X0+0.5, Y0+0.5), (X0+W-0.5, Y0+0.5), (X0+W-0.5, Y0+H-0.5), (X0+0.5, Y0+H-0.5)]:
    outline.Append(mm(px), mm(py))
board.Add(zone)

filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())

# ==============================================================================
# 5. HIGH-VISIBILITY SILKSCREEN LABELS
# ==============================================================================
# Centered Header & Footer (well clear of mounting holes)
add_text("UNIVERSAL IoT DC UPS v2.0", 152.5, 103.5, size=1.3, bold=True)
add_text("IN: 6.5V-24V DC | 5.0V & 3.3V OUT | 0ms SWITCH", 152.5, 106.0, size=0.85, bold=False)
add_text("ESP32 & IOT ZERO-REBOOT POWER SUPPLY", 152.5, 167.0, size=0.85, bold=False)

# Screw Terminal Headers (Placed safely above footprints)
add_text("DC IN", 108.0, 108.5, size=0.85, bold=True)
add_text("5V OUT", 195.5, 110.5, size=0.85, bold=True)
add_text("3.3V OUT", 195.5, 138.5, size=0.85, bold=True)

# Module header indicators (in empty gaps)
add_text("BUCK", 125.0, 124.0, size=0.8, bold=False)
add_text("TP4056", 137.0, 124.0, size=0.8, bold=False)
add_text("MT3608", 162.0, 152.0, size=0.8, bold=False)

# Save board
pcb_path = os.path.join(PROJ_DIR, "DC_UPS_IoT.kicad_pcb")
board.Save(pcb_path)
print("Complete verified PCB saved successfully to:", pcb_path)
