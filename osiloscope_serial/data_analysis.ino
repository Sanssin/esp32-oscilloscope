// data_analysis.ino - Signal analysis and measurements

void peak_mean(uint16_t *buffer, uint32_t len, float *max_value, float *min_value, float *pt_mean) {
  /*
   * Calculate peak values and mean of signal
   */
  max_value[0] = buffer[0];
  min_value[0] = buffer[0];
  
  // Apply simple filter to reduce noise
  mean_filter filter(5);
  filter.init(buffer[0]);
  
  float mean = 0;
  for (uint32_t i = 0; i < len; i++) {
    float value = filter.filter((float)buffer[i]);
    
    if (value > max_value[0])
      max_value[0] = value;
    if (value < min_value[0])
      min_value[0] = value;
    
    mean += buffer[i];
  }
  
  mean /= (float)len;
  pt_mean[0] = mean;
}

void calculate_frequency(uint16_t *buffer, uint32_t len, float sample_rate, float mean, float *pt_freq, float *pt_period) {
  /*
   * Estimate frequency using zero-crossing method
   */
  float freq = 0;
  uint32_t crossing_count = 0;
  bool signal_side = (buffer[0] > mean);
  
  // Count rising edges
  for (uint32_t i = 1; i < len; i++) {
    bool current_side = (buffer[i] > mean);
    
    if (!signal_side && current_side) {
      // Rising edge detected
      crossing_count++;
    }
    
    signal_side = current_side;
  }
  
  if (crossing_count > 1) {
    // Calculate frequency from number of cycles
    float total_time = len / sample_rate; // in seconds
    freq = crossing_count / total_time;
    pt_freq[0] = freq;
    pt_period[0] = 1.0 / freq;
  } else {
    pt_freq[0] = 0;
    pt_period[0] = 0;
  }
}

bool check_trigger(uint16_t *buffer, uint32_t len, float trigger_value, bool rising) {
  /*
   * Check if trigger condition is met
   * Returns true if trigger found, false otherwise
   */
  if (trigger_mode == 0) return true; // Auto mode always triggers
  
  for (uint32_t i = 1; i < len; i++) {
    if (rising) {
      // Rising edge trigger
      if (buffer[i-1] < trigger_value && buffer[i] >= trigger_value) {
        return true;
      }
    } else {
      // Falling edge trigger
      if (buffer[i-1] > trigger_value && buffer[i] <= trigger_value) {
        return true;
      }
    }
  }
  
  return false;
}

bool detect_signal_present(uint16_t *buffer, uint32_t len) {
  /*
   * Detect if there's an actual signal or just noise/DC
   * Returns true if signal detected
   */
  float max_v, min_v, mean;
  peak_mean(buffer, len, &max_v, &min_v, &mean);
  
  float vpp = to_voltage(max_v) - to_voltage(min_v);
  
  // Signal present if Vpp > 50mV
  return (vpp > 0.05);
}
