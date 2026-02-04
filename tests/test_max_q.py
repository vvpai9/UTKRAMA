import sys
import os
import matplotlib.pyplot as plt
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.core.simulation import Simulation

def test_max_q():
    sim = Simulation()
    # Mass: 10t dry, 90t fuel -> 100t total. Weight ~1MN. Default Thrust 2MN. TWR ~2.0
    sim.initialize("Earth", 200, 50, 10000, 90000, "liquid") 
    
    # Run ascent
    qs = []
    alts = []
    vels = []
    times = []
    
    # Run for 150 seconds (should pass Max Q)
    for i in range(3000):
        sim.step(sim.dt)
        if sim.time > 150: break
        
        # Debug trace
        if i % 100 == 0 or sim.rocket.status == "CRASHED":
             print(f"Step {i}: T={sim.time:.2f} Alt={np.linalg.norm(sim.rocket.position)-sim.planet.radius:.2f} V={np.linalg.norm(sim.rocket.velocity):.2f} Status={sim.rocket.status}")
             if sim.rocket.status == "CRASHED":
                 break
        
        times.append(sim.time)
        qs.append(sim.rocket.q)
        alts.append(np.linalg.norm(sim.rocket.position) - sim.planet.radius)
        vels.append(np.linalg.norm(sim.rocket.velocity))
        
    max_q = max(qs)
    max_q_idx = qs.index(max_q)
    max_q_time = times[max_q_idx]
    max_q_alt = alts[max_q_idx]
    max_q_vel = vels[max_q_idx]
    
    print(f"Max Q: {max_q:.2f} Pa")
    print(f"Time:  {max_q_time:.2f} s")
    print(f"Alt:   {max_q_alt/1000:.2f} km")
    print(f"Vel:   {max_q_vel:.2f} m/s")
    
    # Check if reasonable
    # Falcon 9 Max Q ~ 30-35 kPa (~1 min, 10-15km)
    if 10000 < max_q < 50000:
        print("SUCCESS: Max Q is within typical aerospace range (10-50 kPa).")
    else:
        print("WARNING: Max Q seems off (Too low/high).")

    # Plot
    # plt.plot(times, qs)
    # plt.show()

if __name__ == "__main__":
    test_max_q()
