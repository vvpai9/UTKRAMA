import numpy as np

def rho(h):
    if h < 0:
        h = 0
    return 1.225 * np.exp(-h / 8500.0)
