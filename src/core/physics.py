import numpy as np

# Constants
G = 6.67430e-11  # Gravitational constant

class Planet:
    def __init__(self, name, radius, mass, atmosphere_height, surface_pressure, scale_height, color):
        self.name = name
        self.radius = radius            # meters
        self.mass = mass                # kg
        self.mu = G * mass              # Standard gravitational parameter
        self.atmosphere_height = atmosphere_height # meters
        self.surface_pressure = surface_pressure   # Pascals
        self.scale_height = scale_height           # meters (approx for exponential model)
        self.color = color
        
    @property
    def has_atmosphere(self):
        return self.atmosphere_height > 0

    def get_gravity(self, r):
        """Calculates gravitational acceleration at distance r from center."""
        return self.mu / (r**2)

    def get_atmospheric_density(self, altitude):
        """Calculates atmospheric density using a simple exponential model."""
        if altitude > self.atmosphere_height:
            return 0.0
        
        # Simple isothermal approximation: rho = rho0 * exp(-h / H)
        # Using Ideal Gas Law approx for rho0: P = rho * R_specific * T
        # Ideally we'd have rho0 input, but deriving from pressure for now or assuming standard earth-like relation
        # For simplicity, let's use a reference density if available, or approximate.
        # Earth rho0 ~ 1.225 kg/m^3
        
        rho0 = 1.225 if self.name == 'Earth' else 0.020 # Mars approx
        if self.name == 'Moon':
             return 0.0

        return rho0 * np.exp(-altitude / self.scale_height)

# Predefined Planets
EARTH = Planet("Earth", 6371000, 5.972e24, 100000, 101325, 8500, 'blue')
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
