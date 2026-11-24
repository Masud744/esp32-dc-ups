import numpy as np
import matplotlib.pyplot as plt

# -------------------------------------------------------------
# DC UPS Transient Simulation for ESP32 IoT Device
# Modeling: 5V Adapter Cut & Restore, P-MOSFET Load Share, 
#           MT3608 Boost, 1000uF Buffer, AMS1117 & ESP32 Brownout
# -------------------------------------------------------------

# Time vector: 0 to 100 ms with 2 us resolution
dt = 2e-6  # 2 microseconds
t = np.arange(0, 0.100, dt)
N = len(t)

# Circuit Constants
V_BAT = 3.70           # Li-ion cell nominal voltage (V)
R_BAT = 0.05           # Battery internal resistance (Ohms)
C_IN = 220e-6          # Switched rail buffer capacitor (220 uF)
ESR_CIN = 0.08         # ESR of Cin
C_OUT = 1000e-6        # Output bulk capacitor (1000 uF Low-ESR)
ESR_COUT = 0.03        # ESR of Cout
V_TARGET = 5.10        # MT3608 boost target voltage (V)
BOOST_ETA = 0.90       # Boost converter efficiency (90%)
R_ON_PMOS = 0.040      # AO3401A Rds(on) when fully enhanced (40 mOhms)
V_TH_PMOS = -0.80      # AO3401A threshold voltage (V)
V_BROWNOUT = 2.80      # ESP32 hardware brownout threshold (V)

# Adapter Voltage Profile:
# 0 to 20 ms: 5.0V
# 20 to 25 ms: Decay to 0V (Mains power loss)
# 25 to 60 ms: 0.0V (Battery backup running)
# 60 to 63 ms: Restore back to 5.0V (Mains electricity returns)
# 63 to 100 ms: 5.0V
v_adapter = np.zeros(N)
for i, time in enumerate(t):
    if time < 0.020:
        v_adapter[i] = 5.0
    elif 0.020 <= time < 0.025:
        decay = (time - 0.020) / 0.0015
        v_adapter[i] = 5.0 * np.exp(-decay)
    elif 0.025 <= time < 0.060:
        v_adapter[i] = 0.0
    elif 0.060 <= time < 0.063:
        v_adapter[i] = 5.0 * ((time - 0.060) / 0.003)
    else:
        v_adapter[i] = 5.0

# ESP32 Load Current Profile:
# Base load: 100 mA
# Wi-Fi TX bursts: 450 mA at t = 10ms (normal) and t = 22ms to 27ms (WORST CASE: power cut during TX!)
i_load = np.full(N, 0.100) # 100 mA idle/CPU
for i, time in enumerate(t):
    if 0.010 <= time <= 0.012:
        i_load[i] = 0.450 # Wi-Fi burst under adapter
    elif 0.021 <= time <= 0.026:
        i_load[i] = 0.480 # Wi-Fi burst exactly during power failure!
    elif 0.075 <= time <= 0.078:
        i_load[i] = 0.450 # Wi-Fi burst after power returns

# State variables arrays
v_gate = np.zeros(N)
v_sw = np.zeros(N)
v_out = np.zeros(N)
v_esp_3v3 = np.zeros(N)
i_adapter_d1 = np.zeros(N)
i_pmos_channel = np.zeros(N)
i_pmos_body = np.zeros(N)

# Initial conditions (t = 0, steady state with adapter ON)
v_gate[0] = 5.0
v_sw[0] = 5.0 - 0.35  # Schottky drop
v_out[0] = V_TARGET
v_esp_3v3[0] = 3.30

