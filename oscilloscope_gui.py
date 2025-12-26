"""
ESP32 Oscilloscope GUI Application
Python 3.8+
Required: pip install pyserial numpy matplotlib pyqt5
"""

import sys
import serial
import serial.tools.list_ports
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QComboBox, QLabel, 
                             QSpinBox, QDoubleSpinBox, QGroupBox, QGridLayout,
                             QMessageBox, QSlider, QDial, QScrollArea, QSizePolicy)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QPainter, QColor, QPen
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
        self.setWrapping(False)  # No wrap around
        self.setFixedSize(80, 80)
        
        # Style
        self.setStyleSheet("""
            QDial {
                background-color: #2a2a2a;
                border: 3px solid #00ff00;
                border-radius: 40px;
            }
        """)

class SerialThread(QThread):
    data_received = pyqtSignal(list, int)
    connection_lost = pyqtSignal()
    
    def __init__(self, port, baudrate=921600):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.running = True
        self.waiting_for_data = False
        
    def run(self):
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)  # Wait for ESP32 to boot
            
            while self.running:
                if self.serial_conn.in_waiting:
                    try:
                        line = self.serial_conn.readline().decode('utf-8').strip()
                        
                        if line.startswith("DATA:"):
                            parts = line[5:].split(',')
                            if len(parts) >= 5:
                                sample_rate = int(parts[0])
                                # Skip freq, vpp, mean (indices 1,2,3)
                                data = [int(x) for x in parts[4:]]
                                self.data_received.emit(data, sample_rate)
                                self.waiting_for_data = False
                            
                    except Exception as e:
                        print(f"Parse error: {e}")
                        
                time.sleep(0.01)
                
        except Exception as e:
            print(f"Serial error: {e}")
            self.connection_lost.emit()
            
    def send_command(self, cmd):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.write(f"{cmd}\n".encode())
            
    def stop(self):
        self.running = False
        if self.serial_conn:
            self.serial_conn.close()

class OscilloscopeCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(10, 6), facecolor='#1e1e1e')
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.ax = self.fig.add_subplot(111)
        self.h_divisions = 10  # Horizontal divisions
        self.v_divisions = 8   # Vertical divisions
        self.v_offset = 0.0    # Vertical offset in volts
        self.h_offset = 0.0    # Horizontal offset in ms
        self.v_per_div = 0.5   # Volts per division
        self.t_per_div = 2.0   # Time per division (ms)
        
        self.setup_plot()
        
    def setup_plot(self):
        self.ax.set_facecolor('#0a0a0a')
        
        # Custom grid for divisions (like real oscilloscope)
        self.ax.grid(True, color='#00ff00', linestyle='-', linewidth=0.8, alpha=0.3)
        self.ax.minorticks_on()
        self.ax.grid(which='minor', color='#00ff00', linestyle=':', linewidth=0.3, alpha=0.2)
        
        # Remove default labels (we'll add custom ones)
        self.ax.set_xlabel('')
        self.ax.set_ylabel('')
        self.ax.tick_params(colors='#00ff00', labelsize=8)
        
        # Make spines more visible
        for spine in self.ax.spines.values():
            spine.set_color('#00ff00')
            spine.set_linewidth(2)
        
        # Initialize empty line
        self.line, = self.ax.plot([], [], color='#00ff00', linewidth=2.0)
        
        # Ground/Zero reference line (center horizontal)
        self.zero_line = self.ax.axhline(y=0, color='#00ff00', 
                                         linestyle='-', linewidth=2, alpha=0.8)
        
        # Trigger level line
        self.trigger_line = self.ax.axhline(y=0, color='#ff0000', 
                                           linestyle='--', linewidth=2, alpha=0.8)
        
        # Center vertical line (time reference)
        self.center_vline = self.ax.axvline(x=0, color='#00ff00',
                                           linestyle='-', linewidth=2, alpha=0.5)
        
        # No signal text
        self.no_signal_text = self.ax.text(0.5, 0.5, 'NO SIGNAL', 
                                          transform=self.ax.transAxes,
                                          fontsize=40, color='#ff0000',
                                          ha='center', va='center',
                                          weight='bold', alpha=0.7,
                                          visible=True)
        
        # Division labels
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
        
        # Set initial limits centered at zero
        self.update_limits()
        
    def update_limits(self):
        """Update display limits based on divisions and offsets"""
        # Time axis: center at h_offset, extend ±5 divisions
        t_center = self.h_offset
        t_span = self.t_per_div * self.h_divisions / 2
        self.ax.set_xlim(t_center - t_span, t_center + t_span)
        
        # Voltage axis: center at v_offset (ground level), extend ±4 divisions
        v_center = self.v_offset
        v_span = self.v_per_div * self.v_divisions / 2
        self.ax.set_ylim(v_center - v_span, v_center + v_span)
        
        # Update zero reference line position
        self.zero_line.set_ydata([v_center, v_center])
        
        # Update center vertical line
        self.center_vline.set_xdata([t_center, t_center])
        
        # Update major ticks to show divisions
        x_ticks = np.arange(t_center - t_span, t_center + t_span + self.t_per_div, self.t_per_div)
        y_ticks = np.arange(v_center - v_span, v_center + v_span + self.v_per_div, self.v_per_div)
        self.ax.set_xticks(x_ticks)
        self.ax.set_yticks(y_ticks)
        
        # Set minor ticks (5 subdivisions per division)
        x_minor = np.arange(t_center - t_span, t_center + t_span, self.t_per_div / 5)
        y_minor = np.arange(v_center - v_span, v_center + v_span, self.v_per_div / 5)
        self.ax.set_xticks(x_minor, minor=True)
        self.ax.set_yticks(y_minor, minor=True)
    
    def update_plot(self, adc_data, sample_rate, v_per_div, t_per_div):
        if len(adc_data) == 0:
            # Show NO SIGNAL
            self.no_signal_text.set_visible(True)
            self.line.set_data([], [])
            self.update_limits()
            self.draw()
            return
            
        # Hide NO SIGNAL text when data is present
        self.no_signal_text.set_visible(False)
        
        # Update divisions
        self.v_per_div = v_per_div
        self.t_per_div = t_per_div
        
        # Convert ADC to voltage (0-4095 -> 0-3.3V)
        # Shift to center at ground (1.65V becomes 0V)
        voltage = np.array(adc_data) * 3.3 / 4095.0 - 1.65
        
        # Apply vertical offset
        voltage = voltage - self.v_offset
        
        # Calculate time axis in milliseconds, centered at h_offset
        time_ms = (np.arange(len(voltage)) / sample_rate * 1000.0) - (len(voltage) / sample_rate * 1000.0 / 2) + self.h_offset
        
        # Update line data
        self.line.set_data(time_ms, voltage)
        
        # Update limits and labels
        self.update_limits()
        self.time_label.set_text(f'Time: {self.t_per_div:.2f} ms/div')
        self.volt_label.set_text(f'Volt: {self.v_per_div:.3f} V/div')
        
        self.draw()
    
    def set_vertical_offset(self, offset):
        """Set vertical position offset (moves signal up/down)"""
        self.v_offset = offset
        self.update_limits()
        self.draw()
    
    def set_horizontal_offset(self, offset):
        """Set horizontal position offset (moves signal left/right)"""
        self.h_offset = offset
        self.update_limits()
        self.draw()
    
    def show_no_signal(self):
        """Show NO SIGNAL message"""
        self.no_signal_text.set_visible(True)
        self.line.set_data([], [])
        self.update_limits()
        self.draw()
        
    def update_trigger_line(self, level):
        """Update trigger level line (relative to center/ground)"""
        # Trigger level is in absolute voltage, convert to relative
        trigger_relative = level - 1.65 - self.v_offset
        self.trigger_line.set_ydata([trigger_relative, trigger_relative])
        self.draw()

class OscilloscopeGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.serial_thread = None
        self.adc_data = []
        self.sample_rate = 100000
        self.is_running = False
        self.probe_attenuation = 1
        
        self.initUI()
        
        # Start update timer for GUI refresh even without connection
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(100)  # Update every 100ms
        
    def initUI(self):
        self.setWindowTitle('ESP32 Oscilloscope')
        self.setGeometry(100, 100, 1200, 700)  # Smaller default size
        self.setMinimumSize(1000, 600)  # Minimum size
        self.setStyleSheet("background-color: #2b2b2b; color: #ffffff;")
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Top: Display area
        display_widget = QWidget()
        display_layout = QHBoxLayout(display_widget)
        display_layout.setContentsMargins(0, 0, 0, 0)
        display_layout.setSpacing(5)
        
        # Left: Canvas
        self.canvas = OscilloscopeCanvas(self)
        display_layout.addWidget(self.canvas, 3)
        
        # Right: Control panel (scrollable for small screens)
        control_scroll = QScrollArea()
        control_scroll.setWidgetResizable(True)
        control_scroll.setMaximumWidth(300)
        control_scroll.setMinimumWidth(250)
        control_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        control_panel = self.create_control_panel()
        control_scroll.setWidget(control_panel)
        display_layout.addWidget(control_scroll, 0)
        
        main_layout.addWidget(display_widget, 1)
        
        # Bottom: Status and measurements (fixed height)
        bottom_panel = self.create_bottom_panel()
        main_layout.addWidget(bottom_panel, 0)
        
    def create_control_panel(self):
        panel = QWidget()
        panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        panel.setStyleSheet("""
            QGroupBox {
                border: 2px solid #00ff00;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
                color: #00ff00;
                font-size: 10px;
                padding-top: 10px;
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
                padding: 5px;
                font-weight: bold;
                min-height: 25px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #00ff00;
                color: #000000;
            }
            QComboBox {
                background-color: #3a3a3a;
                border: 1px solid #00ff00;
                color: #00ff00;
                padding: 3px;
                font-size: 10px;
            }
            QLabel {
                color: #ffffff;
                font-size: 9px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Connection Group
        conn_group = QGroupBox("Connection")
        conn_layout = QGridLayout()
        
        self.port_combo = QComboBox()
        self.refresh_ports()
        conn_layout.addWidget(QLabel("Port:"), 0, 0)
        conn_layout.addWidget(self.port_combo, 0, 1)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        conn_layout.addWidget(self.connect_btn, 1, 0, 1, 2)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_ports)
        conn_layout.addWidget(refresh_btn, 2, 0, 1, 2)
        
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)
        
        # Acquisition Control
        acq_group = QGroupBox("Acquisition")
        acq_layout = QVBoxLayout()
        
        self.run_btn = QPushButton("⏸ Stop" if self.is_running else "▶ Run")
        self.run_btn.clicked.connect(self.toggle_acquisition)
        self.run_btn.setEnabled(False)
        acq_layout.addWidget(self.run_btn)
        
        self.single_btn = QPushButton("⏺ Single")
        self.single_btn.clicked.connect(self.single_acquisition)
        self.single_btn.setEnabled(False)
        acq_layout.addWidget(self.single_btn)
        
        acq_group.setLayout(acq_layout)
        layout.addWidget(acq_group)
        
        # VERTICAL CONTROL with Rotary Knob
        vert_group = QGroupBox("⬍ VERTICAL (CH1) ⬍")
        vert_layout = QVBoxLayout()
        vert_layout.setAlignment(Qt.AlignCenter)
        
        # Volts/DIV Knob
        knob_layout = QVBoxLayout()
        knob_layout.setAlignment(Qt.AlignCenter)
        
        volts_label = QLabel("VOLTS/DIV")
        volts_label.setAlignment(Qt.AlignCenter)
        volts_label.setStyleSheet("font-weight: bold; color: #00ff00; font-size: 11px;")
        knob_layout.addWidget(volts_label)
        
        self.v_knob = RotaryKnob()
        self.v_knob.setMinimum(0)
        self.v_knob.setMaximum(19)  # 20 steps (0-19)
        self.v_knob.setValue(5)  # Start at 0.5V (index 5)
        self.v_knob.valueChanged.connect(self.on_v_knob_changed)
        
        # Set range so knob rotation is limited (270 degrees typical)
        self.v_knob.setNotchTarget(1.5)  # Make notches more granular
        
        knob_layout.addWidget(self.v_knob, alignment=Qt.AlignCenter)
        
        self.v_div_display = QLabel("0.500 V/div")
        self.v_div_display.setAlignment(Qt.AlignCenter)
        self.v_div_display.setStyleSheet("color: #00ff00; font-size: 12px; font-weight: bold; background-color: #1a1a1a; padding: 3px; border-radius: 3px;")
        knob_layout.addWidget(self.v_div_display)
        
        vert_layout.addLayout(knob_layout)
        
        # Position slider
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("Position:"))
        self.v_pos_slider = QSlider(Qt.Horizontal)
        self.v_pos_slider.setMinimum(-200)
        self.v_pos_slider.setMaximum(200)
        self.v_pos_slider.setValue(0)
        self.v_pos_slider.valueChanged.connect(lambda v: self.change_v_position(v/100.0))
        pos_layout.addWidget(self.v_pos_slider)
        self.v_pos_label = QLabel("0.0V")
        self.v_pos_label.setMinimumWidth(50)
        pos_layout.addWidget(self.v_pos_label)
        vert_layout.addLayout(pos_layout)
        
        vert_group.setLayout(vert_layout)
        layout.addWidget(vert_group)
        
        # HORIZONTAL CONTROL with Rotary Knob
        horiz_group = QGroupBox("⬌ HORIZONTAL (TIME) ⬌")
        horiz_layout = QVBoxLayout()
        horiz_layout.setAlignment(Qt.AlignCenter)
        
        # Time/DIV Knob
        knob_layout2 = QVBoxLayout()
        knob_layout2.setAlignment(Qt.AlignCenter)
        
        time_label = QLabel("TIME/DIV")
        time_label.setAlignment(Qt.AlignCenter)
        time_label.setStyleSheet("font-weight: bold; color: #00ff00; font-size: 11px;")
        knob_layout2.addWidget(time_label)
        
        self.t_knob = RotaryKnob()
        self.t_knob.setMinimum(0)
        self.t_knob.setMaximum(25)  # 26 steps (0-25)
        self.t_knob.setValue(4)  # Start at 2ms (index 4)
        self.t_knob.valueChanged.connect(self.on_t_knob_changed)
        self.t_knob.setNotchTarget(1.5)
        knob_layout2.addWidget(self.t_knob, alignment=Qt.AlignCenter)
        
        self.t_div_display = QLabel("2.00 ms/div")
        self.t_div_display.setAlignment(Qt.AlignCenter)
        self.t_div_display.setStyleSheet("color: #00ff00; font-size: 12px; font-weight: bold; background-color: #1a1a1a; padding: 3px; border-radius: 3px;")
        knob_layout2.addWidget(self.t_div_display)
        
        horiz_layout.addLayout(knob_layout2)
        
        # Sample rate
        rate_layout = QHBoxLayout()
        rate_layout.addWidget(QLabel("Rate:"))
        self.rate_combo = QComboBox()
        self.rate_combo.addItems(['10k', '50k', '100k', '200k', '500k', '1M'])
        self.rate_combo.setCurrentText('100k')
        self.rate_combo.currentTextChanged.connect(self.change_sample_rate)
        rate_layout.addWidget(self.rate_combo)
        horiz_layout.addLayout(rate_layout)
        
        # Position slider
        pos_layout2 = QHBoxLayout()
        pos_layout2.addWidget(QLabel("Position:"))
        self.h_pos_slider = QSlider(Qt.Horizontal)
        self.h_pos_slider.setMinimum(-500)
        self.h_pos_slider.setMaximum(500)
        self.h_pos_slider.setValue(0)
        self.h_pos_slider.valueChanged.connect(lambda v: self.change_h_position(v/10.0))
        pos_layout2.addWidget(self.h_pos_slider)
        self.h_pos_label = QLabel("0.0ms")
        self.h_pos_label.setMinimumWidth(50)
        pos_layout2.addWidget(self.h_pos_label)
        horiz_layout.addLayout(pos_layout2)
        
        horiz_group.setLayout(horiz_layout)
        layout.addWidget(horiz_group)
        
        # Trigger Control
        trig_group = QGroupBox("⚡ Trigger")
        trig_layout = QGridLayout()
        
        trig_layout.addWidget(QLabel("Mode:"), 0, 0)
        self.trig_mode_combo = QComboBox()
        self.trig_mode_combo.addItems(['Auto', 'Normal', 'Single'])
        self.trig_mode_combo.currentIndexChanged.connect(self.change_trigger_mode)
        trig_layout.addWidget(self.trig_mode_combo, 0, 1)
        
        trig_layout.addWidget(QLabel("Edge:"), 1, 0)
        self.trig_edge_combo = QComboBox()
        self.trig_edge_combo.addItems(['Rising ↗', 'Falling ↘'])
        self.trig_edge_combo.currentIndexChanged.connect(self.change_trigger_edge)
        trig_layout.addWidget(self.trig_edge_combo, 1, 1)
        
        trig_layout.addWidget(QLabel("Level:"), 2, 0)
        self.trig_level_slider = QSlider(Qt.Horizontal)
        self.trig_level_slider.setMinimum(0)
        self.trig_level_slider.setMaximum(330)
        self.trig_level_slider.setValue(165)
        self.trig_level_slider.valueChanged.connect(lambda v: self.change_trigger_level(v/100.0))
        trig_layout.addWidget(self.trig_level_slider, 2, 1)
        
        self.trig_level_label = QLabel("1.65V")
        trig_layout.addWidget(self.trig_level_label, 3, 0, 1, 2)
        
        trig_group.setLayout(trig_layout)
        layout.addWidget(trig_group)
        
        # Probe Settings
        probe_group = QGroupBox("🔌 Probe")
        probe_layout = QHBoxLayout()
        
        self.probe_combo = QComboBox()
        self.probe_combo.addItems(['1x', '10x', '100x'])
        self.probe_combo.setCurrentText('1x')
        self.probe_combo.currentTextChanged.connect(self.change_probe)
        probe_layout.addWidget(self.probe_combo)
        
        probe_group.setLayout(probe_layout)
        layout.addWidget(probe_group)
        
        layout.addStretch()
        
        return panel
    
    def create_bottom_panel(self):
        """Create bottom panel with status and measurements"""
        panel = QWidget()
        panel.setMaximumHeight(100)
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        panel.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                border-top: 2px solid #00ff00;
            }
            QLabel {
                color: #00ff00;
                font-size: 11px;
                font-weight: bold;
                padding: 3px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(3)
        
        # Combined status and measurements
        combined_layout = QHBoxLayout()
        
        # Status
        self.status_label = QLabel('● Disconnected')
        self.status_label.setStyleSheet("color: #ff0000; font-size: 12px; font-weight: bold;")
        combined_layout.addWidget(self.status_label)
        
        combined_layout.addStretch()
        
        # Measurements in compact grid
        meas_layout = QGridLayout()
        meas_layout.setSpacing(10)
        meas_layout.setContentsMargins(0, 0, 0, 0)
        
        # Row 1: Voltage measurements
        self.vmax_label = QLabel("Vmax:--")
        self.vmin_label = QLabel("Vmin:--")
        self.vavg_label = QLabel("Vavg:--")
        self.vpp_label = QLabel("Vpp:--")
        
        meas_layout.addWidget(self.vmax_label, 0, 0)
        meas_layout.addWidget(self.vmin_label, 0, 1)
        meas_layout.addWidget(self.vavg_label, 0, 2)
        meas_layout.addWidget(self.vpp_label, 0, 3)
        
        # Row 2: Frequency and time measurements
        self.freq_label = QLabel("Freq:--")
        self.period_label = QLabel("Period:--")
        self.duty_label = QLabel("Duty:--")
        self.samples_label = QLabel("Samp:2000")
        
        meas_layout.addWidget(self.freq_label, 1, 0)
        meas_layout.addWidget(self.period_label, 1, 1)
        meas_layout.addWidget(self.duty_label, 1, 2)
        meas_layout.addWidget(self.samples_label, 1, 3)
        
        combined_layout.addLayout(meas_layout)
        layout.addLayout(combined_layout)
        
        return panel

    def get_v_div_values(self):
        """Get voltage per division values (in Volts)"""
        return [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 
                0.015, 0.025, 0.075, 0.15, 0.25, 0.75, 1.5, 2.5,
                0.03, 0.04, 0.06]  # 20 values (index 0-19)

    def get_t_div_values(self):
        """Get time per division values (in ms)"""
        return [0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0,
                0.25, 0.75, 1.5, 2.5, 7.5, 15.0, 25.0,
                0.3, 0.4, 0.6, 0.8, 3.0, 4.0, 6.0, 8.0, 30.0, 40.0]  # 26 values

    def on_v_knob_changed(self, value):
        """Handle voltage knob rotation"""
        values = self.get_v_div_values()
        if 0 <= value < len(values):
            v_div = values[value]
            # Update display
            if v_div < 1.0:
                self.v_div_display.setText(f"{v_div*1000:.0f} mV/div")
            else:
                self.v_div_display.setText(f"{v_div:.3f} V/div")

    def on_t_knob_changed(self, value):
        """Handle time knob rotation"""
        values = self.get_t_div_values()
        if 0 <= value < len(values):
            t_div = values[value]
            # Update display
            if t_div < 1.0:
                self.t_div_display.setText(f"{t_div*1000:.0f} µs/div")
            else:
                self.t_div_display.setText(f"{t_div:.2f} ms/div")
        
    def refresh_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(f"{port.device} - {port.description}")
            
    def toggle_connection(self):
        if self.serial_thread is None or not self.serial_thread.isRunning():
            port = self.port_combo.currentText().split(' ')[0]
            
            try:
                self.serial_thread = SerialThread(port)
                self.serial_thread.data_received.connect(self.on_data_received)
                self.serial_thread.connection_lost.connect(self.on_connection_lost)
                self.serial_thread.start()
                
                self.status_label.setText('● Connected')
                self.status_label.setStyleSheet("color: #00ff00; font-size: 12px; font-weight: bold;")
                self.connect_btn.setText("Disconnect")
                self.run_btn.setEnabled(True)
                self.single_btn.setEnabled(True)
                
                # Clear NO SIGNAL on connection
                self.adc_data = []
                
            except Exception as e:
                QMessageBox.critical(self, "Connection Error", str(e))
        else:
            self.serial_thread.send_command("STOP")
            self.serial_thread.stop()
            self.serial_thread.wait()
            self.serial_thread = None
            
            self.status_label.setText('● Disconnected')
            self.status_label.setStyleSheet("color: #ff0000; font-size: 12px; font-weight: bold;")
            self.connect_btn.setText("Connect")
            self.run_btn.setEnabled(False)
            self.single_btn.setEnabled(False)
            self.is_running = False
            self.run_btn.setText("Run")
            
            # Show NO SIGNAL after disconnect
            self.adc_data = []
            self.canvas.show_no_signal()
            self.reset_measurements()
            
    def toggle_acquisition(self):
        if self.serial_thread:
            if self.is_running:
                self.serial_thread.send_command("STOP")
                self.run_btn.setText("▶ Run")
                self.is_running = False
            else:
                self.serial_thread.send_command("START")
                self.run_btn.setText("⏸ Stop")
                self.is_running = True
                
    def single_acquisition(self):
        if self.serial_thread:
            self.serial_thread.send_command("TRIG_MODE:2")
            self.serial_thread.send_command("START")
            
    def change_sample_rate(self, text):
        rates = {
            '10k': 10000,
            '50k': 50000,
            '100k': 100000,
            '200k': 200000,
            '500k': 500000,
            '1M': 1000000
        }
        
        if text in rates:
            self.sample_rate = rates[text]
            if self.serial_thread:
                self.serial_thread.send_command(f"RATE:{self.sample_rate}")
    
    def change_v_position(self, value):
        """Change vertical position (offset)"""
        self.canvas.set_vertical_offset(value)
        self.v_pos_label.setText(f"{value:.1f}V")
    
    def change_h_position(self, value):
        """Change horizontal position (offset)"""
        self.canvas.set_horizontal_offset(value)
        self.h_pos_label.setText(f"{value:.1f}ms")
            
    def change_trigger_mode(self, index):
        if self.serial_thread:
            self.serial_thread.send_command(f"TRIG_MODE:{index}")
            
    def change_trigger_edge(self, index):
        if self.serial_thread:
            self.serial_thread.send_command(f"TRIG_EDGE:{index}")
            
    def change_trigger_level(self, value):
        if self.serial_thread:
            self.serial_thread.send_command(f"TRIG_LEVEL:{value}")
        self.canvas.update_trigger_line(value)
        self.trig_level_label.setText(f"{value:.2f}V")
    
    def change_probe(self, text):
        probe_values = {'1x': 1, '10x': 10, '100x': 100}
        self.probe_attenuation = probe_values.get(text, 1)
        if self.serial_thread:
            self.serial_thread.send_command(f"PROBE:{self.probe_attenuation}")
    
    def update_display(self):
        """Periodic update even when disconnected"""
        if self.serial_thread is None or not self.serial_thread.isRunning():
            # Show NO SIGNAL when not connected
            if len(self.adc_data) == 0:
                self.canvas.show_no_signal()
            
    def on_data_received(self, data, sample_rate):
        self.adc_data = data
        self.sample_rate = sample_rate
        
        # Get division settings from knobs
        v_values = self.get_v_div_values()
        t_values = self.get_t_div_values()
        
        v_idx = self.v_knob.value()
        t_idx = self.t_knob.value()
        
        v_per_div = v_values[v_idx] if v_idx < len(v_values) else 0.5
        t_per_div = t_values[t_idx] if t_idx < len(t_values) else 2.0
        
        # Update plot
        self.canvas.update_plot(data, sample_rate, v_per_div, t_per_div)
        
        # Calculate measurements (in centered voltage)
        voltage = np.array(data) * 3.3 / 4095.0 - 1.65
        v_max = voltage.max()
        v_min = voltage.min()
        v_avg = voltage.mean()
        v_pp = v_max - v_min
        
        # Estimate frequency
        freq = self.estimate_frequency(voltage, sample_rate)
        period = 1000.0 / freq if freq > 0 else 0
        
        # Update labels with compact format
        self.vmax_label.setText(f"Vmax:{v_max:.2f}V")
        self.vmin_label.setText(f"Vmin:{v_min:.2f}V")
        self.vavg_label.setText(f"Vavg:{v_avg:.2f}V")
        self.vpp_label.setText(f"Vpp:{v_pp:.2f}V")
        
        if freq > 0:
            if freq < 1000:
                self.freq_label.setText(f"Freq:{freq:.1f}Hz")
            elif freq < 1000000:
                self.freq_label.setText(f"Freq:{freq/1000:.2f}kHz")
            else:
                self.freq_label.setText(f"Freq:{freq/1000000:.2f}MHz")
            
            self.period_label.setText(f"Per:{period:.2f}ms")
        else:
            self.freq_label.setText("Freq:--")
            self.period_label.setText("Per:--")
            
    def estimate_frequency(self, voltage, sample_rate):
        try:
            # Find zero crossings
            mean_val = voltage.mean()
            crossings = np.where(np.diff(np.sign(voltage - mean_val)))[0]
            
            if len(crossings) > 2:
                # Calculate period from average distance between crossings
                periods = np.diff(crossings)
                avg_period = np.mean(periods) * 2  # *2 because zero-crossing is half period
                frequency = sample_rate / avg_period
                return frequency
            return 0
        except:
            return 0
            
    def on_connection_lost(self):
        QMessageBox.warning(self, "Connection Lost", "Serial connection was lost!")
        self.toggle_connection()
    
    def reset_measurements(self):
        """Reset all measurement displays"""
        self.vmax_label.setText("V Max: -- V")
        self.vmin_label.setText("V Min: -- V")
        self.vavg_label.setText("V Avg: -- V")
        self.vpp_label.setText("Vpp: -- V")
        self.freq_label.setText("Frequency: -- Hz")
        
def main():
    app = QApplication(sys.argv)
    gui = OscilloscopeGUI()
    gui.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
