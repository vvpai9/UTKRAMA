from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtGui import QPixmap, QTransform
from PySide6.QtCore import Qt

class AttitudeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rocket Attitude View")

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)

        self.pixmap = QPixmap("rocket.png")
        self.label.setPixmap(self.pixmap)

        layout = QVBoxLayout(self)
        layout.addWidget(self.label)

    def update_attitude(self, angle_rad):
        angle_deg = -angle_rad * 180 / 3.14159  # Qt rotates clockwise
        transform = QTransform().rotate(angle_deg)
        rotated = self.pixmap.transformed(transform, Qt.SmoothTransformation)
        self.label.setPixmap(rotated)
