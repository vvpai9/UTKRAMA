from PySide6.QtWidgets import *
from PySide6.QtCore import Qt

class MissionDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mission Setup")

        # ---- Mission Mode ----
        self.mode_sub = QRadioButton("Suborbital")
        self.mode_orb = QRadioButton("Orbital")
        self.mode_sub.setChecked(True)

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.mode_sub)
        self.mode_group.addButton(self.mode_orb)

        # ---- Inputs ----
        self.apogee = QLineEdit("50000")
        self.fuel = QLineEdit("150")
        self.dry = QLineEdit("350")
        self.margin = QLineEdit("3000")

        # ---- Propellant ----
        self.prop_solid = QRadioButton("Solid")
        self.prop_liquid = QRadioButton("Liquid")
        self.prop_solid.setChecked(True)

        self.prop_group = QButtonGroup(self)
        self.prop_group.addButton(self.prop_solid)
        self.prop_group.addButton(self.prop_liquid)

        # ---- Retro Brake ----
        self.retro_chk = QCheckBox("Enable Retro Braking")
        self.retro_chk.setEnabled(False)
        self.retro_chk.setChecked(False)

        # ---- Signals ----
        self.prop_liquid.toggled.connect(self._sync_options)
        self.prop_solid.toggled.connect(self._sync_options)
        self.mode_sub.toggled.connect(self._sync_options)
        self.mode_orb.toggled.connect(self._sync_options)

        # ---- Layout ----
        form = QFormLayout()
        form.addRow("Mission Mode", self.mode_sub)
        form.addRow("", self.mode_orb)
        form.addRow("Target Apogee (m)", self.apogee)
        form.addRow("Fuel Mass (kg)", self.fuel)
        form.addRow("Dry Mass (kg)", self.dry)
        form.addRow("Apogee Safety Margin (m)", self.margin)
        form.addRow("Propellant", self.prop_solid)
        form.addRow("", self.prop_liquid)
        form.addRow("Recovery", self.retro_chk)

        self.btn = QPushButton("Start Mission")
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.btn)

        self.btn.clicked.connect(self.accept)

        self._sync_options()

    def _sync_options(self):
        # Orbital only allowed with liquid
        if self.prop_solid.isChecked():
            self.mode_orb.setEnabled(False)
            if self.mode_orb.isChecked():
                self.mode_sub.setChecked(True)
        else:
            self.mode_orb.setEnabled(True)

        # Retro braking only for liquid + suborbital
        if self.prop_liquid.isChecked() and self.mode_sub.isChecked():
            self.retro_chk.setEnabled(True)
        else:
            self.retro_chk.setEnabled(False)
            self.retro_chk.setChecked(False)

    def get_params(self):
        try:
            alt = float(self.apogee.text())
            fuel = float(self.fuel.text())
            dry = float(self.dry.text())
            margin = float(self.margin.text())

            if alt <= 0 or fuel <= 0 or dry <= 0 or margin < 0:
                raise ValueError

            prop = "liquid" if self.prop_liquid.isChecked() else "solid"
            mode = "orbital" if self.mode_orb.isChecked() else "suborbital"
            retro = self.retro_chk.isChecked()

            return dict(
                mode=mode,
                apogee=alt,
                fuel=fuel,
                dry=dry,
                margin=margin,
                propellant=prop,
                retro=retro
            )
        except:
            QMessageBox.critical(self, "Error", "Invalid mission parameters")
            return None
