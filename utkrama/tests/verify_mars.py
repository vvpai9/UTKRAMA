
import sys
import os
import numpy as np

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.simulation import Simulation

def test_mars_mission():
    print("Testing Mars Mission (Atmosphere Landing)...")
    sim = Simulation()
    # Initialize Mars Mission
    sim.initialize(
        planet_name="Mars", 
        target_apo_km=100.0, 
        safety_margin_km=5.0, 
        dry_mass=1000.0, 
        fuel_mass=5000.0, 
        propellant_type="liquid"
    )
    
    print(f"Planet: {sim.planet.name}. Atmosphere? {sim.planet.has_atmosphere}")
    if not sim.planet.has_atmosphere:
        print("FAIL: Mars SHOULD have atmosphere.")
        return

    # Run Simulation
    print("Starting Sim...")
    dt = 0.5
    max_steps = 20000 
    
    retro_burn_ignited = False
    chutes_deployed = False
    
    for i in range(max_steps):
        sim.step(dt)
        
        alt = np.linalg.norm(sim.rocket.position) - sim.planet.radius
        vel = np.linalg.norm(sim.rocket.velocity)
        
        if i % 200 == 0:
            print(f"T={sim.time:.1f} | Alt={alt:.0f}m | Vel={vel:.1f}m/s | Status={sim.rocket.status}")

        if sim.rocket.status == "RETRO_BRAKE" and sim.rocket.engine.running:
             if not retro_burn_ignited:
                 print(f"RETRO IGNITION CONFIRMED at {alt:.0f}m, Vel={vel:.1f} m/s")
                 retro_burn_ignited = True
                 
        if "CHUTE" in sim.rocket.status:
             if not chutes_deployed:
                 print(f"CHUTES DEPLOYED at {alt:.0f}m")
                 chutes_deployed = True
                 
        if sim.rocket.status == "LANDED":
             print(f"SUCCESS: LANDED! Final Vel={vel:.2f} m/s")
             if vel > 12.0:
                 print("FAIL: Hard Landing > 12 m/s")
             else:
                 print("PASS: Soft Landing.")
             return
        
        if sim.rocket.status == "CRASHED":
             print(f"FAIL: CRASHED! Impact Vel={vel:.2f} m/s")
             return
             
    print("TEST TIMEOUT")

if __name__ == "__main__":
    test_mars_mission()
