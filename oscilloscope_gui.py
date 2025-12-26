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
                             QMessageBox, QSlider, QDial, QScrollArea, QSizePolicy, QFrame)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QPainter, QColor, QPen
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
        self.setFixedSize(80, 80)
        
        # Set rotation range: from ~210 degrees (7 o'clock) to ~-30 degrees (5 o'clock)
        # Total rotation: 240 degrees (like real oscilloscope knobs)
        # QDial uses: 0 deg = 6 o'clock, rotates counter-clockwise
        # We want: minimum at 7 o'clock (210°), maximum at 5 o'clock (330° or -30°)
        
        # Style
        self.setStyleSheet("""
            QDial {
                background-color: #2a2a2a;
                border: 3px solid #00ff00;
                border-radius: 40px;
            }
        """)
    
    def paintEvent(self, event):
        """Custom paint to show knob pointer/indicator"""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate angle based on value
        # Map value range to 270 degrees rotation (from -135° to +135° from top)
        # In oscilloscope style: minimum at bottom-left, maximum at bottom-right
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
        self.setMinimumSize(1100, 650)  # Minimum size
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
        display_layout.addWidget(self.canvas, 1)
        
        # Right: Control panel (NO SCROLL - compact design)
        control_panel = self.create_control_panel()
        control_panel.setMaximumWidth(280)
        control_panel.setMinimumWidth(260)
        display_layout.addWidget(control_panel, 0)
        
        main_layout.addWidget(display_widget, 1)
        
        # Bottom: Status and measurements (fixed height, spread layout)
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
        
        # Connection Group - Compact
        conn_group = QGroupBox("Connection")
        conn_layout = QVBoxLayout()
        conn_layout.setSpacing(3)
        
        # Port selection in horizontal
        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(100)
        self.refresh_ports()
        port_row.addWidget(self.port_combo, 1)
        conn_layout.addLayout(port_row)
        
        # Buttons in horizontal
        btn_row = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        btn_row.addWidget(self.connect_btn)
        
        refresh_btn = QPushButton("⟳")
        refresh_btn.setMaximumWidth(35)
        refresh_btn.clicked.connect(self.refresh_ports)
        refresh_btn.setToolTip("Refresh Ports")
        btn_row.addWidget(refresh_btn)
        conn_layout.addLayout(btn_row)
        
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)
        
        # Acquisition Control - Compact Horizontal
        acq_group = QGroupBox("Acquisition")
        acq_layout = QHBoxLayout()
        acq_layout.setSpacing(3)
        
        self.run_btn = QPushButton("▶ Run")
        self.run_btn.clicked.connect(self.toggle_acquisition)
        self.run_btn.setEnabled(False)
        acq_layout.addWidget(self.run_btn)
        
        self.single_btn = QPushButton("Single")
        self.single_btn.clicked.connect(self.single_acquisition)
        self.single_btn.setEnabled(False)
        acq_layout.addWidget(self.single_btn)
        
        acq_group.setLayout(acq_layout)
        layout.addWidget(acq_group)
        
        # VERTICAL CONTROL with Rotary Knob
        vert_group = QGroupBox("Vertical")
        vert_main_layout = QHBoxLayout()  # Main horizontal layout
        vert_main_layout.setSpacing(5)
        
        # Left side: Knob (fixed width)
        knob_section = QVBoxLayout()
        knob_section.setAlignment(Qt.AlignCenter)
        knob_section.setSpacing(2)  # Reduced from 3
        
        volts_label = QLabel("VOLTS/DIV")
        volts_label.setAlignment(Qt.AlignCenter)
        volts_label.setStyleSheet("font-weight: bold; color: #00ff00; font-size: 10px;")
        volts_label.setFixedWidth(90)  # Fixed width to prevent shift
        knob_section.addWidget(volts_label)
        
        knob_section.addSpacing(10)  # Increased from 5 to 10
        
        self.v_knob = RotaryKnob()
        self.v_knob.setMinimum(0)
        self.v_knob.setMaximum(19)  # 20 steps (0-19)
        self.v_knob.setValue(5)  # Start at 0.5V (index 5)
        self.v_knob.valueChanged.connect(self.on_v_knob_changed)
        self.v_knob.setNotchTarget(1.5)
        self.v_knob.setFixedSize(70, 70)
        knob_section.addWidget(self.v_knob, alignment=Qt.AlignCenter)
        
        knob_section.addSpacing(10)  # Increased from 5 to 10
        
        self.v_div_display = QLabel("0.500 V/div")
        self.v_div_display.setAlignment(Qt.AlignCenter)
        self.v_div_display.setStyleSheet("color: #00ff00; font-size: 11px; font-weight: bold; background-color: #1a1a1a; padding: 2px; border-radius: 3px;")
        self.v_div_display.setFixedWidth(90)  # Fixed width to prevent shift
        knob_section.addWidget(self.v_div_display)
        
        # Create container with fixed width for knob section
        knob_container = QWidget()
        knob_container.setFixedWidth(100)
        knob_container.setMinimumHeight(130)  # Set minimum height to accommodate spacing
        knob_container.setLayout(knob_section)
        vert_main_layout.addWidget(knob_container)
        
        # Add separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #00ff00;")
        vert_main_layout.addWidget(separator)
        
        # Right side: Position slider (vertical orientation)
        slider_section = QVBoxLayout()
        slider_section.setSpacing(3)
        
        pos_label = QLabel("Position")
        pos_label.setAlignment(Qt.AlignCenter)
        pos_label.setStyleSheet("font-weight: bold; color: #00ff00; font-size: 9px;")
        slider_section.addWidget(pos_label)
        
        # Slider with reset button
        slider_row = QHBoxLayout()
        slider_row.setSpacing(3)
        
        self.v_pos_slider = QSlider(Qt.Vertical)
        self.v_pos_slider.setMinimum(-200)
        self.v_pos_slider.setMaximum(200)
        self.v_pos_slider.setValue(0)
        self.v_pos_slider.setInvertedAppearance(True)  # Up = positive
        self.v_pos_slider.valueChanged.connect(lambda v: self.change_v_position(v/100.0))
        self.v_pos_slider.setFixedHeight(100)
        slider_row.addWidget(self.v_pos_slider, alignment=Qt.AlignCenter)
        
        v_reset_btn = QPushButton("⟲")
        v_reset_btn.setFixedSize(25, 25)
        v_reset_btn.setToolTip("Reset to center")
        v_reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #00ff00;
                border: 1px solid #00ff00;
                border-radius: 3px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
            QPushButton:pressed {
                background-color: #1a1a1a;
            }
        """)
        v_reset_btn.clicked.connect(lambda: self.v_pos_slider.setValue(0))
        slider_row.addWidget(v_reset_btn, alignment=Qt.AlignTop)
        
        slider_section.addLayout(slider_row)
        
        self.v_pos_label = QLabel("0.0V")
        self.v_pos_label.setAlignment(Qt.AlignCenter)
        self.v_pos_label.setMinimumWidth(40)
        self.v_pos_label.setStyleSheet("font-size: 9px;")
        slider_section.addWidget(self.v_pos_label)
        
        vert_main_layout.addLayout(slider_section)
        
        vert_group.setLayout(vert_main_layout)
        layout.addWidget(vert_group)
        
        # HORIZONTAL CONTROL with Rotary Knob
        horiz_group = QGroupBox("Horizontal")
        horiz_main_layout = QHBoxLayout()  # Main horizontal layout
        horiz_main_layout.setSpacing(5)
        
        # Left side: Knob (fixed width)
        knob_section = QVBoxLayout()
        knob_section.setAlignment(Qt.AlignCenter)
        knob_section.setSpacing(2)  # Reduced from 3
        
        time_label = QLabel("TIME/DIV")
        time_label.setAlignment(Qt.AlignCenter)
        time_label.setStyleSheet("font-weight: bold; color: #00ff00; font-size: 10px;")
        time_label.setFixedWidth(90)  # Fixed width to prevent shift
        knob_section.addWidget(time_label)
        
        knob_section.addSpacing(10)  # Increased from 5 to 10
        
        self.t_knob = RotaryKnob()
        self.t_knob.setMinimum(0)
        self.t_knob.setMaximum(25)  # 26 steps (0-25)
        self.t_knob.setValue(4)  # Start at 2ms (index 4)
        self.t_knob.valueChanged.connect(self.on_t_knob_changed)
        self.t_knob.setNotchTarget(1.5)
        self.t_knob.setFixedSize(70, 70)
        knob_section.addWidget(self.t_knob, alignment=Qt.AlignCenter)
        
        knob_section.addSpacing(10)  # Increased from 5 to 10
        
        self.t_div_display = QLabel("2.00 ms/div")
        self.t_div_display.setAlignment(Qt.AlignCenter)
        self.t_div_display.setStyleSheet("color: #00ff00; font-size: 11px; font-weight: bold; background-color: #1a1a1a; padding: 2px; border-radius: 3px;")
        self.t_div_display.setFixedWidth(90)  # Fixed width to prevent shift
        knob_section.addWidget(self.t_div_display)
        
        # Create container with fixed width for knob section
        knob_container = QWidget()
        knob_container.setFixedWidth(100)
        knob_container.setMinimumHeight(130)  # Set minimum height to accommodate spacing
        knob_container.setLayout(knob_section)
        horiz_main_layout.addWidget(knob_container)
        
        # Add separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #00ff00;")
        horiz_main_layout.addWidget(separator)
        
        # Right side: Rate and Position (in one row)
        controls_section = QVBoxLayout()
        controls_section.setSpacing(8)
        
        # Sample rate - compact horizontal
        rate_row = QHBoxLayout()
        rate_row.setSpacing(3)
        rate_label = QLabel("Rate:")
        rate_label.setStyleSheet("font-weight: bold; color: #00ff00; font-size: 9px;")
        rate_row.addWidget(rate_label)
        
        self.rate_combo = QComboBox()
        self.rate_combo.addItems(['10k', '50k', '100k', '200k', '500k', '1M'])
        self.rate_combo.setCurrentText('100k')
        self.rate_combo.currentTextChanged.connect(self.change_sample_rate)
        self.rate_combo.setMaximumWidth(70)
        rate_row.addWidget(self.rate_combo)
        rate_row.addStretch()
        controls_section.addLayout(rate_row)
        
        # Position
        pos_label = QLabel("Position")
        pos_label.setAlignment(Qt.AlignCenter)
        pos_label.setStyleSheet("font-weight: bold; color: #00ff00; font-size: 9px;")
        controls_section.addWidget(pos_label)
        
        # Position slider with reset button
        pos_slider_layout = QHBoxLayout()
        pos_slider_layout.setSpacing(3)
        
        self.h_pos_slider = QSlider(Qt.Horizontal)
        self.h_pos_slider.setMinimum(-500)
        self.h_pos_slider.setMaximum(500)
        self.h_pos_slider.setValue(0)
        self.h_pos_slider.valueChanged.connect(lambda v: self.change_h_position(v/10.0))
        pos_slider_layout.addWidget(self.h_pos_slider)
        
        h_reset_btn = QPushButton("⟲")
        h_reset_btn.setFixedSize(25, 25)
        h_reset_btn.setToolTip("Reset to center")
        h_reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #00ff00;
                border: 1px solid #00ff00;
                border-radius: 3px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
            QPushButton:pressed {
                background-color: #1a1a1a;
            }
        """)
        h_reset_btn.clicked.connect(lambda: self.h_pos_slider.setValue(0))
        pos_slider_layout.addWidget(h_reset_btn)
        
        controls_section.addLayout(pos_slider_layout)
        
        self.h_pos_label = QLabel("0.0ms")
        self.h_pos_label.setAlignment(Qt.AlignCenter)
        self.h_pos_label.setMinimumWidth(40)
        self.h_pos_label.setStyleSheet("font-size: 9px;")
        controls_section.addWidget(self.h_pos_label)
        
        horiz_main_layout.addLayout(controls_section)
        
        horiz_group.setLayout(horiz_main_layout)
        layout.addWidget(horiz_group)
        
        # Trigger and Probe - Combined in 2 columns
        trigger_probe_widget = QWidget()
        trigger_probe_layout = QHBoxLayout(trigger_probe_widget)
        trigger_probe_layout.setSpacing(5)
        trigger_probe_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left column: Trigger Control - Compact
        trig_group = QGroupBox("Trigger")
        trig_layout = QVBoxLayout()
        trig_layout.setSpacing(3)
        
        # Mode
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(2)
        mode_layout.addWidget(QLabel("Mode:"))
        self.trig_mode_combo = QComboBox()
        self.trig_mode_combo.addItems(['Auto', 'Normal', 'Single'])
        self.trig_mode_combo.currentIndexChanged.connect(self.change_trigger_mode)
        mode_layout.addWidget(self.trig_mode_combo)
        trig_layout.addLayout(mode_layout)
        
        # Edge
        edge_layout = QHBoxLayout()
        edge_layout.setSpacing(2)
        edge_layout.addWidget(QLabel("Edge:"))
        self.trig_edge_combo = QComboBox()
        self.trig_edge_combo.addItems(['↗', '↘'])
        self.trig_edge_combo.currentIndexChanged.connect(self.change_trigger_edge)
        edge_layout.addWidget(self.trig_edge_combo)
        trig_layout.addLayout(edge_layout)
        
        # Level
        level_layout = QVBoxLayout()
        level_layout.setSpacing(2)
        level_row = QHBoxLayout()
        level_row.setSpacing(2)
        level_row.addWidget(QLabel("Level:"))
        self.trig_level_slider = QSlider(Qt.Horizontal)
        self.trig_level_slider.setMinimum(0)
        self.trig_level_slider.setMaximum(330)
        self.trig_level_slider.setValue(165)
        self.trig_level_slider.valueChanged.connect(lambda v: self.change_trigger_level(v/100.0))
        level_row.addWidget(self.trig_level_slider)
        level_layout.addLayout(level_row)
        
        self.trig_level_label = QLabel("1.65V")
        self.trig_level_label.setAlignment(Qt.AlignCenter)
        self.trig_level_label.setStyleSheet("color: #ff0000; font-weight: bold; font-size: 10px;")
        level_layout.addWidget(self.trig_level_label)
        trig_layout.addLayout(level_layout)
        
        trig_group.setLayout(trig_layout)
        trigger_probe_layout.addWidget(trig_group)
        
        # Right column: Probe Settings - Compact
        probe_group = QGroupBox("Probe")
        probe_layout = QVBoxLayout()
        probe_layout.setSpacing(3)
        
        probe_layout.addWidget(QLabel("Attenuation:"))
        self.probe_combo = QComboBox()
        self.probe_combo.addItems(['1x', '10x', '100x'])
        self.probe_combo.setCurrentText('1x')
        self.probe_combo.currentTextChanged.connect(self.change_probe)
        probe_layout.addWidget(self.probe_combo)
        
        probe_layout.addStretch()
        
        probe_group.setLayout(probe_layout)
        trigger_probe_layout.addWidget(probe_group)
        
        layout.addWidget(trigger_probe_widget)
        
        layout.addStretch()
        
        return panel
    
    def create_bottom_panel(self):
        """Create bottom panel with status and measurements"""
        panel = QWidget()
        panel.setMaximumHeight(90)
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
                padding: 2px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)
        
        # Row 1: Status
        status_row = QHBoxLayout()
        self.status_label = QLabel('● Disconnected')
        self.status_label.setStyleSheet("color: #ff0000; font-size: 12px; font-weight: bold;")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        layout.addLayout(status_row)
        
        # Row 2: Voltage measurements
        volt_row = QHBoxLayout()
        volt_row.setSpacing(10)
        
        self.vmax_label = QLabel("Vmax: --")
        self.vmax_label.setMinimumWidth(120)
        self.vmax_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.vmin_label = QLabel("Vmin: --")
        self.vmin_label.setMinimumWidth(120)
        self.vmin_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.vavg_label = QLabel("Vavg: --")
        self.vavg_label.setMinimumWidth(120)
        self.vavg_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.vpp_label = QLabel("Vpp: --")
        self.vpp_label.setMinimumWidth(120)
        self.vpp_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
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
        
        self.period_label = QLabel("Period: --")
        self.period_label.setMinimumWidth(150)
        self.period_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.duty_label = QLabel("Duty: --")
        self.duty_label.setMinimumWidth(120)
        self.duty_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.samples_label = QLabel("Samples: 2000")
        self.samples_label.setMinimumWidth(120)
        self.samples_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        freq_row.addWidget(self.freq_label)
        freq_row.addWidget(self.period_label)
        freq_row.addWidget(self.duty_label)
        freq_row.addWidget(self.samples_label)
        freq_row.addStretch()
        layout.addLayout(freq_row)
        
        return panel

    def get_v_div_values(self):
        """Get voltage per division values (in Volts) - sorted from smallest to largest"""
        return [0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05, 0.06, 0.075, 0.1,
                0.15, 0.2, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 5.0]  # 20 values (index 0-19)

    def get_t_div_values(self):
        """Get time per division values (in ms) - sorted from smallest to largest"""
        return [0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.75, 0.8, 1.0,
                1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.5, 8.0, 10.0,
                15.0, 20.0, 25.0, 30.0, 40.0, 50.0]  # 26 values (index 0-25)

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
        self.vmax_label.setText(f"Vmax: {v_max:.2f}V")
        self.vmin_label.setText(f"Vmin: {v_min:.2f}V")
        self.vavg_label.setText(f"Vavg: {v_avg:.2f}V")
        self.vpp_label.setText(f"Vpp: {v_pp:.2f}V")
        
        if freq > 0:
            if freq < 1000:
                self.freq_label.setText(f"Freq: {freq:.1f} Hz")
            elif freq < 1000000:
                self.freq_label.setText(f"Freq: {freq/1000:.2f} kHz")
            else:
                self.freq_label.setText(f"Freq: {freq/1000000:.2f} MHz")
            
            self.period_label.setText(f"Period: {period:.2f} ms")
        else:
            self.freq_label.setText("Freq: --")
            self.period_label.setText("Period: --")
            
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
        self.vmax_label.setText("Vmax: --")
        self.vmin_label.setText("Vmin: --")
        self.vavg_label.setText("Vavg: --")
        self.vpp_label.setText("Vpp: --")
        self.freq_label.setText("Freq: --")
        self.period_label.setText("Period: --")
        self.duty_label.setText("Duty: --")
        
def main():
    app = QApplication(sys.argv)
    gui = OscilloscopeGUI()
    gui.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
