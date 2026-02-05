import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# Add project root
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.simulation import Simulation

def run_stability_test(offset, name):
    print(f"Running Stability Test: {name} (Offset={offset}m)")
    sim = Simulation()
    sim.initialize("Earth", 200, 10, 1000, 50000, "liquid")
    
    # Cheat: Hack the rocket offset
    sim.rocket.cop_offset = offset 
    
    # Launch
    sim.rocket.status = "THRUSTING"
    sim.rocket.ignite_engine()
    
    # Disable Guidance (Lock Gimbal)
    # We can just override the guidance step or set gimbal to 0 manually in loop
    # Or set guidance gains to 0?
    # Better: Force gimbal = 0 in loop.
    
    # Initial Perturbation
    sim.rocket.orientation += np.deg2rad(5.0) # 5 deg initial error
    
    dt = 0.05
    times = []
    alphas = []
    
    for i in range(200): # 10 seconds
        # Lock Gimbal
        sim.rocket.engine.gimbal_angle = 0.0
        
        sim.step(dt)
        sim.time += dt
        
        # Calculate Alpha
        v = sim.rocket.velocity
        if np.linalg.norm(v) > 1:
            gamma = np.arctan2(v[1], v[0])
            alpha = sim.rocket.orientation - gamma
            # Wrap
            alpha = (alpha + np.pi) % (2 * np.pi) - np.pi
            
            times.append(sim.time)
            alphas.append(np.rad2deg(alpha))
            
    return times, alphas

def main():
    # 1. Unstable Case (Positive Offset)
    t1, a1 = run_stability_test(2.0, "Unstable")
    
    # 2. Stable Case (Negative Offset - Fins)
    t2, a2 = run_stability_test(-2.0, "Stable")
    
    # Plot
    plt.figure()
    plt.plot(t1, np.abs(a1), 'r-', label='Unstable (+2m)')
    plt.plot(t2, np.abs(a2), 'b-', label='Stable (-2m)')
    plt.xlabel('Time (s)')
    plt.ylabel('Abs Alpha (deg)')
    plt.title('Aerodynamic Stability Check')
    plt.legend()
    plt.grid(True)
    plt.savefig('test_stability.png')
    
    print("Unstable Final Alpha:", a1[-1])
    print("Stable Final Alpha:", a2[-1])
    
    # Assertions
    if abs(a1[-1]) > abs(a1[0]):
        print("PASS: Unstable case diverged.")
    else:
        print("FAIL: Unstable case did not diverge.")
        
    if abs(a2[-1]) < abs(a2[0]) + 5.0: # Allow some oscillation but shouldn't explode
        print("PASS: Stable case stayed bounded.")
    else:
        print("FAIL: Stable case diverged.")

if __name__ == "__main__":
    main()
