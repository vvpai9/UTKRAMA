
import sys
import os
import numpy as np

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.guidance import GuidanceSystem
from src.core.rocket import Rocket
from src.core.physics import MOON, EARTH

def test_vacuum_guidance():
    print("Testing GuidanceSystem Vacuum Logic...")
    
    guidance = GuidanceSystem(target_apoapsis=50000)
    rocket = Rocket(dry_mass=100, fuel_mass=100, isp=300, max_thrust=1000, propellant_type="liquid")
    
    # Test 1: Earth (Atmosphere)
    # Should use standard Liquid profile (Start Turn @ 1000m)
    angle_earth = guidance.get_steering_command(rocket, altitude=500, velocity_vector=np.array([0,100]), planet=EARTH)
    print(f"Earth Alt=500m Angle={np.rad2deg(angle_earth):.2f} deg (Expected 0.00)")
    
    angle_earth_2km = guidance.get_steering_command(rocket, altitude=5000, velocity_vector=np.array([0,100]), planet=EARTH)
    print(f"Earth Alt=5000m Angle={np.rad2deg(angle_earth_2km):.2f} deg (Expected > 0)")
    
    # Test 2: Moon (Vacuum)
    # Should use Vacuum profile (Start Turn @ 50m)
    angle_moon = guidance.get_steering_command(rocket, altitude=500, velocity_vector=np.array([0,100]), planet=MOON)
    print(f"Moon Alt=500m Angle={np.rad2deg(angle_moon):.2f} deg (Expected > 0)")
    
    angle_moon_5km = guidance.get_steering_command(rocket, altitude=5000, velocity_vector=np.array([0,100]), planet=MOON)
    print(f"Moon Alt=5000m Angle={np.rad2deg(angle_moon_5km):.2f} deg (Expected ~26)")

    # Check Internal Constants via behavior
    # Fraction at 500m for Moon: (500-50)/(15000-50) = 450/14950 = 0.03. Target 80. Angle = 2.4 deg.
    
if __name__ == "__main__":
    test_vacuum_guidance()