# Simulation Loop (Euler integration with non-linear physics)
for i in range(N - 1):
    # 1. Gate voltage RC tracking
    # tau = R1 * Ciss = 10k * 600pF = 6 us
    tau_gate = 6e-6
    v_gate[i + 1] = v_gate[i] + (v_adapter[i] - v_gate[i]) * (dt / tau_gate)
    
    # 2. Schottky Diode D1 (1N5822: Vf ~ 0.32V + Rs*I)
    v_d1 = v_adapter[i] - v_sw[i]
    if v_d1 > 0.28:
        i_d1 = (v_d1 - 0.28) / 0.08  # dynamic conduction
    else:
        i_d1 = 0.0
    i_adapter_d1[i] = max(0.0, i_d1)
    
    # 3. P-MOSFET Q1 (AO3401A)
    # Source is at v_sw[i], Drain is at V_BAT
    # V_GS = V_Gate - V_Source
    v_gs = v_gate[i] - v_sw[i]
    
    # Body diode: Anode = Drain (V_BAT), Cathode = Source (v_sw)
    v_body = V_BAT - v_sw[i]
    if v_body > 0.55:
        i_body = (v_body - 0.55) / 0.15 # body diode conduction
    else:
        i_body = 0.0
    i_pmos_body[i] = max(0.0, i_body)
    
    # MOSFET Channel conduction:
    # Turns ON when V_GS < V_TH_PMOS (-0.8V)
    if v_gs < V_TH_PMOS:
        # Full enhancement curve
        overdrive = abs(v_gs) - abs(V_TH_PMOS)
        r_effective = max(R_ON_PMOS, R_ON_PMOS + 0.15 * np.exp(-overdrive * 1.5))
        i_ch = (V_BAT - v_sw[i]) / (r_effective + R_BAT)
    else:
        i_ch = 0.0
    i_pmos_channel[i] = max(0.0, i_ch)
    
    # Total battery current feeding v_sw
    i_from_battery = i_pmos_channel[i] + i_pmos_body[i]
    
    # 4. MT3608 Boost Converter Stage
    # Power required by output: P_out = v_out * i_load
    p_load = v_out[i] * i_load[i]
    p_in_boost = p_load / BOOST_ETA
    i_boost_in = p_in_boost / max(1.5, v_sw[i]) # clamp to prevent division by zero
    i_boost_in = min(i_boost_in, 2.0)           # 2A switch current limit
    
    # Switched Rail C_IN dV/dt
    dv_sw_dt = (i_adapter_d1[i] + i_from_battery - i_boost_in) / C_IN
    v_sw[i + 1] = max(0.0, v_sw[i] + dv_sw_dt * dt)
    
    # Output Rail C_OUT dV/dt (MT3608 feedback control bandwidth ~ 50 kHz)
    # The boost converter tries to deliver I_boost_out = (v_sw * i_boost_in * ETA) / v_out
    i_boost_out = (v_sw[i] * i_boost_in * BOOST_ETA) / max(1.0, v_out[i])
    dv_out_dt = (i_boost_out - i_load[i]) / C_OUT
    v_out[i + 1] = max(0.0, v_out[i] + dv_out_dt * dt)
    # Boost regulator upper clamp (regulation setpoint)
    if v_out[i + 1] > V_TARGET:
        v_out[i + 1] = V_TARGET
        
    # 5. ESP32 Onboard AMS1117-3.3 Regulator Model
    # Dropout is ~1.15V at 100mA, up to ~1.25V at 450mA
    dropout = 1.15 if i_load[i] < 0.2 else 1.25
    v_esp_3v3[i + 1] = min(3.30, max(0.0, v_out[i + 1] - dropout))

# Fill last point
i_adapter_d1[-1] = i_adapter_d1[-2]
i_pmos_channel[-1] = i_pmos_channel[-2]
i_pmos_body[-1] = i_pmos_body[-2]

# Diagnostics & Stats
min_v_out = np.min(v_out)
min_v_3v3 = np.min(v_esp_3v3)
brownout_triggered = np.any(v_esp_3v3 < V_BROWNOUT)

