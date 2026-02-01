from PySide6.QtWidgets import (QMainWindow, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QTextEdit, QMessageBox, QFrame)
from PySide6.QtCore import QTimer, Qt
from src.core.simulation import Simulation
from src.gui.widgets import RocketView, PlotWidget
from src.gui.dialogs import LaunchConfigDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("2D Rocket Launch Simulator")
        self.setGeometry(100, 100, 1200, 800)
        
        self.simulation = Simulation()
        self.simulation.guidance = None # Will be init in config
        
        self.init_ui()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.time_warp = 1.0
        
        # Open Config Dialog on Start
        self.show_config_dialog()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main Grid Layout (2x2)
        grid = QGridLayout()
        central_widget.setLayout(grid)
        
        # 1. Mini Console & Altitude vs Downrange (Top Left)
        self.console_panel = QWidget()
        console_layout = QVBoxLayout()
        
        self.telemetry_label = QLabel("Waiting for Launch Configuration...")
        self.telemetry_label.setStyleSheet("font-family: Monospace; font-size: 12px; background-color: black; color: lime; padding: 10px;")
        self.telemetry_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.events_log = QTextEdit()
        self.events_log.setReadOnly(True)
        self.events_log.setStyleSheet("font-family: Monospace; font-size: 10px; background-color: #222; color: #ddd;")
        self.events_log.setMaximumHeight(150)
        
        self.alt_range_plot = PlotWidget("Altitude vs Downrange", "Downrange (m)", "Altitude (m)")
        
        console_layout.addWidget(self.telemetry_label)
        console_layout.addWidget(self.events_log)
        console_layout.addWidget(self.alt_range_plot)
        self.console_panel.setLayout(console_layout)
        
        # 2. External View (Top Right)
        self.rocket_view = RocketView(self.simulation)
        
        # 3. Time vs Altitude (Bottom Left)
        self.time_alt_plot = PlotWidget("Time vs Altitude", "Time (s)", "Altitude (m)")
        
        # 4. Time vs Velocity (Bottom Right)
        self.time_vel_plot = PlotWidget("Time vs Velocity", "Time (s)", "Velocity (m/s)")
        
        # Add to Grid
        grid.addWidget(self.console_panel, 0, 0)
        grid.addWidget(self.rocket_view, 0, 1)
        grid.addWidget(self.time_alt_plot, 1, 0)
        grid.addWidget(self.time_vel_plot, 1, 1)
        
        # Control Dock (Bottom)
        control_panel = QFrame()
        control_layout = QHBoxLayout()
        
        self.btn_launch = QPushButton("LAUNCH")
        self.btn_launch.clicked.connect(self.start_launch)
        self.btn_launch.setEnabled(False)
        self.btn_launch.setStyleSheet("background-color: green; color: white; font-weight: bold;")
        
        self.btn_pause = QPushButton("PAUSE")
        self.btn_pause.setCheckable(True)
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.btn_pause.setEnabled(False) # Enable on launch
        
        self.btn_abort = QPushButton("ABORT")
        self.btn_abort.clicked.connect(self.request_abort)
        self.btn_abort.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        self.btn_abort.setEnabled(False) # Disabled until launch
        
        self.btn_close = QPushButton("CLOSE")
        self.btn_close.clicked.connect(self.close)
        
        self.btn_warp_1x = QPushButton("1x")
        self.btn_warp_2x = QPushButton("2x")
        self.btn_warp_4x = QPushButton("4x")
        self.btn_warp_8x = QPushButton("8x")
        
        self.btn_warp_1x.clicked.connect(lambda: self.set_warp(1))
        self.btn_warp_2x.clicked.connect(lambda: self.set_warp(2))
        self.btn_warp_4x.clicked.connect(lambda: self.set_warp(4))
        self.btn_warp_8x.clicked.connect(lambda: self.set_warp(8))
        
        warp_layout = QHBoxLayout()
        warp_layout.addWidget(QLabel("Time Warp:"))
        warp_layout.addWidget(self.btn_warp_1x)
        warp_layout.addWidget(self.btn_warp_2x)
        warp_layout.addWidget(self.btn_warp_4x)
        warp_layout.addWidget(self.btn_warp_8x)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_launch)
        btn_layout.addWidget(self.btn_pause)
        btn_layout.addWidget(self.btn_abort)
        btn_layout.addWidget(self.btn_close)
        
        control_layout.addLayout(warp_layout)
        control_layout.addStretch() # Add stretch between warp and control buttons
        control_layout.addLayout(btn_layout)
        
        control_panel.setLayout(control_layout)
        
        # Add Control Panel to layout (e.g. Row 2, spanning 2 columns)
        grid.addWidget(control_panel, 2, 0, 1, 2)

    def show_config_dialog(self):
        dialog = LaunchConfigDialog(self.simulation)
        if dialog.exec():
            # Mission Feasible & Accepted
            cfg = dialog.config
            self.simulation.initialize(
                cfg['planet'], cfg['apoapsis'], cfg['safety_margin'], cfg['dry_mass'], cfg['fuel_mass'], cfg['propellant']
            )
            self.simulation.guidance.set_logger(self.log_event)
            self.btn_launch.setEnabled(True)
            self.log_event(f"Mission Configured: Target Ap {cfg['apoapsis']}km, Planet {cfg['planet']}")
            
            # Start Log File
            self.log_file_path = "mission_log.txt"
            with open(self.log_file_path, "w") as f:
                f.write(f"Mission Log - Planet: {cfg['planet']} - Target: {cfg['apoapsis']}km\n")
                f.write("-" * 50 + "\n")
            
            # Reset Displays
            self.alt_range_plot.clear()
            self.time_alt_plot.clear()
            self.time_vel_plot.clear()
        else:
            # User cancelled or failed
            pass

    def toggle_pause(self, checked):
        if checked:
            self.btn_pause.setText("RESUME")
            self.timer.stop()
            self.log_event("Simulation PAUSED")
        else:
            self.btn_pause.setText("PAUSE")
            self.timer.start(50)
            self.log_event("Simulation RESUMED")

    def start_launch(self):
        self.simulation.rocket.status = "THRUSTING"
        self.simulation.rocket.ignite_engine()
        self.timer.start(50) # 20 FPS GUI update
        self.log_event("LAUNCH INITIATED")
        self.btn_launch.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_abort.setEnabled(True)
        self.btn_close.setEnabled(False)

    def request_abort(self):
        reply = QMessageBox.question(self, 'Confirm Abort', 
                                     "Are you sure you want to ABORT the mission?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.simulation.rocket.status = "ABORT"
            self.simulation.rocket.cutoff_engine()
            self.log_event("!!! MISSION ABORTED !!!")
            self.rocket_view.update() # Trigger explosion draw
            self.btn_abort.setEnabled(False)
            self.btn_close.setEnabled(True)

    def set_warp(self, factor):
        self.time_warp = float(factor)
        self.log_event(f"Time Warp set to {factor}x")

    def log_event(self, message):
        timestamp = f"[{self.simulation.time:.1f}s]"
        full_msg = f"{timestamp} {message}"
        self.events_log.append(full_msg)
        
        # File Logging
        if hasattr(self, 'log_file_path'):
            try:
                with open(self.log_file_path, "a") as f:
                    f.write(full_msg + "\n")
            except Exception:
                pass

    def update_simulation(self):
        # Run simulation steps
        # dt = 0.1s in simulation.
        # If timer is 50ms (0.05s) real time.
        # At 1x warp, we want sim time to advance 0.05s.
        # So sim steps = 1 * (0.05 / 0.1) = 0.5 steps?
        # Better: Fixed dt = 0.1.
        # We run N steps per frame.
        # Real dt = 0.05s. Target Sim dt = 0.05 * warp.
        # Steps = Target Sim dt / Fixed dt = 0.05 * warp / 0.1 = 0.5 * warp
        
        sim_dt = 0.1
        target_advance = 0.05 * self.time_warp
        
        # Accumulate time or just run loop
        steps = int(target_advance / sim_dt)
        if steps < 1: steps = 1 # Minimum 1 step per frame if running
        
        for _ in range(steps):
             if self.simulation.rocket.status in ["CRASHED", "LANDED", "ABORT"]:
                 break
             self.simulation.step(sim_dt)
        
        self.update_telemetry()
        self.rocket_view.update()

    def update_telemetry(self):
        r = self.simulation.rocket
        physics_time = self.simulation.time
        
        alt = r.position[1] - self.simulation.planet.radius # y - R? 
        # Wait, if pos is (0, R) initially. y is R.
        # Sim logic: altitude = norm(pos) - R. Correct.
        alt = list(self.simulation.history['altitude'])[-1] if self.simulation.history['altitude'] else 0
        vel = list(self.simulation.history['velocity'])[-1] if self.simulation.history['velocity'] else 0
        
        # Downrange?
        # If launched vertical from (0,R), x is downrange approximation
        downrange = r.position[0]
        
        # Dynamic Q?
        q = list(self.simulation.history['q'])[-1] if self.simulation.history['q'] else 0
        apo = list(self.simulation.history['apoapsis'])[-1] if self.simulation.history.get('apoapsis') else 0
        peri = list(self.simulation.history['periapsis'])[-1] if self.simulation.history.get('periapsis') else 0
        
        achieved = self.simulation._achieved_apoapsis if hasattr(self.simulation, '_achieved_apoapsis') else 0
        
        status_text = f"""
Time: {physics_time:.1f} s
Altitude: {alt/1000:.2f} km
Velocity: {vel:.1f} m/s
Downrange: {downrange/1000:.2f} km

Status: {r.status}
Fuel: {r.fuel_mass:.1f} kg
Throttle: {r.engine.throttle*100:.0f}%
Dynamic Q: {q:.0f} Pa

Target Apoapsis: {self.simulation.target_apoapsis/1000:.1f} km
Predicted Apoapsis: {apo/1000:.1f} km
Achieved Apoapsis: {achieved/1000:.1f} km
"""
        self.telemetry_label.setText(status_text)
        
        # Update Plots (decimate for performance if needed)
        if len(self.simulation.history['time']) > len(self.time_alt_plot.x_data):
            # Only update with new data points
            # Sim history updates every 0.1s * 5 = 0.5s ?
            # Logic in simulation.py: "if int(self.time * 10) % 5 == 0" -> every 0.5s
            
            # Just push all new history to plots
            self.time_alt_plot.update_data(physics_time, alt)
            self.time_vel_plot.update_data(physics_time, vel)
            self.alt_range_plot.update_data(downrange, alt)
        
        # Check specific events
        if r.status in ["CRASHED", "LANDED", "ABORT", "IMPACT DETECTED"]:
            if self.timer.isActive():
                 self.timer.stop()
                 if r.status == "CRASHED":
                     self.log_event("IMPACT DETECTED")
                     QMessageBox.critical(self, "Failure", "Rocket Crashed!")
                 elif r.status == "LANDED":
                     self.log_event("TOUCHDOWN CONFIRMED")
                     QMessageBox.information(self, "Success", "Rocket Landed Safely!")
            
            self.btn_launch.setEnabled(False)
            self.btn_pause.setEnabled(False)
            self.btn_abort.setEnabled(False)
            self.btn_close.setEnabled(True)
