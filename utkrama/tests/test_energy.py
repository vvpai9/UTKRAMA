import sys
import os
import numpy as np
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.simulation import Simulation

def calculate_energy(sim):
    r_vec = sim.rocket.position
    v_vec = sim.rocket.velocity
    r = np.linalg.norm(r_vec)
    v = np.linalg.norm(v_vec)
    mass = sim.rocket.total_mass
    
    # Specific Energy = v^2/2 - mu/r
    pe = -sim.planet.mu / r
    ke = 0.5 * v**2
    return (pe + ke)

def run_test(integrator_name, duration=3000):
    sim = Simulation()
    # Initialize in Vacuum (Moon) to test pure gravity integration without drag
    sim.initialize("Moon", 100, 0, 1000, 0, "liquid") # Moon has no atmo
    sim.integration_method = integrator_name
    
    # Set Circular Orbit State manually
    r_orbit = sim.planet.radius + 100000 # 100km altitude
    v_orbit = np.sqrt(sim.planet.mu / r_orbit)
    
    sim.rocket.position = np.array([0.0, r_orbit])
    sim.rocket.velocity = np.array([v_orbit, 0.0])
    sim.rocket.status = "COAST" # Disable engine
    
    initial_energy = calculate_energy(sim)
    
    dt = 0.1
    steps = int(duration / dt)
    
    for _ in range(steps):
        sim.step(dt)
        
    final_energy = calculate_energy(sim)
    
    return initial_energy, final_energy

def main():
    print("Running Orbital Energy Conservation Test (Moon/Vacuum)")
    
    # Euler
    e_start, e_end = run_test("Euler")
    drift_euler = abs((e_end - e_start) / e_start) * 100
    print(f"Euler Drift: {drift_euler:.6f}%")
    
    # RK4
    e_start, e_end = run_test("RK4")
    drift_rk4 = abs((e_end - e_start) / e_start) * 100
    print(f"RK4 Drift:   {drift_rk4:.6f}%")
    
    improvement = drift_euler / (drift_rk4 + 1e-15)
    print(f"Improvement: {improvement:.1f}x")
    
    if drift_rk4 < 0.001:
        print("SUCCESS: RK4 is stable.")
    else:
        print("FAILURE: RK4 drift too high.")

if __name__ == "__main__":
    main()
