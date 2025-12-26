// i2s.ino - I2S configuration and ADC sampling

void configure_i2s(uint32_t sampling_rate) {
  /*
   * Configure I2S for ADC sampling
   * Using DMA for high-speed data acquisition
   */
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX | I2S_MODE_ADC_BUILT_IN),
    .sample_rate = sampling_rate,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = (i2s_comm_format_t)(I2S_COMM_FORMAT_I2S | I2S_COMM_FORMAT_I2S_MSB),
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 4,
    .dma_buf_len = 512,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };
  
  // Configure ADC channel and width
  adc1_config_channel_atten((adc1_channel_t)ADC_CHANNEL, ADC_ATTEN);
  adc1_config_width(ADC_WIDTH);
  
  // Install and configure I2S driver
  i2s_driver_install(I2S_NUM, &i2s_config, 0, NULL);
  i2s_set_adc_mode(ADC_UNIT_1, ADC_CHANNEL);
  
  // Invert ADC data for correct polarity
  SET_PERI_REG_MASK(SYSCON_SARADC_CTRL2_REG, SYSCON_SARADC_SAR1_INV);
  
  i2s_adc_enable(I2S_NUM);
}

void ADC_Sampling(uint16_t *buffer) {
  /*
   * Read ADC samples using I2S DMA
   * This is much faster than analogRead()
   */
  size_t bytes_read = 0;
  uint16_t temp_buffer[BUFFER_SIZE];
  
  // Read from I2S DMA buffer
  i2s_read(I2S_NUM, (void*)temp_buffer, BUFFER_SIZE * sizeof(uint16_t), &bytes_read, portMAX_DELAY);
  
  // Process and mask to 12-bit
  for (int i = 0; i < BUFFER_SIZE; i++) {
    buffer[i] = temp_buffer[i] & 0x0FFF;
  }
}

void set_sample_rate(uint32_t rate) {
  /*
   * Change sample rate by reconfiguring I2S
   */
  i2s_adc_disable(I2S_NUM);
  i2s_driver_uninstall(I2S_NUM);
  configure_i2s(rate);
}