print("=" * 60)
print("DC UPS SIMULATION RESULTS SUMMARY")
print("=" * 60)
print(f"Target Output Rail:              {V_TARGET:.2f} V")
print(f"Minimum V_OUT during switch:     {min_v_out:.3f} V (Max Droop: {V_TARGET - min_v_out:.3f} V)")
print(f"Minimum ESP32 3.3V Rail:         {min_v_3v3:.3f} V")
print(f"ESP32 Brownout Threshold:        {V_BROWNOUT:.2f} V")
print(f"Safety Margin above Brownout:    {min_v_3v3 - V_BROWNOUT:.3f} V")
print(f"Brownout / Reboot Triggered?     {'YES (FAILED)' if brownout_triggered else 'NO (100% SUCCESS - SEAMLESS!)'}")
print("=" * 60)

# Plotting High-Resolution Results
fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(10, 10), sharex=True)

# Panel 1: Voltages (Adapter, V_sw, V_out)
ax1.plot(t * 1000, v_adapter, 'b-', label='Adapter Input (V_adapter)', linewidth=1.8)
ax1.plot(t * 1000, v_sw, 'm--', label='Switched Rail (V_sw)', linewidth=1.5)
ax1.plot(t * 1000, v_out, 'g-', label='Boost 5V Output (V_out)', linewidth=2.0)
ax1.axvline(20, color='r', linestyle=':', label='Mains Loss (20ms)')
ax1.axvline(60, color='c', linestyle=':', label='Mains Return (60ms)')
ax1.set_ylabel('Voltage (V)')
ax1.set_title('DC UPS Transient Response: Mains Power Cut & Restoration', fontsize=12, fontweight='bold')
ax1.grid(True, linestyle='--', alpha=0.6)
ax1.legend(loc='lower left', fontsize=9)
ax1.set_ylim(-0.5, 5.8)

# Panel 2: ESP32 Internal 3.3V Rail & Brownout Limit
ax2.plot(t * 1000, v_esp_3v3, 'darkgreen', label='ESP32 VDD (3.3V Rail)', linewidth=2.2)
ax2.axhline(V_BROWNOUT, color='red', linestyle='--', linewidth=1.5, label='ESP32 Brownout Trip Limit (2.80V)')
ax2.fill_between(t * 1000, 0, V_BROWNOUT, color='red', alpha=0.15, label='Brownout / Reboot Zone')
ax2.set_ylabel('ESP 3.3V Rail (V)')
ax2.grid(True, linestyle='--', alpha=0.6)
ax2.legend(loc='lower left', fontsize=9)
ax2.set_ylim(2.2, 3.6)

# Panel 3: Current Distribution (Mains Diode vs Battery MOSFET)
ax3.plot(t * 1000, i_adapter_d1 * 1000, 'blue', label='Adapter Current via D1 (mA)', linewidth=1.8)
ax3.plot(t * 1000, i_pmos_channel * 1000, 'orange', label='Battery Current via P-MOSFET (mA)', linewidth=1.8)
ax3.plot(t * 1000, i_pmos_body * 1000, 'red', linestyle='--', label='P-MOSFET Body Diode Sub-microsecond (mA)', linewidth=1.2)
ax3.set_ylabel('Current (mA)')
ax3.set_title('Power Path Source Transition (Adapter vs Battery)', fontsize=10, fontweight='bold')
ax3.grid(True, linestyle='--', alpha=0.6)
ax3.legend(loc='upper right', fontsize=9)

# Panel 4: ESP32 Dynamic Load Profile (Wi-Fi TX Spikes)
ax4.plot(t * 1000, i_load * 1000, 'black', label='ESP32 Load (with 450mA Wi-Fi TX burst)', linewidth=1.5)
ax4.set_xlabel('Time (milliseconds)', fontsize=11)
ax4.set_ylabel('ESP Load (mA)')
ax4.grid(True, linestyle='--', alpha=0.6)
ax4.legend(loc='upper right', fontsize=9)
ax4.set_ylim(0, 550)

plt.tight_layout()
output_chart = "/home/shahriar-alom-masud/Projects/PCB/DC UPS IoT/simulation/ups_transient_simulation.png"
plt.savefig(output_chart, dpi=200)
print(f"Chart saved to: {output_chart}")
