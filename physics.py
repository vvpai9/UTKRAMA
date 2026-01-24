import numpy as np
from atmosphere import rho
from guidance import thrust_direction
from math import pi

g = 9.81
Cd = 0.25
A = 0.05

# Defaults (overwritten by set_mission)
dry_mass = 350.0
m_dot = 5.0
_THRUST = 15000.0

# Parachutes
DROGUE_ALT = 8000.0
MAIN_ALT   = 3000.0

DROGUE_VEL = -150.0
MAIN_VEL   = -40.0

Cd_drogue = 1.0
A_drogue  = 3.0

Cd_main = 2.75
A_main  = 18.0

chute_state = 0 # 0 = stowed, 1 = drogue, 2 = main


def thrust(t, m, launched):
    return _THRUST if launched and m > dry_mass else 0.0

def rocket_ode(t, s, launched, direction):
    x, y, vx, vy, m = s

    # Mass flow logic
    if m <= dry_mass:
        m = dry_mass
        md = 0.0
    else:
        md = -m_dot if launched else 0.0

    v = np.hypot(vx, vy) + 1e-6

    rho_a = rho(y)

    global chute_state

    Cd_eff = Cd
    A_eff = A

    # Drogue deploy
    if chute_state == 0 and y < DROGUE_ALT and vy < DROGUE_VEL:
        chute_state = 1

    # Main deploy
    if chute_state == 1 and y < MAIN_ALT and vy < MAIN_VEL:
        chute_state = 2

    if chute_state == 1:
        Cd_eff = Cd_drogue
        A_eff = A_drogue
    elif chute_state == 2:
        Cd_eff = Cd_main
        A_eff = A_main

    D = 0.5 * rho_a * Cd_eff * A_eff * v**2

    Dx = -D * vx / v
    Dy = -D * vy / v

    T = thrust(t, m, launched)
    if direction == "prograde":
        ang = thrust_direction(t)
    else:
        ang = np.arctan2(vy, vx) + np.pi

    Tx = T * np.cos(ang)
    Ty = T * np.sin(ang)

    ax = (Tx + Dx) / m
    ay = (Ty + Dy) / m - g

    return [vx, vy, ax, ay, md]

def dynamic_pressure(y, vx, vy):
    v = np.hypot(vx, vy)
    return 0.5 * rho(y) * v**2

def set_mission(m):
    global _THRUST, m_dot, dry_mass, chute_state
    chute_state = 0
    _THRUST = m["thrust"]
    m_dot = m["m_dot"]
    dry_mass = m["dry"]
