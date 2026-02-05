import numpy as np

def calculate_orbital_elements(r_vec, v_vec, mu):
    """Calculates orbital elements from state vectors.

    This function computes the apoapsis and periapsis radii of an orbit given the
    position and velocity vectors at a specific point in time, assuming a
    two-body Keplerian orbit.

    Args:
        r_vec (numpy.ndarray): The position vector [x, y] in meters.
        v_vec (numpy.ndarray): The velocity vector [vx, vy] in meters/second.
        mu (float): The standard gravitational parameter of the central body (m^3/s^2).

    Returns:
        tuple[float, float]: A tuple containing:
            - apoapsis_radius (float): The maximum distance from the center of attraction (meters).
            - periapsis_radius (float): The minimum distance from the center of attraction (meters).
            
            If the orbit is hyperbolic or parabolic (energy >= 0), returns (infinity, 0.0).
    """
    r_mag = np.linalg.norm(r_vec)
    v_mag = np.linalg.norm(v_vec)
    
    # Specific Mechanical Energy
    energy = (v_mag**2) / 2 - mu / r_mag
    
    if energy >= 0:
        # Hyperbolic or Parabolic
        # Apoapsis is infinite or undefined for practical "target altitude" purposes in this context
        return float('inf'), 0.0

    # Semi-major axis
    a = -mu / (2 * energy)
    
    # Eccentricity vector
    # e_vec = (1/mu) * ((v^2 - mu/r)*r - (r.v)*v)
    e_vec = (1/mu) * ((v_mag**2 - mu/r_mag)*r_vec - np.dot(r_vec, v_vec)*v_vec)
    e = np.linalg.norm(e_vec)
    
    # Radius of Apoapsis and Periapsis
    ra = a * (1 + e)
    rp = a * (1 - e)
    
    return ra, rp
