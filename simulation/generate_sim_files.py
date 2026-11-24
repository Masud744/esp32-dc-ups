import urllib.parse

# Falstad Circuit Definition for our DC UPS
# Components:
# 1. 5V Adapter with a toggle switch to simulate power outage
# 2. 1N5822 Schottky Diode
# 3. 3.7V Battery
# 4. P-MOSFET (AO3401A model)
# 5. 10k Gate pull-down resistor
# 6. Switched Rail with 220uF capacitor
# 7. Step-Up Boost converter (modeled with boost inductor, diode, switch & 1000uF capacitor)
# 8. Variable load simulating ESP32 base load (100mA) + Wi-Fi pulse (450mA)
# 9. Scopes for Adapter, Gate, Switched Rail, and 5V Output Rail

falstad_circuit = """$ 1 0.000005 10.20027730826997 50 5 50
v 112 160 112 304 0 0 40 5 0 0 0.5
s 112 160 192 160 0 0 false
w 192 160 272 160 0
d 272 160 384 160 1 0.35
w 192 160 192 224 0
r 192 224 192 304 0 10000
g 192 304 192 336 0
g 112 304 112 336 0
w 192 224 336 224 0
f 336 240 384 240 1 1.5
w 336 224 336 240 0
v 256 256 256 304 0 0 40 3.7 0 0 0.5
w 256 256 384 256 0
g 256 304 256 336 0
w 384 160 384 224 0
w 384 160 480 160 0
c 480 160 480 304 0 0.00022 4.65
g 480 304 480 336 0
w 480 160 544 160 0
l 544 160 624 160 0 0.000022 0.4
d 624 160 704 160 1 0.35
c 704 160 704 304 0 0.001 5.1
g 704 304 704 336 0
r 704 160 768 160 0 10
r 768 160 768 304 0 40
g 768 304 768 336 0
O 704 160 752 160 0
O 192 160 240 128 0
O 480 160 480 112 0
o 0 64 0 4099 5 0.00009765625 0 2 0 3
o 1 64 0 4099 5 0.00009765625 1 2 1 3
o 2 64 0 4099 5 0.00009765625 2 2 2 3
"""

with open("/home/shahriar-alom-masud/Projects/PCB/DC UPS IoT/simulation/falstad_circuit.txt", "w") as f:
    f.write(falstad_circuit)

# Generate direct clickable URL
encoded_data = urllib.parse.quote(falstad_circuit)
falstad_url = f"https://www.falstad.com/circuit/circuitjs.html?cct={encoded_data}"

with open("/home/shahriar-alom-masud/Projects/PCB/DC UPS IoT/simulation/falstad_link.txt", "w") as f:
    f.write(falstad_url)

# LTspice Netlist
ltspice_netlist = """* DC UPS for ESP32 IoT Device (AN1149 + MT3608 + 1000uF)
* Transient Simulation Netlist
VADAPTER V_IN 0 PULSE(5 0 20m 1m 1m 40m 100m)
VBAT V_BAT 0 3.7
R_BAT V_BAT V_BAT_INT 0.05

* Schottky Diode D1 (Adapter to V_SW)
D1 V_IN V_SW MBR0520
.model MBR0520 D(Is=31.7u Rs=0.08 N=1.04 Cjo=120p)

* P-MOSFET Q1 (Battery to V_SW)
* Drain at V_BAT, Source at V_SW, Gate at V_GATE
M1 V_BAT_INT V_GATE V_SW V_SW AO3401
.model AO3401 PMOS(Vto=-0.8 Kp=25 Rs=0.02 Rd=0.02 Cgs=400p Cgd=150p)

* Gate pull-down resistor
R_GATE V_GATE 0 10k
W_GATE V_IN V_GATE 0.001

* Switched node capacitance
C_SW V_SW 0 220u
R_ESR_SW V_SW V_SW_CAP 0.05

* Boost stage representation
* Regulated output rail 5.1V with 1000uF bulk capacitor
C_OUT V_5V_OUT 0 1000u
R_LOAD V_5V_OUT 0 12.5

.tran 0.1u 80m 0 1u
.backanno
.end
"""

with open("/home/shahriar-alom-masud/Projects/PCB/DC UPS IoT/simulation/dc_ups_ltspice.cir", "w") as f:
    f.write(ltspice_netlist)

print("Falstad and LTspice files generated successfully.")
