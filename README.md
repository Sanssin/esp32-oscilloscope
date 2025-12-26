# ESP32 Oscilloscope Project

## Overview
DIY Oscilloscope using ESP32U DevKit V4 with Python GUI interface on PC. This project is inspired by the ESP32-Oscilloscope project but modified for serial communication instead of TFT display.

## Project Structure

### ESP32 Firmware Files:
- **ESP32_Oscilloscope.ino** - Main program with setup, loop, and command handling
- **i2s.ino** - I2S configuration for high-speed ADC sampling
- **adc.ino** - ADC characterization and voltage conversion
- **data_analysis.ino** - Signal analysis, frequency calculation, and trigger detection
- **filters.h** - Digital filter implementations (low-pass and mean filter)
- **debug_routines.ino** - Debugging and diagnostic functions

### Python GUI:
- **oscilloscope_gui.py** - Full-featured GUI application
- **test_serial.py** - Serial connection test utility
- **requirements.txt** - Python dependencies

## Hardware Requirements
- ESP32U DevKit V4
- USB Cable (for serial communication)
- Signal source to measure (max 3.3V)

## Connections
- **ADC Input**: GPIO34 (ADC1_CHANNEL_6)
- **Ground**: GND
- **Power**: USB

**IMPORTANT**: Input voltage must be 0-3.3V. For higher voltages, use a voltage divider circuit.

### Voltage Divider Example (for 5V signals):
```
Signal ----[10kΩ]---- GPIO34
                |
              [6.8kΩ]
                |
               GND
```
This divides 5V to ~2V (safe for ESP32).

## Software Requirements

### For ESP32:
1. Arduino IDE (1.8.x or higher)
2. ESP32 Board support
   - In Arduino IDE: File → Preferences → Additional Board Manager URLs
   - Add: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
   - Tools → Board → Boards Manager → Install "ESP32 by Espressif"

### For PC (Python GUI):
- Python 3.8 or higher
- Required libraries:
```bash
pip install pyserial numpy matplotlib pyqt5
```

## Installation

### 1. Upload ESP32 Firmware
1. Open `ESP32_Oscilloscope.ino` in Arduino IDE
2. Select board: Tools → Board → ESP32 Arduino → ESP32 Dev Module
3. Select port: Tools → Port → (your ESP32 port)
4. Upload the sketch

### 2. Run Python GUI
```bash
python oscilloscope_gui.py
```

**Note:** GUI will open even without ESP32 connected, showing "NO SIGNAL" until device is connected.

### 3. Test Connection (Optional)
Before running the full GUI, you can test the serial connection:
```bash
python test_serial.py
```

This will verify:
- ESP32 is detected on COM port
- Firmware responds to commands
- Data acquisition is working

## Features

### Firmware Features:
- **High-speed sampling** using I2S DMA (up to 1 MSPS)
- **Modular architecture** - separate files for each function
- **Advanced trigger system** - Auto, Normal, Single modes with rising/falling edge
- **Real-time measurements** - frequency, Vpp, mean calculated on ESP32
- **Probe compensation** - 1x, 10x, 100x attenuation support
- **Digital filtering** - low-pass and mean filters for noise reduction
- **Serial protocol** - efficient text-based communication
- **Debug utilities** - self-test and buffer inspection

### GUI Features:
- **Professional oscilloscope UI** - classic green trace on black background
- **Works offline** - GUI can open without ESP32 connected
- **"NO SIGNAL" indicator** - clear visual feedback when disconnected
- **Real-time waveform** - smooth display with grid overlay
- **Auto-scaling** - automatic voltage and time scale adjustment
- **Manual controls** - full control over all parameters
- **Measurements panel** - displays Vmax, Vmin, Vavg, Vpp, Frequency
- **Multiple sample rates** - 10kHz to 1MHz selectable
- **Probe settings** - compensate for probe attenuation

### Acquisition Modes:
- **Auto**: Continuous acquisition without trigger
- **Normal**: Wait for trigger condition
- **Single**: Single shot acquisition

### Trigger Settings:
- **Edge**: Rising or Falling edge detection
- **Level**: Adjustable voltage threshold (0-3.3V)

### Timebase:
- Sample rates: 10 kHz to 1 MHz
- Adjustable time scale: 0.1 - 100 ms

### Vertical Scale:
- Auto-scale or manual (0.5V, 1V, 2V, 3.3V, 5V)

### Measurements:
- Vmax, Vmin, Vavg
- Vpp (peak-to-peak)
- Frequency estimation

### Display:
- Classic oscilloscope-style green trace
- Grid overlay
- Real-time waveform display

## Usage

### Testing GUI First (Recommended)

Before connecting real hardware, test the GUI with dummy data:

```bash
python oscilloscope_dummy.py
```

This opens the GUI with simulated signals. You can:
- ✅ Test all controls (timebase, voltage scale, trigger)
- ✅ Try different waveforms (sine, square, triangle, etc.)
- ✅ Adjust frequency, amplitude, offset
- ✅ Verify measurements display correctly
- ✅ Check if display updates smoothly

### Using with Real ESP32

1. **Start GUI First**:
   - Run `oscilloscope_gui.py`
   - GUI will open and display "NO SIGNAL"
   - This is normal - you haven't connected yet!

2. **Connect Hardware**:
   - Connect ESP32 to PC via USB
   - Connect signal to GPIO34 (remember: max 3.3V!)

3. **Start GUI** (if not already running):
   - Run `oscilloscope_gui.py`
   - Select COM port from dropdown
   - Click "Connect"
   - "NO SIGNAL" should disappear when data starts flowing

