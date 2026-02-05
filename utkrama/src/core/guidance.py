import numpy as np

class GuidanceSystem:
    """Manages the flight guidance logic for the rocket.

    Controls the vehicle's pitch and engine state (in select modes) to achieve
    target mission parameters (e.g., target apoapsis).

    Attributes:
        target_apoapsis (float): The target orbit apoapsis in meters.
        switch_altitude (float): The altitude at which to switch from open-loop to closed-loop guidance.
        mode (str): Current guidance mode ("OPEN_LOOP" or "CLOSED_LOOP").
    """
    def __init__(self, target_apoapsis, switch_altitude=30000):
        self.target_apoapsis = target_apoapsis
        self.switch_altitude = switch_altitude # Meters
        self.mode = "OPEN_LOOP" # or "CLOSED_LOOP"
        self.log_callback = None

    def set_logger(self, callback):
        """Sets the logging callback function."""
        self.log_callback = callback

    def get_steering_command(self, rocket, altitude, velocity_vector, planet):
        """Determines the target pitch angle for the current flight state.

        Args:
            rocket (Rocket): The rocket instance.
            altitude (float): Current altitude in meters.
            velocity_vector (numpy.ndarray): Current velocity vector [vx, vy] in m/s.
            planet (Planet): The planet being orbited.

        Returns:
            float: The command pitch angle in radians (from vertical, or world frame depending on convention).
        """
        
        # Simple Logic:
        # 1. Vertical ascent for first few seconds / low altitude to clear tower/dense air.
        # 2. Gravity turn (pitch down gradually).
        # 3. Closed Loop (Proportional Nav or Energy management) for orbit insertion.

        if self.mode == "OPEN_LOOP":
            # Early switch for solid?
            switch_alt = self.switch_altitude
            
            # Vacuum Logic: Switch earlier too? 
            if not planet.has_atmosphere:
                switch_alt = 10000 # 10km CLG switch for Moon
            elif rocket.propellant_type == "solid": 
                switch_alt = 15000 # Switch to CLG much earlier (15km vs 30km)
                
            if altitude > switch_alt:
                self.mode = "CLOSED_LOOP"
                if self.log_callback:
                    self.log_callback(f"CLG INIT at Altitude {altitude:.0f}m")
                return self._closed_loop_guidance(rocket, altitude, velocity_vector)
            else:
                return self._open_loop_guidance(altitude, rocket.propellant_type, planet, velocity_vector)
        else:
            return self._closed_loop_guidance(rocket, altitude, velocity_vector)

    def _open_loop_guidance(self, altitude, propellant_type="liquid", planet=None, velocity_vector=None):
        """Executes the open-loop phase of the flight (Gravity Turn).

        Calculates pitch based on a predefined altitude-pitch profile.
        """
        # Simple gravity turn profile
        
        turn_end_alt = 80000 # 80km default
        start_turn = 1000
        
        if planet and not planet.has_atmosphere:
             # VACUUM GRAVITY TURN (Aggressive)
             # No air drag. Turn immediately to maximize horizontal gains.
             # Moon launches are short (MECO < 10s). Turn FAST.
             start_turn = 50.0 # 50m
             turn_end_alt = 3000.0 # Reach horizontal by 3km
        elif propellant_type == "solid":
            # Aggressive turn for solid to gain downrange before burnout
            turn_end_alt = 60000 # Reach 80 deg by 60km (was 40km - too aggressive low down)
            start_turn = 500 # Start turning at 500m (was 200m)
            
        if altitude < start_turn:
            return 0.0 # Vertical
        
        fraction = (altitude - start_turn) / (turn_end_alt - start_turn)
        fraction = min(max(fraction, 0.0), 1.0)
        
        # Target: 0 to 80 degrees
        return fraction * np.deg2rad(80)

    def _closed_loop_guidance(self, rocket, altitude, velocity_vector):
        """Executes the closed-loop phase of the flight.

        Adjusts pitch to optimize orbit insertion or maintain trajectory.
        This is a simplified implementation for a 2D simulation.
        """
        # Very simple "Velocity Search" or "Pitch for Apoapsis"
        # If Ap < Target, pitch up slightly or stay optimal?
        
        # For this simplified 2D sim, let's just use a proportional controller 
        # based on orbital energy or Ap error, but keep it stable.
        
        # If we are effectively in vacuum, we can just point prograde to maximize DeltaV usage
        # or steer to hit specific Ap.
        
        # Simplest functional CLG: Point at horizon (90deg) if close to Ap, 
        # or manage vertical velocity to hit target Ap exactly.
        
        # Let's just hold a steady angle for orbit insertion efficiently:
        # e.g. 85-90 degrees. 
        
        return np.deg2rad(85) # Simple placeholder for "Closed Loop" functionality requiring tuning in sim
