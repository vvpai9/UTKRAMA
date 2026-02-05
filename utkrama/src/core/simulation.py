import numpy as np
from dataclasses import dataclass
from src.core.physics import PLANETS, EnvironmentState
from src.core.rocket import Rocket
from src.core.guidance import GuidanceSystem
from src.core.utils import calculate_orbital_elements

@dataclass
class State:
    """Represents the complete physical state of the rocket at a point in time.

    Attributes:
        x (float): X-coordinate position relative to planet center (meters).
        y (float): Y-coordinate position relative to planet center (meters).
        vx (float): X-component of velocity (m/s).
        vy (float): Y-component of velocity (m/s).
        mass (float): Total mass of the vehicle (kg).
        temperature (float): Surface temperature (Kelvin).
        theta (float): Orientation angle relative to inertial frame (radians).
        omega (float): Angular velocity (rad/s).
    """
    x: float
    y: float
    vx: float
    vy: float
    mass: float
    temperature: float
    theta: float # Orientation (rad)
    omega: float # Angular velocity (rad/s)

    def to_array(self):
        """Converts the state to a numpy array for integration."""
        return np.array([self.x, self.y, self.vx, self.vy, self.mass, self.temperature, self.theta, self.omega])

    @staticmethod
    def from_array(arr):
        """Creates a State object from a numpy array."""
        return State(arr[0], arr[1], arr[2], arr[3], arr[4], arr[5], arr[6], arr[7])

