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
                             QMessageBox, QSlider, QRadioButton, QButtonGroup, QDial)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import time

class RotaryKnob(QDial):
    """Custom rotary knob widget that looks like oscilloscope knob"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(50)
        self.setNotchesVisible(True)
        self.setWrapping(False)
        self.setFixedSize(80, 80)
        
        # Style
        self.setStyleSheet("""
            QDial {
                background-color: #2a2a2a;
                border: 3px solid #00ff00;
                border-radius: 40px;
            }
        """)

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
        self.setGeometry(100, 100, 1600, 900)
        self.setStyleSheet("background-color: #2b2b2b; color: #ffffff;")
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # Left side - Display
        display_layout = QVBoxLayout()
        
        # Warning banner
        warning = QLabel('⚠️ DUMMY DATA MODE - For Testing GUI Only ⚠️')
        warning.setStyleSheet("background-color: #ff8800; color: #000000; padding: 10px; font-size: 14px; font-weight: bold;")
        warning.setAlignment(Qt.AlignCenter)
        display_layout.addWidget(warning)
        
        self.canvas = OscilloscopeCanvas(self)
        display_layout.addWidget(self.canvas)
        
        # Status bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel('Status: DUMMY MODE ACTIVE')
        self.status_label.setStyleSheet("color: #ffff00; font-size: 12px; font-weight: bold;")
        self.freq_label = QLabel('Frequency: 1000 Hz')
        self.freq_label.setStyleSheet("color: #00ff00; font-size: 12px;")
        self.vpp_label = QLabel('Vpp: 2.00 V')
        self.vpp_label.setStyleSheet("color: #00ff00; font-size: 12px;")
        
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.freq_label)
        status_layout.addWidget(self.vpp_label)
        
        display_layout.addLayout(status_layout)
        main_layout.addLayout(display_layout, 3)
        
        # Right side - Controls
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
    def create_control_panel(self):
        panel = QWidget()
        panel.setStyleSheet("""
            QGroupBox {
                border: 2px solid #00ff00;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
                color: #00ff00;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QPushButton {
                background-color: #3a3a3a;
                border: 2px solid #00ff00;
                border-radius: 5px;
                color: #00ff00;
                padding: 8px;
                font-weight: bold;
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
                padding: 5px;
            }
            QLabel {
                color: #ffffff;
            }
            QRadioButton {
                color: #ffffff;
            }
        """)
        
        layout = QVBoxLayout(panel)
        
        # Signal Generator Group
        sig_group = QGroupBox("Signal Generator (Dummy)")
        sig_layout = QGridLayout()
        
        sig_layout.addWidget(QLabel("Signal Type:"), 0, 0)
        self.signal_combo = QComboBox()
        self.signal_combo.addItems(['Sine', 'Square', 'Triangle', 'Sawtooth', 'Pulse', 'Noise', 'DC'])
        self.signal_combo.currentTextChanged.connect(self.change_signal_type)
        sig_layout.addWidget(self.signal_combo, 0, 1)
        
        sig_layout.addWidget(QLabel("Frequency:"), 1, 0)
        self.freq_spin = QSpinBox()
        self.freq_spin.setRange(1, 100000)
        self.freq_spin.setValue(1000)
        self.freq_spin.setSuffix(" Hz")
        self.freq_spin.valueChanged.connect(self.change_frequency)
        sig_layout.addWidget(self.freq_spin, 1, 1)
        
        sig_layout.addWidget(QLabel("Amplitude:"), 2, 0)
        self.amp_spin = QDoubleSpinBox()
        self.amp_spin.setRange(0.1, 1.65)
        self.amp_spin.setValue(1.0)
        self.amp_spin.setSingleStep(0.1)
        self.amp_spin.setSuffix(" V")
        self.amp_spin.valueChanged.connect(self.change_amplitude)
        sig_layout.addWidget(self.amp_spin, 2, 1)
        
        sig_layout.addWidget(QLabel("DC Offset:"), 3, 0)
        self.offset_spin = QDoubleSpinBox()
        self.offset_spin.setRange(0, 3.3)
        self.offset_spin.setValue(1.65)
        self.offset_spin.setSingleStep(0.1)
        self.offset_spin.setSuffix(" V")
        self.offset_spin.valueChanged.connect(self.change_offset)
        sig_layout.addWidget(self.offset_spin, 3, 1)
        
        sig_layout.addWidget(QLabel("Noise Level:"), 4, 0)
        self.noise_spin = QDoubleSpinBox()
        self.noise_spin.setRange(0, 0.5)
        self.noise_spin.setValue(0.05)
        self.noise_spin.setSingleStep(0.01)
        self.noise_spin.setSuffix(" V")
        self.noise_spin.valueChanged.connect(self.change_noise)
        sig_layout.addWidget(self.noise_spin, 4, 1)
        
        sig_group.setLayout(sig_layout)
        layout.addWidget(sig_group)
        
        # Acquisition Control
        acq_group = QGroupBox("Acquisition Control")
        acq_layout = QGridLayout()
        
        self.run_btn = QPushButton("Stop" if self.is_running else "Run")
        self.run_btn.clicked.connect(self.toggle_acquisition)
        acq_layout.addWidget(self.run_btn, 0, 0, 1, 2)
        
        acq_group.setLayout(acq_layout)
        layout.addWidget(acq_group)
        
        # Timebase Control
        time_group = QGroupBox("Horizontal (Timebase)")
        time_layout = QGridLayout()
        
        time_layout.addWidget(QLabel("Sample Rate:"), 0, 0)
        self.rate_combo = QComboBox()
        self.rate_combo.addItems(['10 kHz', '50 kHz', '100 kHz', '200 kHz', '500 kHz', '1 MHz'])
        self.rate_combo.setCurrentText('100 kHz')
        self.rate_combo.currentTextChanged.connect(self.change_sample_rate)
        time_layout.addWidget(self.rate_combo, 0, 1)
        
        time_layout.addWidget(QLabel("Time/DIV:"), 1, 0)
        self.time_per_div = QDoubleSpinBox()
        self.time_per_div.setRange(0.1, 50)
        self.time_per_div.setValue(2.0)
        self.time_per_div.setSingleStep(0.1)
        self.time_per_div.setSuffix(" ms/div")
        time_layout.addWidget(self.time_per_div, 1, 1)
        
        time_layout.addWidget(QLabel("Position:"), 2, 0)
        self.h_position = QDoubleSpinBox()
        self.h_position.setRange(-50, 50)
        self.h_position.setValue(0)
        self.h_position.setSingleStep(0.5)
        self.h_position.setSuffix(" ms")
        self.h_position.valueChanged.connect(lambda v: self.canvas.set_horizontal_offset(v))
        time_layout.addWidget(self.h_position, 2, 1)
        
        time_group.setLayout(time_layout)
        layout.addWidget(time_group)
        
        # Vertical Control
        vert_group = QGroupBox("Vertical (Channel 1)")
        vert_layout = QGridLayout()
        
        vert_layout.addWidget(QLabel("Volts/DIV:"), 0, 0)
        self.volts_per_div = QDoubleSpinBox()
        self.volts_per_div.setRange(0.01, 2.0)
        self.volts_per_div.setValue(0.5)
        self.volts_per_div.setSingleStep(0.01)
        self.volts_per_div.setDecimals(3)
        self.volts_per_div.setSuffix(" V/div")
        vert_layout.addWidget(self.volts_per_div, 0, 1)
        
        vert_layout.addWidget(QLabel("Position:"), 1, 0)
        self.v_position = QDoubleSpinBox()
        self.v_position.setRange(-2.0, 2.0)
        self.v_position.setValue(0.0)
        self.v_position.setSingleStep(0.1)
        self.v_position.setSuffix(" V")
        self.v_position.valueChanged.connect(lambda v: self.canvas.set_vertical_offset(v))
        vert_layout.addWidget(self.v_position, 1, 1)
        
        # Quick preset buttons
        preset_layout = QHBoxLayout()
        
        preset_50mv = QPushButton("50mV")
        preset_50mv.clicked.connect(lambda: self.volts_per_div.setValue(0.05))
        preset_layout.addWidget(preset_50mv)
        
        preset_100mv = QPushButton("100mV")
        preset_100mv.clicked.connect(lambda: self.volts_per_div.setValue(0.1))
        preset_layout.addWidget(preset_100mv)
        
        preset_500mv = QPushButton("500mV")
        preset_500mv.clicked.connect(lambda: self.volts_per_div.setValue(0.5))
        preset_layout.addWidget(preset_500mv)
        
        preset_1v = QPushButton("1V")
        preset_1v.clicked.connect(lambda: self.volts_per_div.setValue(1.0))
        preset_layout.addWidget(preset_1v)
        
        vert_layout.addLayout(preset_layout, 2, 0, 1, 2)
        
        vert_group.setLayout(vert_layout)
        layout.addWidget(vert_group)
        
        # Trigger Control
        trig_group = QGroupBox("Trigger")
        trig_layout = QGridLayout()
        
        trig_layout.addWidget(QLabel("Level:"), 0, 0)
        self.trig_level = QDoubleSpinBox()
        self.trig_level.setRange(0, 3.3)
        self.trig_level.setValue(1.65)
        self.trig_level.setSingleStep(0.1)
        self.trig_level.setSuffix(" V")
        self.trig_level.valueChanged.connect(self.change_trigger_level)
        trig_layout.addWidget(self.trig_level, 0, 1)
        
        trig_group.setLayout(trig_layout)
        layout.addWidget(trig_group)
        
        # Measurements
        meas_group = QGroupBox("Measurements")
        meas_layout = QVBoxLayout()
        
        self.vmax_label = QLabel("V Max: 2.650 V")
        self.vmin_label = QLabel("V Min: 0.650 V")
        self.vavg_label = QLabel("V Avg: 1.650 V")
        
        meas_layout.addWidget(self.vmax_label)
        meas_layout.addWidget(self.vmin_label)
        meas_layout.addWidget(self.vavg_label)
        
        meas_group.setLayout(meas_layout)
        layout.addWidget(meas_group)
        
        layout.addStretch()
        
        return panel
    
    def change_signal_type(self, text):
        self.generator.signal_type = text.lower()
    
    def change_frequency(self, value):
        self.generator.frequency = value
        self.freq_label.setText(f'Frequency: {value} Hz')
    
    def change_amplitude(self, value):
        self.generator.amplitude = value
    
    def change_offset(self, value):
        self.generator.offset = value
    
    def change_noise(self, value):
        self.generator.noise_level = value
    
    def change_sample_rate(self, text):
        rates = {
            '10 kHz': 10000,
            '50 kHz': 50000,
            '100 kHz': 100000,
            '200 kHz': 200000,
            '500 kHz': 500000,
            '1 MHz': 1000000
        }
        self.sample_rate = rates.get(text, 100000)
    
    def change_trigger_level(self, value):
        self.canvas.update_trigger_line(value)
    
    def toggle_acquisition(self):
        self.is_running = not self.is_running
        self.run_btn.setText("Stop" if self.is_running else "Run")
    
    def update_waveform(self):
        if not self.is_running:
            return
        
        # Generate dummy data
        data = self.generator.generate(self.sample_rate, self.buffer_size)
        
        # Get division settings
        v_per_div = self.volts_per_div.value()
        t_per_div = self.time_per_div.value()
        
        # Update plot
        self.canvas.update_plot(data, self.sample_rate, v_per_div, t_per_div)
        
        # Calculate measurements (convert to centered voltage)
        voltage = np.array(data) * 3.3 / 4095.0 - 1.65
        v_max = voltage.max()
        v_min = voltage.min()
        v_avg = voltage.mean()
        v_pp = v_max - v_min
        
        # Update labels
        self.vmax_label.setText(f"V Max: {v_max:.3f} V")
        self.vmin_label.setText(f"V Min: {v_min:.3f} V")
        self.vavg_label.setText(f"V Avg: {v_avg:.3f} V")
        self.vpp_label.setText(f"Vpp: {v_pp:.3f} V")

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
