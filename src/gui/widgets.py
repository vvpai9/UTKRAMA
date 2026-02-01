from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QPolygonF, QTransform
import matplotlib
matplotlib.use('qtagg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
import random

class RocketView(QWidget):
    def __init__(self, simulation):
        super().__init__()
        self.simulation = simulation
        self.flame_flicker = 0
        self.setMinimumSize(300, 300)
        self.setStyleSheet("background-color: #87CEEB;") # Sky blue default

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Background (Sky to Space gradient based on altitude?)
        # For simplicity, just solid color or simple gradient depending on 'atmosphere' logic
        # Or just clear logic:
        alt = 0
        if self.simulation.rocket:
            r_vec = self.simulation.rocket.position
            alt = np.linalg.norm(r_vec) - self.simulation.planet.radius
        
        # Simple sky color interpolation
        # 0m: Blue (135, 206, 235) -> 100km: Black (0, 0, 0)
        max_atm = 100000
        factor = min(alt / max_atm, 1.0)
        r = int(135 * (1 - factor))
        g = int(206 * (1 - factor))
        b = int(235 * (1 - factor))
        painter.fillRect(self.rect(), QColor(r, g, b))
        
        # 2. Draw stars if space
        if factor > 0.8:
            painter.setPen(QColor(255, 255, 255))
            for _ in range(20):
                x = random.randint(0, self.width())
                y = random.randint(0, self.height())
                painter.drawPoint(x, y)

        if not self.simulation.rocket:
            return

        # 3. Setup Coordinate System
        # Center the rocket in the view
        cx = self.width() / 2
        cy = self.height() / 2
        
        painter.translate(cx, cy)
        
        # 4. Camera Zoom/Scale?
        # Fixed scale for rocket size
        
        # 5. Rotate based on rocket orientation
        # Rocket orientation is in radians. 
        # 0 rad = ? In simulation we said 0 is Vertical? 
        # If simulation: 0 = Vertical/Radial Out. 
        # QPainter: 0 is Right (3 o'clock). -90 is Up.
        # So we rotate by (orientation - 90 deg)? 
        # Let's assume Sim 0 = Up. Painter needs -90 offset.
        angle_deg = np.degrees(self.simulation.rocket.orientation)
        # Sim Angle: 90 deg = Up. 0 deg = Right.
        # Painter: Rocket drawn pointing Up (-Y). 0 Rot = Up. +90 Rot = Right.
        # Map: 90 -> 0. 0 -> 90.
        # Rotation = 90 - angle_deg
        
        painter.rotate(90 - angle_deg) 
        # Wait, if I rotate convex system, Up is still Up relative to screen if 0?
        # QPainter coordinate: +Y is Down. +X is Right.
        # So 'Up' is -Y.
        # If I want to draw 'Up' at 0 degrees, I should define my shape pointing to -Y.
        # Then rotation: Positive rotation rotates Coordinate System Clockwise.
        # Sim Angle: usually CCW is positive? Or CW?
        # In sim, Thrust = Right * sin + Up * cos.
        # Up = (0,1). Right = (0, -1) visual? 
        # Let's just draw the rocket pointing UP (-Y) and rotate by angle.
        # If rocket leans Right (positive angle?), we rotate CW.
        
        # 6. Draw Rocket
        # Width 20, Height 60
        w = 20
        h = 60
        
        # Body
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(240, 240, 240)))
        # Rect -10, -30, 20, 60? 
        # Pointing Up means top is at -h/2. Bottom at +h/2.
        painter.drawRect(QRectF(-w/2, -h/2, w, h))
        
        # Nose cone
        path = QPolygonF()
        path.append(QPointF(-w/2, -h/2))
        path.append(QPointF(w/2, -h/2))
        path.append(QPointF(0, -h/2 - 20))
        painter.setBrush(QBrush(QColor(200, 0, 0))) # Red nose
        painter.drawPolygon(path)
        
        # Fins
        painter.setBrush(QBrush(QColor(100, 100, 100)))
        path_fin = QPolygonF()
        path_fin.append(QPointF(-w/2, h/2 - 10))
        path_fin.append(QPointF(-w/2 - 10, h/2 + 10))
        path_fin.append(QPointF(-w/2, h/2 + 10))
        painter.drawPolygon(path_fin)
        
        path_fin2 = QPolygonF()
        path_fin2.append(QPointF(w/2, h/2 - 10))
        path_fin2.append(QPointF(w/2 + 10, h/2 + 10))
        path_fin2.append(QPointF(w/2, h/2 + 10))
        painter.drawPolygon(path_fin2)
        
        # 7. Draw Flame if Thrusting
        if self.simulation.rocket.engine.running:
            throttle = self.simulation.rocket.engine.throttle
            self.flame_flicker = (self.flame_flicker + 1) % 3
            # Base length 30 * throttle. Plus flicker.
            flame_len = (30 * throttle) + random.randint(0, 10)
            
            painter.setBrush(QBrush(QColor(255, 140, 0))) # Orange
            path_flame = QPolygonF()
            path_flame.append(QPointF(-w/2 + 5, h/2 + 10))
            path_flame.append(QPointF(w/2 - 5, h/2 + 10))
            path_flame.append(QPointF(0, h/2 + 10 + flame_len))
            painter.drawPolygon(path_flame)
            
            # Inner flame
            painter.setBrush(QBrush(QColor(255, 255, 0))) # Yellow
            path_flame2 = QPolygonF()
            path_flame2.append(QPointF(-w/2 + 8, h/2 + 10))
            path_flame2.append(QPointF(w/2 - 8, h/2 + 10))
            path_flame2.append(QPointF(0, h/2 + 10 + flame_len * 0.6))
            painter.drawPolygon(path_flame2)

        # Chutes
        if self.simulation.rocket.status == "DROGUE_CHUTE":
            # Draw small chute trailing
            painter.setBrush(QBrush(QColor(200, 200, 200)))
            painter.setPen(QPen(QColor(255, 255, 255)))
            # Lines
            painter.drawLine(QPointF(-w/2, -h/2), QPointF(-20, -h/2 - 40))
            painter.drawLine(QPointF(w/2, -h/2), QPointF(20, -h/2 - 40))
            # Canopy
            painter.drawPie(QRectF(-20, -h/2 - 55, 40, 30), 0, 180*16)
            
        elif self.simulation.rocket.status == "MAIN_CHUTE":
            # Draw big chute
            painter.setBrush(QBrush(QColor(255, 100, 100))) # Red/White
            painter.setPen(QPen(QColor(255, 255, 255)))
            # Lines
            painter.drawLine(QPointF(-w/2, -h/2), QPointF(-40, -h/2 - 80))
            painter.drawLine(QPointF(w/2, -h/2), QPointF(40, -h/2 - 80))
            # Canopy
            painter.drawPie(QRectF(-60, -h/2 - 120, 120, 80), 0, 180*16)
            
        # Explosion Check
        if self.simulation.rocket.status == "CRASHED" or self.simulation.rocket.status == "ABORT":
             # Draw Realistic Explosion (Particles/Shards)
             for _ in range(15):
                 ex = random.randint(-50, 50)
                 ey = random.randint(-50, 50)
                 ew = random.randint(5, 20)
                 # Fire color
                 color = QColor(255, random.randint(0, 165), 0, 200)
                 painter.setBrush(QBrush(color))
                 painter.setPen(Qt.PenStyle.NoPen)
                 painter.drawEllipse(QPointF(ex, ey), ew, ew)
             
             # Smoke
             for _ in range(10):
                 ex = random.randint(-40, 40)
                 ey = random.randint(-40, 40)
                 ew = random.randint(10, 30)
                 painter.setBrush(QBrush(QColor(100, 100, 100, 150)))
                 painter.drawEllipse(QPointF(ex, ey), ew, ew)


class PlotWidget(QWidget):
    def __init__(self, title, xlabel, ylabel):
        super().__init__()
        self.layout = QVBoxLayout()
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)
        
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title(title)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        self.line, = self.ax.plot([], [], 'b-')
        self.point, = self.ax.plot([], [], 'ro') # Blinking point
        
        self.x_data = []
        self.y_data = []
        
        # Blinking Timer
        self._blink_timer = QTimer()
        self._blink_timer.timeout.connect(self._toggle_point)
        self._blink_timer.start(500) # 500ms
        self._point_visible = True
        
    def _toggle_point(self):
        if not self.x_data:
            return
        self._point_visible = not self._point_visible
        self.point.set_visible(self._point_visible)
        self.canvas.draw_idle()

    def update_data(self, x, y):
        self.x_data.append(x)
        self.y_data.append(y)
        
        self.line.set_data(self.x_data, self.y_data)
        self.point.set_data([x], [y])
        self.point.set_visible(True) # Force visible on update
        self._point_visible = True
        
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()
        
    def clear(self):
        self.x_data = []
        self.y_data = []
        self.line.set_data([], [])
        self.point.set_data([], [])
        self.canvas.draw_idle()
