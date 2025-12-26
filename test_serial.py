"""
Simple test script to verify ESP32 serial communication
Run this before starting the full GUI
"""

import serial
import serial.tools.list_ports
import time

def list_ports():
    print("\n=== Available Serial Ports ===")
    ports = serial.tools.list_ports.comports()
    for i, port in enumerate(ports):
        print(f"{i+1}. {port.device} - {port.description}")
    return ports

def test_connection(port, baudrate=921600):
    print(f"\n=== Testing connection to {port} ===")
    
    try:
        ser = serial.Serial(port, baudrate, timeout=2)
        print("✓ Port opened successfully")
        time.sleep(2)  # Wait for ESP32 boot
        
        # Send PING command
        print("Sending PING...")
        ser.write(b"PING\n")
        time.sleep(0.5)
        
        # Read response
        if ser.in_waiting:
            response = ser.readline().decode('utf-8').strip()
            print(f"Response: {response}")
            
            if response == "PONG":
                print("✓ ESP32 responding correctly!")
            else:
                print("⚠ Unexpected response")
        else:
            print("✗ No response from ESP32")
            print("  Check if firmware is uploaded correctly")
            
        # Test data acquisition
        print("\nTesting data acquisition...")
        ser.write(b"GET_DATA\n")
        time.sleep(1)
        
        data_received = False
        for _ in range(50):  # Try reading for 5 seconds
            if ser.in_waiting:
                line = ser.readline().decode('utf-8').strip()
                if line.startswith("DATA:"):
                    print("✓ Data received!")
                    parts = line[5:].split(',')
                    sample_rate = parts[0]
                    data_count = len(parts) - 1
                    print(f"  Sample rate: {sample_rate} Hz")
                    print(f"  Data points: {data_count}")
                    if data_count > 0:
                        print(f"  First 5 values: {parts[1:6]}")
                    data_received = True
                    break
            time.sleep(0.1)
            
        if not data_received:
            print("✗ No data received")
            print("  ESP32 may not be sampling correctly")
            
        ser.close()
        print("\n=== Test complete ===")
        
    except serial.SerialException as e:
        print(f"✗ Serial error: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")

def main():
    print("ESP32 Oscilloscope - Connection Test")
    print("=" * 40)
    
    ports = list_ports()
    
    if not ports:
        print("\n✗ No serial ports found!")
        print("  Make sure ESP32 is connected")
        return
        
    print("\nEnter port number to test (or 'q' to quit): ", end='')
    choice = input().strip()
    
    if choice.lower() == 'q':
        return
        
    try:
        port_index = int(choice) - 1
        if 0 <= port_index < len(ports):
            test_connection(ports[port_index].device)
        else:
            print("Invalid port number")
    except ValueError:
        print("Invalid input")

if __name__ == "__main__":
    main()
