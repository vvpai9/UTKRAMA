# UTKRAMA
**Unified Trajectory and Kinematics for Rocket Ascent and Mission Analysis**

UTKRAMA is a physics-based, modular 2D launch vehicle simulation framework designed for guidance, control, and trajectory experimentation across multiple planetary environments. The framework integrates rigid-body dynamics, aerodynamic stability modeling, propulsion systems, closed-loop guidance, and automated experimentation tools.

This repository preserves the evolution of the simulator:

```v1.0/``` – Initial proof-of-concept

```v2.0/``` – Intermediate stabilized architecture

```utkrama/``` – Final research-grade framework used in the IEEE paper

---

# Associated Paper

Varun Vivek Pai,
UTKRAMA: A Modular Physics-Based 2D Launch Vehicle Simulation Framework with Guidance, Control, and Experimental Instrumentation, 2026.

---

## Key Capabilities
- Physics-based rigid body dynamics with RK4 integration
- Multi-planetary environments (Earth, Mars, Moon, Venus, Mercury, Pluto)
- Atmospheric and aerodynamic modeling with Mach dependence
- Gravity turn and closed-loop apoapsis targeting guidance
- Aerodynamic stability and control via thrust vectoring
- Re-entry, retro-braking, and two-stage parachute descent
- Automated Monte Carlo testing and parameter sweeps
- Deterministic, reproducible simulation runs

---

## Why UTKRAMA?

UTKRAMA is designed as a **research and education platform**, not a game engine.
It enables rapid prototyping and experimental evaluation of guidance and control
algorithms under realistic physical constraints.

---

## Getting Started

```bash
git clone https://github.com/vvpai9/UTKRAMA.git
cd UTKRAMA
pip install -r requirements.txt
python main.py
```

---

# License + Citation

See ```LICENSE``` and ```CITATION.cff```

---

## Paper ↔ Code Mapping

| Paper Section | Code Location |
|--------------|---------------|
| RK4 Integration | utkrama/src/core/simulation.py |
| Aerodynamics | utkrama/src/core/physics.py |
| Stability Analysis | utkrama/tests/test_stability.py |
| Guidance Laws | utkrama/src/core/guidance.py |

---

