// adc.ino - ADC characterization and conversion functions

void characterize_adc() {
  /*
   * Characterize ADC for accurate voltage conversion
   * Uses eFuse Vref value if available
   */
  esp_adc_cal_characterize(
    ADC_UNIT_1,
    ADC_ATTEN,
    ADC_WIDTH,
    1100,  // Default Vref
    &adc_chars
  );
}

float to_voltage(uint16_t adc_value) {
  /*
   * Convert ADC value (0-4095) to voltage (0-3.3V)
   * Takes into account ADC calibration
   */
  uint32_t voltage_mv = esp_adc_cal_raw_to_voltage(adc_value, &adc_chars);
  return voltage_mv / 1000.0;
}

uint16_t from_voltage(float voltage) {
  /*
   * Convert voltage to ADC value
   */
  return (uint16_t)(voltage / 3.3 * 4095.0);
}