class Simulation:
    """Manages the physics simulation, time stepping, and mission logic.

    Integrates the equations of motion using RK4, handles event detection (staging, landing),
    and logs telemetry data.

    Attributes:
        planet (Planet): The celestial body being simulated.
        rocket (Rocket): The vehicle being simulated.
        guidance (GuidanceSystem): The guidance logic controller.
        time (float): Current simulation time in seconds.
        dt (float): Simulation time step in seconds.
        history (dict): Dictionary storing time-series telemetry data.
        mission_outcome (str): Final status of the mission (e.g., "SUCCESS", "FAILED").
    """
    def __init__(self):
        self.planet = PLANETS['Earth']
        self.rocket = None
        self.guidance = None
        self.time = 0.0
        self.dt = 0.05 # Lower DT for stability with rigid body dynamics
        self.target_apoapsis = 0.0
        self.safety_margin = 0.0
        self.integration_method = "RK4"
        self._achieved_apoapsis = 0.0 # Track max altitude 
        
        # Telemetry History
        self.history = {
            'time': [],
            'altitude': [],
            'velocity': [],
            'velocity': [],
            'q': [],
            'mach': [],
            'heat_flux': [],
            'temperature': [],
            'g_load': [], # Fixed KeyError
            'gimbal': [],
            'theta': [],
            'apoapsis': [],
            'periapsis': [],
            'x': [],
            'y': [],
            'status': [] 
        }
        self.logger = None
        self._apoapsis_reached = False
        self.max_g_so_far = 0.0 # Track Max G for Display
        self.max_q_value = 0.0 # Track Max Q
        self.events = [] # List of {'label': str, 'time': float}
        self._events_triggered = set() # To avoid duplicates
        self.mission_outcome = None # REJECTED, ABORTED, FAILED, SUCCESS
        
    def set_logger(self, callback):
        self.logger = callback
        
    def log(self, msg):
        if self.logger:
            self.logger(msg)
            
    def initialize(self, planet_name, target_apo_km, safety_margin_km, dry_mass, fuel_mass, propellant_type):
        self.planet = PLANETS.get(planet_name, PLANETS['Earth'])
        self.target_apoapsis = target_apo_km * 1000 
        self.safety_margin = safety_margin_km * 1000
        self.max_g_so_far = 0.0 # Reset max G
        
        # Estimate Isp and Thrust 
        if propellant_type == "liquid":
            isp = 350
            thrust = 2000000 
        else:
            isp = 260
            # Solid Scaling Law
            # Thrust depends on Fuel Mass (burn area) and Burn Time
            # Assume characteristic burn time for this class of solids ~ 110s
            burn_time_target = 110.0 
            g0 = 9.80665
            # F = m_fuel * Isp * g0 / t_burn
            thrust = (fuel_mass * isp * g0) / burn_time_target
            
        self.rocket = Rocket(dry_mass, fuel_mass, isp, thrust, propellant_type)
        self.guidance = GuidanceSystem(self.target_apoapsis)
        self.time = 0.0
        self._achieved_apoapsis = 0.0
        
        self.rocket.position = np.array([0.0, self.planet.radius])
        self.rocket.velocity = np.array([0.0, 0.0]) 
        self.rocket.orientation = np.pi / 2 # 90 degrees = Vertical Up 
        self.rocket.omega = 0.0
        self.rocket.status = "PRELAUNCH"
    def check_feasibility(self, planet_name, target_apo_km, dry_mass, fuel_mass, propellant_type, safety_margin_km=0):
        """Analyzes mission feasibility based on physics constraints/delta-v.

        Estimates the required delta-v for the target orbit and compares it against
        the rocket's capabilities (Tsiolkovsky equation, TWR).

        Args:
            planet_name (str): Name of the target planet.
            target_apo_km (float): Desired apoapsis altitude in kilometers.
            dry_mass (float): Structure mass in kg.
            fuel_mass (float): Propellant mass in kg.
            propellant_type (str): 'liquid' or 'solid'.
            safety_margin_km (float): Extra altitude buffer in km.

        Returns:
            tuple: (is_feasible (bool), reason (str), rocket_dv (float), required_dv (float), extra_fuel_needed (float))
        """
        planet = PLANETS.get(planet_name, PLANETS['Earth'])
        target_r = planet.radius + target_apo_km * 1000
        
        # 1. Estimate Required Delta-V
        # V_orbit_target = sqrt(mu / r) (Standard circular orbit velocity)
        # Add Losses: Gravity + Drag + Steering 
        # Heuristic: Earth LEO ~9400 m/s.
        
        # Scaling Heuristic
        earth_leo_dv = 9400.0
        v_esc_planet = np.sqrt(2 * planet.mu / planet.radius)
        v_esc_earth = np.sqrt(2 * PLANETS['Earth'].mu / PLANETS['Earth'].radius)
        
        # Baseline scaling
        req_dv = earth_leo_dv * (v_esc_planet / v_esc_earth)
        
        # Adjust for specific altitude if significantly different from LEO (200km)
        # Not strictly accurate but suffices for "feasibility game".
        # If target < 400km, use ballistic/suborbital feasibility?
        
        # Losses based on atmosphere
        losses_est = 1500.0 * (planet.surface_pressure / 101325.0) 
        if losses_est < 100: losses_est = 100 
        
        # Determine Feasibility
        is_feasible = True
        extra_fuel = 0.0
        
        # ... logic ...
        # If not feasible, return REJECTED? 
        # The caller handles the 'REJECTED' string usually, but we can store it?
        # Let's just keep this calculating physics.
        
        if target_apo_km < 400: # Suborbital/Low Orbit
             # Vis-viva approximation for suborbital peak
             # 1/2 v^2 - mu/R = -mu/R_target
             v_ballistic = np.sqrt(2 * planet.mu * (1/planet.radius - 1/target_r))
             req_dv = v_ballistic + losses_est * 0.8 # Less losses for vertical hop
        else:
             # Orbital
             v_circ_surf = np.sqrt(planet.mu / planet.radius)
             req_dv = v_circ_surf * 1.1 + losses_est
        
        # 2. Calculate Rocket Delta V & Physics Constraints
        # Instantiate a temporary rocket to get physics parameters (thrust, flow, etc)
        # Assuming defaults for Isp/Thrust based on Propellant Type
        if propellant_type == "liquid":
             isp = 350
             thrust = 2000000
        else:
             isp = 260
             # Solid Scaling Law
             burn_time_target = 110.0
             g0 = 9.80665
             thrust = (fuel_mass * isp * g0) / burn_time_target
             
             # Solid Constraints (Checked Here)
             # Max Fuel Mass
             if fuel_mass > 500000:
                 reason = "Invalid solid motor configuration (Mass > 500t)"
                 print(f"REJECT: {reason}")
                 return False, reason, 0, 0, 0


             
        # Calculate derived physics
        g0 = 9.80665
        initial_mass = dry_mass + fuel_mass
        weight = initial_mass * g0
        
        # TWR
        twr = thrust / weight
        
        # Burn Time
        # m_dot = F / (Isp * g0)
        m_dot = thrust / (isp * g0)
        burn_time = fuel_mass / m_dot
        
        
        # Physics Penalties & Hard Limits for Feasibility
        
        if twr < 1.1:
             is_feasible = False
             reason = f"TWR too low ({twr:.2f} < 1.1)"
             return False, reason, 0, 0, 0 # Return tuple immediately? Or set outcome?
             # Caller logic doesn't support setting outcome here directly, returns bool.
             
        # 2. Burn Time Check (REMOVED per user request)

        # 3. Mass Ratio Check (Structural/Efficiency limits)
        # Ratio = Total / Dry
        mass_ratio = initial_mass / dry_mass
        if mass_ratio < 1.1: # Mostly dry mass?
             print(f"WARNING: Mass Ratio too low ({mass_ratio:.2f} < 1.1)")
        
        if propellant_type == "liquid":
             if mass_ratio > 30.0: # Balloon tank? Too fragile?
                  print(f"WARNING: Mass Ratio high for liquid ({mass_ratio:.2f} > 30)")
        else:
             # Solid Ratio Constraint
             if mass_ratio > 15.0:
                  print(f"WARNING: Invalid solid motor configuration (Mass Ratio {mass_ratio:.1f} > 15)")
                  
        # Burn Time Check (Max) for Solids
        if propellant_type == "solid" and burn_time > 150.0:
             print(f"WARNING: Invalid solid motor configuration (Burn Time {burn_time:.1f}s > 150s)")

        # 4. Delta-V Check
        rocket_dv = isp * g0 * np.log(initial_mass / dry_mass) # Tsiolkovsky
        
        # Penalties for Drag/Gravity
        drag_penalty_factor = 1.0
        gravity_penalty_factor = 1.0

        if twr > 8.0:
            drag_penalty_factor = 2.0 # Fast acceleration low down = high drag
        elif twr < 1.3:
            gravity_penalty_factor = 1.3 # Slow ascent = high gravity losses
            
        req_dv *= drag_penalty_factor * gravity_penalty_factor
        
        if rocket_dv < req_dv:
             is_feasible = False
             reason = f"Insufficient Delta-V (Rocket: {rocket_dv:.0f} < Req: {req_dv:.0f})"
             # Calculate extra fuel needed to meet req_dv
             # m_final = dry_mass
             # m_initial_required = m_final * exp(req_dv / (isp * g0))
             # required_fuel = m_initial_required - dry_mass
             # extra_fuel = required_fuel - fuel_mass
             required_total_mass = dry_mass * np.exp(req_dv / (isp * g0))
             extra_fuel = required_total_mass - initial_mass
             return False, reason, rocket_dv, req_dv, extra_fuel
             
        return is_feasible, None, rocket_dv, req_dv, extra_fuel

    def compute_forces(self, state: State, t: float):
        """Calculates the net forces and state derivatives for the rocket.

        Computes gravity, aerodynamic drag (blunt body + rocket), thrust (pressure adjusted),
        aerodynamic stability torque, and RCS/gimbal control torque.

        Args:
            state (State): The current physical state of the vehicle.
            t (float): Current simulation time.

        Returns:
            tuple: (state_derivative (numpy.ndarray), g_load (float))
                   state_derivative contains [vx, vy, ax, ay, dm/dt, dT/dt, omega, alpha].
        """
        # 1. Environment
        r_mag = np.sqrt(state.x**2 + state.y**2)
        altitude = r_mag - self.planet.radius
        env = self.planet.query_environment(altitude, t)
        
        # 2. Gravity
        if r_mag > 1e-6:
            r_hat = np.array([state.x, state.y]) / r_mag
        else:
            r_hat = np.array([0.0, 1.0])
            
        gravity_acc = -env.gravity * r_hat
        
        # 3. Aerodynamics
        v_vec = np.array([state.vx, state.vy])
        v_mag = np.linalg.norm(v_vec)
        
        mach = 0.0
        if env.speed_of_sound > 0:
            mach = v_mag / env.speed_of_sound
            
        if v_mag > 0:
            v_hat = v_vec / v_mag
        else:
            v_hat = np.array([0.0, 1.0])
            
        # Cd from Rocket (Mach dependent)
        # Use simple Cd area if area not in Rocket? Rocket has self.area now.
        cd = self.rocket.get_drag_coefficient(mach)
        
        # --- Blunt Body Logic ---
        # If angle of attack is high (flying backwards/sideways), Cd increases.
        # AoA = Angle between Velocity and Orientation
        # If flying retrograde (AoA ~ 180), we expose engine bells/base (Blunt body).
        # Cd for blunt cylinder/base ~ 0.8 - 1.2
        if v_mag > 1.0:
            flight_angle = np.arctan2(state.vy, state.vx)
            aoa = abs(state.theta - flight_angle)
            aoa = (aoa + np.pi) % (2 * np.pi) - np.pi # Normalize
            aoa = abs(aoa)
            
            # If AoA > 90 degrees (90 to 270), we are flying tail-firstish
            if aoa > np.deg2rad(90):
                 # Blend to blunt Cd
                 # Simple heuristic: Max(Cd_aero, 1.2)
                 cd = max(cd, 1.2)
        
        # Area: Rocket now has dimensions.
        area = self.rocket.area 
        
        # Parachute Overrides (Dynamic Sizing for Target Terminal Velocity)
        rho = env.density
        if self.rocket.status in ["DROGUE_CHUTE", "MAIN_CHUTE"]:
            # Target Terminal Velocity
            vt = 30.0 if self.rocket.status == "DROGUE_CHUTE" else 5.0
            
            # Allow settling?
            # F_drag = Weight at terminal velocity
            # 0.5 * rho * vt^2 * Cd * A = m * g
            # Cd * A = (2 * m * g) / (rho * vt^2)
            
            g_local = env.gravity
            rho_safe = max(rho, 0.01) # Avoid divide by zero
            
            required_CdA = (2.0 * state.mass * g_local) / (rho_safe * vt**2)
            
            # Use fixed Cd, solve for Area
            cd = 1.0
            area = required_CdA
            
            # Clamp Area to avoid infinite deployment in vacuum
            # But realistically chutes don't work in vacuum.
            # So if rho is low, required area is huge. 
            # Let's cap area to something physical max (e.g. 5000 m^2) to simulate "not enough air yet"
            area = min(area, 10000.0) 
            
            area = min(area, 10000.0) 
            
        q = 0.5 * rho * v_mag**2
        
        q = 0.5 * rho * v_mag**2
        
        drag_force_mag = q * cd * area
        
        # --- Strict Physics Fix for Drag ---
        # Apply exactly opposite to velocity vector
        if v_mag > 1e-6:
            ux = v_vec[0] / v_mag
            uy = v_vec[1] / v_mag
            
            Fx_drag = -drag_force_mag * ux
            Fy_drag = -drag_force_mag * uy
            
            drag_force = np.array([Fx_drag, Fy_drag])
        else:
            drag_force = np.zeros(2)
            
        drag_acc = drag_force / state.mass
        
        # --- Aerodynamic Torque ---
        
        if v_mag > 0.1:
            gamma = np.arctan2(state.vy, state.vx)
            alpha = state.theta - gamma
            
            # Drag acts opposite to velocity.
            # If CoP is AHEAD (positive offset), Drag pushes nose further away -> Unstable.
            # Torque = F_drag * offset * sin(alpha)
            # Check signs:
            # F_drag magnitude is positive.
            # If alpha > 0 (theta > gamma), nose is "left" of velocity.
            # Drag pushes "right" (relative to CoM)?
            # Wait.
            # Velocity: Up. Drag: Down.
            # Rocket: Tilted Left (Theta > Gamma).
            # CoP Ahead: Drag (Down) at Nose (Left).
            # Force Down on Left Nose -> Rotates CCW (Positive Torque).
            # So Positive Torque increases Theta -> Increases Alpha. Unstable.
            # Logic holds: Tau = F_drag * offset * sin(alpha)
            
            aero_torque = drag_force_mag * self.rocket.cop_offset * np.sin(alpha)
        else:
            aero_torque = 0.0
            
        # 4. Thrust & Torque
        thrust_acc = np.zeros(2)
        dm_dt = 0.0
        torque = 0.0
        
        if self.rocket.engine.running and state.mass > self.rocket.dry_mass:
            throttle = self.rocket.engine.throttle
            if self.rocket.propellant_type == "solid": throttle = 1.0
            
            # New Propulsion Model
            # ambient pressure needed
            thrust_force_mag, mass_flow_rate = self.rocket.get_thrust(env.pressure)
            
            # Instantaneous ISP calculation for telemetry logging if needed
            # Isp = F / (m_dot * g0)
            current_isp = 0.0
            if mass_flow_rate > 0:
                current_isp = thrust_force_mag / (mass_flow_rate * 9.80665)
                # We could log this if we had a field.
            
            # Thrust Direction
            # Rocket Orientation (Theta) + Gimbal Angle (Delta)
            theta = state.theta
            delta = self.rocket.engine.gimbal_angle
            
            # Effective Thrust Angle
            thrust_angle = theta + delta
            
            # Thrust Vector (Standard Polar: cos, sin). 
            thrust_dir = np.array([np.cos(theta + delta), np.sin(theta + delta)])
            thrust_acc = thrust_dir * (thrust_force_mag / state.mass)
            
            # Torque
            # L_arm approx half length (CoM to Engine)
            l_arm = self.rocket.length / 2.0
            torque = thrust_force_mag * np.sin(delta) * l_arm
            
            # Mass Flow
            # dm_dt is negative
            dm_dt = -mass_flow_rate
        else:
            # --- RCS LOGIC (Reaction Control System) ---
            # If engine is off, we still need torque for orientation (Retrograde turn).
            # Use gimbal_angle (delta) as the steering command.
            # Max Gimbal (5 deg) maps to Max RCS Torque.
            
            delta = self.rocket.engine.gimbal_angle
            gimbal_limit = self.rocket.gimbal_limit
            
            # Normalized Command (-1.0 to 1.0)
            cmd = max(-1.0, min(1.0, delta / gimbal_limit)) if gimbal_limit > 0 else 0
            
            # RCS Torque Max
            # Assume sufficient authority: 50 kNm?
            # 50 Ton rocket, 50m long. I ~ 1/12 * 50000 * 2500 ~ 1e7.
            # Alpha = Torque / I.
            # Want 1 deg/s^2 alpha? ~ 0.017 rad/s^2.
            # Torque = I * alpha = 1e7 * 0.017 ~ 170,000.
            # Let's say 200 kNm.
            max_rcs_torque = 200000.0
            
            torque = max_rcs_torque * cmd
            
        # 5. Angular Damping (Stabilize vacuum spin)
        # Tau_damping = -c * omega
        # c needs to be tuned.
        # Large enough to stop spin, small enough not to feel viscous.
        c_damping = 100000.0 if self.rocket.status != "CRASHED" else 0.0
        # Reduce damping in atmosphere if Aero interactions dominate (not simulated yet)?
        # Or Just constant small damping.
        # vacuum damping is "fake" but needed.
        if rho > 0.01:
             c_damping = 1000000.0 # More damping in air (simplified aero damping)
             
        torque -= c_damping * state.omega
        torque += aero_torque
        
        # 6. Heating
        # Q_dot = k * sqrt(rho) * v^3
        # Simple Model
        if env.density > 0:
             k_heat = 1.8e-4 
             # Flux [W/m^2]
             q_flux = k_heat * np.sqrt(env.density) * (v_mag**3)
        else:
             q_flux = 0.0
             
        # Radiative Cooling
        # P_rad = epsilon * sigma * T^4
        sigma = 5.67e-8
        epsilon = 0.85
        t_curr = state.temperature
        q_rad = epsilon * sigma * (t_curr**4 - env.temperature**4)
        
        # Net Flux
        q_net = q_flux - q_rad
        
        # Thermal Mass
        # Assume skin mass is fraction of dry mass? Or fixed?
        # Let's say effective thermal mass is 200 kg of Aluminum (Cp ~ 900 J/kgK)
        # Area? Assume flux applies to frontal area?
        # Power = q_net * Area
        # dT/dt = Power / (m * Cp)
        
        area_heat = self.rocket.area # Frontal
        m_thermal = 200.0 
        cp = 1000.0
        
        dT_dt = (q_net * area_heat) / (m_thermal * cp)
        
        # Log Flux for telemetry (Hack: Store in rocket momentarily or just rely on state.temperature integration)
        # We can't easily set rocket.heat_flux here as 'compute_forces' is pure function of state usually.
        # But for history tracking, we need it.
        # We'll calculate it in 'step' again for logging?
        
        dT_dt = (q_net * area_heat) / (m_thermal * cp)
        
        total_acc = gravity_acc + drag_acc + thrust_acc
        
        # Calculate G-Load (Thrust + Drag + Lift if we had it) / g0 / Mass
        # Actually F_felt = F_contact + F_aero.
        # F_contact = Thrust.
        # F_aero = Drag.
        # G = |F_thrust + F_drag| / (mass * 9.80665)
        
        f_aero = drag_force
        f_thrust = thrust_acc * state.mass
        f_total_non_grav = f_aero + f_thrust
        g_load = np.linalg.norm(f_total_non_grav) / (state.mass * 9.80665)
        
        # Store in state derivative? No.
        
        # Moment of Inertia
        # I = mass * ... (Re-calculate based on current mass?)
        # Rocket property uses total_mass, but here we have state.mass
        I = (1.0/12.0) * state.mass * (self.rocket.length**2)
        alpha = torque / I
        
        # Return Derivative AND Telemetry
        # We return a tuple? But solvers expect array.
        # We need a way to get telemetry out.
        # Let's attach it to the instance momentarily if this is the "main" step?
        # NO, RK4 calls this multiple times.
        
        return np.array([state.vx, state.vy, total_acc[0], total_acc[1], dm_dt, dT_dt, state.omega, alpha]), g_load

    def get_state_derivative(self, t, state_arr):
        state = State.from_array(state_arr)
        deriv, _ = self.compute_forces(state, t)
        return deriv
        
    def get_physics_state(self, t, state_arr):
        """Helper to get full physics context for current state."""
        state = State.from_array(state_arr)
        return self.compute_forces(state, t)

    def rk4_step(self, dt):
        """Advances the simulation state by `dt` seconds using the Runge-Kutta 4 method.

        Args:
            dt (float): Time step in seconds.
        """
        y = self.current_state_y()
        t = self.time
        
        k1 = self.get_state_derivative(t, y)
        k2 = self.get_state_derivative(t + 0.5*dt, y + 0.5*dt*k1)
        k3 = self.get_state_derivative(t + 0.5*dt, y + 0.5*dt*k2)
        k4 = self.get_state_derivative(t + dt, y + dt*k3)
        
        y_next = y + (dt/6.0) * (k1 + 2*k2 + 2*k3 + k4)
        
        self.apply_state(y_next)

    def current_state_y(self):
        return np.array([
            self.rocket.position[0], self.rocket.position[1],
            self.rocket.velocity[0], self.rocket.velocity[1],
            self.rocket.total_mass, self.rocket.temperature,
            self.rocket.orientation, self.rocket.omega
        ])
    
    def apply_state(self, y):
        self.rocket.position = y[0:2]
        self.rocket.velocity = y[2:4]
        
        # Mass extract
        new_mass = y[4]
        fuel = new_mass - self.rocket.dry_mass
        if fuel < 0: fuel = 0
        self.rocket.fuel_mass = fuel
        
        self.rocket.temperature = y[5]
        self.rocket.orientation = y[6]
        self.rocket.omega = y[7]
        
        if self.rocket.fuel_mass <= 0 and self.rocket.engine.running:
             self.rocket.cutoff_engine()

    def step(self, dt):
        """Executes one full simulation cycle.

        Includes guidance updates, control loop execution (PID), state integration,
        event handling (MECO, staging), and telemetry recording.

        Args:
            dt (float): Time step in seconds.
        """
        if self.rocket.status in ["CRASHED", "LANDED", "ABORT"]:
            return

        # --- Guidance & Control (PID) ---
        # 1. Get Target Orientation from Guidance
        pos = self.rocket.position
        vel = self.rocket.velocity
        r_mag = np.linalg.norm(pos)
        altitude = r_mag - self.planet.radius
        
        # Calculate Environment for Telemetry
        env = self.planet.query_environment(altitude, self.time)
        v_mag = np.linalg.norm(vel)
        speed_of_sound = env.speed_of_sound if env.speed_of_sound > 0 else 343.0
        self.rocket.mach = v_mag / speed_of_sound
        self.rocket.mach = v_mag / speed_of_sound
        self.rocket.q = 0.5 * env.density * v_mag**2
        
        # Heating Telemetry (Recalculate for logging)
        k_heat = 1.8e-4
        if env.density > 0:
             self.rocket.heat_flux = k_heat * np.sqrt(env.density) * (v_mag**3)
        else:
             self.rocket.heat_flux = 0.0
             
        # Recalculate G-Load for Telemetry Checking
        # We can call 'get_physics_state' with current state
        # But that's expensive re-calculation.
        # Alternatively, assume last step?
        # Let's re-calc to be safe and accurate.
        current_y = self.current_state_y()
        _, g_load = self.get_physics_state(self.time, current_y)
        self.rocket.g_load = g_load
             
        # Structural Checks
        if self.rocket.temperature > self.rocket.max_temperature:
             self.rocket.status = "CRASHED"
             self.mission_outcome = "FAILED"
             self.log(f"Outcome: FAILED (Structural Failure - Overheat: {self.rocket.temperature:.0f}K)")
             return
             
        if self.rocket.g_load > self.rocket.max_g_load:
             self.rocket.status = "CRASHED"
             self.mission_outcome = "FAILED"
             self.log(f"Outcome: FAILED (Structural Failure - G-Force Limit: {self.rocket.g_load:.1f}G)")
             return
             
        if abs(self.rocket.omega) > self.rocket.max_angular_rate:
             self.rocket.status = "CRASHED"
             self.mission_outcome = "FAILED"
             self.log(f"Outcome: FAILED (Structural Failure - Spin Limit: {abs(self.rocket.omega):.1f} rad/s)")
             return
             
             self.rocket.status = "THRUSTING"
             self.rocket.ignite_engine()

        target_pitch = 0.0 # From Vertical
        if self.rocket.status == "THRUSTING":
             # Staging Check
             if self.rocket.current_stage and self.rocket.current_stage.fuel_mass <= 1.0: # Almost empty
                 if self.rocket.active_stage_index < len(self.rocket.stages) - 1:
                     # Perform Separation
                     self.log(f"MECO Stage {self.rocket.stage}. Separating...")
                     
                     # 1. Physics Jump
                     # Add Impulse to Velocity (Instantaneous)
                     dv_jump = self.rocket.separate_stage()
                     
                     # Apply along current orientation (approximate)
                     # Or drag-aligned? Orientation is best guess.
                     theta = self.rocket.orientation
                     jump_vec = np.array([np.cos(theta), np.sin(theta)]) * dv_jump
                     self.rocket.velocity += jump_vec
                     
                     self.log(f"Staging Event: Alt={altitude/1000.0:.1f}km, Velocity Jump={dv_jump:.1f}m/s")
                     
                     # 2. Ignite Next Stage
                     self.rocket.ignite_engine()
                     self.log(f"Stage {self.rocket.stage} Ignition Confirmed.")
                     
                     # 3. Update Guidance? (User Requirement)
                     # Maybe relax limits or change target?
                     # For now, just logging stability.

             # Ground Check (Clamp)
             if altitude <= 0.1 and vel[1] <= 0.1:
                  self.rocket.position = (pos / r_mag) * self.planet.radius
                  self.rocket.velocity = np.zeros(2)
                  # If we have enough
             
             # Max Q Tracking
             if self.rocket.q > self.max_q_value:
                  self.max_q_value = self.rocket.q

             pitch_from_vertical = self.guidance.get_steering_command(self.rocket, altitude, vel, self.planet)
             # Convert to World Theta (0=Horizontal Right, 90=Vertical Up)
             # Guidance: 0=Up.
             target_theta = np.pi/2 - pitch_from_vertical
             
             # PID Control for Gimbal (PD Control with Actuator Dynamics)
             # ----------------------------------------------------------
             # 1. Control Law: u = Kp * e - Kd * e_dot
             # Target: theta_cmd
             # Current: theta, omega
             
             Kp = 5.0 # Proportional Gain (Stiffness)
             Kd = 2.0 # Derivative Gain (Damping) - Increased for stability
             
             theta_error = target_theta - self.rocket.orientation
             # Normalize angle error (-pi to pi) if needed, but here flight is likely constrained.
             
             # Command (Ideal Gimbal Angle)
             # Note: Gimbal Angle Delta produces Torque.
             # Positive Delta -> Positive Torque (CCW)?
             # Check Compute Forces: torque = F * sin(delta) * L.
             # If Error > 0 (Target > Current), we want +Omega (CCW).
             # So we want +Torque. So we want +Delta.
             
             cmd_delta = Kp * theta_error - Kd * self.rocket.omega
             
             # 2. Actuator Dynamics (Rate Limiting)
             # Simulates the hydraulic/electric gimbal actuators.
             # delta_new = clamp(delta_prev + delta_dot * dt)
             
             max_slew_rate = np.deg2rad(10.0) # 10 deg/s limit
             current_delta = self.rocket.engine.gimbal_angle
             
             # Desired change
             delta_diff = cmd_delta - current_delta
             
             # Limit change per step
             max_change = max_slew_rate * dt
             delta_change = max(-max_change, min(max_change, delta_diff))
             
             new_delta = current_delta + delta_change
             
             # 3. Position Limiting (Mechanical Stops)
             limit = self.rocket.gimbal_limit
             self.rocket.engine.gimbal_angle = max(-limit, min(limit, new_delta))
             
             # Telemetry for Control
             if int(self.time * 20) % 5 == 0:
                  pass # Already logging theta and gimbal. Error would be nice.
                  # Let's add 'error' to history?
                  self.history.setdefault('theta_error', []).append(theta_error)
             
             # MECO Logic (Main Engine Cut Off)
             if self.rocket.propellant_type == "liquid":
                 ra, _ = calculate_orbital_elements(pos, vel, self.planet.mu)
                 current_apo = ra - self.planet.radius
                 if current_apo >= (self.target_apoapsis + self.safety_margin):
                     self.rocket.cutoff_engine()
                     self.rocket.status = "COAST"
                     if self.guidance.log_callback: 
                         self.guidance.log_callback(f"MECO at {altitude/1000:.1f}km. Apo: {current_apo/1000:.1f}km")
             
        elif self.rocket.status == "RETRO_BRAKE":
             # Retro Logic (Thrust Vectoring for landing)
             # Point Retrograde
             if v_mag > 1:
                 retro_angle = np.arctan2(vel[1], vel[0]) + np.pi
                 if (abs(vel[0]) < 1 and vel[1] < 0) or altitude < 100: retro_angle = np.pi/2
             else:
                 retro_angle = np.pi/2
                 
             # Normalize angle to -pi, pi for shortest turn
             # error = target - current
             error = retro_angle - self.rocket.orientation
             error = (error + np.pi) % (2 * np.pi) - np.pi
             
             kp = 5.0
             kd = 10.0
             gimbal = kp * error - kd * self.rocket.omega
             limit = self.rocket.gimbal_limit
             self.rocket.engine.gimbal_angle = max(-limit, min(limit, gimbal))
             
             # Throttle Logic (Reuse stored logic or adapt)
             self._handle_retro_throttle(v_mag, altitude)
             
        elif self.rocket.status == "COAST":
             ra, _ = calculate_orbital_elements(pos, vel, self.planet.mu)
             
             # Drag Compensation (Restart if dipping)
             if self.rocket.propellant_type == "liquid" and (ra - self.planet.radius) < self.target_apoapsis and self.rocket.fuel_mass > 0:
                 self.rocket.status = "THRUSTING"
                 self.rocket.ignite_engine()
                 if self.guidance.log_callback:
                      self.guidance.log_callback(f"Drag Comp Restart. Ap={ra/1000 - self.planet.radius/1000:.1f} km")

             # --- Coast Orientation Logic ---
             # Ascent (Vy > 0) -> Prograde
             # Descent (Vy < 0) -> Retrograde
             # Allow RCS to orient
             
             flight_angle = np.arctan2(vel[1], vel[0])
             if vel[1] >= 0:
                 target_theta = flight_angle # Prograde
             else:
                 target_theta = flight_angle + np.pi # Retrograde
                 
             # Normalize Error
             error = target_theta - self.rocket.orientation
             error = (error + np.pi) % (2 * np.pi) - np.pi
             
             kp = 5.0
             kd = 10.0
             gimbal = kp * error - kd * self.rocket.omega
             
             limit = self.rocket.gimbal_limit
             # Apply to gimbal (which drives RCS in coast)
             self.rocket.engine.gimbal_angle = max(-limit, min(limit, gimbal))

             # Init Retro Brake
             # Check for descent
             radial_v = np.dot(vel, pos/r_mag)
             # Logic: descending, low enough (starts high for orientation), fast enough
             # User said Phase 1 Ballistic starts above 15km.
             if altitude < 100000 and v_mag > 50 and radial_v < -10 and self.rocket.propellant_type == "liquid":
                  self.rocket.status = "RETRO_BRAKE"
                  # self.rocket.cutoff_engine() # Start cold
                  if self.guidance.log_callback: self.guidance.log_callback("RE-ENTRY PHASE STARTED (Ballistic alignment)")

        # Recovery Logic
        if altitude < 10000 and vel[1] < -1.0:
            self._handle_recovery(altitude, v_mag)

        # 2. Integrate
        self.rk4_step(dt)
        self.time += dt
        
        # 3. Post Checks (Crash, Recovery)
        altitude = np.linalg.norm(self.rocket.position) - self.planet.radius
        if altitude < 0:
            # Check impact speed
            iv_mag = np.linalg.norm(self.rocket.velocity)
            if iv_mag > 10.0:
                 self.rocket.status = "CRASHED"
                 self.rocket.position = (self.rocket.position / np.linalg.norm(self.rocket.position)) * self.planet.radius
            else:
                 # Soft / Pad contact
                 self.rocket.status = "LANDED" if self.time > 10.0 else self.rocket.status # Keep status if just starting
                 self.rocket.position = (self.rocket.position / np.linalg.norm(self.rocket.position)) * self.planet.radius
                 self.rocket.position = (self.rocket.position / np.linalg.norm(self.rocket.position)) * self.planet.radius
                 self.rocket.velocity = np.zeros(2)

        # Track Achieved Apoapsis
        if altitude > self._achieved_apoapsis:
             self._achieved_apoapsis = altitude

        # History
        if int(self.time * 20) % 5 == 0:
             self.history['time'].append(self.time)
             self.history['altitude'].append(altitude)
             self.history['velocity'].append(np.linalg.norm(self.rocket.velocity))
             self.history['q'].append(self.rocket.q)
             self.history['mach'].append(self.rocket.mach)
             self.history['heat_flux'].append(self.rocket.heat_flux)
             self.history['temperature'].append(self.rocket.temperature)
             self.history['temperature'].append(self.rocket.temperature)
             self.history['g_load'].append(self.rocket.g_load)
             self.history['gimbal'].append(self.rocket.engine.gimbal_angle)
             
             # Track Max G
             if self.rocket.g_load > self.max_g_so_far:
                 self.max_g_so_far = self.rocket.g_load
             self.history['theta'].append(self.rocket.orientation)
             
             # Orbital Elements
             ra, rp = calculate_orbital_elements(pos, vel, self.planet.mu)
             self.history['apoapsis'].append(ra - self.planet.radius)
             self.history['periapsis'].append(rp - self.planet.radius)
             
             # Event Check: Reached Apoapsis?
             # On Spherical planet, check Radial Velocity crossing 0 (from positive to negative)
             # velocity[1] < 0 is only valid at x=0.
             radial_v = np.dot(vel, pos/np.linalg.norm(pos)) if np.linalg.norm(pos) > 0 else vel[1]
             
             if self.rocket.status not in ["PRELAUNCH", "CRASHED", "LANDED"] and not self._apoapsis_reached:
                 if radial_v < 0 and self.time > 10.0: # Check radial V, ensure launched
                     self._apoapsis_reached = True
                     self._record_event("APOGEE")
                     alt_km = (np.linalg.norm(self.rocket.position) - self.planet.radius) / 1000.0
                     self.log(f"APOAPSIS REACHED at {alt_km:.2f} km")

             # Trajectory Data
             self.history['x'].append(self.rocket.position[0])
             self.history['y'].append(self.rocket.position[1])
             self.history['status'].append(self.rocket.status)

    def _handle_recovery(self, altitude, v_mag):
        if not self.planet.has_atmosphere: return
        
        if altitude < 3000:
             if self.rocket.status not in ["MAIN_CHUTE", "CRASHED", "LANDED"]:
                 self.rocket.status = "MAIN_CHUTE"
                 self.rocket.cutoff_engine()
                 if self.guidance.log_callback: self.guidance.log_callback(f"[REENTRY] MAIN CHUTE DEPLOYED @ {altitude:.0f}m")
                 # Force Orientation Up for chute visual
                 self.rocket.orientation = np.pi/2
                 self.rocket.omega = 0.0 # Kill rotation
        elif altitude < 10000: # Changed from 8000 to 10000 per user request
             if self.rocket.status not in ["DROGUE_CHUTE", "MAIN_CHUTE", "CRASHED", "LANDED"]:
                 self.rocket.status = "DROGUE_CHUTE"
                 self.rocket.cutoff_engine()
                 if self.guidance.log_callback: self.guidance.log_callback(f"[REENTRY] DROGUE CHUTE DEPLOYED @ {altitude:.0f}m")
                 self.rocket.orientation = np.pi/2
                 self.rocket.omega = 0.0

    def _handle_retro_throttle(self, v_mag, altitude):
        g = self.planet.get_gravity(self.planet.radius)
        
        if self.planet.has_atmosphere:
            # New Atmosphere Logic
            # Phase 1: Ballistic (> 15km) -> Throttle 0
            # Phase 2: Retro Braking (10km - 15km) -> Target 50 m/s
            
            if altitude > 15000:
                # Phase 1
                if self.rocket.engine.running:
                    self.rocket.cutoff_engine()
            elif altitude > 10000:
                # Phase 2: Atmospheric Retro Braking
                target_v = 50.0
                
                # Check for Start of phase logging
                if not self.rocket.engine.running:
                     self.rocket.ignite_engine()
                     if self.guidance.log_callback: 
                         self.guidance.log_callback(f"[REENTRY] Retro braking initiated at h = {altitude/1000:.1f} km, v = {v_mag:.0f} m/s")
                
                # Control Law: speed_error = v - 50
                # throttle = clamp(K * speed_error, 0, 1)
                error = v_mag - target_v
                
                if error > 0:
                     K = 0.02 # Gain TBD
                     cmd = K * error
                     self.rocket.engine.throttle = max(0.0, min(1.0, cmd))
                else:
                     # Cutoff if slow enough? User said "Engines cutoff when v <= 50"
                     self.rocket.cutoff_engine()
                     if self.guidance.log_callback:
                          self.guidance.log_callback(f"[REENTRY] Retro cutoff at v = {v_mag:.1f} m/s")
            else:
                 # Below 10km (Handled by Chutes usually, but if chute failed?)
                 self.rocket.cutoff_engine()
                 
        else:
            # Vacuum Landing (Proportional Hover)
            
            # --- Landing Cutoff (User Request) ---
            if altitude < 20.0 and v_mag < 10.0:
                 self.rocket.status = "LANDED"
                 self.rocket.cutoff_engine()
                 return
                 
            # Desired V = 0.1 * h + 2.0
            target_v = 0.1 * altitude + 2.0
            weight_force = self.rocket.total_mass * g
            hover_throttle = weight_force / self.rocket.max_thrust
            
            # Use Radial Velocity as primary control variable
            radial_v = np.dot(self.rocket.velocity, self.rocket.position / np.linalg.norm(self.rocket.position))
            
            # Anti-Pogo Logic:
            # If we are moving UP (radial_v > 0.5) near the ground, limit throttle to let gravity work.
            if radial_v > 1.0 and altitude < 500:
                 self.rocket.engine.throttle = 0.1 # Idle to maintain control but fall
                 return

            # Ensure Engine is Running if we are in this phase (Vacuum Braking)
            if not self.rocket.engine.running:
                 self.rocket.ignite_engine()

            # Descent Control
            # We want radial_v to approach -target_v
            # target_v is magnitude (positive). Descent means negative radial_v.
            # So desired_radial = -target_v.
            # Error = desired - actual = -target_v - radial_v
            # If radial_v is -100 and target is 10 (desired -10), error = -10 - (-100) = +90 (Need Thrust)
            
            desired_radial = -target_v
            error = desired_radial - radial_v # Note: Sign convention!
            
            # Wait, original logic used v_mag.
            # v_mag ~ abs(radial_v) in vertical descent.
            # Previous: error = v_mag - target_v.
            # If v_mag=100, target=10 -> error=90.
            
            # Let's use |radial_v| for error magnitude if descending?
            if radial_v < 0:
                 # Descending
                 v_descent = abs(radial_v)
                 error = v_descent - target_v
                 
                 kp = 0.1
                 # Add some D-term?
                 cmd = hover_throttle + error * kp
                 self.rocket.engine.throttle = max(0.0, min(1.0, cmd))
            else:
                 # Ascent/Hovering
                 self.rocket.engine.throttle = hover_throttle * 0.9 # Reduce slightly to settle

    def determine_outcome(self):
        """Returns the final outcome string."""
        if self.mission_outcome: # Already set by failure/check (CRASHED, REJECTED, etc)
             return self.mission_outcome
             
        # If not failed explicitly, check trajectory
        # Did we reach target apoapsis?
        if self._achieved_apoapsis >= self.target_apoapsis * 0.95:
             return "SUCCESS"
        
        return f"FAILED (Did not reach target. Apo: {self._achieved_apoapsis/1000:.1f}km / {self.target_apoapsis/1000:.0f}km)"

    def _record_event(self, label):
        if label not in self._events_triggered:
            self._events_triggered.add(label)
            self.events.append({'label': label, 'time': self.time, 'altitude': (np.linalg.norm(self.rocket.position) - self.planet.radius)})

