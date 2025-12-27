# ESP32 Oscilloscope Project (0-10V Input)

## Overview
DIY Oscilloscope using ESP32U DevKit V4 with Python GUI interface on PC. This project is inspired by the ESP32-Oscilloscope project but modified for serial communication instead of TFT display.

**✨ Updated for 0-10V Input Range** - Uses voltage divider circuit to measure signals from 0-10V.

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
- Signal source to measure (0-10V)
- **Resistors for voltage divider:**
  - R1: 20kΩ (1/4W, tolerance 1% or 5%)
  - R2: 10kΩ (1/4W, tolerance 1% or 5%)
- **Optional:** 100nF ceramic capacitor (code: 104)

## Voltage Divider Circuit (REQUIRED for 0-10V)

**WARNING: ESP32 GPIO pins accept MAX 3.3V! Direct 10V connection will damage the chip!**

### Circuit Diagram:
```
Input Signal (0-10V)
       |
       +--[R1: 20kΩ]--+--- GPIO34 (ESP32)
       |               |
       |            [R2: 10kΩ]
       |               |
      GND ----------- GND (ESP32)
```

### With Optional Filter Capacitor:
```
Input Signal (0-10V)
       |
       +--[R1: 20kΩ]--+--- GPIO34 (ESP32)
                       |
                    [R2: 10kΩ] || [C: 100nF]
                       |
                      GND
```

### Voltage Divider Calculation:
- **Ratio**: R2 / (R1 + R2) = 10k / 30k = 1/3
- **Input 0V** → GPIO34 = 0V
- **Input 10V** → GPIO34 = 3.33V ✓ (Safe!)
- **Scaling Factor**: 3.03x (10V / 3.3V)

### Component Notes:
- Use **1/4 Watt** resistors minimum
- **1% tolerance** preferred for accuracy, 5% is acceptable
- **100nF capacitor** reduces noise (optional but recommended)
- Do NOT use 100µF capacitor (too large, will slow response)

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
- **Level**: Adjustable voltage threshold (0-10V)

### Timebase:
- Sample rates: 10 kHz to 1 MHz
- Adjustable time scale: 0.1 - 50 ms

### Vertical Scale:
- Manual voltage/div: 0.05V to 10V per division
- Full range: 0-10V input

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

1. **Build Voltage Divider Circuit**:
   - Solder R1 (20kΩ) and R2 (10kΩ) according to circuit diagram
   - Optional: Add 100nF capacitor parallel to R2
   - Test with multimeter: 10V input should give ~3.3V at midpoint

2. **Connect Hardware**:
   - Connect voltage divider output to GPIO34 (ESP32 Pin 34)
   - Connect both grounds together (signal ground and ESP32 ground)
   - Connect ESP32 to PC via USB

3. **Start GUI**:
   - Run `oscilloscope_gui.py`
   - GUI will display "NO SIGNAL" (normal before connection)
   - Select COM port from dropdown
   - Click "Connect"

4. **Acquire Signal**:
   - Connect your 0-10V signal source
   - Click "Run" for continuous acquisition
   - Click "Single" for one-shot capture
   - Adjust Volts/Div knob for proper vertical scale
   - Adjust Time/Div knob for proper horizontal scale

5. **Configure Trigger**:
   - Set trigger mode (Auto recommended for first test)
   - Adjust trigger level (0-10V range)
   - Choose edge direction (Rising ↗ or Falling ↘)

6. **Adjust Display**:
   - Use VOLTS/DIV knob to change vertical scale
   - Use TIME/DIV knob to change time scale  
   - Use Position sliders to move waveform
   - View measurements at bottom panel

## Specifications

- **Input Range**: 0 - 10V DC (via voltage divider)
- **Input at GPIO34**: 0 - 3.3V (after divider)
- **Input Impedance**: ~30kΩ (R1 + R2)
- **Resolution**: 12-bit (4096 levels) = ~2.4 mV per step
- **Voltage Accuracy**: ±5% (with 5% resistors), ±1% (with 1% resistors)
- **Max Sample Rate**: 1 MSPS
- **Buffer Size**: 2000 samples
- **Bandwidth**: ~100 kHz (limited by ADC and processing)
- **Voltage Scale Range**: 0.05V/div to 10V/div
- **Time Scale Range**: 0.1ms/div to 50ms/div

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

