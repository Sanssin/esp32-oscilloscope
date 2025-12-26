"""
ESP32 Oscilloscope - Dummy Data Mode
Test GUI without ESP32 hardware by generating simulated signals
Run this to test GUI controls and display
"""

import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QComboBox, QLabel, 
                             QSpinBox, QDoubleSpinBox, QGroupBox, QGridLayout,
                             QMessageBox, QSlider, QRadioButton, QButtonGroup, QDial, 
                             QSizePolicy, QFrame, QScrollArea)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QPainter, QPen, QColor
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import time

class RotaryKnob(QDial):
    """Custom rotary knob widget that looks like oscilloscope knob with limited rotation"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(0)
        self.setNotchesVisible(True)
        self.setWrapping(False)  # No wrap around
        self.setFixedSize(70, 70)
        
        # Style
        self.setStyleSheet("""
            QDial {
                background-color: #2a2a2a;
                border: 3px solid #00ff00;
                border-radius: 35px;
            }
        """)
    
    def paintEvent(self, event):
        """Custom paint to show knob pointer/indicator"""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate angle based on value (270 degree rotation range)
        # 0% = -135 degrees (7 o'clock), 100% = +135 degrees (5 o'clock)
        percent = (self.value() - self.minimum()) / (self.maximum() - self.minimum())
        angle = -135 + (percent * 270)  # -135 to +135 degrees
        
        # Draw pointer line from center to edge
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(center_x, center_y) - 10
        
        angle_rad = np.radians(angle)
        end_x = center_x + radius * np.cos(angle_rad)
        end_y = center_y + radius * np.sin(angle_rad)
        
        pen = QPen(QColor(255, 255, 0), 3)
        painter.setPen(pen)
        painter.drawLine(int(center_x), int(center_y), int(end_x), int(end_y))

class OscilloscopeCanvas(FigureCanvas):
    """Matplotlib canvas for oscilloscope display"""
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(10, 6), facecolor='#000000')
        self.ax = self.fig.add_subplot(111, facecolor='#001a00')
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Setup oscilloscope-style grid
        self.ax.grid(True, color='#00ff00', alpha=0.3, linestyle='-', linewidth=0.5)
        self.ax.set_xlabel('Time', color='#00ff00', fontsize=10)
        self.ax.set_ylabel('Voltage (V)', color='#00ff00', fontsize=10)
        self.ax.tick_params(colors='#00ff00', labelsize=8)
        
        # Set tight layout
        self.fig.tight_layout(pad=2.0)
        
        # Initial plot
        self.line, = self.ax.plot([], [], color='#00ff00', linewidth=1.5)
        
    def update_plot(self, time_data, voltage_data, v_scale, t_scale, v_pos, h_pos):
        """Update the oscilloscope display"""
        self.ax.clear()
        
        # Apply position offsets
        voltage_data = voltage_data - (v_pos / 10.0)  # Vertical position
        time_data = time_data - (h_pos * t_scale / 100.0)  # Horizontal position
        
        # Plot signal
        self.ax.plot(time_data, voltage_data, color='#00ff00', linewidth=1.5)
        
        # Set limits based on scale
        self.ax.set_xlim(-5 * t_scale, 5 * t_scale)  # 10 divisions
        self.ax.set_ylim(-4 * v_scale, 4 * v_scale)  # 8 divisions (center zero)
        
        # Add center lines (axis)
        self.ax.axhline(y=0, color='#ffff00', linestyle='-', linewidth=1, alpha=0.7)
        self.ax.axvline(x=0, color='#ffff00', linestyle='-', linewidth=1, alpha=0.7)
        
        # Grid
        self.ax.grid(True, color='#00ff00', alpha=0.3, linestyle='-', linewidth=0.5)
        self.ax.set_xlabel('Time', color='#00ff00', fontsize=10)
        self.ax.set_ylabel('Voltage (V)', color='#00ff00', fontsize=10)
        self.ax.tick_params(colors='#00ff00', labelsize=8)
        
        self.ax.set_facecolor('#001a00')
        self.draw()

class DummyOscilloscope(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('ESP32 Oscilloscope - Dummy Mode')
        self.setGeometry(100, 100, 1400, 750)
        
        # Voltage and time scale values
        self.v_scale_values = ['50 mV', '100 mV', '200 mV', '500 mV', '1 V', '2 V', '5 V']
        self.t_scale_values = ['0.1 ms', '0.2 ms', '0.5 ms', '1 ms', '2 ms', '5 ms', '10 ms', '20 ms', '50 ms']
        self.v_scale_index = 4  # Start at 1V
        self.t_scale_index = 3  # Start at 1ms
        
        self.initUI()
        
    def initUI(self):
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("ESP32 Oscilloscope - DUMMY MODE")
        title.setFont(QFont('Arial', 16, QFont.Bold))
        title.setStyleSheet("color: #00ff00; padding: 10px;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Oscilloscope display
        self.canvas = OscilloscopeCanvas(self)
        self.canvas.setMinimumHeight(400)
        main_layout.addWidget(self.canvas)
        
        # Measurement display below the plot
        meas_frame = QFrame()
        meas_frame.setStyleSheet("background-color: #1a1a1a; border: 1px solid #444;")
        meas_layout = QHBoxLayout(meas_frame)
        meas_layout.setContentsMargins(10, 5, 10, 5)
        
        # Status indicator
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(2)
        
        status_title = QLabel("STATUS")
        status_title.setFont(QFont('Arial', 8, QFont.Bold))
        status_title.setStyleSheet("color: #888;")
        self.status_label = QLabel("● DUMMY MODE")
        self.status_label.setFont(QFont('Arial', 9, QFont.Bold))
        self.status_label.setStyleSheet("color: #00ff00;")
        
        status_layout.addWidget(status_title)
        status_layout.addWidget(self.status_label)
        meas_layout.addWidget(status_widget)
        
        # Add separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet("color: #444;")
        meas_layout.addWidget(sep1)
        
        # Measurements in fixed-width columns
        self.vpp_label = QLabel("Vpp\n--- V")
        self.vmax_label = QLabel("Vmax\n--- V")
        self.vmin_label = QLabel("Vmin\n--- V")
        self.vavg_label = QLabel("Vavg\n--- V")
        self.freq_label = QLabel("Freq\n--- Hz")
        self.period_label = QLabel("Period\n--- ms")
        
        for label in [self.vpp_label, self.vmax_label, self.vmin_label, self.vavg_label, self.freq_label, self.period_label]:
            label.setFont(QFont('Courier New', 9))
            label.setStyleSheet("color: #ffff00; padding: 5px; min-width: 80px;")
            label.setAlignment(Qt.AlignCenter)
            meas_layout.addWidget(label)
        
        meas_layout.addStretch()
        main_layout.addWidget(meas_frame)
        
        # Control panels
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        
        # LEFT SIDE: Signal Generator
        sig_group = QGroupBox("Signal Generator")
        sig_group.setStyleSheet("QGroupBox { color: #00ff00; font-weight: bold; border: 1px solid #444; padding-top: 10px; }")
        sig_layout = QGridLayout()
        sig_layout.setSpacing(8)
        
        sig_layout.addWidget(QLabel("Waveform:"), 0, 0)
        self.wave_combo = QComboBox()
        self.wave_combo.addItems(["Sine", "Square", "Triangle", "Sawtooth"])
        sig_layout.addWidget(self.wave_combo, 0, 1)
        
        sig_layout.addWidget(QLabel("Frequency (Hz):"), 1, 0)
        self.freq_spin = QDoubleSpinBox()
        self.freq_spin.setRange(0.1, 10000)
        self.freq_spin.setValue(1000)
        self.freq_spin.setSingleStep(10)
        sig_layout.addWidget(self.freq_spin, 1, 1)
        
        sig_layout.addWidget(QLabel("Amplitude (V):"), 2, 0)
        self.amp_spin = QDoubleSpinBox()
        self.amp_spin.setRange(0.1, 5.0)
        self.amp_spin.setValue(2.5)
        self.amp_spin.setSingleStep(0.1)
        sig_layout.addWidget(self.amp_spin, 2, 1)
        
        sig_layout.addWidget(QLabel("Offset (V):"), 3, 0)
        self.offset_spin = QDoubleSpinBox()
        self.offset_spin.setRange(-5.0, 5.0)
        self.offset_spin.setValue(0.0)
        self.offset_spin.setSingleStep(0.1)
        sig_layout.addWidget(self.offset_spin, 3, 1)
        
        sig_layout.addWidget(QLabel("Noise:"), 4, 0)
        self.noise_spin = QDoubleSpinBox()
        self.noise_spin.setRange(0.0, 1.0)
        self.noise_spin.setValue(0.1)
        self.noise_spin.setSingleStep(0.01)
        sig_layout.addWidget(self.noise_spin, 4, 1)
        
        sig_group.setLayout(sig_layout)
        controls_layout.addWidget(sig_group)
        
        # MIDDLE: Vertical Control
        v_group = QGroupBox("Vertical Control")
        v_group.setStyleSheet("QGroupBox { color: #00ff00; font-weight: bold; border: 1px solid #444; padding-top: 10px; }")
        v_main_layout = QHBoxLayout()
        
        # Knob section
        v_knob_layout = QVBoxLayout()
        v_knob_layout.setSpacing(5)
        v_knob_label = QLabel("VOLT/DIV")
        v_knob_label.setAlignment(Qt.AlignCenter)
        v_knob_label.setStyleSheet("color: #888; font-size: 9px;")
        
        self.v_knob = RotaryKnob()
        self.v_knob.valueChanged.connect(self.on_v_knob_changed)
        
        self.v_value_display = QLabel("1 V")
        self.v_value_display.setAlignment(Qt.AlignCenter)
        self.v_value_display.setStyleSheet("color: #ffff00; font-weight: bold; font-size: 12px; padding: 5px; background-color: #1a1a1a; border-radius: 3px;")
        
        v_knob_layout.addWidget(v_knob_label)
        v_knob_layout.addWidget(self.v_knob)
        v_knob_layout.addWidget(self.v_value_display)
        v_main_layout.addLayout(v_knob_layout)
        
        # Position slider section
        v_pos_frame = QFrame()
        v_pos_frame.setFrameShape(QFrame.VLine)
        v_pos_frame.setStyleSheet("background-color: #444;")
        v_main_layout.addWidget(v_pos_frame)
        
        v_slider_layout = QVBoxLayout()
        v_slider_layout.setSpacing(5)
        
        v_pos_label = QLabel("POSITION")
        v_pos_label.setAlignment(Qt.AlignCenter)
        v_pos_label.setStyleSheet("color: #888; font-size: 9px;")
        
        self.vpos_slider = QSlider(Qt.Vertical)
        self.vpos_slider.setRange(-100, 100)
        self.vpos_slider.setValue(0)
        self.vpos_slider.setInvertedAppearance(True)
        self.vpos_slider.valueChanged.connect(self.update_display)
        self.vpos_slider.setMinimumHeight(100)
        
        v_reset_btn = QPushButton("⟲")
        v_reset_btn.setFixedSize(30, 25)
        v_reset_btn.setStyleSheet("font-size: 14px; background-color: #444; border-radius: 3px;")
        v_reset_btn.clicked.connect(lambda: self.vpos_slider.setValue(0))
        
        v_slider_layout.addWidget(v_pos_label)
        v_slider_layout.addWidget(self.vpos_slider)
        v_slider_layout.addWidget(v_reset_btn, alignment=Qt.AlignCenter)
        v_main_layout.addLayout(v_slider_layout)
        
        v_group.setLayout(v_main_layout)
        controls_layout.addWidget(v_group)
        
        # RIGHT: Horizontal Control
        h_group = QGroupBox("Horizontal Control")
        h_group.setStyleSheet("QGroupBox { color: #00ff00; font-weight: bold; border: 1px solid #444; padding-top: 10px; }")
        h_main_layout = QHBoxLayout()
        
        # Knob section
        h_knob_layout = QVBoxLayout()
        h_knob_layout.setSpacing(5)
        h_knob_label = QLabel("TIME/DIV")
        h_knob_label.setAlignment(Qt.AlignCenter)
        h_knob_label.setStyleSheet("color: #888; font-size: 9px;")
        
        self.h_knob = RotaryKnob()
        self.h_knob.valueChanged.connect(self.on_h_knob_changed)
        
        self.h_value_display = QLabel("1 ms")
        self.h_value_display.setAlignment(Qt.AlignCenter)
        self.h_value_display.setStyleSheet("color: #ffff00; font-weight: bold; font-size: 12px; padding: 5px; background-color: #1a1a1a; border-radius: 3px;")
        
        h_knob_layout.addWidget(h_knob_label)
        h_knob_layout.addWidget(self.h_knob)
        h_knob_layout.addWidget(self.h_value_display)
        h_main_layout.addLayout(h_knob_layout)
        
        # Position slider section
        h_pos_frame = QFrame()
        h_pos_frame.setFrameShape(QFrame.VLine)
        h_pos_frame.setStyleSheet("background-color: #444;")
        h_main_layout.addWidget(h_pos_frame)
        
        h_slider_layout = QVBoxLayout()
        h_slider_layout.setSpacing(5)
        
        h_pos_label = QLabel("POSITION")
        h_pos_label.setAlignment(Qt.AlignCenter)
        h_pos_label.setStyleSheet("color: #888; font-size: 9px;")
        
        self.hpos_slider = QSlider(Qt.Horizontal)
        self.hpos_slider.setRange(-100, 100)
        self.hpos_slider.setValue(0)
        self.hpos_slider.valueChanged.connect(self.update_display)
        self.hpos_slider.setMinimumWidth(150)
        
        h_reset_btn = QPushButton("⟲")
        h_reset_btn.setFixedSize(30, 25)
        h_reset_btn.setStyleSheet("font-size: 14px; background-color: #444; border-radius: 3px;")
        h_reset_btn.clicked.connect(lambda: self.hpos_slider.setValue(0))
        
        h_slider_layout.addWidget(h_pos_label)
        h_slider_layout.addWidget(self.hpos_slider)
        h_slider_layout.addWidget(h_reset_btn, alignment=Qt.AlignCenter)
        h_main_layout.addLayout(h_slider_layout)
        
        h_group.setLayout(h_main_layout)
        controls_layout.addWidget(h_group)
        
        main_layout.addLayout(controls_layout)
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1a1a1a;
                color: #00ff00;
            }
            QGroupBox {
                border: 2px solid #00ff00;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #00ff00;
                color: black;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00dd00;
            }
            QPushButton:pressed {
                background-color: #00bb00;
            }
            QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #2a2a2a;
                color: #00ff00;
                border: 1px solid #00ff00;
                padding: 3px;
                border-radius: 3px;
            }
            QLabel {
                color: #00ff00;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background: #2a2a2a;
                border: 1px solid #00ff00;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #00ff00;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::groove:vertical {
                width: 8px;
                background: #2a2a2a;
                border: 1px solid #00ff00;
                border-radius: 4px;
            }
            QSlider::handle:vertical {
                background: #00ff00;
                height: 18px;
                margin: 0 -5px;
                border-radius: 9px;
            }
        """)
        
        # Initialize knobs to middle position
        self.v_knob.setValue(50)
        self.h_knob.setValue(50)
        
        # Start update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(50)  # Update every 50ms
    
    def on_v_knob_changed(self, value):
        """Handle voltage scale knob rotation"""
        # Map 0-100 to array indices
        index = int((value / 100.0) * (len(self.v_scale_values) - 1))
        self.v_scale_index = index
        self.v_value_display.setText(self.v_scale_values[index])
        self.update_display()
    
    def on_h_knob_changed(self, value):
        """Handle time scale knob rotation"""
        # Map 0-100 to array indices
        index = int((value / 100.0) * (len(self.t_scale_values) - 1))
        self.t_scale_index = index
        self.h_value_display.setText(self.t_scale_values[index])
        self.update_display()
    
    def parse_scale_value(self, scale_str):
        """Parse scale string like '1 V' or '1 ms' to float"""
        parts = scale_str.split()
        value = float(parts[0])
        unit = parts[1]
        
        if unit == 'mV':
            value /= 1000.0
        elif unit == 'ms':
            value /= 1000.0
        
        return value
    
    def generate_signal(self):
        """Generate dummy signal based on settings"""
        freq = self.freq_spin.value()
        amp = self.amp_spin.value()
        offset = self.offset_spin.value()
        noise = self.noise_spin.value()
        waveform = self.wave_combo.currentText()
        
        # Get time scale
        t_scale = self.parse_scale_value(self.t_scale_values[self.t_scale_index])
        
        # Generate time array - 10 divisions, 50 points per division
        t = np.linspace(-5 * t_scale, 5 * t_scale, 500)
        
        # Generate signal based on waveform type
        if waveform == "Sine":
            signal = amp * np.sin(2 * np.pi * freq * t)
        elif waveform == "Square":
            signal = amp * np.sign(np.sin(2 * np.pi * freq * t))
        elif waveform == "Triangle":
            signal = amp * (2 * np.abs(2 * (freq * t - np.floor(freq * t + 0.5))) - 1)
        elif waveform == "Sawtooth":
            signal = amp * 2 * (freq * t - np.floor(freq * t + 0.5))
        
        # Add offset and noise
        signal = signal + offset + noise * np.random.randn(len(t))
        
        return t, signal
    
    def update_display(self):
        """Update oscilloscope display with dummy data"""
        # Generate signal
        t, signal = self.generate_signal()
        
        # Get scales
        v_scale = self.parse_scale_value(self.v_scale_values[self.v_scale_index])
        t_scale = self.parse_scale_value(self.t_scale_values[self.t_scale_index])
        
        # Get positions
        v_pos = self.vpos_slider.value()
        h_pos = self.hpos_slider.value()
        
        # Update plot
        self.canvas.update_plot(t, signal, v_scale, t_scale, v_pos, h_pos)
        
        # Update measurements
        vpp = np.max(signal) - np.min(signal)
        vmax = np.max(signal)
        vmin = np.min(signal)
        vavg = np.mean(signal)
        freq = self.freq_spin.value()
        period = (1.0 / freq) * 1000 if freq > 0 else 0  # in ms
        
        self.vpp_label.setText(f"Vpp\n{vpp:.3f} V")
        self.vmax_label.setText(f"Vmax\n{vmax:.3f} V")
        self.vmin_label.setText(f"Vmin\n{vmin:.3f} V")
        self.vavg_label.setText(f"Vavg\n{vavg:.3f} V")
        self.freq_label.setText(f"Freq\n{freq:.1f} Hz")
        self.period_label.setText(f"Period\n{period:.3f} ms")

def main():
    app = QApplication(sys.argv)
    window = DummyOscilloscope()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
