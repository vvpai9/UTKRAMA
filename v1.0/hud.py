from PySide6.QtWidgets import *
from PySide6.QtCore import QTimer
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np
import physics

class HUD(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("2D Rocket HUD")

        self.launch_btn = QPushButton("LAUNCH")
        self.abort_btn = QPushButton("ABORT")
        self.abort_btn.setEnabled(False)

        self.close_btn = QPushButton("CLOSE")
        self.close_btn.setEnabled(True)  # initially allowed

        self.apogee_lbl = QLabel("Achieved Apogee: 0 m")
        self.pred_apogee = QLabel("Pred Apogee: 0.0 m")

        self.time_lbl = QLabel("Time: 0.0 s")
        self.alt = QLabel("Altitude: 0 m")
        self.vel = QLabel("Speed: 0 m/s")
        self.mass = QLabel("Mass: 0 kg")
        self.q = QLabel("Dynamic Q: 0 Pa")
        self.maxq = QLabel("MAX-Q: SAFE")
        self.maxq.setStyleSheet("color:green;")

        self.chute_lbl = QLabel("CHUTES: STOWED")

        self.status_lbl = QLabel ("STATUS: READY")

        self.w1 = QRadioButton("1x")
        self.w2 = QRadioButton("2x")
        self.w4 = QRadioButton("4x")
        self.w8 = QRadioButton("8x")

        self.w1.setChecked(True)


        self.blink = True
        self.fig = Figure()
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("Downrange (m)")
        self.ax.set_ylabel("Altitude (m)")
        self.rocket_body, = self.ax.plot([], [], 'ro')   # rocket position
        self.rocket_dir, = self.ax.plot([], [], 'r-')    # orientation line


        side = QVBoxLayout()
        for w in [self.time_lbl, self.alt, self.vel, self.apogee_lbl, self.pred_apogee, self.mass, self.q, self.maxq, self.chute_lbl, self.status_lbl, self.w1, self.w2, self.w4, self.w8, self.launch_btn, self.abort_btn, self.close_btn]:
            side.addWidget(w)

        main = QHBoxLayout(self)
        main.addLayout(side)
        main.addWidget(self.canvas)

        self.traj_x = []
        self.traj_y = []
        self.max_q = 0

    def update(self, t, x, y, vx, vy, m, q):
        self.traj_x.append(x)
        self.traj_y.append(y)

        self.time_lbl.setText(f"Time: {t: .1f} s")
        self.alt.setText(f"Altitude: {y:.1f} m")
        self.vel.setText(f"Speed: {((vx**2+vy**2)**0.5):.1f} m/s")
        self.mass.setText(f"Mass: {m:.1f} kg")
        self.q.setText(f"Dynamic Q: {q:.1f} Pa")

        if q > self.max_q:
            self.max_q = q
        if abs(q - self.max_q) < 50 and q > 5000:
            self.maxq.setText("MAX-Q")
            self.maxq.setStyleSheet("color:red;")
        else:
            self.maxq.setText("MAX-Q: SAFE")
            self.maxq.setStyleSheet("color:green;")

        if physics.chute_state == 0:
            self.chute_lbl.setText("CHUTES: STOWED")
        elif physics.chute_state == 1:
            self.chute_lbl.setText("CHUTES: DROGUE")
            self.status_lbl.setText("STATUS: CHUTES DEPLOYED")
            self.chute_lbl.setStyleSheet("color: orange;")
        else:
            self.chute_lbl.setText("CHUTES: MAIN")
            self.status_lbl.setText("STATUS: CHUTES DEPLOYED")
            self.chute_lbl.setStyleSheet("color: cyan;")


        self.ax.clear()
        self.ax.plot(self.traj_x, self.traj_y, 'b')

        # rocket position
        if self.blink:
            self.ax.plot(x, y, 'ro')

        self.blink = not self.blink

        self.ax.set_xlabel("Downrange (m)")
        self.ax.set_ylabel("Altitude (m)")

        self.canvas.draw()
