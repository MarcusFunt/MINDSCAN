#include <Arduino.h>

const double samplingFrequency = 5000.0;  // Set desired sample rate in Hz
unsigned long samplingInterval;           // Time interval between samples in microseconds
unsigned long nextSampleTime;

void setup() {
  Serial.begin(1000000);                  // Set baud rate for serial communication
  samplingInterval = 1000000 / samplingFrequency;  // Calculate sampling interval in microseconds
  nextSampleTime = micros();              // Initialize the next sample time
}

void loop() {
  unsigned long currentTime = micros();
  
  // Take sample only when appropriate time has passed
  if (currentTime >= nextSampleTime) {
    // Read analog value (0-1023 for 10-bit ADC)
    uint16_t value = analogRead(4);

    // Send as two bytes (little endian)
    Serial.write(value & 0xFF);        // Low byte
    Serial.write((value >> 8) & 0xFF); // High byte

    // Schedule next sample
    nextSampleTime += samplingInterval;

    // Handle timing drift
    if (currentTime > nextSampleTime) {
      nextSampleTime = currentTime + samplingInterval;
    }
  }
}
