import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.simulation import Simulation
from src.core.physics import PLANETS

def test_simulation_headless():
    print("Initializing Simulation...")
    sim = Simulation()
    
    print("Setting up mission parameters...")
    # Earth, 300km Apoapsis, 350kg Dry, 50000kg Fuel, Liquid
    is_feasible, rocket_dv, req_dv, extra = sim.check_feasibility("Earth", 300, 350, 50000, "liquid")
        
    print(f"Feasibility Check: {is_feasible}")
    print(f"Rocket DeltaV: {rocket_dv:.2f}")
    print(f"Required DeltaV: {req_dv:.2f}")
    
    if not is_feasible:
        print("Mission not feasible (expected for low fuel test?), adding fuel to force feasibility for test.")
        # Re-init with more fuel
        sim.initialize("Earth", 300, 5, 5000, 100000, "liquid")
    else:
        sim.initialize("Earth", 300, 5, 5000, 50000, "liquid")
        
    print("Starting Main Loop...")
    sim.rocket.status = "THRUSTING"
    sim.rocket.ignite_engine()
    
    # Run for 100 seconds
    for i in range(1000):
        sim.step(0.1)
        if i % 100 == 0:
            r = sim.rocket
            alt = list(sim.history['altitude'])[-1] if sim.history['altitude'] else 0
            vel = list(sim.history['velocity'])[-1] if sim.history['velocity'] else 0
            print(f"T={sim.time:.1f}s | Alt={alt:.0f}m | Vel={vel:.0f}m/s | Pitch={sim.rocket.orientation:.2f} rad")
            
    print("Simulation Test Complete.")

if __name__ == "__main__":
    try:
        from PySide6.QtWidgets import QApplication
        print("PySide6 imported successfully.")
    except ImportError:
        print("WARNING: PySide6 not found in this environment. GUI will not work.")
        
    try:
        import matplotlib.pyplot as plt
        print("Matplotlib imported successfully.")
    except ImportError:
        print("WARNING: Matplotlib not found.")
        
    test_simulation_headless()