### Voltage readings incorrect:
- **Check resistor values** with multimeter
- Verify R1 = 20kΩ, R2 = 10kΩ
- Test divider: 10V input should give 3.3V at GPIO34
- Use 1% tolerance resistors for better accuracy

### GUI shows "NO SIGNAL":
- **This is normal when not connected!** 
- Connect ESP32 and click "Connect"
- If still showing after connecting:
  - Check COM port selection
  - Verify firmware is uploaded
  - Try clicking "Run" button
  - Check serial monitor for errors

### Reading shows 0V or wrong scale:
- Verify voltage divider is connected correctly
- Check software voltage_scale = 3.03 in code
- Ensure signal ground connected to ESP32 ground
- Test with known voltage source (battery)

### ESP32 not detected:
- Install CP210x or CH340 USB driver
- Check Device Manager (Windows) or `ls /dev/tty*` (Linux/Mac)
- Try different USB cable

### No waveform displayed:
- Check voltage divider output is 0-3.3V (NOT 0-10V direct!)
- Verify signal is connected through voltage divider
- Try "Auto" trigger mode
- Adjust trigger level to signal range

### Noisy signal:
- Add 100nF capacitor parallel to R2 (if not installed)
- Check grounding - use twisted pair or shielded cable
- Keep voltage divider wires short
- Lower sample rate
- Avoid running near power supplies or motors

### ESP32 damaged / not working:
- **Did you connect 10V directly without voltage divider?**
- Check if GPIO34 still responds with multimeter
- Test with 1.5V battery through divider first
- May need to replace ESP32 if GPIO damaged

### GUI won't start:
- Install missing dependencies: `pip install -r requirements.txt`
- Use Python 3.8+
- Try: `python -m pip install --upgrade pip`
- On Linux, may need: `sudo apt-get install python3-pyqt5`

### Slow/choppy display:
- Lower sample rate
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

1. **Voltage Range**: Limited to 0-10V DC with voltage divider
2. **Input Protection**: Basic voltage divider only - no reverse polarity or overvoltage protection
3. **Bandwidth**: Limited to ~100 kHz by ESP32 ADC speed
4. **Single Channel**: Only one input channel
5. **AC Coupling**: No built-in AC coupling (use external capacitor if needed)
6. **Accuracy**: Depends on resistor tolerance (±1% to ±5%)
7. **Isolation**: No galvanic isolation from signal source

## Safety Warnings

⚠️ **CRITICAL SAFETY RULES:**

1. **NEVER apply more than 3.3V directly to GPIO34!**
   - Always use voltage divider circuit
   - Test divider with multimeter first
   - 10V input must become 3.3V at GPIO34

2. **NEVER connect to mains AC power (110V/220V)**
   - This circuit is for DC or low-voltage AC only
   - Mains voltage will destroy ESP32 and possibly start fire
   - Use proper isolated oscilloscope for mains measurements

3. **Check polarity and voltage before connecting**
   - Measure unknown signals with multimeter first
   - Ensure signal is within 0-10V range
   - Negative voltages or >10V will damage ESP32

4. **Use proper grounding**
   - Connect signal ground to ESP32 ground
   - Do not create ground loops
   - Isolated power supplies may cause measurement errors

5. **For unknown/dangerous signals:**
   - Use isolated probe or optocoupler
   - Add fuse or current limiting
   - Consider using commercial oscilloscope instead

## License

Open source - feel free to modify and distribute.

## Credits

Based on ESP32 ADC and I2S capabilities.
GUI built with PyQt5 and Matplotlib.

## Support

For issues and questions, check:
- ESP32 documentation: https://docs.espressif.com/
- PySerial docs: https://pythonhosted.org/pyserial/
