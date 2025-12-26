/*
 * ESP32 Oscilloscope - Serial Communication Version
 * For ESP32U DevKit V4
 * ADC Input: GPIO34 (ADC1_CHANNEL_6)
 * Communication: USB Serial (921600 baud)
 */

#include <Arduino.h>
#include <driver/adc.h>
#include <driver/i2s.h>
#include <soc/syscon_reg.h>
#include "esp_adc_cal.h"
#include "filters.h"

// Configuration
#define ADC_CHANNEL       ADC1_CHANNEL_6  // GPIO34
#define ADC_WIDTH         ADC_WIDTH_BIT_12
#define ADC_ATTEN         ADC_ATTEN_DB_11
#define BUFFER_SIZE       2000
#define I2S_NUM           I2S_NUM_0
#define SERIAL_BAUD       921600

// Global Variables
uint16_t adc_buffer[BUFFER_SIZE];
esp_adc_cal_characteristics_t adc_chars;
bool is_running = true;
uint32_t sample_rate = 100000; // 100kHz default
uint8_t trigger_mode = 0; // 0=Auto, 1=Normal, 2=Single
float trigger_level = 1.65; // Volts
bool trigger_edge = true; // true=rising, false=falling
bool new_data_ready = false;
uint8_t probe_attenuation = 1; // 1x, 10x, 100x

// Forward declarations - implemented in separate files
void configure_i2s(uint32_t sampling_rate);
void ADC_Sampling(uint16_t *buffer);
void characterize_adc();
float to_voltage(uint16_t adc_value);
void peak_mean(uint16_t *buffer, uint32_t len, float *max_v, float *min_v, float *mean);
void calculate_frequency(uint16_t *buffer, uint32_t len, float sample_rate, float mean, float *freq, float *period);
bool check_trigger(uint16_t *buffer, uint32_t len, float trigger_v, bool rising);

void setup() {
  Serial.begin(SERIAL_BAUD);
  while(!Serial && millis() < 3000); // Wait for serial or timeout
  
  // Characterize ADC
  characterize_adc();
  
  // Configure I2S for high-speed sampling
  configure_i2s(sample_rate);
  
  delay(100);
  Serial.println("ESP32_OSC_READY");
  Serial.flush();
}

// Send data to PC with measurements
void send_data() {
  float max_v, min_v, mean, freq, period;
  
  // Calculate measurements
  peak_mean(adc_buffer, BUFFER_SIZE, &max_v, &min_v, &mean);
  calculate_frequency(adc_buffer, BUFFER_SIZE, sample_rate, mean, &freq, &period);
  
  // Send in format: DATA:sample_rate,freq,vpp,mean,data1,data2,...
  Serial.print("DATA:");
  Serial.print(sample_rate);
  Serial.print(",");
  Serial.print(freq, 2);
  Serial.print(",");
  Serial.print((to_voltage(max_v) - to_voltage(min_v)) * probe_attenuation, 3);
  Serial.print(",");
  Serial.print(to_voltage(mean) * probe_attenuation, 3);
  Serial.print(",");
  
  for (int i = 0; i < BUFFER_SIZE; i++) {
    Serial.print(adc_buffer[i]);
    if (i < BUFFER_SIZE - 1) Serial.print(",");
  }
  Serial.println();
  Serial.flush();
}

// Process commands from PC
void process_command(String cmd) {
  cmd.trim();
  
  if (cmd == "START") {
    is_running = true;
    Serial.println("ACK:START");
  }
  else if (cmd == "STOP") {
    is_running = false;
    Serial.println("ACK:STOP");
  }
  else if (cmd.startsWith("RATE:")) {
    sample_rate = cmd.substring(5).toInt();
    i2s_adc_disable(I2S_NUM);
    i2s_driver_uninstall(I2S_NUM);
    configure_i2s(sample_rate);
    Serial.println("ACK:RATE");
  }
  else if (cmd.startsWith("TRIG_MODE:")) {
    trigger_mode = cmd.substring(10).toInt();
    Serial.println("ACK:TRIG_MODE");
  }
  else if (cmd.startsWith("TRIG_LEVEL:")) {
    trigger_level = cmd.substring(11).toFloat();
    Serial.println("ACK:TRIG_LEVEL");
  }
  else if (cmd.startsWith("TRIG_EDGE:")) {
    trigger_edge = (cmd.substring(10).toInt() == 1);
    Serial.println("ACK:TRIG_EDGE");
  }
  else if (cmd == "GET_DATA") {
    send_data();
  }
  else if (cmd == "PING") {
    Serial.println("PONG");
  }
  else if (cmd.startsWith("PROBE:")) {
    probe_attenuation = cmd.substring(6).toInt();
    if (probe_attenuation != 1 && probe_attenuation != 10 && probe_attenuation != 100) {
      probe_attenuation = 1;
    }
    Serial.println("ACK:PROBE");
  }
  else if (cmd == "STATUS") {
    Serial.print("STATUS:");
    Serial.print(is_running ? "1" : "0");
    Serial.print(",");
    Serial.print(sample_rate);
    Serial.print(",");
    Serial.print(trigger_mode);
    Serial.print(",");
    Serial.print(trigger_level, 2);
    Serial.print(",");
    Serial.println(trigger_edge ? "1" : "0");
  }
}

void loop() {
  // Check for serial commands
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    process_command(cmd);
  }
  
  // Acquire data if running
  if (is_running) {
    ADC_Sampling(adc_buffer);
    
    // Check trigger condition
    float trigger_v = trigger_level / 3.3 * 4095.0;
    bool triggered = check_trigger(adc_buffer, BUFFER_SIZE, trigger_v, trigger_edge);
    
    if (trigger_mode == 0 || triggered) {
      send_data();
      
      // If single trigger mode, stop after one acquisition
      if (trigger_mode == 2) {
        is_running = false;
      }
    }
    
    delay(50); // Adjust for desired refresh rate
  } else {
    delay(100);
  }
}
