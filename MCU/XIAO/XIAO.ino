/*
  EEG Signal Reader and Serial Transmitter
  ----------------------------------------
  This sketch reads a raw analog EEG signal from GPIO4, centered around VCC/2,
  and transmits the data over the serial port for further processing or visualization.

  Hardware Requirements:
  - Arduino-compatible board with an analog-capable GPIO4 pin (e.g., ESP32)
  - EEG device outputting a raw analog signal centered at VCC/2
  - Appropriate resistors/capacitors for signal conditioning (if necessary)

  Author: [Your Name]
  Date: [Current Date]
*/

const int eegPin = 4;          // GPIO4 (Analog-capable pin)
const unsigned long baudRate = 115200; // Serial communication speed

void setup() {
  // Initialize serial communication
  Serial.begin(baudRate);
  
  // Give some time for the serial connection to establish
  while (!Serial) {
    ; // Wait for serial port to connect. Needed for native USB
  }

  // Configure the EEG pin as input (optional, as analogRead sets it automatically)
  pinMode(eegPin, INPUT);
  
  // Optional: If using a board with configurable ADC settings, initialize them here
  // For example, on ESP32 you might set ADC attenuation or resolution
}

void loop() {
  // Read the analog EEG signal
  int eegValue = analogRead(eegPin); // Typically returns a value between 0 and 4095 for 12-bit ADCs (e.g., ESP32)
  
  // Optional: Convert the raw ADC value to voltage
  // float voltage = eegValue * (VCC / ADC_MAX_VALUE);
  // For example, on a 3.3V system with a 12-bit ADC:
  // float voltage = eegValue * (3.3 / 4095.0);
  
  // Transmit the raw EEG value over serial
  Serial.println(eegValue);
  
  // Control the sampling rate
  // EEG typically requires high sampling rates (e.g., 250 Hz or higher)
  // Adjust the delay accordingly. For 250 Hz, delay ~4 ms
  delay(1); // 4 milliseconds delay for ~250 samples per second
}
