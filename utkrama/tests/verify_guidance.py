
import sys
import os
import numpy as np

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.simulation import Simulation

def test_moon_guidance():
    print("Testing Moon Ascent Guidance (Vacuum Turn)...")
    sim = Simulation()
    # Initialize Moon Mission
    sim.initialize(
        planet_name="Moon", 
        target_apo_km=50.0, 
        safety_margin_km=5.0, 
        dry_mass=350.0, 
        fuel_mass=2000.0, 
        propellant_type="liquid"
    )
    
    sim.rocket.ignite_engine()
    dt = 0.5
    
    for i in range(200): # 100 seconds
        sim.step(dt)
        alt = np.linalg.norm(sim.rocket.position) - sim.planet.radius
        
        # Check Pitch Angle (from Vertical)
        # Orientation is angle wrt vertical (pi/2 is Vertical Up in our confusing convention? No, pi/2 is Vertical Up)
        # Pitch from vertical = pi/2 - orientation
        pitch_deg = 90 - np.rad2deg(sim.rocket.orientation)
        
        if i % 10 == 0:
            print(f"T={sim.time:.1f} | Alt={alt:.0f}m | PitchFromVert={pitch_deg:.1f} deg")
            
        if alt > 5000:
            if pitch_deg < 25.0:
               print(f"FAIL: Pitch only {pitch_deg:.1f} deg at 5km. Should be > 30 deg for Moon.")
               return
            else:
               print(f"PASS: Pitch {pitch_deg:.1f} deg at >5km (Aggressive Turn confirmed).")
               return

if __name__ == "__main__":
    test_moon_guidance()
