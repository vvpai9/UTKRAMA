
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.physics import PLANETS

def test_planets():
    print("Verifying New Planets...")
    
    expected = ["Mercury", "Venus", "Pluto"]
    for p in expected:
        if p not in PLANETS:
            print(f"FAIL: {p} not found in PLANETS dict.")
            return
        
        planet = PLANETS[p]
        print(f"Planet: {planet.name} | Atmosphere? {planet.has_atmosphere}")
        
        if p == "Mercury" or p == "Pluto":
            if planet.has_atmosphere:
                print(f"FAIL: {p} should be Vacuum.")
        elif p == "Venus":
            if not planet.has_atmosphere:
                print(f"FAIL: {p} should have Atmosphere.")
                
    print("SUCCESS: All new planets verified.")

if __name__ == "__main__":
    test_planets()
