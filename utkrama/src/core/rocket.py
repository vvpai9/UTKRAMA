from dataclasses import dataclass
import numpy as np

@dataclass
class Stage:
    """Represents a single rocket stage with its physical and propulsive properties.

    Attributes:
        dry_mass (float): The mass of the stage structure without fuel in kg.
        fuel_mass (float): The current mass of the fuel in kg.
        initial_fuel_mass (float): The initial mass of the fuel at launch in kg.
        vacuum_isp (float): Specific impulse in vacuum in seconds.
        vacuum_thrust (float): Maximum thrust in vacuum in Newtons.
        propellant_type (str): Type of propellant ('liquid' or 'solid').
        mass_flow_max (float): Maximum mass flow rate in kg/s (calculated).
        exit_pressure (float): Engine nozzle exit pressure in Pascals (calculated).
        nozzle_area (float): Area of the engine nozzle exit in m^2 (calculated).
        exhaust_velocity (float): Effective exhaust velocity in m/s (calculated).
    """
    dry_mass: float
    fuel_mass: float
    initial_fuel_mass: float
    vacuum_isp: float
    vacuum_thrust: float
    propellant_type: str
    
    # Engine Params
    mass_flow_max: float = 0.0
    exit_pressure: float = 0.0
    nozzle_area: float = 0.0
    exhaust_velocity: float = 0.0
    
    def __post_init__(self):
        # Calculate derived physics (moved from Rocket.__init__)
        g0 = 9.80665
        self.mass_flow_max = self.vacuum_thrust / (self.vacuum_isp * g0)
        
        if self.propellant_type == "liquid":
            self.exit_pressure = 60000.0
            loss_factor = 0.12
        else:
            self.exit_pressure = 80000.0
            loss_factor = 0.05
            
        self.nozzle_area = (loss_factor * self.vacuum_thrust) / 101325.0
        self.exhaust_velocity = (self.vacuum_thrust - self.exit_pressure * self.nozzle_area) / self.mass_flow_max

@dataclass
class EngineState:
    """Tracks the current operating state of the rocket engine.

    Attributes:
        running (bool): True if the engine is currently active/burning.
        throttle (float): Current throttle level from 0.0 to 1.0.
        gimbal_angle (float): Engine nozzle deflection angle in radians.
    """
    running: bool = False
    throttle: float = 0.0 # 0.0 to 1.0
    gimbal_angle: float = 0.0 # Radians, deflection from centerline


