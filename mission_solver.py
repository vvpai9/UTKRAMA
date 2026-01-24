import numpy as np
from physics import dry_mass

g = 9.81
Ve = 2500.0
T_W = 3.0
loss_factor = 1.8

def solve_mission(target_apogee, fuel_mass):

    print("DEBUG dry_mass in solver =", dry_mass)
    print("DEBUG target apogee =", target_apogee)
    print("DEBUG fuel mass =", fuel_mass)


    if target_apogee <= 0 or fuel_mass <= 0:
        raise ValueError("Target apogee and fuel mass must be positive.")


    m0 = dry_mass + fuel_mass

    # Max delta-V available
    dv_max = Ve * np.log(m0 / dry_mass)

    # Minimum required vertical speed
    v_req = np.sqrt(2 * g * target_apogee) * loss_factor

    print("DEBUG dv_max =", dv_max, "v_req =", v_req)


    if dv_max < v_req:
        raise ValueError(
            f"Mission impossible: required Δv = {v_req:.0f} m/s, "
            f"but available Δv = {dv_max:.0f} m/s"
        )

    T = T_W * m0 * g
    m_dot = T / Ve
    burn_time = fuel_mass / m_dot

    return {
        "thrust": T,
        "burn": burn_time,
        "m_dot": m_dot,
        "m0": m0,
        "dry": dry_mass
    }
