import numpy as np

def thrust_direction(t):
    pitch0 = np.deg2rad(90)
    pitchf = np.deg2rad(10)
    turn_time = 60.0
    if t > turn_time:
        return pitchf
    return pitch0 - (pitch0 - pitchf)*(t/turn_time)
