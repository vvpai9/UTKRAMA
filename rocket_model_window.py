import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Polygon
from PySide6.QtCore import QTimer

class RocketModelWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rocket External View")

        self.fig = Figure()
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.ax = self.fig.add_subplot(111)

        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)

        self._define_geometry()
        self._setup_axes()

    def _setup_axes(self):
        self.ax.set_aspect("equal")
        self.ax.set_xlim(-6, 6)
        self.ax.set_ylim(-10, 10)
        self.ax.axis("off")

    def _define_geometry(self):
        # local rocket coordinates (upright)
        self.body = np.array([
            [-0.6,-4], [0.6,-4], [0.6,3], [-0.6,3]
        ])

        self.nose = np.array([
            [-0.6,3], [0.6,3], [0,5]
        ])

        self.finL = np.array([
            [-0.6,-4], [-2,-6], [-0.6,-6]
        ])

        self.finR = np.array([
            [0.6,-4], [2,-6], [0.6,-6]
        ])

        self.flame = np.array([
            [0,-4], [0.7,-7], [-0.7,-7]
        ])

    def _rotate(self, pts, angle):
        R = np.array([
            [np.cos(angle), -np.sin(angle)],
            [np.sin(angle),  np.cos(angle)]
        ])
        return pts @ R.T

    def update_attitude(self, angle, thrust_on=True):
        self.ax.clear()
        self._setup_axes()

        body = self._rotate(self.body, angle)
        nose = self._rotate(self.nose, angle)
        finL = self._rotate(self.finL, angle)
        finR = self._rotate(self.finR, angle)
        flame = self._rotate(self.flame, angle)

        self.ax.add_patch(Polygon(body, color="silver"))
        self.ax.add_patch(Polygon(nose, color="blue"))
        self.ax.add_patch(Polygon(finL, color="red"))
        self.ax.add_patch(Polygon(finR, color="red"))

        if thrust_on:
            self.ax.add_patch(Polygon(flame, color="orange"))

        self.canvas.draw()

    def explode(self):
        self.ax.clear()
        self._setup_axes()

        self.blast_radius = 0.2
        self.blast_timer = QTimer()
        self.blast_timer.timeout.connect(self._blast_step)
        self.blast_timer.start(50)

    def _blast_step(self):
        self.ax.clear()
        self._setup_axes()

        angles = np.linspace(0, 2*np.pi, 30)
        x = self.blast_radius * np.cos(angles)
        y = self.blast_radius * np.sin(angles)

        self.ax.scatter(x, y, color="orange", s=60)
        self.ax.scatter(x*0.5, y*0.5, color="red", s=40)

        self.blast_radius += 0.4

        if self.blast_radius > 8:
            self.blast_timer.stop()
            self._clear_white()   # 👈 clears screen after blast

        self.canvas.draw()


    def _clear_white(self):
        self.ax.clear()
        self._setup_axes()
        self.canvas.draw()



