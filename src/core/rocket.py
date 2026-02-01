from dataclasses import dataclass
import numpy as np

@dataclass
class EngineState:
    running: bool = False
    throttle: float = 0.0 # 0.0 to 1.0

class Rocket:
    def __init__(self, dry_mass, fuel_mass, isp, max_thrust, propellant_type="liquid"):
        self.dry_mass = dry_mass
        self.fuel_mass = fuel_mass
        self.initial_fuel_mass = fuel_mass
        self.isp = isp
        self.max_thrust = max_thrust
        self.max_g = 5.0 # Max Gs allowed (structural/throttle limit)
        self.propellant_type = propellant_type # "liquid" or "solid"
        
        # State: [x, y, vx, vy, theta, dtheta]
        # x, y: position relative to planet center (2D)
        # vx, vy: velocity
        # theta: angle relative to vertical (or standard polar... let's say 0 is up from launch site?)
        # Actually simplest for planet-centric is [r, phi, vr, vphi, theta, omega]?
        # Or Cartesian [x, y, vx, vy] + [theta, omega]
        
        # Let's use Cartesian for physics, maybe polar for output.
        # Initial state will be set by simulation initialization.
        self.position = np.array([0.0, 0.0]) # x, y
        self.velocity = np.array([0.0, 0.0]) # vx, vy
        self.orientation = 0.0 # theta (radians), 0 = Vertical relative to local surface? 
                               # Or global angle? Let's use global angle logic in physics engine.
                               # But for guidance, "0 degrees pitch" usually means straight up.
        self.omega = 0.0 # Angular velocity

        self.engine = EngineState()
        
        self.stage = 1 # Single stage for now based on prompt implying simple params, 
                       # but "stages" could be simulated by mass drops if we want.

        self.status = "PRELAUNCH" # PRELAUNCH, THRUSTING, COAST, REENTRY, LANDED, CRASHED, ABORT

    @property
    def total_mass(self):
        return self.dry_mass + self.fuel_mass

    def thrust(self):
        if not self.engine.running:
            return 0.0
        # Check fuel
        if self.fuel_mass <= 0:
            self.engine.running = False
            return 0.0
            
        # Solid boosters often burn at fixed profile, but prompt asks for "propellant type".
        # We can assume solid = 100% throttle until empty, liquid = controllable.
        throttle = self.engine.throttle
        if self.propellant_type == "solid":
            throttle = 1.0 # Override
            
        return self.max_thrust * throttle

    def burn_fuel(self, dt):
        if not self.engine.running or self.fuel_mass <= 0:
             return
            
        thrust_force = self.thrust()
        # Mass flow rate: m_dot = F / (Isp * g0)
        # Use g0 = 9.80665 m/s^2 standard
        g0 = 9.80665
        dm = (thrust_force / (self.isp * g0)) * dt
        
        self.fuel_mass -= dm
        if self.fuel_mass < 0:
            self.fuel_mass = 0
            self.engine.running = False
            print("Engine Cutoff (Fuel Exhaustion)")

    def ignite_engine(self):
        self.engine.running = True
        self.engine.throttle = 1.0
    
    def cutoff_engine(self):
        self.engine.running = False
