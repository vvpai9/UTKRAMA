import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.physics import PLANETS

def test_earth_atmosphere():
    earth = PLANETS['Earth']
    
    print(f"{'Alt (km)':<10} {'Rho (kg/m3)':<15} {'Temp (K)':<10} {'Press (Pa)':<15} {'SpeedSd (m/s)':<15}")
    print("-" * 70)
    
    test_alts_km = [0, 5, 10, 11, 15, 20, 25, 32, 40, 50, 60, 80, 100]
    
    for h_km in test_alts_km:
        h_m = h_km * 1000
        env = earth.query_environment(h_m)
        print(f"{h_km:<10} {env.density:<15.5f} {env.temperature:<10.2f} {env.pressure:<15.2f} {env.speed_of_sound:<15.2f}")

if __name__ == "__main__":
    test_earth_atmosphere()
