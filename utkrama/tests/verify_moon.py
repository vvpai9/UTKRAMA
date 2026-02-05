
import sys
import os
import numpy as np

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.simulation import Simulation
from src.core.physics import MOON

def test_moon_mission():
    print("Testing Moon Mission (Vacuum Landing)...")
    sim = Simulation()
    # Initialize Moon Mission: Target Ap 50km, Safety 5km, Dry 350, Fuel 2000, Liquid (Required for powered landing)
    sim.initialize(
        planet_name="Moon", 
        target_apo_km=50.0, 
        safety_margin_km=5.0, 
        dry_mass=350.0, 
        fuel_mass=2000.0, 
        propellant_type="liquid"
    )
    
    print(f"Planet: {sim.planet.name}. Atmosphere? {sim.planet.has_atmosphere}")
    if sim.planet.has_atmosphere:
        print("FAIL: Moon should not have atmosphere.")
        return

    # Run Simulation
    print("Starting Sim...")
    dt = 0.1
    max_steps = 10000 
    
    apex_reached = False
    retro_burn_detected = False
    chute_detected = False
    landed = False
    crashed = False
    
    for i in range(max_steps):
        sim.step(dt)
        
        alt = np.linalg.norm(sim.rocket.position) - sim.planet.radius
        vel = np.linalg.norm(sim.rocket.velocity)
        
        if i % 500 == 0:
            print(f"T={sim.time:.1f} | Alt={alt:.0f}m | Vel={vel:.1f}m/s | Status={sim.rocket.status}")

        if sim.rocket.velocity[1] < 0 and alt > 1000 and not apex_reached:
             apex_reached = True
             print(f"APOGEE at {alt:.0f}m")

        if "RETRO" in sim.rocket.status or (sim.rocket.status == "COAST" and sim.rocket.engine.running and sim.rocket.velocity[1] < 0):
             # Detection of powered descent
             # In my implementation, status might remain COAST or switch to RETRO_BRAKE?
             # Implementation: _handle_retro_braking is called if RETRO_BRAKE.
             # Logic switches to RETRO_BRAKE if descending fast.
             if sim.rocket.status == "RETRO_BRAKE":
                 retro_burn_detected = True
                 
        if "CHUTE" in sim.rocket.status:
             chute_detected = True
             print("FAIL: Chute detected in Vacuum!")
             break
             
        if sim.rocket.status == "LANDED":
             landed = True
             print(f"SUCCESS: LANDED! Final Vel={vel:.2f} m/s")
             break
        
        if sim.rocket.status == "CRASHED":
             crashed = True
             print(f"FAIL: CRASHED! Impact Vel={vel:.2f} m/s")
             break
             
        if alt < 0:
             print("Ground Collision not detected as Landing/Crash?")
             break

    if chute_detected:
        print("TEST FAILED: Chutes deployed.")
    elif crashed:
        print("TEST FAILED: Crashed.")
    elif landed:
        print("TEST PASSED: Powered Landing Successful.")
    else:
        print("TEST TIMEOUT / INCOMPLETE")

if __name__ == "__main__":
    test_moon_mission()
