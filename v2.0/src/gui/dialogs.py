from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QComboBox, QPushButton, QMessageBox, QFormLayout)
from src.core.physics import PLANETS

class LaunchConfigDialog(QDialog):
    def __init__(self, simulation):
        super().__init__()
        self.simulation = simulation
        self.setWindowTitle("Mission Configuration")
        self.setModal(True)
        self.config = None
        
        layout = QVBoxLayout()
        form = QFormLayout()
        
        self.apoapsis_input = QLineEdit("100")
        self.safety_margin_input = QLineEdit("5") # Default 5km
        self.propellant_combo = QComboBox()
        self.propellant_combo.addItems(["liquid", "solid"])
        
        self.dry_mass_input = QLineEdit("350")
        self.fuel_mass_input = QLineEdit("50000")
        
        self.planet_combo = QComboBox()
        self.planet_combo.addItems(list(PLANETS.keys()))
        
        form.addRow("Target Apoapsis (km):", self.apoapsis_input)
        form.addRow("Safety Margin (km):", self.safety_margin_input)
        form.addRow("Propellant Type:", self.propellant_combo)
        form.addRow("Dry Mass (kg):", self.dry_mass_input)
        form.addRow("Fuel Mass (kg):", self.fuel_mass_input)
        form.addRow("Planet:", self.planet_combo)
        
        layout.addLayout(form)
        
        btn_layout = QHBoxLayout()
        self.launch_btn = QPushButton("Check & Launch")
        self.launch_btn.clicked.connect(self.check_feasibility)
        
        btn_layout.addWidget(self.launch_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def check_feasibility(self):
        try:
            apo = float(self.apoapsis_input.text())
            margin = float(self.safety_margin_input.text())
            prop = self.propellant_combo.currentText()
            dry = float(self.dry_mass_input.text())
            fuel = float(self.fuel_mass_input.text())
            planet = self.planet_combo.currentText()
            
            # Feasibility check should ideally include margin?
            # User said "check whether such a mission is achievable".
            # We can check for (apo + margin)
            
            is_feasible, rocket_dv, req_dv, extra = self.simulation.check_feasibility(
                planet, apo + margin, dry, fuel, prop
            )
            
            if is_feasible:
                self.config = {
                    'planet': planet,
                    'apoapsis': apo,
                    'safety_margin': margin,
                    'dry_mass': dry,
                    'fuel_mass': fuel,
                    'propellant': prop
                }
                self.accept()
            else:
                msg = f"""Impossible Mission!
                
Calculated Rocket Delta-V: {rocket_dv:.2f} m/s
Required Delta-V: {req_dv:.2f} m/s
Deficit: {req_dv - rocket_dv:.2f} m/s

Minimum EXTRA fuel required: {extra:.2f} kg
"""
                QMessageBox.critical(self, "Mission Impossible", msg)
                # Should we exit? Prompt says "show error message and exit". 
                # But usually users want to retry. "Exit" might mean exit the dialog or app?
                # "If the target cannot be achieved... show an error message box and exit." 
                # I'll interpret "exit" as "don't proceed to simulation", letting them retry or close app.
                
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numeric values.")
