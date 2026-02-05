import numpy as np
from dataclasses import dataclass

# --------------------
# PHYSICS MODULE
# --------------------

@dataclass
class EnvironmentState:
    """Represents the atmospheric and gravitational state at a specific point.

    Attributes:
        density (float): Atmospheric density in kg/m^3.
        pressure (float): Atmospheric pressure in Pascals (Pa).
        temperature (float): Ambient temperature in Kelvin (K).
        speed_of_sound (float): Speed of sound in the medium in m/s.
        gravity (float): Gravitational acceleration at this radius in m/s^2.
    """
    density: float          # kg/m^3
    pressure: float         # Pa
    temperature: float      # K
    speed_of_sound: float   # m/s
    gravity: float          # m/s^2

class Planet:
    """Represents a celestial body with gravitational and atmospheric properties.

    This class encapsulates the physical constants of a planet and provides methods
    to calculate gravity and atmospheric properties at varying altitudes.

    Attributes:
        name (str): The name of the planet.
        radius (float): The planetary radius in meters.
        mass (float): The mass of the planet in kilograms.
        mu (float): The standard gravitational parameter (G * mass) in m^3/s^2.
        atmosphere_height (float): The altitude limit of the atmosphere in meters.
        surface_pressure (float): The atmospheric pressure at surface level in Pascals.
        scale_height (float): The scale height for the exponential atmosphere model in meters.
        color (str): The visual color representation of the planet.
    """
    def __init__(self, name, radius, mass, atmosphere_height, surface_pressure, scale_height, color):
        self.name = name
        self.radius = radius            # meters
        self.mass = mass                # kg
        self.mu = 6.67430e-11 * mass    # Standard gravitational parameter
        self.atmosphere_height = atmosphere_height # meters
        self.surface_pressure = surface_pressure   # Pascals
        self.scale_height = scale_height           # meters
        self.color = color

        # ISA Layers (Earth) - Simplified 1976 Standard Atmosphere
        # H (Geopotential km), T (K), L (K/km), P (Pa)
        # We'll use Geometric altitude approx for simplicity or convert?
        # Standard uses Geopotential, but for a game/sim, Geometric is fine if close.
        # Layer: (Base Alt m, Base Temp K, Lapse Rate K/m, Base Press Pa)
        if name == "Earth":
            self.atmos_layers = [
                (0,       288.15, -0.0065, 101325.0),    # Troposphere
                (11000,   216.65,  0.0,    22632.1),     # Tropopause
                (20000,   216.65,  0.001,  5474.89),     # Stratosphere 1
                (32000,   228.65,  0.0028, 868.02),      # Stratosphere 2
                (47000,   270.65,  0.0,    110.91),      # Stratopause
                (51000,   270.65, -0.0028, 66.94),       # Mesosphere 1
                (71000,   214.65, -0.002,  3.96),        # Mesosphere 2
                (84852,   186.95,  0.0,    0.3734)       # Mesopause (approx limit for this simple model)
            ]
        else:
            self.atmos_layers = []

    @property
    def has_atmosphere(self):
        """Checks if the planet has an atmosphere."""
        return self.atmosphere_height > 0

    def get_gravity(self, r):
        """Calculates gravitational acceleration at a given radial distance.

        Args:
            r (float): The distance from the center of the planet in meters.

        Returns:
            float: The gravitational acceleration in m/s^2.
        """
        return self.mu / (r**2)

    def query_environment(self, altitude, t=0.0) -> EnvironmentState:
        """Queries the environmental state at a specific altitude.

        Determines the gravity, air density, pressure, temperature, and speed of sound
        based on the planet's atmospheric model (Standard or Exponential).

        Args:
            altitude (float): The altitude above the planet's surface in meters.
            t (float, optional): The simulation time in seconds. Defaults to 0.0.
                                 Reserved for future dynamic atmosphere effects.

        Returns:
            EnvironmentState: An object containing the physical properties of the environment.
        """
        g = self.get_gravity(self.radius + altitude)
        
        if not self.has_atmosphere or altitude > self.atmosphere_height:
             return EnvironmentState(0.0, 0.0, 0.0, 0.0, g)

        if self.name == "Earth" and self.atmos_layers:
            return self._get_standard_atmosphere(altitude, g)
        else:
            return self._get_exponential_atmosphere(altitude, g)

    def _get_standard_atmosphere(self, h, g):
        # Constants
        R_univ = 8.314462618
        M_air = 0.0289644 # kg/mol
        R_spec = R_univ / M_air
        GAMMA = 1.4

        # Find layer
        # Default to first layer
        base_h, base_T, L, base_P = self.atmos_layers[0]
        
        found = False
        for layer in self.atmos_layers:
            if h >= layer[0]:
                base_h, base_T, L, base_P = layer
                found = True
            else:
                break
        
        dh = h - base_h
        
        if abs(L) < 1e-9:
            # Isothermal
            # P = P_b * exp(-g0 * M * dh / (R * T_b)) = P_b * exp(-g * dh / (R_spec * T_b))
            # Note: Standard Atmosphere uses Geopotential everywhere, so g is 'constant' g0 inside the exp?
            # Or uses actual gravity? ISA uses g0. Let's use g (local) for consistency with our physics, 
            # implies scale height changes with gravity.
            
            exponent = - (g * dh) / (R_spec * base_T)
            P = base_P * np.exp(exponent)
            T = base_T
        else:
            # Linear change
            # T = T_b + L * dh
            # P = P_b * (T_b / T) ^ (g * M / (R * L)) = P_b * (T / T_b) ^ (-g / (R_spec * L))
            T = base_T + L * dh
            exponent = - g / (R_spec * L)
            P = base_P * (T / base_T) ** exponent

        rho = P / (R_spec * T)
        a = np.sqrt(GAMMA * R_spec * T)
        
        return EnvironmentState(rho, P, T, a, g)

    def _get_exponential_atmosphere(self, h, g):
        # Fallback for Mars/others
        if h > self.atmosphere_height:
             return EnvironmentState(0.0, 0.0, 0.0, 0.0, g)
             
        rho0 = 1.225 if self.name == 'Earth' else 0.020
        # Simple T model
        T0 = 288.15 if self.name == 'Earth' else 210.0
        T = max(150.0, T0 - 0.004 * h) 
        
        rho = rho0 * np.exp(-h / self.scale_height)
        
        # P = rho * R * T
        R_spec = 287.05 # Earth air approx
        P = rho * R_spec * T
        
        a = np.sqrt(1.4 * R_spec * T)
        
        return EnvironmentState(rho, P, T, a, g)

    # Legacy helper for compatibility if needed (though we should refactor usages)
    def get_atmospheric_density(self, altitude):
        return self.query_environment(altitude).density

# Constants Instances
EARTH = Planet("Earth", 6371000, 5.972e24, 140000, 101325, 8500, 'blue') # Higher atmo limit for high layers
MARS = Planet("Mars", 3389500, 6.417e23, 50000, 600, 11100, 'red')
MOON = Planet("Moon", 1737400, 7.342e22, 0, 0, 1, 'gray')
MERCURY = Planet("Mercury", 2440000, 3.301e23, 0, 0, 1, 'darkgray')
VENUS = Planet("Venus", 6052000, 4.867e24, 120000, 9200000, 15900, 'orange')
PLUTO = Planet("Pluto", 1188000, 1.309e22, 0, 0, 1, 'brown')

PLANETS = {
    "Earth": EARTH,
    "Mars": MARS,
    "Moon": MOON,
    "Mercury": MERCURY,
    "Venus": VENUS,
    "Pluto": PLUTO
}
