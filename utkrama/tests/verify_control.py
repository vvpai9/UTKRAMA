import numpy as np
import matplotlib.pyplot as plt
from src.core.simulation import Simulation

def verify_control():
    sim = Simulation()
    # Typical mission
    sim.initialize("Earth", 100, 50, 20000, 80000, "liquid") # High TWR to test control
    
    # Run
    times = []
    errors = []
    gimbals = []
    thetas = []
    targets = []
    
    # Run for 60 seconds (Ascent Phase)
    for _ in range(1200): # 1200 * 0.05 = 60s
        sim.step(0.05)
        if sim.rocket.status == "CRASHED": break
        
        times.append(sim.time)
        # Re-calculate error for plotting as it's not fully exposed in history every step
        # But we added it to history!
        
        # Let's just pull from rocket state
        gimbals.append(np.rad2deg(sim.rocket.engine.gimbal_angle))
        thetas.append(np.rad2deg(sim.rocket.orientation))
        
        # Target?
        # We need to peek at guidance output.
        # Re-run guidance logic for plotting:
        pos = sim.rocket.position
        vel = sim.rocket.velocity
        alt = np.linalg.norm(pos) - sim.planet.radius
        pitch = sim.guidance.get_steering_command(sim.rocket, alt, vel, sim.planet)
        target = 90 - np.rad2deg(pitch)
        targets.append(target)
        
        errors.append(target - np.rad2deg(sim.rocket.orientation))

    # Plot
    plt.figure(figsize=(10, 8))
    
    # 1. Attitude Tracking
    plt.subplot(2, 1, 1)
    plt.plot(times, targets, 'g--', label='Target Theta (deg)')
    plt.plot(times, thetas, 'b-', label='Actual Theta (deg)')
    plt.ylabel("Attitude (deg)")
    plt.title("Attitude Tracking Response")
    plt.legend()
    plt.grid(True)
    
    # 2. Control Effort & Error
    plt.subplot(2, 1, 2)
    plt.plot(times, gimbals, 'r-', label='Gimbal Angle (deg)')
    plt.plot(times, errors, 'k:', label='Tracking Error (deg)')
    plt.ylabel("Angle (deg)")
    plt.xlabel("Time (s)")
    plt.title("Control Effort & Error")
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig("control_verification.png")
    print("Verification plot saved to control_verification.png")

if __name__ == "__main__":
    verify_control()
