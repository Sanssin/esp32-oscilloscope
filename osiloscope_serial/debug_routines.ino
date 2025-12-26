// debug_routines.ino - Debugging and diagnostic functions

void debug_buffer() {
  /*
   * Debug function to test ADC sampling
   * Prints buffer contents to serial
   */
  Serial.println("\n=== Debug: ADC Buffer Test ===");
  
  ADC_Sampling(adc_buffer);
  
  Serial.print("Buffer size: ");
  Serial.println(BUFFER_SIZE);
  
  Serial.println("First 20 samples:");
  for (int i = 0; i < 20 && i < BUFFER_SIZE; i++) {
    Serial.print(i);
    Serial.print(": ");
    Serial.print(adc_buffer[i]);
    Serial.print(" (");
    Serial.print(to_voltage(adc_buffer[i]), 3);
    Serial.println("V)");
  }
  
  float max_v, min_v, mean;
  peak_mean(adc_buffer, BUFFER_SIZE, &max_v, &min_v, &mean);
  
  Serial.print("\nMax: ");
  Serial.print(to_voltage(max_v), 3);
  Serial.println("V");
  
  Serial.print("Min: ");
  Serial.print(to_voltage(min_v), 3);
  Serial.println("V");
  
  Serial.print("Mean: ");
  Serial.print(to_voltage(mean), 3);
  Serial.println("V");
  
  Serial.print("Vpp: ");
  Serial.print(to_voltage(max_v) - to_voltage(min_v), 3);
  Serial.println("V");
  
  Serial.println("=== End Debug ===\n");
}

void print_status() {
  /*
   * Print current configuration status
   */
  Serial.println("\n=== ESP32 Oscilloscope Status ===");
  Serial.print("Sample Rate: ");
  Serial.print(sample_rate / 1000.0, 1);
  Serial.println(" kHz");
  
  Serial.print("Trigger Mode: ");
  switch(trigger_mode) {
    case 0: Serial.println("Auto"); break;
    case 1: Serial.println("Normal"); break;
    case 2: Serial.println("Single"); break;
    default: Serial.println("Unknown");
  }
  
  Serial.print("Trigger Level: ");
  Serial.print(trigger_level, 2);
  Serial.println("V");
  
  Serial.print("Trigger Edge: ");
  Serial.println(trigger_edge ? "Rising" : "Falling");
  
  Serial.print("Running: ");
  Serial.println(is_running ? "Yes" : "No");
  
  Serial.print("Probe: ");
  Serial.print(probe_attenuation);
  Serial.println("x");
  
  Serial.println("=================================\n");
}

void self_test() {
  /*
   * Perform self-test diagnostics
   */
  Serial.println("\n=== Self Test ===");
  
  // Test 1: ADC Reading
  Serial.print("Test 1: ADC Reading... ");
  ADC_Sampling(adc_buffer);
  if (adc_buffer[0] >= 0 && adc_buffer[0] <= 4095) {
    Serial.println("PASS");
  } else {
    Serial.println("FAIL");
  }
  
  // Test 2: Voltage Conversion
  Serial.print("Test 2: Voltage Conversion... ");
  float v1 = to_voltage(0);
  float v2 = to_voltage(4095);
  if (v1 >= 0 && v1 < 0.2 && v2 > 3.0 && v2 <= 3.5) {
    Serial.println("PASS");
  } else {
    Serial.print("FAIL (");
    Serial.print(v1, 2);
    Serial.print("V - ");
    Serial.print(v2, 2);
    Serial.println("V)");
  }
  
  // Test 3: Signal Detection
  Serial.print("Test 3: Signal Detection... ");
  bool signal = detect_signal_present(adc_buffer, BUFFER_SIZE);
  Serial.println(signal ? "Signal Detected" : "No Signal");
  
  Serial.println("=== End Self Test ===\n");
}
