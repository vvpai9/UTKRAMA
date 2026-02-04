from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QPolygonF, QTransform, QLinearGradient
import matplotlib
matplotlib.use('qtagg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
import random

class Particle:
    def __init__(self, x, y, vx, vy, life, color, size):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size

class Camera:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.zoom = 1.0
        self.target_zoom = 1.0
        
    def teleport(self, x, y):
        """Immediately moves camera to target."""
        self.x = x
        self.y = y
        # Reset zoom too? maybe to default surface zoom
        self.zoom = 10.0 # Close up
        self.target_zoom = 10.0
        
    def update(self, target_pos, dt):
        # Smooth Follow
        # target_pos is (x, y) tuple or list
        # Simple Lerp
        alpha = 5.0 * dt
        self.x += (target_pos[0] - self.x) * alpha
        self.y += (target_pos[1] - self.y) * alpha
        
        # Smooth Zoom
        self.zoom += (self.target_zoom - self.zoom) * 5.0 * dt

    def world_to_screen(self, wx, wy, width, height):
        # Center of screen is camera position
        # Screen X = (World X - Cam X) * Zoom + Width/2
        # Screen Y = (World Y - Cam Y) * Zoom * -1 (Flip Y) + Height/2
        # Note: Physics Y is Up, Screen Y is Down.
        
        sx = (wx - self.x) * self.zoom + width / 2
        sy = height / 2 - (wy - self.y) * self.zoom
        return sx, sy
        
    def screen_to_world(self, sx, sy, width, height):
        # Inverse
        # (sx - w/2) / zoom + cam_x = wx
        wx = (sx - width/2) / self.zoom + self.x
        wy = self.y - (sy - height/2) / self.zoom
        return wx, wy

class StarField:
    def __init__(self, width, height, count=100):
        self.stars = []
        self.width = width
        self.height = height
        for _ in range(count):
            self.stars.append([random.randint(-1000, 1000), random.randint(-1000, 1000), random.uniform(0.5, 2.0)]) # x, y, size

    def update(self, v_rocket, dt):
        # Move stars opposite to rocket
        # Scale factor for parallax? Let's say background is "infinite" so only rotation matters?
        # Actually for 2D side scroller feel, we move them.
        # factor 0.05 to make them feel distant
        dx = -v_rocket[0] * dt * 0.05
        # Screen Y is inverted (Down is +), Sim Y is Up (+).
        # Rocket moving Up (+v_y) -> Should move stars Down (+Screen Y).
        # So we want Positive change in star Y.
        dy = v_rocket[1] * dt * 0.05
        
        for s in self.stars:
            s[0] += dx
            s[1] += dy
            
            # Wrap around (infinite field logic)
            # Center is relative to camera 0,0?
            # If star goes too far, wrap? 
            # Simple approach: Keep them in a 2000x2000 box centered on view? 
            # But view is static texturally?
            # Let's just wrap within a modulo window
            if s[0] > 1000: s[0] -= 2000
            if s[0] < -1000: s[0] += 2000
            if s[1] > 1000: s[1] -= 2000
            if s[1] < -1000: s[1] += 2000

class RocketView(QWidget):
    def __init__(self, simulation):
        super().__init__()
        self.simulation = simulation
        self.setMinimumSize(300, 300)
        self.camera = Camera()
        self.stars = StarField(2000, 2000)
        self.particles = [] 
        
        # Settings
        self.show_trajectory = True
        self.auto_zoom = True
        self.camera_locked = True # Start locked on rocket
        
        # Colors
        self.col_sky_top = QColor(10, 10, 20)
        self.col_sky_bot = QColor(135, 206, 235)
        self.col_ground = QColor(101, 67, 33)
        self.col_traj_burn = QColor(0, 200, 255) # Blue
        self.col_traj_coast = QColor(255, 255, 0) # Yellow
        self.col_traj_drag = QColor(255, 50, 50) # Red
        
        self.flame_flicker = 0
        
        # Mouse Interaction
        self.dragging = False
        self.last_mouse_pos = QPointF(0,0)

    def wheelEvent(self, event):
        # Zoom control
        steps = event.angleDelta().y() / 120.0
        factor = 1.1 ** steps
        self.camera.target_zoom *= factor
        # Clamp zoom
        self.camera.target_zoom = max(0.001, min(100.0, self.camera.target_zoom))
        self.auto_zoom = False # User took control

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.last_mouse_pos = event.position()
            
    def mouseMoveEvent(self, event):
        if self.dragging:
            # Pan Camera -> Unlock Camera
            self.camera_locked = False
            self.auto_zoom = False # Disable auto zoom if panning manually
            
            # Delta Screen
            pos = event.position()
            dsx = pos.x() - self.last_mouse_pos.x()
            dsy = pos.y() - self.last_mouse_pos.y()
            
            # Convert to World Delta
            # World = Screen / Zoom
            dwx = -dsx / self.camera.zoom
            dwy = dsy / self.camera.zoom 
            
            self.camera.x -= dwx
            self.camera.y += dwy 
            
            self.last_mouse_pos = pos
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Update Camera
        dt = 0.05 # Approx
        
        # Calculate Local Vertical Rotation
        # We want the Rocket's position vector to point UP on screen.
        # Rocket Phase Angle
        view_rotation = 0.0
        if self.simulation.rocket:
             rx, ry = self.simulation.rocket.position
             # Angle of position vector in World
             # At (0, R), angle is 90 deg (pi/2). Use arctan2(y, x).
             phase_angle = np.arctan2(ry, rx)
             # We want this angle to be Vertical Up (270 deg / -90 deg in Qt Coords? or Math coords?)
             # Qt Y is Down. Math Y is Up.
             # Standard View: World Y is Up (Sim). Screen Y is Down.
             # We map World Y -> Screen -Y.
             # So World 90 deg -> Screen Up.
             # If Rocket is at 80 deg. To make it 90 deg, we rotate World by +10. (or View by -10).
             # Rotation Correction = (pi/2) - phase_angle.
             # Let's apply this rotation to the painter transform centered on the rocket?
             view_rotation = np.degrees(np.pi/2 - phase_angle)
             
        # Center of rotation: Screen center?
        cx, cy = self.width() / 2, self.height() / 2
        
        painter.translate(cx, cy)
        # Revert rotation as per user. Rocket will tilt, ground will be steep.
        # painter.rotate(-view_rotation) 
        painter.translate(-cx, -cy)
        
        # Particle Physics Update
        new_particles = []
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.life -= dt
            if p.life > 0:
                new_particles.append(p)
        self.particles = new_particles
        
        rocket_pos = np.array([0.0, 6371000.0]) # Default surface
        if self.simulation.rocket:
            rocket_pos = self.simulation.rocket.position
            
            # Auto Zoom Logic (Only if locked?)
            # User said: "Once launched, you can move the camera dynamically"
            # This implies if they move it, auto zoom might also stop or persist?
            # Usually strict tracking implies auto zoom. Free cam implies manual zoom.
            # I'll tie auto_zoom to camera_locked for consistency, OR keep them separate?
            # Existing code: wheelEvent disables auto_zoom. 
            
            if self.auto_zoom and self.camera_locked:
                alt = np.linalg.norm(rocket_pos) - self.simulation.planet.radius
                target_scale = 1000.0 / (alt + 100.0) 
                target_scale = max(0.0005, min(5.0, target_scale))
                self.camera.target_zoom = target_scale
                
            if self.camera_locked:
                self.camera.update(rocket_pos, dt)
            
            # Star Update
            self.stars.update(self.simulation.rocket.velocity, dt)
        
        # 2. Draw Background (Atmosphere Layers)
        # Calculate Altitude at Top/Bottom of Screen
        view_h_world = self.height() / self.camera.zoom
        cam_alt = self.camera.y - self.simulation.planet.radius
        
        alt_top = cam_alt + view_h_world / 2
        alt_bot = cam_alt - view_h_world / 2
        
        # Helper to get color
        def get_sky_color(h):
            # Colors
            c_space = QColor(10, 10, 20)
            c_meso = QColor(20, 20, 60)   # 80km
            c_strato = QColor(50, 80, 160) # 30km
            c_tropo = QColor(135, 206, 235) # 0km
            
            if h > 100000: return c_space
            elif h > 50000:
                # 50k - 100k: Strato -> Space (Meso)
                t = (h - 50000) / 50000
                return QColor(
                    int(c_strato.red() * (1-t) + c_space.red() * t),
                    int(c_strato.green() * (1-t) + c_space.green() * t),
                    int(c_strato.blue() * (1-t) + c_space.blue() * t)
                )
            elif h > 10000:
                # 10k - 50k: Tropo -> Strato
                t = (h - 10000) / 40000
                return QColor(
                    int(c_tropo.red() * (1-t) + c_strato.red() * t),
                    int(c_tropo.green() * (1-t) + c_strato.green() * t),
                    int(c_tropo.blue() * (1-t) + c_strato.blue() * t)
                )
            elif h > 0:
                # 0 - 10k: Surface -> Tropo (Deep Blue)
                # Actually Tropo is Blue. Surface is White-Blue?
                # Keep Tropo solid for now or fade slightly darker?
                return c_tropo
            else:
                 return c_tropo # Underground?
                 
        # Create Gradient
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, get_sky_color(alt_top))
        gradient.setColorAt(1, get_sky_color(alt_bot))
        
        painter.fillRect(self.rect(), QBrush(gradient))
        
        # Stars (Fade in based on Camera Alt, not Rocket)
        # Visibility factor based on SKY darkness (Simple heuristic: Alt > 20km)
        star_alpha = 0
        if cam_alt > 10000:
             star_alpha = min(255, int(255 * (cam_alt - 10000) / 40000))
             
        if star_alpha > 0:
            cx, cy = self.width()/2, self.height()/2
            painter.setPen(Qt.PenStyle.NoPen)
            # alpha = star_alpha
            painter.setBrush(QBrush(QColor(255, 255, 255, star_alpha)))
            for s in self.stars.stars:
                # Simple Parallax: Star Pos - Camera Pos * 0.1?
                # Stars are "infinitely far", only rotation affects them usually.
                # But here we do 2D scroll.
                # Just draw them screen relative + offset
                sx = (s[0] - self.camera.x * 0.001) % 2000 
                sy = (s[1] + self.camera.y * 0.001) % 2000
                if sx > 1000: sx -= 2000
                if sy > 1000: sy -= 2000
                
                # Center on screen
                sx += cx
                sy += cy
                
                painter.drawEllipse(QPointF(sx, sy), s[2], s[2])

        # 3. Coordinate Tranform Setup
        # We want to draw world objects.
        # Can use painter transform or manual project.
        # Manual projection is easier for infinite lines/ground.
        
        # Ground
        # Planet Radius R. Ground is Circle at (0,0) radius R.
        # Rotating the view aligns local ground to horizontal!
        # Draw Planet Circle
        
        planet_r = self.simulation.planet.radius
        
        # Draw Ground
        # Center of Earth in Screen Coords
        earth_sx, earth_sy = self.camera.world_to_screen(0, 0, self.width(), self.height())
        earth_r_screen = planet_r * self.camera.zoom

        # Since we rotated the view, the "Ground" (Surface at R) should be roughly horizontal below the rocket.
        # Just drawing the circle is enough!
        
        painter.setBrush(QBrush(self.col_ground))
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Qt 6 DrawEllipse handles floats
        # Optimization: If huge, maybe issues?
        # But Rotation Logic handles the orientation.
        painter.drawEllipse(QPointF(earth_sx, earth_sy), earth_r_screen, earth_r_screen)
        
        # Trajectory Drawing... (Remove old ground logic lines)
        earth_sx, earth_sy = self.camera.world_to_screen(0, 0, self.width(), self.height())
        earth_r_screen = planet_r * self.camera.zoom
        
        # (Old Ground Logic Removed)

        # 4. Trajectory
        if self.show_trajectory and 'x' in self.simulation.history:
             hist_x = self.simulation.history['x']
             hist_y = self.simulation.history['y']
             hist_status = self.simulation.history.get('status', [])
             
             # Optimization: Don't draw all points.
             # Decimate based on zoom?
             step = max(1, len(hist_x) // 500)
             
             path = QPolygonF()
             # Color coding segments is hard with single Polygon.
             # Draw Lines?
             
             painter.setBrush(Qt.BrushStyle.NoBrush)
             
             # Quick way: Draw one path, single color for now? User asked for multi-color.
             # Multi-color means multiple paths or line segments.
             # Segment loop:
             for i in range(0, len(hist_x) - step, step):
                 p1 = self.camera.world_to_screen(hist_x[i], hist_y[i], self.width(), self.height())
                 p2 = self.camera.world_to_screen(hist_x[i+step], hist_y[i+step], self.width(), self.height())
                 
                 # Clip check?
                 if (p1[0] < -100 and p2[0] < -100) or (p1[0] > self.width()+100 and p2[0] > self.width()+100):
                     continue
                 
                 status = hist_status[i] if i < len(hist_status) else "UNKNOWN"
                 col = self.col_traj_coast
                 if status == "THRUSTING": col = self.col_traj_burn
                 elif status in ["MAIN_CHUTE", "DROGUE_CHUTE", "RETRO_BRAKE"]: col = self.col_traj_drag
                 
                 painter.setPen(QPen(col, 2))
                 painter.drawLine(QPointF(*p1), QPointF(*p2))

        # 5. Rocket
        if self.simulation.rocket:
             r = self.simulation.rocket
             sx, sy = self.camera.world_to_screen(r.position[0], r.position[1], self.width(), self.height())
             
             painter.save()
             painter.translate(sx, sy)
             
             # Rotate
             # Rocket Physics: 0 rad = Right, pi/2 = Up.
             # Sprite: Points Up (-Y).
             # To point Right (0 rad), rotate +90 deg.
             # To point Up (pi/2), rotate 0 deg.
             # Formula: 90 - angle_deg
             
             angle_deg = np.degrees(r.orientation)
             # Restore rotation so rocket tilts
             painter.rotate(90 - angle_deg) 
             if r.status not in ["CRASHED", "ABORT", "IMPACT DETECTED"]:
                 self.draw_rocket_body(painter, r)
             
             painter.restore()

        # 6. Global Particles (Explosions)
        # Explosion Trigger
        if self.simulation.rocket.status in ["CRASHED", "ABORT", "IMPACT DETECTED"]:
             if not self.exploded:
                 self.exploded = True
                 # Spawn particles at Rocket Position
                 rx, ry = self.simulation.rocket.position
                 for _ in range(200):
                     vx = random.uniform(-200, 200)
                     vy = random.uniform(-200, 200)
                     col = QColor(255, random.randint(50, 150), 0)
                     self.particles.append(Particle(rx, ry, vx, vy, random.uniform(1.0, 4.0), col, random.uniform(2, 10)))
        
        # Draw Global Particles
        # Need to project world coords to screen
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self.particles:
             sx, sy = self.camera.world_to_screen(p.x, p.y, self.width(), self.height())
             
             # Fade alpha
             alpha = int(255 * (p.life / p.max_life))
             if alpha < 0: alpha = 0
             p.color.setAlpha(alpha)
             painter.setBrush(QBrush(p.color))
             
             # Scale size by zoom? Or fix pixel size?
             # Fixed size for visibility
             painter.drawEllipse(QPointF(sx, sy), p.size, p.size)

    def draw_rocket_body(self, painter, rocket):
        w = 20
        h = 60
        
        # Update particles
        # ... logic moved to update mainly
        
        # Draw Body (Shaded)
        painter.setPen(Qt.PenStyle.NoPen)
        # Left (Dark)
        painter.setBrush(QBrush(QColor(200, 200, 200))) 
        painter.drawRect(QRectF(-w/2, -h/2, w/2, h))
        # Right (Light)
        painter.setBrush(QBrush(QColor(230, 230, 230)))
        painter.drawRect(QRectF(0, -h/2, w/2, h))
        
        # Nose
        path_nose = QPolygonF([QPointF(-w/2, -h/2), QPointF(w/2, -h/2), QPointF(0, -h/2 - 20)])
        painter.setBrush(QBrush(QColor(200, 50, 50)))
        painter.drawPolygon(path_nose)
        
        # Fins
        painter.setBrush(QBrush(QColor(80, 80, 80)))
        pf1 = QPolygonF([QPointF(-w/2, h/2-10), QPointF(-w/2-10, h/2+10), QPointF(-w/2, h/2+10)])
        painter.drawPolygon(pf1)
        pf2 = QPolygonF([QPointF(w/2, h/2-10), QPointF(w/2+10, h/2+10), QPointF(w/2, h/2+10)])
        painter.drawPolygon(pf2)
        
             # Mach Cone Removed as per user request

             
        # Exhaust
        if rocket.engine.running and rocket.engine.throttle > 0.001:
             throttle = rocket.engine.throttle
             flame_len = 80 * throttle + random.randint(0, 5)
             
             # Core
             painter.setBrush(QBrush(QColor(255, 255, 200)))
             path_core = QPolygonF([QPointF(-5, h/2), QPointF(5, h/2), QPointF(0, h/2 + flame_len*0.8)])
             painter.drawPolygon(path_core)
             
             # Outer
             painter.setBrush(QBrush(QColor(255, 100, 0, 100)))
             path_out = QPolygonF([QPointF(-10, h/2), QPointF(10, h/2), QPointF(0, h/2 + flame_len)])
             painter.drawPolygon(path_out)

        # Chutes
        if rocket.status == "MAIN_CHUTE":
             painter.setBrush(QBrush(QColor(255, 100, 100)))
             painter.setPen(QPen(QColor(255, 255, 255), 1))
             painter.drawLine(QPointF(0, -h/2), QPointF(0, -h/2-80))
             painter.drawPie(QRectF(-60, -h/2 - 140, 120, 80), 0, 180*16)


class PlotWidget(QWidget):
    def __init__(self, title, xlabel, ylabel):
        super().__init__()
        self.layout = QVBoxLayout()
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)
        
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title(title, fontsize=10)
        self.ax.set_xlabel(xlabel, fontsize=8)
        self.ax.set_ylabel(ylabel, fontsize=8)
        self.ax.tick_params(axis='both', which='major', labelsize=8)
        # Explicit margins to ensure labels are never cut off
        self.figure.subplots_adjust(top=0.85, bottom=0.25, left=0.20, right=0.95)
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
