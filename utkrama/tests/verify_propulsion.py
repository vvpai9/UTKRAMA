import numpy as np
import matplotlib.pyplot as plt
from src.core.rocket import Rocket
from src.core.physics import PLANETS

def verify_propulsion():
    # Setup standard rocket
    # Vacuum Thrust: 2MN, Isp: 350s
    rocket = Rocket(dry_mass=10000, fuel_mass=90000, isp=350, max_thrust=2000000, propellant_type="liquid")
    rocket.ignite_engine()
    
    planet = PLANETS['Earth']
    
    altitudes = np.linspace(0, 50000, 100) # 0 to 50km
    thrusts = []
    isps = []
    pressures = []
    
    for alt in altitudes:
        env = planet.query_environment(alt)
        thrust, m_dot = rocket.get_thrust(env.pressure)
        
        # Calculate Isp = F / (m_dot * g0)
        isp = thrust / (m_dot * 9.80665)
        
        thrusts.append(thrust / 1000.0) # kN
        isps.append(isp)
        pressures.append(env.pressure / 1000.0) # kPa
        
    # Plotting
    plt.figure(figsize=(12, 5))
    
    # Thrust vs Altitude
    plt.subplot(1, 2, 1)
    plt.plot(altitudes/1000, thrusts, 'b-', label='Thrust (kN)')
    plt.axhline(y=rocket.vacuum_thrust/1000.0, color='r', linestyle='--', label='Vacuum Thrust')
    plt.title("Thrust vs Altitude")
    plt.xlabel("Altitude (km)")
    plt.ylabel("Thrust (kN)")
    plt.grid(True)
    plt.legend()
    
    # Isp vs Altitude
    plt.subplot(1, 2, 2)
    plt.plot(altitudes/1000, isps, 'g-', label='Isp (s)')
    plt.axhline(y=rocket.vacuum_isp, color='r', linestyle='--', label='Vacuum Isp')
    plt.title("Isp vs Altitude")
    plt.xlabel("Altitude (km)")
    plt.ylabel("Specific Impulse (s)")
    plt.grid(True)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig("propulsion_verification.png")
    print("Verification plot saved to propulsion_verification.png")
    
    # Print some key points
    print(f"Sea Level: Thrust={thrusts[0]:.1f} kN (Loss: {100*(1-thrusts[0]/(rocket.vacuum_thrust/1000)):.1f}%), Isp={isps[0]:.1f} s")
    print(f"10 km:     Thrust={thrusts[20]:.1f} kN, Isp={isps[20]:.1f} s")
    print(f"Vacuum:    Thrust={rocket.vacuum_thrust/1000:.1f} kN, Isp={rocket.vacuum_isp:.1f} s")

if __name__ == "__main__":
    verify_propulsion()