4. **Acquire Signal**:
   - Click "Run" for continuous acquisition
   - Click "Single" for one-shot capture
   - Adjust sample rate and scales as needed

5. **Configure Probe** (if using probe):
   - Select probe attenuation (1x, 10x, 100x)
   - Voltage readings will be automatically scaled

6. **Configure Trigger**:
   - Set trigger mode (Auto/Normal/Single)
   - Set trigger level using spin box
   - Choose edge direction (Rising/Falling)

## Specifications

- **Input Range**: 0 - 3.3V DC
- **Input Impedance**: ~50kΩ (ESP32 ADC)
- **Resolution**: 12-bit (4096 levels)
- **Max Sample Rate**: 1 MSPS
- **Buffer Size**: 2000 samples
- **Bandwidth**: ~100 kHz (limited by ADC and processing)

## Serial Protocol

### Commands (PC → ESP32):
- `START` - Start acquisition
- `STOP` - Stop acquisition
- `RATE:<value>` - Set sample rate in Hz (e.g., `RATE:100000`)
- `TRIG_MODE:<0|1|2>` - Set trigger mode (0=Auto, 1=Normal, 2=Single)
- `TRIG_LEVEL:<voltage>` - Set trigger level in volts (e.g., `TRIG_LEVEL:1.65`)
- `TRIG_EDGE:<0|1>` - Set trigger edge (0=Falling, 1=Rising)
- `PROBE:<1|10|100>` - Set probe attenuation
- `STATUS` - Request current status
- `PING` - Check connection (returns `PONG`)
- `GET_DATA` - Request data transmission

### Responses (ESP32 → PC):
**Data format:**
```
DATA:<sample_rate>,<freq>,<vpp>,<mean>,<adc1>,<adc2>,...,<adcN>
```
Example:
```
DATA:100000,1000.50,2.500,1.650,2048,2100,2150,...
```

**Acknowledgments:**
```
ACK:START
ACK:STOP
ACK:RATE
ACK:TRIG_MODE
ACK:TRIG_LEVEL
ACK:TRIG_EDGE
ACK:PROBE
PONG
ESP32_OSC_READY
```

**Status format:**
```
STATUS:<running>,<sample_rate>,<trig_mode>,<trig_level>,<trig_edge>
```

## Troubleshooting

### GUI shows "NO SIGNAL":
- **This is normal when not connected!** 
- Connect ESP32 and click "Connect"
- If still showing after connecting:
  - Check COM port selection
  - Verify firmware is uploaded
  - Try clicking "Run" button
  - Check serial monitor for errors

### ESP32 not detected:
- Install CP210x or CH340 USB driver
- Check Device Manager (Windows) or `ls /dev/tty*` (Linux/Mac)
- Try different USB cable

### No waveform displayed:
- Check signal is connected to GPIO34
- Verify signal voltage is 0-3.3V
- Try "Auto" trigger mode
- Lower trigger level

### Noisy signal:
- Check grounding
- Use shorter wires
- Add 100nF capacitor between GPIO34 and GND
- Lower sample rate

### GUI won't start:
- Install missing dependencies: `pip install -r requirements.txt`
- Use Python 3.8+
- Try: `python -m pip install --upgrade pip`
- On Linux, may need: `sudo apt-get install python3-pyqt5`

### Slow/choppy display:
- Lower sample rate
- Reduce update frequency in code
- Close other applications
- Check CPU usage

## Comparison with Reference Project

This project differs from the ESP32-Oscilloscope reference in several ways:

### Similarities:
✅ Modular architecture with separate .ino files
✅ I2S-based high-speed ADC sampling  
✅ Digital filtering (low-pass and mean)
✅ Trigger system with edge detection
✅ Frequency and peak detection algorithms
✅ Similar data analysis functions

### Differences:
- **Display**: Python GUI on PC instead of TFT screen
- **Communication**: Serial protocol instead of local display
- **Controls**: GUI buttons instead of physical buttons
- **Storage**: Data processed on PC instead of ESP32 memory
- **Features**: Some features adapted for PC display (larger screen, more processing power)

## Architecture Comparison

**Reference Project (TFT):**
```
ESP32 → ADC → I2S DMA → Processing → TFT Display
        ↑                              ↑
    GPIO34                        Physical Buttons
```

**This Project (Serial):**
```
ESP32 → ADC → I2S DMA → Processing → Serial → PC
        ↑                                      ↓
    GPIO34                              Python GUI
                                             ↓
                                      Display + Controls
```

## Limitations

1. **Input Protection**: No built-in over-voltage protection. Use voltage divider for >3.3V signals.
2. **Bandwidth**: Limited to ~100 kHz by ESP32 ADC speed
3. **Single Channel**: Only one input channel
4. **AC Coupling**: No built-in AC coupling (use external capacitor if needed)
5. **Calibration**: ADC may have small offset errors

## Future Enhancements

- [ ] Dual channel support
- [ ] FFT spectrum analyzer
- [ ] Data logging to CSV
- [ ] Advanced trigger modes (pulse width, pattern)
- [ ] Cursor measurements
- [ ] Math channels (add, subtract, multiply)
- [ ] Waveform storage and recall

## Safety Warning

⚠️ **NEVER apply more than 3.3V directly to ESP32 GPIO pins!**
- Use voltage divider for higher voltages
- Do not connect to mains AC power
- Use proper isolation for measuring unknown signals

## License

Open source - feel free to modify and distribute.

## Credits

Based on ESP32 ADC and I2S capabilities.
GUI built with PyQt5 and Matplotlib.

## Support

For issues and questions, check:
- ESP32 documentation: https://docs.espressif.com/
- PySerial docs: https://pythonhosted.org/pyserial/
