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
        
        # Set rotation range: from ~210 degrees (7 o'clock) to ~-30 degrees (5 o'clock)
        # Total rotation: 270 degrees (like real oscilloscope knobs)
        
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
        from PyQt5.QtGui import QPainter, QPen, QColor
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate angle based on value
        # Map value range to 270 degrees rotation (from -135° to +135° from top)
        range_val = self.maximum() - self.minimum()
        if range_val > 0:
            normalized = (self.value() - self.minimum()) / range_val
        else:
            normalized = 0
        
        # Rotation from -135° (bottom-left) to +135° (bottom-right) = 270° total
        angle = -135 + (normalized * 270)  # degrees from top (0°)
        angle_rad = np.radians(angle)
        
        # Draw indicator line from center
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(self.width(), self.height()) / 2 - 8
        
        end_x = center_x + radius * np.sin(angle_rad)
        end_y = center_y - radius * np.cos(angle_rad)
        
        # Draw white indicator line
        pen = QPen(QColor('#ffffff'))
        pen.setWidth(3)
        painter.setPen(pen)
        painter.drawLine(int(center_x), int(center_y), int(end_x), int(end_y))
        
        # Draw center dot
        painter.setBrush(QColor('#00ff00'))
        painter.drawEllipse(int(center_x - 4), int(center_y - 4), 8, 8)

class SignalGenerator:
    """Generate various test signals"""
    
    def __init__(self):
        self.signal_type = 'sine'
        self.frequency = 1000  # Hz
        self.amplitude = 2.0   # Volts
        self.offset = 1.65     # Volts
        self.noise_level = 0.05
        self.duty_cycle = 50   # For square wave
        
    def generate(self, sample_rate, num_samples):
        """Generate signal data"""
        t = np.arange(num_samples) / sample_rate
        
        if self.signal_type == 'sine':
            signal = self.amplitude * np.sin(2 * np.pi * self.frequency * t)
        
        elif self.signal_type == 'square':
            signal = self.amplitude * np.sign(np.sin(2 * np.pi * self.frequency * t))
        
        elif self.signal_type == 'triangle':
            signal = self.amplitude * 2 * np.abs(2 * (t * self.frequency - np.floor(t * self.frequency + 0.5))) - self.amplitude
        
        elif self.signal_type == 'sawtooth':
            signal = self.amplitude * 2 * (t * self.frequency - np.floor(t * self.frequency + 0.5))
        
        elif self.signal_type == 'pulse':
            duty = self.duty_cycle / 100.0
            signal = self.amplitude * (np.fmod(t * self.frequency, 1.0) < duty)
        
        elif self.signal_type == 'noise':
            signal = np.random.normal(0, self.amplitude/3, num_samples)
        
        elif self.signal_type == 'dc':
            signal = np.zeros(num_samples)
        
        else:
            signal = np.zeros(num_samples)
        
        # Add offset and noise
        signal = signal + self.offset
        signal = signal + np.random.normal(0, self.noise_level, num_samples)
        
        # Clip to valid voltage range (0-3.3V)
        signal = np.clip(signal, 0, 3.3)
        
        # Convert to ADC values (0-4095)
        adc_data = (signal / 3.3 * 4095).astype(int)
        
        return adc_data.tolist()

class OscilloscopeCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(10, 6), facecolor='#1e1e1e')
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.ax = self.fig.add_subplot(111)
        self.h_divisions = 10
        self.v_divisions = 8
        self.v_offset = 0.0
        self.h_offset = 0.0
        self.v_per_div = 0.5
        self.t_per_div = 2.0
        
        self.setup_plot()
        
    def setup_plot(self):
        self.ax.set_facecolor('#0a0a0a')
        
        self.ax.grid(True, color='#00ff00', linestyle='-', linewidth=0.8, alpha=0.3)
        self.ax.minorticks_on()
        self.ax.grid(which='minor', color='#00ff00', linestyle=':', linewidth=0.3, alpha=0.2)
        
        self.ax.set_xlabel('')
        self.ax.set_ylabel('')
        self.ax.tick_params(colors='#00ff00', labelsize=8)
        
        for spine in self.ax.spines.values():
            spine.set_color('#00ff00')
            spine.set_linewidth(2)
        
        self.line, = self.ax.plot([], [], color='#00ff00', linewidth=2.0)
        
        self.zero_line = self.ax.axhline(y=0, color='#00ff00', 
                                         linestyle='-', linewidth=2, alpha=0.8)
        
        self.trigger_line = self.ax.axhline(y=0, color='#ff0000', 
                                           linestyle='--', linewidth=2, alpha=0.8)
        
        self.center_vline = self.ax.axvline(x=0, color='#00ff00',
                                           linestyle='-', linewidth=2, alpha=0.5)
        
        self.no_signal_text = self.ax.text(0.5, 0.5, 'DUMMY MODE', 
                                          transform=self.ax.transAxes,
                                          fontsize=30, color='#ffff00',
                                          ha='center', va='center',
                                          weight='bold', alpha=0.5,
                                          visible=True)
        
        self.time_label = self.ax.text(0.02, 0.98, 'Time: 2.0 ms/div', 
                                      transform=self.ax.transAxes,
                                      fontsize=10, color='#00ff00',
                                      ha='left', va='top',
                                      bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))
        
        self.volt_label = self.ax.text(0.02, 0.92, 'Volt: 0.5 V/div', 
                                      transform=self.ax.transAxes,
                                      fontsize=10, color='#00ff00',
                                      ha='left', va='top',
                                      bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))
        
        self.update_limits()
    
    def update_limits(self):
        t_center = self.h_offset
        t_span = self.t_per_div * self.h_divisions / 2
        self.ax.set_xlim(t_center - t_span, t_center + t_span)
        
        v_center = self.v_offset
        v_span = self.v_per_div * self.v_divisions / 2
        self.ax.set_ylim(v_center - v_span, v_center + v_span)
        
        self.zero_line.set_ydata([v_center, v_center])
        self.center_vline.set_xdata([t_center, t_center])
        
        x_ticks = np.arange(t_center - t_span, t_center + t_span + self.t_per_div, self.t_per_div)
        y_ticks = np.arange(v_center - v_span, v_center + v_span + self.v_per_div, self.v_per_div)
        self.ax.set_xticks(x_ticks)
        self.ax.set_yticks(y_ticks)
        
        x_minor = np.arange(t_center - t_span, t_center + t_span, self.t_per_div / 5)
        y_minor = np.arange(v_center - v_span, v_center + v_span, self.v_per_div / 5)
        self.ax.set_xticks(x_minor, minor=True)
        self.ax.set_yticks(y_minor, minor=True)
    
    def update_plot(self, adc_data, sample_rate, v_per_div, t_per_div):
        if len(adc_data) == 0:
            self.no_signal_text.set_visible(True)
            self.line.set_data([], [])
            self.update_limits()
            self.draw()
            return
            
        self.no_signal_text.set_visible(False)
        
        self.v_per_div = v_per_div
        self.t_per_div = t_per_div
        
        voltage = np.array(adc_data) * 3.3 / 4095.0 - 1.65
        voltage = voltage - self.v_offset
        
        time_ms = (np.arange(len(voltage)) / sample_rate * 1000.0) - (len(voltage) / sample_rate * 1000.0 / 2) + self.h_offset
        
        self.line.set_data(time_ms, voltage)
        
        self.update_limits()
        self.time_label.set_text(f'Time: {self.t_per_div:.2f} ms/div')
        self.volt_label.set_text(f'Volt: {self.v_per_div:.3f} V/div')
        
        self.draw()
    
    def set_vertical_offset(self, offset):
        self.v_offset = offset
        self.update_limits()
        self.draw()
    
    def set_horizontal_offset(self, offset):
        self.h_offset = offset
        self.update_limits()
        self.draw()
    
    def update_trigger_line(self, level):
        trigger_relative = level - 1.65 - self.v_offset
        self.trigger_line.set_ydata([trigger_relative, trigger_relative])
        self.draw()

class DummyOscilloscopeGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.generator = SignalGenerator()
        self.sample_rate = 100000
        self.is_running = True
        self.buffer_size = 2000
        
        self.initUI()
        
        # Auto-update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_waveform)
        self.update_timer.start(100)  # Update every 100ms
        
    def initUI(self):
        self.setWindowTitle('ESP32 Oscilloscope - DUMMY DATA MODE')
        self.setGeometry(100, 100, 1400, 800)
        self.setStyleSheet("background-color: #2b2b2b; color: #ffffff;")
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Warning banner
        warning = QLabel('⚠️ DUMMY DATA MODE - For Testing GUI Only ⚠️')
        warning.setStyleSheet("background-color: #ff8800; color: #000000; padding: 10px; font-size: 14px; font-weight: bold;")
        warning.setAlignment(Qt.AlignCenter)
        warning.setMaximumHeight(40)
        main_layout.addWidget(warning)
        
        # Canvas
        self.canvas = OscilloscopeCanvas(self)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.canvas)
        
        # Measurements panel (below canvas)
        meas_panel = QWidget()
        meas_panel.setStyleSheet("background-color: #1e1e1e; border: 1px solid #444; border-radius: 3px;")
        layout = QVBoxLayout(meas_panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)
        
        # Row 1: Status
        status_row = QHBoxLayout()
        self.status_label = QLabel('● DUMMY MODE')
        self.status_label.setStyleSheet("color: #ffff00; font-size: 13px; font-weight: bold;")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        layout.addLayout(status_row)
        
        # Row 2: Voltage measurements
        volt_row = QHBoxLayout()
        volt_row.setSpacing(10)
        
        self.vmax_label = QLabel("Vmax: --")
        self.vmax_label.setMinimumWidth(120)
        self.vmax_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.vmax_label.setStyleSheet("color: #00ff00; font-size: 12px;")
        
        self.vmin_label = QLabel("Vmin: --")
        self.vmin_label.setMinimumWidth(120)
        self.vmin_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.vmin_label.setStyleSheet("color: #00ff00; font-size: 12px;")
        
        self.vavg_label = QLabel("Vavg: --")
        self.vavg_label.setMinimumWidth(120)
        self.vavg_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.vavg_label.setStyleSheet("color: #00ff00; font-size: 12px;")
        
        self.vpp_label = QLabel("Vpp: --")
        self.vpp_label.setMinimumWidth(120)
        self.vpp_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.vpp_label.setStyleSheet("color: #00ff00; font-size: 12px;")
        
        volt_row.addWidget(self.vmax_label)
        volt_row.addWidget(self.vmin_label)
        volt_row.addWidget(self.vavg_label)
        volt_row.addWidget(self.vpp_label)
        volt_row.addStretch()
        layout.addLayout(volt_row)
        
        # Row 3: Frequency and time measurements
        freq_row = QHBoxLayout()
        freq_row.setSpacing(10)
        
        self.freq_label = QLabel("Freq: --")
        self.freq_label.setMinimumWidth(150)
        self.freq_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.freq_label.setStyleSheet("color: #00ff00; font-size: 12px;")
        
        self.period_label = QLabel("Period: --")
        self.period_label.setMinimumWidth(150)
        self.period_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.period_label.setStyleSheet("color: #00ff00; font-size: 12px;")
        
        self.duty_label = QLabel("Duty: --")
        self.duty_label.setMinimumWidth(120)
        self.duty_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.duty_label.setStyleSheet("color: #00ff00; font-size: 12px;")
        
        self.samples_label = QLabel("Samples: 2000")
        self.samples_label.setMinimumWidth(120)
        self.samples_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.samples_label.setStyleSheet("color: #00ff00; font-size: 12px;")
        
        freq_row.addWidget(self.freq_label)
        freq_row.addWidget(self.period_label)
        freq_row.addWidget(self.duty_label)
        freq_row.addWidget(self.samples_label)
        freq_row.addStretch()
        layout.addLayout(freq_row)
        
        main_layout.addWidget(meas_panel)
        
        # Control panel
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
    def create_control_panel(self):
        panel = QWidget()
        panel.setMaximumHeight(180)
        panel.setStyleSheet("""
            QGroupBox {
                border: 2px solid #00ff00;
                border-radius: 5px;
                margin-top: 5px;
                font-weight: bold;
                color: #00ff00;
                font-size: 11px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QPushButton {
                background-color: #3a3a3a;
                border: 2px solid #00ff00;
                border-radius: 3px;
                color: #00ff00;
                padding: 5px;
                font-weight: bold;
                font-size: 10px;
                min-height: 25px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #00ff00;
                color: #000000;
            }
            QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #3a3a3a;
                border: 1px solid #00ff00;
                color: #00ff00;
                padding: 3px;
                font-size: 10px;
            }
            QLabel {
                color: #ffffff;
                font-size: 10px;
            }
        """)
        
        layout = QHBoxLayout(panel)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Column 1: Signal Generator + Run/Stop
        col1 = QWidget()
        col1_layout = QVBoxLayout(col1)
        col1_layout.setSpacing(5)
        col1_layout.setContentsMargins(0, 0, 0, 0)
        
        sig_group = QGroupBox("Signal Gen (Dummy)")
        sig_layout = QGridLayout()
        sig_layout.setSpacing(3)
        sig_layout.setContentsMargins(5, 8, 5, 5)
        
        sig_layout.addWidget(QLabel("Type:"), 0, 0)
        self.signal_combo = QComboBox()
        self.signal_combo.addItems(['Sine', 'Square', 'Triangle', 'Sawtooth'])
        self.signal_combo.currentTextChanged.connect(self.change_signal_type)
        sig_layout.addWidget(self.signal_combo, 0, 1)
        
        sig_layout.addWidget(QLabel("Freq:"), 1, 0)
        self.freq_spin = QSpinBox()
        self.freq_spin.setRange(10, 50000)
        self.freq_spin.setValue(1000)
        self.freq_spin.setSuffix(" Hz")
        self.freq_spin.valueChanged.connect(self.change_frequency)
        sig_layout.addWidget(self.freq_spin, 1, 1)
        
        sig_layout.addWidget(QLabel("Amp:"), 2, 0)
        self.amp_spin = QDoubleSpinBox()
        self.amp_spin.setRange(0.1, 1.5)
        self.amp_spin.setValue(0.8)
        self.amp_spin.setSingleStep(0.1)
        self.amp_spin.setSuffix(" V")
        self.amp_spin.valueChanged.connect(self.change_amplitude)
        sig_layout.addWidget(self.amp_spin, 2, 1)
        
        sig_group.setLayout(sig_layout)
        col1_layout.addWidget(sig_group)
        
        self.run_btn = QPushButton("⏸ Stop" if self.is_running else "▶ Run")
        self.run_btn.clicked.connect(self.toggle_acquisition)
        col1_layout.addWidget(self.run_btn)
        
        col1_layout.addStretch()
        layout.addWidget(col1)
        
        # Column 2: Vertical Control
        vert_group = self.create_vertical_control()
        layout.addWidget(vert_group)
        
        # Column 3: Horizontal Control  
        horiz_group = self.create_horizontal_control()
        layout.addWidget(horiz_group)
        
        layout.addStretch()
        
        return panel
    
    def create_vertical_control(self):
        """Create vertical control with rotary knob"""
        group = QGroupBox("Vertical")
        vert_main_layout = QHBoxLayout()
        vert_main_layout.setSpacing(5)
        vert_main_layout.setContentsMargins(5, 8, 5, 5)
        
        # Left: Knob
        knob_section = QVBoxLayout()
        knob_section.setAlignment(Qt.AlignCenter)
        knob_section.setSpacing(2)
        
        volts_label = QLabel("VOLTS/DIV")
        volts_label.setAlignment(Qt.AlignCenter)
        volts_label.setStyleSheet("font-weight: bold; color: #00ff00; font-size: 9px;")
        volts_label.setFixedWidth(90)
        knob_section.addWidget(volts_label)
        
        knob_section.addSpacing(8)
        
        self.v_knob = RotaryKnob()
        self.v_knob.setMinimum(0)
        self.v_knob.setMaximum(19)
        self.v_knob.setValue(13)  # 0.5V
        self.v_knob.valueChanged.connect(self.on_v_knob_changed)
        knob_section.addWidget(self.v_knob, alignment=Qt.AlignCenter)
        
        knob_section.addSpacing(8)
        
        self.v_div_display = QLabel("0.500 V/div")
        self.v_div_display.setAlignment(Qt.AlignCenter)
        self.v_div_display.setStyleSheet("color: #00ff00; font-size: 10px; font-weight: bold;")
        self.v_div_display.setFixedWidth(90)
        knob_section.addWidget(self.v_div_display)
        
        knob_container = QWidget()
        knob_container.setFixedWidth(100)
        knob_container.setLayout(knob_section)
        vert_main_layout.addWidget(knob_container)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet("background-color: #00ff00;")
        vert_main_layout.addWidget(separator)
        
        # Right: Position slider with reset
        slider_section = QVBoxLayout()
        slider_section.setSpacing(3)
        
        pos_label = QLabel("Position")
        pos_label.setStyleSheet("color: #00ff00; font-size: 9px;")
        slider_section.addWidget(pos_label, alignment=Qt.AlignCenter)
        
        self.v_position_slider = QSlider(Qt.Vertical)
        self.v_position_slider.setRange(-100, 100)
        self.v_position_slider.setValue(0)
        self.v_position_slider.valueChanged.connect(self.on_v_position_changed)
        self.v_position_slider.setMinimumHeight(60)
        slider_section.addWidget(self.v_position_slider, alignment=Qt.AlignCenter)
        
        self.v_pos_display = QLabel("0.0 V")
        self.v_pos_display.setAlignment(Qt.AlignCenter)
        self.v_pos_display.setStyleSheet("color: #00ff00; font-size: 9px;")
        slider_section.addWidget(self.v_pos_display)
        
        reset_btn = QPushButton("⟲")
        reset_btn.setFixedSize(30, 20)
        reset_btn.setStyleSheet("font-size: 12px; padding: 0px;")
        reset_btn.clicked.connect(lambda: self.v_position_slider.setValue(0))
        slider_section.addWidget(reset_btn, alignment=Qt.AlignCenter)
        
        vert_main_layout.addLayout(slider_section)
        
        group.setLayout(vert_main_layout)
        return group
    
    def create_horizontal_control(self):
        """Create horizontal control with rotary knob"""
        group = QGroupBox("Horizontal")
        horiz_main_layout = QHBoxLayout()
        horiz_main_layout.setSpacing(5)
        horiz_main_layout.setContentsMargins(5, 8, 5, 5)
        
        # Left: Knob
        knob_section = QVBoxLayout()
        knob_section.setAlignment(Qt.AlignCenter)
        knob_section.setSpacing(2)
        
        time_label = QLabel("TIME/DIV")
        time_label.setAlignment(Qt.AlignCenter)
        time_label.setStyleSheet("font-weight: bold; color: #00ff00; font-size: 9px;")
        time_label.setFixedWidth(90)
        knob_section.addWidget(time_label)
        
        knob_section.addSpacing(8)
        
        self.t_knob = RotaryKnob()
        self.t_knob.setMinimum(0)
        self.t_knob.setMaximum(25)
        self.t_knob.setValue(11)  # 2ms
        self.t_knob.valueChanged.connect(self.on_t_knob_changed)
        knob_section.addWidget(self.t_knob, alignment=Qt.AlignCenter)
        
        knob_section.addSpacing(8)
        
        self.t_div_display = QLabel("2.00 ms/div")
        self.t_div_display.setAlignment(Qt.AlignCenter)
        self.t_div_display.setStyleSheet("color: #00ff00; font-size: 10px; font-weight: bold;")
        self.t_div_display.setFixedWidth(90)
        knob_section.addWidget(self.t_div_display)
        
        knob_container = QWidget()
        knob_container.setFixedWidth(100)
        knob_container.setLayout(knob_section)
        horiz_main_layout.addWidget(knob_container)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet("background-color: #00ff00;")
        horiz_main_layout.addWidget(separator)
        
        # Right: Position controls with reset
        right_section = QVBoxLayout()
        right_section.setSpacing(5)
        right_section.setAlignment(Qt.AlignTop)
        
        pos_label = QLabel("Position")
        pos_label.setStyleSheet("color: #00ff00; font-size: 9px;")
        right_section.addWidget(pos_label, alignment=Qt.AlignCenter)
        
        slider_row = QHBoxLayout()
        slider_row.setSpacing(3)
        
        self.h_position_slider = QSlider(Qt.Horizontal)
        self.h_position_slider.setRange(-100, 100)
        self.h_position_slider.setValue(0)
        self.h_position_slider.setMinimumWidth(120)
        self.h_position_slider.valueChanged.connect(self.on_h_position_changed)
        slider_row.addWidget(self.h_position_slider)
        
        reset_btn = QPushButton("⟲")
        reset_btn.setFixedSize(25, 25)
        reset_btn.setStyleSheet("font-size: 12px; padding: 0px;")
        reset_btn.clicked.connect(lambda: self.h_position_slider.setValue(0))
        slider_row.addWidget(reset_btn)
        
        right_section.addLayout(slider_row)
        
        self.h_pos_display = QLabel("0.0 ms")
        self.h_pos_display.setAlignment(Qt.AlignCenter)
        self.h_pos_display.setStyleSheet("color: #00ff00; font-size: 9px;")
        right_section.addWidget(self.h_pos_display)
        
        horiz_main_layout.addLayout(right_section)
        
        group.setLayout(horiz_main_layout)
        return group
    
    def get_v_div_values(self):
        """Get voltage per division values - sorted from smallest to largest"""
        return [0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05, 0.06, 0.075, 0.1,
                0.15, 0.2, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 5.0]
    
    def get_t_div_values(self):
        """Get time per division values - sorted from smallest to largest"""
        return [0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.75, 0.8, 1.0,
                1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.5, 8.0, 10.0,
                15.0, 20.0, 25.0, 30.0, 40.0, 50.0]
    
    def on_v_knob_changed(self, value):
        """Handle voltage knob rotation"""
        values = self.get_v_div_values()
        if 0 <= value < len(values):
            v_div = values[value]
            if v_div < 1.0:
                self.v_div_display.setText(f"{v_div*1000:.0f} mV/div")
            else:
                self.v_div_display.setText(f"{v_div:.3f} V/div")
            self.canvas.v_per_div = v_div
    
    def on_t_knob_changed(self, value):
        """Handle time knob rotation"""
        values = self.get_t_div_values()
        if 0 <= value < len(values):
            t_div = values[value]
            if t_div < 1.0:
                self.t_div_display.setText(f"{t_div*1000:.0f} µs/div")
            else:
                self.t_div_display.setText(f"{t_div:.2f} ms/div")
            self.canvas.t_per_div = t_div
    
    def on_v_position_changed(self, value):
        """Handle vertical position slider"""
        offset = value / 100.0 * 2.0  # -2.0 to +2.0 V
        self.v_pos_display.setText(f"{offset:.2f} V")
        self.canvas.set_vertical_offset(offset)
    
    def on_h_position_changed(self, value):
        """Handle horizontal position slider"""
        offset = value / 100.0 * 10.0  # -10 to +10 ms
        self.h_pos_display.setText(f"{offset:.1f} ms")
        self.canvas.set_horizontal_offset(offset)
    
    def change_signal_type(self, text):
        self.generator.signal_type = text.lower()
    
    def change_frequency(self, value):
        self.generator.frequency = value
    
    def change_amplitude(self, value):
        self.generator.amplitude = value
    
    def change_sample_rate(self, text):
        rates = {
            '100k': 100000,
            '200k': 200000,
            '500k': 500000
        }
        self.sample_rate = rates.get(text, 100000)
    
    def change_trigger_level(self, value):
        self.canvas.update_trigger_line(value)
    
    def toggle_acquisition(self):
        self.is_running = not self.is_running
        self.run_btn.setText("⏸ Stop" if self.is_running else "▶ Run")
    
    def update_waveform(self):
        if not self.is_running:
            return
        
        # Generate dummy data
        data = self.generator.generate(self.sample_rate, self.buffer_size)
        
        # Get division settings from knobs
        v_per_div = self.canvas.v_per_div
        t_per_div = self.canvas.t_per_div
        
        # Update plot
        self.canvas.update_plot(data, self.sample_rate, v_per_div, t_per_div)
        
        # Calculate measurements (convert to centered voltage)
        voltage = np.array(data) * 3.3 / 4095.0 - 1.65
        v_max = voltage.max()
        v_min = voltage.min()
        v_avg = voltage.mean()
        v_pp = v_max - v_min
        
        # Update labels with fixed width format
        self.vmax_label.setText(f"Vmax: {v_max:.3f} V")
        self.vmin_label.setText(f"Vmin: {v_min:.3f} V")
        self.vavg_label.setText(f"Vavg: {v_avg:.3f} V")
        self.vpp_label.setText(f"Vpp: {v_pp:.3f} V")
        
        # Calculate frequency if possible
        if len(voltage) > 10:
            # Simple zero-crossing detection for frequency
            crossings = np.where(np.diff(np.sign(voltage - v_avg)))[0]
            if len(crossings) > 2:
                period_samples = np.mean(np.diff(crossings)) * 2  # Full period
                freq = self.sample_rate / period_samples
                self.freq_label.setText(f"Freq: {freq:.1f} Hz")
                period_ms = 1000.0 / freq
                self.period_label.setText(f"Period: {period_ms:.3f} ms")
            else:
                self.freq_label.setText("Freq: --")
                self.period_label.setText("Period: --")
        
        self.duty_label.setText("Duty: --")
        self.samples_label.setText(f"Samples: {len(data)}")

def main():
    print("=" * 60)
    print("ESP32 Oscilloscope - DUMMY DATA MODE")
    print("=" * 60)
    print("This mode generates simulated signals for testing GUI controls")
    print("without requiring ESP32 hardware.")
    print()
    print("Available signals:")
    print("  - Sine wave")
    print("  - Square wave")
    print("  - Triangle wave")
    print("  - Sawtooth wave")
    print("  - Pulse")
    print("  - Noise")
    print("  - DC level")
    print()
    print("Use the controls to test:")
    print("  ✓ Signal generation parameters")
    print("  ✓ Timebase and voltage scale")
    print("  ✓ Trigger level adjustment")
    print("  ✓ Run/Stop acquisition")
    print("  ✓ Waveform display and measurements")
    print()
    print("=" * 60)
    
    app = QApplication(sys.argv)
    gui = DummyOscilloscopeGUI()
    gui.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
