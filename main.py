import sys
import numpy as np
from math import pi
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer
from scipy.integrate import solve_ivp
import traceback

# Custom module imports
import physics
from physics import rocket_ode, dynamic_pressure
from guidance import thrust_direction
from hud import HUD
from telemetry_plots import TelemetryPlot
from rocket_model_window import RocketModelWindow
from mission_dialog import MissionDialog
from mission_solver import solve_mission
import mission_solver

print("MISSION_SOLVER FILE =", mission_solver.__file__)

# ---------- GLOBAL STATE ----------
launched = False
aborted = False
apogee_achieved = False
apogee = 0.0
engine_on = False
status = "READY"
in_retro = False
state = [0, 0, 0, 0, 0]
t = 0
dt = 0.1
g = 9.81
warp = 1
direction = "prograde"

# ---------- QT APP ----------
app = QApplication(sys.argv)
dlg = MissionDialog()

if dlg.exec():
    params = dlg.get_params()
    print("DEBUG params =", params)
else:
    sys.exit()

if params is not None:
    try:
        mission = solve_mission(params["apogee"], params["fuel"])
    except ValueError as e:
        QMessageBox.critical(None, "Mission Error", str(e))
        sys.exit()

    physics.set_mission(mission)
    state = [0.0, 0.0, 0.0, 0.0, mission["m0"]]
    t = 0.0
    apogee = 0.0
else:
    sys.exit()

# ---------- UI INITIALIZATION ----------
hud = HUD()
hud.show()

rocket_view = RocketModelWindow()
rocket_view.show()

tv_alt = TelemetryPlot("Time vs Altitude", "Time (s)", "Altitude (m)")
tv_vel = TelemetryPlot("Time vs Velocity", "Time (s)", "Speed (m/s)")
tv_alt.show()
tv_vel.show()

# ---------- SIMULATION STEP ----------
def step():
    global t, state, apogee, engine_on, status, direction, in_retro, apogee_achieved
    try:
        if not launched or aborted:
            return

        for _ in range(warp):
            sol = solve_ivp(lambda tt, ss: rocket_ode(tt, ss, engine_on, direction),
                            [t, t+dt], state, max_step=dt)
            state = sol.y[:, -1]
            t += dt

        x, y, vx, vy, m = state
        q = dynamic_pressure(y, vx, vy)
        target = params["apogee"]
        margin = 3000

        # Thrust Logic
        if params["propellant"] == "liquid" and state[4] > physics.dry_mass:
            if vy > 0:
                pred_ap = y + vy**2 / (2 * g)
                if (not apogee_achieved and pred_ap < target + margin) or (apogee_achieved and pred_ap < target):
                    engine_on = True
                    status = "THRUSTING"
                else:
                    apogee_achieved = True
                    engine_on = False
                    status = "CUTOFF"
            # else:
            #     engine_on = False
            #     status = "COASTING"
        elif params["propellant"] == "solid":
            engine_on = launched and state[4] > physics.dry_mass
            if engine_on:
                status = "THRUSTING"
            elif vy > 0:
                status = "COASTING"

        # Landing/Chute Logic
        if vy < 0 and y < 8000:
            status = "CHUTES DEPLOYED"

        if y < 0:
            timer.stop()
            hud.close_btn.setEnabled(True)
            hud.abort_btn.setEnabled(False)
            status = "LANDED"
            hud.status_lbl.setText(f"STATUS: {status}")

        # Update Apogee
        if y > apogee:
            apogee = y
            hud.apogee_lbl.setText(f"Achieved Apogee: {apogee:.1f} m")

        if vy > 0:
            pred_ap = y + (vy**2) / (2 * g)
            hud.pred_apogee.setText(f"Pred Apogee: {pred_ap:.1f} m")

        hud.update(t, x, y, vx, vy, m, q)

        thrust_on = engine_on and not aborted and state[4] > physics.dry_mass
        v = np.hypot(vx, vy)

        # ---------- CHUTE OVERRIDE ----------
        if physics.chute_state > 0:
            ang = 0.0
            engine_on = False
            status = "CHUTES DEPLOYED"
        else:
            # ---------- RETRO BRAKE ENTRY ----------
            if params["retro"]:
                impact_v = np.sqrt(max(0, 2 * g * y))
                if not in_retro and vy < 0 and impact_v > 120 and m > physics.dry_mass:
                    in_retro = True
                    engine_on = True
                    direction = "retrograde"
                    status = "RETRO BRAKE"

                # ---------- RETRO BRAKE EXIT ----------
                elif in_retro and vy < 0 and impact_v > 120 and m <= physics.dry_mass:
                    engine_on = False
                    direction = "retrograde"
                    status = "RE-ENTRY"

            # ---------- NORMAL FLIGHT ----------
            if not in_retro:
                if v < 1.0:
                    ang = 0.0
                    engine_on = True
                    status = "THRUSTING"
                else:
                    ang = np.arctan2(vy, vx) - pi/2
                    if status not in ["RE-ENTRY"]:
                        direction = "prograde"
                    if vy < 0 and status not in ["LANDED", "RETRO BREAK", "ABORT"]:
                        status = "RE-ENTRY"
                        direction = "retrograde"
            # ---------- RETRO ATTITUDE ----------
            else:
                ang = np.arctan2(vy, vx) + pi/2

        # Final Status Update
        if not in_retro and vy < 0 and physics.chute_state == 0 and status not in ["LANDED", "ABORT"]:
            status = "RE-ENTRY"
            direction = "retrograde"

        hud.status_lbl.setText(f"STATUS: {status}")
        rocket_view.update_attitude(ang, thrust_on)

        speed = np.hypot(vx, vy)
        tv_alt.update(t, y)
        tv_vel.update(t, speed)

    except Exception as e:
        print("\n🚨 FATAL ERROR — shutting down simulation")
        traceback.print_exc()
        timer.stop()
        for w in QApplication.topLevelWidgets():
            w.close()
        QApplication.quit()

# ---------- BUTTON CALLBACKS ----------
def launch():
    global launched, engine_on, status
    launched = True
    engine_on = True
    status = "THRUSTING"
    hud.launch_btn.setEnabled(False)
    hud.close_btn.setEnabled(False)
    hud.abort_btn.setEnabled(True)

def abort():
    global aborted, status
    reply = QMessageBox.question(
        hud, "Confirm Abort", "Are you sure you want to ABORT the mission?",
        QMessageBox.Yes | QMessageBox.No
    )
    if reply == QMessageBox.Yes:
        aborted = True
        status = "ABORT"
        hud.status_lbl.setText(f"STATUS: {status}")
        hud.abort_btn.setEnabled(False)
        hud.close_btn.setEnabled(True)
        rocket_view.explode()

def close_all():
    timer.stop()
    for w in QApplication.topLevelWidgets():
        w.close()
    QApplication.quit()

def set_warp(w):
    global warp
    warp = w

# ---------- CONNECT SIGNALS ----------
hud.w1.clicked.connect(lambda: set_warp(1))
hud.w2.clicked.connect(lambda: set_warp(2))
hud.w4.clicked.connect(lambda: set_warp(4))
hud.w8.clicked.connect(lambda: set_warp(8))
hud.close_btn.clicked.connect(close_all)
hud.launch_btn.clicked.connect(launch)
hud.abort_btn.clicked.connect(abort)

# ---------- TIMER ----------
rocket_view.update_attitude(0, False)
timer = QTimer()
timer.timeout.connect(step)
timer.start(200)

sys.exit(app.exec())
