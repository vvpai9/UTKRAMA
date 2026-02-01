from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QWidget, QVBoxLayout

class TelemetryPlot(QWidget):
    def __init__(self, title, xlabel, ylabel):
        super().__init__()
        self.setWindowTitle(title)
        self.fig = Figure()
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)

        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)

        self.x, self.y = [], []
        self.blink = True   # toggle state

    def update(self, xv, yv):
        self.x.append(xv)
        self.y.append(yv)

        self.ax.clear()
        self.ax.plot(self.x, self.y, 'b')

        # blinking live point
        if self.blink:
            self.ax.plot(self.x[-1], self.y[-1], 'ro')

        self.blink = not self.blink

        self.ax.set_xlabel(self.ax.get_xlabel())
        self.ax.set_ylabel(self.ax.get_ylabel())
        self.canvas.draw()
