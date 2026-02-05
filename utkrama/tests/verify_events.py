import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("Importing Simulation...", flush=True)
from src.core.simulation import Simulation, State
print("Importing Physics...", flush=True)
from src.core.physics import PLANETS

def verify_events():
    print("Verifying Event System...")
    
    # Init Sim
    sim = Simulation()
    # Mock rocket
    from src.core.rocket import Rocket
    from src.core.rocket import SolidStage, Stage
    
    # Config
    sim.initialize("Earth", 100000, 5000, 1000, 10000, "liquid")
    
    # 1. Test Liftoff Event
    sim.state.x = 0
    sim.state.y = PLANETS["Earth"].radius + 2.0 # Just above ground
    sim.time = 0.2
    
    sim.step(0.1)
    
    has_liftoff = any(e['label'] == "LIFTOFF" for e in sim.events)
    if has_liftoff:
        print("PASS: LIFTOFF event recorded.")
    else:
        print("FAIL: LIFTOFF event missing.")
        
    # 2. Test Max Q
    sim.rocket.q = 10000.0
    sim.step(0.1)
    if sim.max_q_value >= 10000.0:
         print(f"PASS: Max Q tracked ({sim.max_q_value})")
    else:
         print(f"FAIL: Max Q not tracked ({sim.max_q_value})")
         
    # 3. Test Apogee Event
    sim.rocket.status = "COAST"
    sim.state.y = PLANETS["Earth"].radius + 50000
    sim.state.vx = 1000
    sim.state.vy = -10 # Moving down
    sim.time = 20.0
    
    sim.step(0.1)
    
    has_apo = any(e['label'] == "APOGEE" for e in sim.events)
    if has_apo:
        print("PASS: APOGEE event recorded.")
    else:
        print("FAIL: APOGEE event missing.")
        
    print("Verification Complete.")

if __name__ == "__main__":
    verify_events()
