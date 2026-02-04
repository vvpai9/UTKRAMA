import numpy as np
from src.core.physics import PLANETS
from src.core.rocket import Rocket
from src.core.guidance import GuidanceSystem
from src.core.utils import calculate_orbital_elements

class Simulation:
    def __init__(self):
        self.planet = PLANETS['Earth']
        self.rocket = None
        self.guidance = None
        self.time = 0.0
        self.dt = 0.1 # Simulation time step
        self.target_apoapsis = 0.0
        
        # Telemetry History
        self.history = {
            'time': [],
            'altitude': [],
            'velocity': [],
            'downrange': [],
            'apoapsis': [],
            'periapsis': [],
            'q': []
        }
        
    def initialize(self, planet_name, target_apo_km, safety_margin_km, dry_mass, fuel_mass, propellant_type):
        self.planet = PLANETS.get(planet_name, PLANETS['Earth'])
        self.target_apoapsis = target_apo_km * 1000 # Convert to meters
        self.safety_margin = safety_margin_km * 1000
        
        # Estimate Isp and Thrust based on propellant type if not set
        
        # Estimate Isp and Thrust based on propellant type if not set
        # Typical values: lqd ~300-450s, solid ~250-280s
        if propellant_type == "liquid":
            isp = 350
            thrust = 2000000 # 2MN approx for medium rocket
        else:
            isp = 260
            thrust = 3500000 # Higher thrust for solid usually
            
        self.rocket = Rocket(dry_mass, fuel_mass, isp, thrust, propellant_type)
        self.guidance = GuidanceSystem(self.target_apoapsis)
        self.time = 0.0
        
        # Reset state: Position slightly above surface (e.g., launch pad)
        # 2D Cartesian Frame: Center of Planet is (0, -Radius). Launch site is (0, 0).
        # Actually standard physics often puts Center at (0,0). Let's do Center at (0,0).
        # Launch site (Create a rotating frame or inertial? Simplified 2D inertial is best)
        # Start at top of planet (0, Radius)
        
        self.rocket.position = np.array([0.0, self.planet.radius])
        self.rocket.velocity = np.array([0.0, 0.0]) 
        self.rocket.orientation = np.pi / 2 # 90 degrees = Vertical Up 
        # Standard angle conventions: 0 = East, 90 = North. 
        # Let's say 90 (pi/2) is Up (Vertical) at launch pad (0, R).
        
        self.rocket.status = "PRELAUNCH"

    def check_feasibility(self, planet_name, target_apo_km, dry_mass, fuel_mass, propellant_type, safety_margin_km=0):
        """
        Returns (is_feasible, rocket_dv, required_dv, extra_fuel_needed)
        """
        planet = PLANETS.get(planet_name, PLANETS['Earth'])
        target_r = planet.radius + target_apo_km * 1000
        
        # Required Delta-V for Hohmann Transfer (Launch -> Elliptical Orbit Apex)
        # But this is launch. Approximation: orbital velocity at surface + gravity drag + aero drag
        # V_orbit = sqrt(mu / r) -> Low orbit ~7800 m/s for Earth
        # Launch Losses ~1500-2000 m/s
        
        # Ideal Vis-viva at apoapsis to hold altitude momentarily? No, we need orbit capability.
        # "Target Apoapsis" usually implies suborbital hop OR orbit insertion. 
        # Assuming we want to *reach* that altitude (suborbital) or Orbit?
        # "Target Apoapsis" usually implies getting there. 
        # Let's assume we need to reach that potential energy.
        
        # Energy balance: E_surf = -mu/R. E_target = -mu/R_target (if circular)
        # For parabolic/suborbital to touch that height:
        # 1/2 v^2 - mu/R = -mu/R_target
        # v_req_suborbital = sqrt(2*mu*(1/R - 1/R_target))
        
        # But user asks for "Mission Feasibility". Usually implies Orbit if margins mentioned?
        # Let's assume Suborbital reach is minimum, but usually rockets want Orbit.
        # Let's calculate Delta V for Low Circular Orbit at that altitude as conservative "Mission"
        # Or just Suborbital if user intent is ambiguous? "Launch Simulator" -> usually orbit.
        # Let's stick to "Orbital Velocity at Altitude" + Losses.
        
        v_orbit_target = np.sqrt(planet.mu / target_r)
        
        # Potential Energy change + Kinetic Energy change
        # Approximate: Dv_req = sqrt(mu/R_target) + Losses
        # A simpler robust approximation for LEO: ~9400 m/s total Dv from surface.
        # Let's scale it by Planet Mu/Radius relative to Earth.
        
        earth_leo_dv = 9400.0
        # Scaling factor? v_esc ~ sqrt(mu/R)
        v_esc_planet = np.sqrt(2 * planet.mu / planet.radius)
        v_esc_earth = np.sqrt(2 * PLANETS['Earth'].mu / PLANETS['Earth'].radius)
        
        req_dv = earth_leo_dv * (v_esc_planet / v_esc_earth)
        
        # Adjust for target altitude if very high
        # Add Hohmann transfer cost?
        # Simple adder: Potential energy diff converted to velocity?
        # Let's just use the scaling for basics + some altitude term.
        # Actually, simpler: V_orbital_srf + Gravity_Loss + Aero_Loss
        # V_orb_srf = sqrt(mu/R)
        # Earth: 7900. Losses ~ 1500. Total 9400.
        
        # specific req_dv
        v_circ_surf = np.sqrt(planet.mu / planet.radius)
        losses_est = 1500.0 * (planet.surface_pressure / 101325.0) # Reduced losses estimate
        if losses_est < 100: losses_est = 100 
        
        # Suborbital Hop vs Orbit?
        # If target < 200km and planet is Earth-like, user might mean suborbital.
        # But "Launch Simulator" usually implies orbit. 
        # However, 100km Ap is just barely space. 
        # Let's use a standard "Reach Altitude" energy calculation + Losses for lower targets.
        
        if target_apo_km < 400: # Assume suborbital hop for feasibility check to be generous
             # Energy to reach height h: mgh roughly? or -mu/r diff.
             # Vis-viva: v at burn_end to coast to r_target.
             # 1/2 v^2 - mu/R = -mu/R_target
             # v_req = sqrt(2*mu*(1/R - 1/R_target))
             v_ballistic = np.sqrt(2 * planet.mu * (1/planet.radius - 1/target_r))
             req_dv = v_ballistic + losses_est * 0.8 # Lower losses for vertical-ish hoppish
        else:
             req_dv = v_circ_surf * 1.1 + losses_est
        
        # Calculate Rocket Delta V
        # Tsiolkovsky: dV = Isp * g0 * ln(m_initial / m_final)
        isp = 350 if propellant_type == "liquid" else 260
        g0 = 9.80665
        
        m_initial = dry_mass + fuel_mass
        m_final = dry_mass
        
        rocket_dv = isp * g0 * np.log(m_initial / m_final)
        
        is_feasible = rocket_dv >= req_dv
        
        extra_fuel = 0.0
        if not is_feasible:
            # Solve Tsiolkovsky for m_initial given req_dv
            # req_dv / (Isp * g0) = ln(m_i / m_f)
            # exp(...) = m_i / m_f
            # m_i_req = m_f * exp(...)
            # extra = m_i_req - m_current_initial
            
            desired_ratio = np.exp(req_dv / (isp * g0))
            required_total_mass = m_final * desired_ratio
            extra_fuel = required_total_mass - m_initial

        return is_feasible, rocket_dv, req_dv, extra_fuel

    def step(self, dt):
        if self.rocket.status == "CRASHED" or self.rocket.status == "LANDED" or self.rocket.status == "ABORT":
             return
             
        # Physics Integration (Euler or RK4)
        # Let's do semi-implicit Euler or just Euler for simplicity since dt is small
        
        r_vec = self.rocket.position
        v_vec = self.rocket.velocity
        
        r_mag = np.linalg.norm(r_vec)
        altitude = r_mag - self.planet.radius
        
        # Gravity
        g_acc = - (self.planet.mu / r_mag**3) * r_vec
        
        # Atmosphere
        rho = self.planet.get_atmospheric_density(altitude)
        v_mag = np.linalg.norm(v_vec)
        
        # Drag
        # Fd = 0.5 * rho * v^2 * Cd * A
        cd = 0.3 # Reduced from 0.5 (Streamlined)
        area = 1.0 # Reduced from 10.0 (Reasonable for 20t rocket diameter ~1m)
        
        if self.rocket.status == "DROGUE_CHUTE":
            cd = 1.5
            target_v = 20.0
            # Planet-Aware Sizing
            g = self.planet.get_gravity(self.planet.radius)
            rho_ssl = self.planet.get_atmospheric_density(0)
            if rho_ssl < 0.001: rho_ssl = 0.001 # Prevent divide by zero if vacuum planet bug
            
            m = self.rocket.total_mass
            area = (2 * m * g) / (rho_ssl * target_v**2 * cd)
            
        elif self.rocket.status == "MAIN_CHUTE":
            cd = 2.5
            target_v = 5.0
            g = self.planet.get_gravity(self.planet.radius)
            rho_ssl = self.planet.get_atmospheric_density(0)
            if rho_ssl < 0.001: rho_ssl = 0.001

            m = self.rocket.total_mass
            area = (2 * m * g) / (rho_ssl * target_v**2 * cd)
            
        drag_force_mag = 0.5 * rho * v_mag**2 * cd * area
        if v_mag > 0:
            drag_vec = - (v_vec / v_mag) * drag_force_mag
        else:
            drag_vec = np.zeros(2)
        
        drag_acc = drag_vec / self.rocket.total_mass
        
        # Stability Clamp: Prevent Drag from reversing velocity in one step (Explosion fix)
        # dv_drag = drag_acc * dt. magnitude check:
        dv_drag_mag = np.linalg.norm(drag_acc) * dt
        if dv_drag_mag > v_mag:
             # Limit acceleration to just stop the object in this step
             scale_factor = v_mag / dv_drag_mag
             drag_acc = drag_acc * scale_factor * 0.9 # 90% stop to be safe

        
        # Thrust
        # Direction determined by guidance (rocket orientation)
        # Orientation is angle wrt vertical?
        # Let's define orientation 'theta' as angle from Local Vertical (Radial vector).
        # Radial vector = r_vec / r_mag
        # Tangent vector = [-y, x] ?
        
        # Guidance step
        if self.rocket.status == "THRUSTING" or self.rocket.status == "PRELAUNCH" or self.rocket.status == "RETRO_BRAKE":
             # We need to ignite if PRELAUNCH
             if self.rocket.status == "PRELAUNCH":
                self.rocket.status = "THRUSTING"
                self.rocket.ignite_engine()
             
             # G-LIMITER Logic (Max Acceleration Limit)
             # Prevent instant burnout on low-g/high-power launches.
             max_g = 5.0 # Limit to 5 Earth Gs
             g0 = 9.81
             max_thrust_force = self.rocket.total_mass * g0 * max_g
             
             # Required throttle to stay under max_g
             # F = F_max * throttle -> throttle = F_req / F_max
             required_throttle = max_thrust_force / self.rocket.max_thrust
             
             # Clamp throttle
             if required_throttle < 1.0:
                 self.rocket.engine.throttle = required_throttle
             else:
                 self.rocket.engine.throttle = 1.0 # Full power if Heavy
                 
             # Calculate Pitch/Orientation
             if self.rocket.status == "RETRO_BRAKE":
                 # Orientation is handled in _handle_retro_braking or kept as is
                 # Wait, thrust_dir logic below uses Pitch Angle relative to Vertical?
                 # My logic below:
                 # thrust_dir = np.cos(pitch_angle) * up_vec + np.sin(pitch_angle) * right_vec
                 # This assumes pitch_angle is defined as angle from Vertical.
                 # Rocket.orientation IS pitch_angle (global angle from vertical?). 
                 # Let's verify: In _handle_retro_braking, I set orientation = retro_angle. 
                 # Is retro_angle relative to Vertical (Up)?
                 # v_angle is atan2(y, x). Up is (0,1). 
                 # If v=(0, 1) [Up], v_angle = pi/2. 
                 # If I want pitch from Vertical(pi/2)? 
                 # Earlier: Thrust Dir construction implies pitch_angle is "Angle from UpVector towards RightVector".
                 # i.e. Pitch=0 -> Up. Pitch=pi/2 -> Right.
                 # This means pitch_angle is NOT standard polar angle! 
                 # It is "Angle deviation from local vertical".
                 
                 # However, Rocket.orientation is used for VISUALS as "90-angle". 
                 # If orientation is Polar Angle (0=Right, 90=Up), then Visuals (90-90)=0 -> Up. Correct.
                 
                 # So Rocket.orientation is Polar Angle (rad).
                 # BUT Simulation "pitch_angle" logic:
                 # thrust_dir = cos(p)*Up + sin(p)*Right.
                 # If p=0, Dir=Up. If p=pi/2, Dir=Right.
                 # In Polar: Up is pi/2. Right is 0.
                 # So p = (pi/2 - PolarAngle)? 
                 
                 # Let's fix this confusion.
                 # Guidance returns "Angle from Vertical". 0=Up.
                 # Rocket.orientation should store "Polar Angle" for consistency with physics/visuals?
                 # Or just store "Angle from Vertical"?
                 
                 # Let's stick to: Rocket.orientation = Polar Angle (0=Right, 90=Up).
                 # Then: 
                 # Guidance returns Polar Angle? Or angle from vertical?
                 # Current Guidance.get_steering_command returns "pitch_angle" used in formula cos(p)Up + sin(p)Right.
                 # This formula implies p=0 is Up.
                 # So Guidance returns Angle From Vertical.
                 
                 # So for RETRO BRAKE, we determine target Polar Angle, convert to Angle From Vertical.
                 target_polar = self.rocket.orientation
                 # Angle From Vertical p = pi/2 - polar ?
                 # If polar=pi/2 (Up), p=0. cos(0)Up = Up. Correct.
                 # If polar=0 (Right), p=pi/2. sin(pi/2)Right = Right. Correct.
                 
                 pitch_angle = np.pi/2 - self.rocket.orientation
                 
             else:
                 # Guidance returns Angle From Vertical (0=Up)
                 pitch_angle = self.guidance.get_steering_command(self.rocket, altitude, v_vec, self.planet)
                 # Update Rocket Orientation (Polar) for Visuals
                 self.rocket.orientation = np.pi/2 - pitch_angle

             # Construct thrust vector
             # Current Radial Vector (Up)
             up_vec = r_vec / r_mag
             # Right Vector (East assuming CCW orbit)
             right_vec = np.array([up_vec[1], -up_vec[0]])
             
             # Thrust direction: Rotate Up vector by pitch_angle towards Right vector
             thrust_dir = np.cos(pitch_angle) * up_vec + np.sin(pitch_angle) * right_vec
             thrust_dir = thrust_dir / np.linalg.norm(thrust_dir)
             
             thrust_force = self.rocket.thrust()
             thrust_acc = (thrust_dir * thrust_force) / self.rocket.total_mass
             
             self.rocket.burn_fuel(dt)
             
        else:
             thrust_acc = np.zeros(2)
        
        # Dynamic Q
        q = 0.5 * rho * v_mag**2
        
        # Integration
        total_acc = g_acc + drag_acc + thrust_acc
        self.rocket.velocity += total_acc * dt
        self.rocket.position += self.rocket.velocity * dt
        
        self.time += dt
        
        # Update History
        if int(self.time * 10) % 5 == 0: # Log every 0.5s roughly
            self.history['time'].append(self.time)
            self.history['altitude'].append(altitude)
            self.history['velocity'].append(v_mag)
            self.history['q'].append(q)
            
            # Simple Orbital Elements estimation
            ra, rp = calculate_orbital_elements(r_vec, v_vec, self.planet.mu)
            apo_alt = ra - self.planet.radius
            peri_alt = rp - self.planet.radius
            self.history['apoapsis'].append(apo_alt)
            self.history['periapsis'].append(peri_alt)

        # Engine Cutoff Logic (MECO) & Station Keeping (Drag Compensation)
        # Calculate current projected apoapsis
        if self.rocket.status == "THRUSTING":
             ra, _ = calculate_orbital_elements(r_vec, v_vec, self.planet.mu)
             current_apo = ra - self.planet.radius
             
             # MECO Condition: Target + Margin? Or just Target? 
             # "Restart engines till pred apopasis >= target + safety margin"
             cutoff_target = self.target_apoapsis + self.safety_margin
             
             # Only Liquid Engines can cut off early. Solid burns to completion.
             if self.rocket.propellant_type == "liquid" and current_apo >= cutoff_target:
                 self.rocket.cutoff_engine()
                 self.rocket.status = "COAST"
                 if self.guidance.log_callback:
                     self.guidance.log_callback(f"MECO: Target {cutoff_target/1000:.1f}km reached. Coasting.")
        
        elif self.rocket.status == "COAST":
             # Drag Compensation Logic (Liquid Only)
             if self.rocket.propellant_type == "liquid" and self.rocket.fuel_mass > 0:
                 ra, _ = calculate_orbital_elements(r_vec, v_vec, self.planet.mu)
                 current_apo = ra - self.planet.radius
                 
                 # If we dropped below target and are still ascending (or even if descending?)
                 # "Restart engines till pred apopasis >= target + safety margin"
                 # Let's say we restart if < Target.
                 if current_apo < self.target_apoapsis:
                     self.rocket.status = "THRUSTING"
                     self.rocket.ignite_engine()
                     if self.guidance.log_callback:
                         self.guidance.log_callback(f"Drag Comp: Restarting Engine. Ap {current_apo/1000:.1f}km < {self.target_apoapsis/1000:.1f}km")

        # Re-entry / Landing Init Logic
        # Only enter RETRO_BRAKE if Liquid engine (restartable)
        if (self.rocket.status == "COAST" or self.rocket.status == "THRUSTING") and altitude < 90000 and v_mag > 100:
             # Check if we are descending
             radial_velocity = np.dot(v_vec, r_vec/r_mag)
             if radial_velocity < -50 and self.rocket.propellant_type == "liquid": # Descending fast AND Liquid
                 self.rocket.status = "RETRO_BRAKE" # New status for landing logic
                 self.rocket.cutoff_engine() # Cutoff to prepare for controlled retro burn
                 if self.guidance.log_callback:
                     self.guidance.log_callback("RETRO BRAKE PHASE INIT")

        # Recovery & Landing Logic (Always Run if appropriate)
        # Recovery & Landing Logic (Always Run if appropriate)
        if altitude < 10000 and self.rocket.velocity[1] < -1.0: # Below 10km and descending
             self._handle_recovery(altitude, v_mag)

        # Retro Braking Logic
        if self.rocket.status == "RETRO_BRAKE":
             self._handle_retro_braking(altitude, v_mag, dt)
             
        # Crash Check (Simplified here, handled in handle_recovery/landing check mostly)
        pass 
        
    # def _handle_retro_braking (Moved below)

        # Check Apoapsis Passage (Vertical Velocity crossing 0 from + to -)
        # Radial velocity
        v_rad = np.dot(v_vec, r_vec/r_mag)
        if v_rad < 0 and self.rocket.status in ["COAST", "THRUSTING"] and altitude > 1000:
             # Just passed apogee?
             # Check if we haven't logged it yet or if we just switched
             if not hasattr(self, '_apogee_logged'):
                 if self.guidance.log_callback:
                     self.guidance.log_callback(f"APOGEE ACHIEVED: Alt {altitude/1000:.2f}km @ T={self.time:.1f}s")
                 self._apogee_logged = True
                 self._achieved_apoapsis = altitude

        # Recovery & Landing Logic (Always Run if appropriate)
        # Recovery & Landing Logic (Always Run if appropriate)
        # MUST check if descending (velocity[1] < 0) to avoid ascent deployment!
        if altitude < 10000 and self.rocket.velocity[1] < -1.0: 
             self._handle_recovery(altitude, v_mag)
        # Detect Crash/Landing (Final Check AFTER integration)
        # Re-calculate altitude with new position
        new_alt = np.linalg.norm(self.rocket.position) - self.planet.radius
        
        if new_alt < 2.0 and self.time > 10.0:
             # Generous tolerance: < 12 m/s
             if v_mag < 12.0: 
                 self.rocket.status = "LANDED"
                 self.rocket.velocity = np.zeros(2)
                 self.rocket.cutoff_engine()
                 # Snap to surface
                 r_dir = self.rocket.position / np.linalg.norm(self.rocket.position)
                 self.rocket.position = r_dir * self.planet.radius
                 if self.guidance.log_callback: self.guidance.log_callback(f"TOUCHDOWN! v={v_mag:.2f} m/s")
             else:
                 self.rocket.status = "CRASHED"
                 self.rocket.velocity = np.zeros(2)
                 self.rocket.cutoff_engine()
                 if self.guidance.log_callback: self.guidance.log_callback(f"CRASH! v={v_mag:.2f} m/s")
                 self.rocket.position = (self.rocket.position / np.linalg.norm(self.rocket.position)) * self.planet.radius

    def _handle_recovery(self, altitude, v_mag):
        # 0. Atmosphere Check
        if not self.planet.has_atmosphere:
             return # No chutes in vacuum
             
        # 1. Chute Logic
        # Main Chute priority Check
        if altitude < 3000:
             if self.rocket.status != "MAIN_CHUTE":
                 if self.rocket.status == "RETRO_BRAKE" or self.rocket.status == "DROGUE_CHUTE" or self.rocket.status == "COAST":
                     self.rocket.status = "MAIN_CHUTE"
                     self.rocket.cutoff_engine()
                     if self.guidance.log_callback: self.guidance.log_callback(f"MAIN CHUTE DEPLOY @ {altitude:.0f}m")
                 
        elif altitude < 8000:
             if self.rocket.status != "DROGUE_CHUTE" and self.rocket.status != "MAIN_CHUTE":
                 if self.rocket.status == "RETRO_BRAKE" or self.rocket.status == "COAST" or self.rocket.status == "THRUSTING":
                      self.rocket.status = "DROGUE_CHUTE"
                      self.rocket.cutoff_engine()
                      if self.guidance.log_callback: self.guidance.log_callback(f"DROGUE CHUTE DEPLOY @ {altitude:.0f}m")
        
        # Force Orientation UP for Chutes
        if self.rocket.status in ["MAIN_CHUTE", "DROGUE_CHUTE"]:
             self.rocket.orientation = np.pi/2

    def _handle_retro_braking(self, altitude, v_mag, dt):
        # 1. Orient Retrograde (Smooth Slew)
        v_vec = self.rocket.velocity
        if v_mag > 1:
            # Retrograde angle is opposite to velocity
            retro_angle = np.arctan2(v_vec[1], v_vec[0]) + np.pi # In radians, direction of motion + 180
            # Normalize to 0-2pi or -pi,pi? Rocket orientation is likely polar angle.
            # Rocket.orientation 0=Right? 90=Up?
            
            # Map atan2 to our convention:
            # atan2(y, x): 0=Right (1,0), pi/2=Up (0,1). Matches.
            target_angle = retro_angle
            
            # STABILITY FIX: Horizontal Deadband
            # If lateral velocity is negligible, lock to Vertical to prevent jitter.
            # ALSO: If altitude is very low (< 100m), force Vertical to prepare for touchdown.
            if (abs(v_vec[0]) < 0.5 and v_vec[1] < 0) or altitude < 100.0:
                target_angle = np.pi/2
            
            # Slew Rate Limit (Reduced for smoothness)
            current_angle = self.rocket.orientation
            
            # Shortest path interpolation
            diff = np.arctan2(np.sin(target_angle - current_angle), np.cos(target_angle - current_angle))
            max_step = 0.5 * dt # 0.5 rad/s slew rate (was 2.0)
            if abs(diff) > max_step:
                change = max_step * np.sign(diff)
            else:
                change = diff
                
            self.rocket.orientation = current_angle + change
        else:
            self.rocket.orientation = np.pi/2 # Default Up if stopped
            target_angle = np.pi/2 # Define for later check
            
        # 2. Engine Control (Deep Burn Hysteresis / Vacuum Landing)
        # Verify Orientation: Don't burn until aligned (within 20 deg)
        alignment_error = abs(np.arctan2(np.sin(self.rocket.orientation - target_angle), np.cos(self.rocket.orientation - target_angle)))
        if alignment_error > np.deg2rad(20):
             self.rocket.cutoff_engine()
             return

        if self.planet.has_atmosphere:
            # Standard Atmosphere Retro Brake (Deep Cycle Hysteresis)
            # User Request: Burn to near zero, coast to threshold.
            
            # Calclulate Ignition Threshold based on Gravity
            # e.g. Allow ~2-3 seconds of freefall before braking?
            # V = g * t. Let's use 5 * g (~50 m/s Earth, ~18 m/s Mars)
            g_surface = self.planet.get_gravity(self.planet.radius)
            upper_threshold = 80.0 * g_surface # User requested "100s of m/s". ~300 m/s on Mars. 
            
            lower_threshold = 2.0  # Stop burn near zero to allow coasting
            
            # G-Limiter: Calculate max thrust force to stay under max_g
            max_thrust_force = self.rocket.max_g * self.rocket.total_mass * self.planet.get_gravity(np.linalg.norm(self.rocket.position))
            
            # Required throttle to stay under max_g
            # F = F_max * throttle -> throttle = F_req / F_max
            required_throttle = max_thrust_force / self.rocket.max_thrust
            
            # Clamp throttle
            
            # Clamp throttle
            if required_throttle < 1.0:
                self.rocket.engine.throttle = required_throttle
            else:
                self.rocket.engine.throttle = 1.0 # Full power if Heavy
            
            if not self.rocket.engine.running:
                 if v_mag > upper_threshold:
                     self.rocket.ignite_engine()
                     # Dynamic Throttle
                     base_throttle = 0.2
                     if v_mag > 1200: base_throttle = 0.5
                     
                     # Apply G-limiter to base_throttle
                     self.rocket.engine.throttle = min(base_throttle, self.rocket.engine.throttle)
                     if self.guidance.log_callback: self.guidance.log_callback(f"RETRO BURN START v={v_mag:.1f} Throt={self.rocket.engine.throttle*100:.0f}%")
            else:
                 # In BURNING state
                 current_throttle = self.rocket.engine.throttle # Get current G-limited throttle
                 if v_mag > 1200: current_throttle = min(0.5, current_throttle)
                 else: current_throttle = min(0.2, current_throttle)
                 self.rocket.engine.throttle = current_throttle
                 
                 if v_mag < lower_threshold:
                     self.rocket.cutoff_engine()
                     if self.guidance.log_callback: self.guidance.log_callback(f"RETRO BURN END v={v_mag:.1f}")
        else:
            # VACUUM LANDING LOGIC (No Chutes)
            # Must land at v < 5 m/s at h=0
            
            # 1. Check required hover thrust
            # F_gravity = m * g
            r_mag = np.linalg.norm(self.rocket.position)
            g_local = self.planet.get_gravity(r_mag)
            weight = self.rocket.total_mass * g_local
            hover_throttle = weight / self.rocket.max_thrust
            
            # Heuristic: V_limit = 0.1 * altitude + 1.0 (Safer, Gentler)
            target_v_limit = (0.1 * altitude) + 1.0
            
            # Allow touchdown: If Alt < 40m and V < 10m/s, Cut/Throttle Down to drop
            if altitude < 40.0 and v_mag < 10.0:
                 self.rocket.engine.throttle = 0.0
                 self.rocket.cutoff_engine()
                 return

            if v_mag > target_v_limit:
                 if not self.rocket.engine.running:
                     self.rocket.ignite_engine()
                 
                 # Proportional Control
                 error = v_mag - target_v_limit
                 
                 # Tuning: Gentle response
                 kp = hover_throttle * 0.5 # Reduced from 2.0 to prevent bounce
                 throttle = hover_throttle + (error * kp)
                 
                 # CLAMP: Prevent 200g kicks.
                 # Limit max TWR to ~50 (50x hover throttle ~ 8g Earth)
                 max_allowed = hover_throttle * 50.0
                 if max_allowed > 1.0: max_allowed = 1.0
                 
                 min_allowed = hover_throttle * 0.1 # Deep throttle
                 
                 throttle = min(max(throttle, min_allowed), max_allowed)
                 
                 self.rocket.engine.throttle = throttle
            else:
                 # Hysteresis
                 if self.rocket.engine.running:
                     if v_mag < target_v_limit * 0.9:
                         self.rocket.cutoff_engine()
