# 2D-Rocket-Simulator

A real-time 2D rocket simulator built in Python that models suborbital rocket launch, powered ascent, cutoff, ballistic coast, atmospheric re-entry, parachute recovery, and optional retro-braking.

The simulator supports both **solid** and **liquid** propulsion logic, real-time guidance, dynamic thrust control, drag, mass flow, and a full event/status system.

This project is designed as a learning platform for **GNC concepts**, **flight dynamics**, and **mission sequencing**.

---

## Features

### Mission Modes
- **Suborbital flights**
- Target apogee control
- Safety margin based engine cutoff (liquid)

### Propulsion
- **Solid propellant**
  - Continuous burn until fuel exhaustion
- **Liquid propellant**
  - Thrust cutoff and optional re-ignition based on trajectory and predicted apogee
  - Optional **retro-braking during re-entry**

### Flight Phases
- READY  
- THRUSTING  
- CUTOFF (liquid only)  
- COASTING  
- RE-ENTRY  
- RETRO BRAKE (liquid + enabled)  
- CHUTES DEPLOYED  
- LANDED  
- ABORT  

### Physics & Environment
- Variable mass with mass flow
- Atmospheric density model
- Aerodynamic drag
- Dynamic pressure (Max-Q)
- Gravity
- Drogue + Main parachute system
- Orientation tied to velocity vector
- Retrograde braking support

### Visualization
- Real-time rocket attitude view
- Downrange vs Altitude trajectory
- Time vs Altitude plot
- Time vs Velocity plot
- HUD with live telemetry

### Controls
- Launch / Abort / Close
- Time warp: **1×, 2×, 4×, 8×**
- Mission configuration dialog

---

## Requirements

- Python 3.9+
- NumPy
- SciPy
- Matplotlib
- PySide6

Install dependencies:

```bash
pip install numpy scipy matplotlib PySide6
```

---

## How to Run
1. Clone the repository
```
git clone https://github.com/vvpai9/2D-Rocket-Simulator
```
2. Run ```main.py```
```
cd 2D-Rocket-Simulator
python3 main.py
```
3. Configure mission parameters:
  - Target Apogee
  - Fuel mass
  - Propellant Type
  - Retro-Braking (liquid only)
4. Click ```Start Mission```
5. Press ```Launch```

---

## Status

Suborbital mode is stable and validated for:
  - Solid propulsion
  - Liquid propulsion
  - Retro-braking
  - Safe parachute recovery

**Orbital launch mode is currently under development in a separate branch**

---
## Author

Developed by Varun Vivek Pai
Electronics & Communication Engineering
Focus: Flight dynamics, guidance & aerospace simulation

---
