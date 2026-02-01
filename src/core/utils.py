import numpy as np

def calculate_orbital_elements(r_vec, v_vec, mu):
    """
    Calculates orbital elements from state vectors.
    Returns:
        apoapsis_radius (meters)
        periapsis_radius (meters)
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
