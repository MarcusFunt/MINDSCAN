#include <Arduino.h>

const double samplingFrequency = 5000.0;           // Set desired sample rate in Hz
unsigned long samplingInterval;                    // Time interval between samples in microseconds

void setup() {
  Serial.begin(115200);                            // Set baud rate for serial communication
  samplingInterval = 1000000 / samplingFrequency;  // Calculate sampling interval in microseconds
}

void loop() {
  unsigned long startTime = micros();              // Start time tracking
  
  // Continuously read and send data
  while (true) {
    double value = analogRead(4);                  // Read from analog pin 4
    Serial.println(value);                         // Send the data with a newline
    
    // Maintain the correct sampling interval
    while (micros() - startTime < samplingInterval) {
      // Wait to maintain the correct sample rate
    }
    startTime += samplingInterval;                 // Update start time to keep consistent intervals
  }
}