class Rocket:
    """Represents a multi-stage rocket vehicle.

    Manages the vehicle's physical state, stages, engine operation, and telemetry.
    Supports multi-stage configurations, though initialized as a single stage by default.

    Attributes:
        stages (list[Stage]): List of rocket stages.
        position (numpy.ndarray): Position vector [x, y] in meters relative to planet center.
        velocity (numpy.ndarray): Velocity vector [vx, vy] in m/s.
        orientation (float): Vehicle pitch angle/orientation in radians (0 is vertical?).
        omega (float): Angular velocity in rad/s.
        temperature (float): Current surface temperature in Kelvin.
        status (str): Current mission status (e.g., "PRELAUNCH", "THRUSTING").
    """
    def __init__(self, dry_mass, fuel_mass, isp, max_thrust, propellant_type="liquid", cop_offset=1.0):
        # Initial Single Stage logic (Backward Compatibility)
        stage1 = Stage(dry_mass, fuel_mass, fuel_mass, isp, max_thrust, propellant_type)
        
        self.stages = [stage1] # [Stage 1 (Bottom), Stage 2 (Top), ...]
        self.active_stage_index = 0
        
        self.cop_offset = cop_offset
        self.max_g = 5.0 
        
        # Dimensions
        self.length = 50.0 
        self.diameter = 3.7
        self.area = np.pi * (self.diameter / 2)**2 
        self.com_offset = self.length / 2.0 
        
        # Rocket State
        self.position = np.array([0.0, 0.0]) 
        self.velocity = np.array([0.0, 0.0]) 
        self.orientation = 0.0 
        self.omega = 0.0 
        
        self.temperature = 300.0 
        self.max_temperature = 2200.0
        self.max_g_load = 15.0
        self.max_angular_rate = 6.0
        
        self.engine = EngineState()
        self.gimbal_limit = np.deg2rad(5.0)
        
        self.stage = 1 # Display number
        self.status = "PRELAUNCH"
        self.has_ignited = False

        self.q = 0.0 
        self.mach = 0.0
        self.heat_flux = 0.0 
        self.g_load = 0.0

    @property
    def current_stage(self):
        if self.active_stage_index < len(self.stages):
            return self.stages[self.active_stage_index]
        return None

    @property
    def dry_mass(self):
        # Sum of current and upper stages
        if not self.current_stage: return 0.0
        return sum(s.dry_mass for s in self.stages[self.active_stage_index:])
        
    @property
    def fuel_mass(self):
        if not self.current_stage: return 0.0
        return sum(s.fuel_mass for s in self.stages[self.active_stage_index:])

    @fuel_mass.setter
    def fuel_mass(self, value):
        # Only set active stage fuel (Simplification for single stage compatibility)
        if self.current_stage:
            self.current_stage.fuel_mass = value

    @property
    def propellant_type(self):
        if self.current_stage: return self.current_stage.propellant_type
        return "liquid"

    @property
    def total_mass(self):
        return self.dry_mass + self.fuel_mass
        
        # Dimensions (Approximation for a medium lifter)
        # Length ~ 50m, Diameter ~ 3.7m (Falcon 9 ish)
        self.length = 50.0 
        self.diameter = 3.7
        self.area = np.pi * (self.diameter / 2)**2 # Frontal Reference Area
        
        # Center of Mass (Simple approx: Half length)
        # In reality, CoM moves as fuel burns.
        # Let's assume CoM is at L/2 roughly.
        self.com_offset = self.length / 2.0 
        
        # Rocket State
        self.position = np.array([0.0, 0.0]) 
        self.velocity = np.array([0.0, 0.0]) 
        self.orientation = 0.0 # Theta (rad), World Frame
        self.omega = 0.0 # Angular velocity (rad/s)
        
        self.temperature = 300.0 
        self.max_temperature = 2200.0 # K (Structural Limit for Advanced Materials)
        self.max_g_load = 15.0 # Max G (Structural Limit)
        self.max_angular_rate = 6.0 # rad/s (~340 deg/s) - Spin Limit
        
        self.engine = EngineState()
        self.gimbal_limit = np.deg2rad(5.0) # Max gimbal 5 degrees
        
        self.stage = 1
        self.status = "PRELAUNCH"
        self.has_ignited = False

        # Current telemetry
        self.q = 0.0 # Dynamic Pressure
        self.mach = 0.0
        self.heat_flux = 0.0 # W/m^2
        self.g_load = 0.0 # Current Axial Gs

    @property
    def total_mass(self):
        return self.dry_mass + self.fuel_mass

    @property
    def max_thrust(self):
        if self.current_stage:
             return self.current_stage.vacuum_thrust
        return 0.0

    @property
    def moment_of_inertia(self):
        # Cylindrical approximation: I = 1/12 * m * L^2
        # (Neglecting width term I = 1/4*m*r^2 + 1/12*ml^2, since L >> r)
        return (1.0/12.0) * self.total_mass * (self.length**2)

    def get_drag_coefficient(self, mach):
        """Calculates the drag coefficient (Cd) based on Mach number.

        Approximates the transonic drag rise and supersonic decay.

        Args:
            mach (float): The current Mach number of the vehicle.

        Returns:
            float: The drag coefficient.
        """
        # Piecewise Cd(Mach)
        # Subsonic: Costant ~ 0.3
        # Transonic (0.8 - 1.2): Rise to 0.7-0.9
        # Supersonic: Decay
        
        mach = abs(mach)
        
        if mach < 0.8:
            return 0.3
        elif mach < 1.05:
            # Linear rise to peak
            # 0.8 -> 0.3
            # 1.05 -> 0.9
            return 0.3 + (0.9 - 0.3) * (mach - 0.8) / (1.05 - 0.8)
        else:
            # Supersonic Decay: 1/sqrt(M^2 - 1) heuristic or simple exp decay
            # Decay from 0.9 down to 0.4 at Mach 5
            # Formula: 0.9 * (1 / M^0.5)? 
            # Let's use simplified decay
            return 0.4 + (0.9 - 0.4) * np.exp(-(mach - 1.05))

    def get_thrust(self, ambient_pressure):
        """Calculates the instantaneous thrust vector and mass flow rate.

        Computes thrust using the standard rocket thrust equation:
        F = m_dot * Ve + (Pe - Pa) * Ae

        Args:
            ambient_pressure (float): The local atmospheric pressure in Pascals.

        Returns:
            tuple[float, float]: A tuple containing:
                - total_thrust (float): The total thrust force in Newtons.
                - mass_flow (float): The current mass flow rate in kg/s.
        """
        if not self.engine.running or not self.current_stage or self.current_stage.fuel_mass <= 0:
            return 0.0, 0.0
            
        stage = self.current_stage
        throttle = self.engine.throttle
        if stage.propellant_type == "solid": throttle = 1.0
        
        m_dot = stage.mass_flow_max * throttle
        
        momentum_thrust = m_dot * stage.exhaust_velocity
        
        # Pressure thrust only exists if there is flow (engine running)
        pressure_thrust = 0.0
        if m_dot > 0:
            pressure_thrust = (stage.exit_pressure - ambient_pressure) * stage.nozzle_area
        
        total_thrust = momentum_thrust + pressure_thrust
        
        return total_thrust, m_dot

    # Deprecated/Wrapper for legacy calls (defaults to Vacuum)
    def thrust(self):
        t, _ = self.get_thrust(0.0)
        return t

    def burn_fuel(self, dt):
        """Consumes fuel based on current engine state and time step.

        Reduces the fuel mass of the current stage. Automatically shuts down the engine
        if fuel is depleted.

        Args:
            dt (float): The time step duration in seconds.
        """
        if not self.engine.running or not self.current_stage or self.current_stage.fuel_mass <= 0:
             return
            
        stage = self.current_stage
        
        # Re-calc thrust to get actual m_dot?
        # m_dot = F / (Isp * g0) is Approx. 
        # Using mass_flow_max * throttle is cleaner.
        throttle = self.engine.throttle
        if stage.propellant_type == "solid": throttle = 1.0
        
        dm = stage.mass_flow_max * throttle * dt
        
        stage.fuel_mass -= dm
        if stage.fuel_mass < 0:
            stage.fuel_mass = 0
            self.engine.running = False
            # Don't print, handle in simulation
    
    def separate_stage(self):
        """Separates the active stage and activates the next stage.

        Returns:
            float: The impulse velocity (delta-v) imparted by the separation mechanism (m/s).
                   Returns 0.0 if no further stages exist.
        """
        if self.active_stage_index >= len(self.stages) - 1:
            return 0.0 # No more stages
            
        old_stage = self.stages[self.active_stage_index]
        self.active_stage_index += 1
        new_stage = self.stages[self.active_stage_index]
        
        self.stage += 1
        self.engine.running = False # Reset engine
        self.has_ignited = False # Allow ignition of new stage
        
        # Calculate Jump
        # Simple separation kicker
        return 10.0 # m/s delta-v jump

    def ignite_engine(self):
        """Ignites the rocket engine of the current stage.

        For solid motors, prevents restart if previously ignited.
        """
        if self.propellant_type == "solid" and self.has_ignited:
             print("IGNITION FAILURE: Cannot restart Solid Rocket Motor")
             return
             
        self.engine.running = True
        self.engine.throttle = 1.0
        self.has_ignited = True
    
    def cutoff_engine(self):
        """Shuts down the rocket engine.

        For solid motors, shutdown may not be physically possible (acts as abstract destruct/abort).
        """
        if self.propellant_type == "solid":
             # Allow termination (Abort) but effectively engine is destroyed?
             pass
             
        self.engine.running = False
