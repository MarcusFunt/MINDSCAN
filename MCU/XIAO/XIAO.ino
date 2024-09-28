/*
  Arduino Code: Enhanced EEG Signal Reader and Serial Transmitter

  Description:
  - Reads analog EEG signal from GPIO4 (A4 on Arduino Uno).
  - Assumes EEG signal is centered around Vcc/2 (e.g., ~2.5V for 5V systems).
  - Transmits raw analog values over serial with a timestamp.

  Data Format:
  <timestamp_ms>,<analog_value>
  Example: 12345,512

  Hardware Connections:
  - Connect EEG signal to A4.
  - Ensure proper grounding and biasing as per your EEG hardware specifications.
*/

const int eegPin = 4;                     // Analog input pin for EEG signal
const unsigned long sampleInterval = 1;    // Sampling interval in milliseconds (~1000 Hz)

void setup() {
  Serial.begin(115200);                    // Initialize serial communication at 115200 baud for higher data rate
  pinMode(eegPin, INPUT);                  // Set EEG pin as input
}

void loop() {
  unsigned long timestamp = millis();       // Get current timestamp in milliseconds
  int analogValue = analogRead(eegPin);    // Read the analog value (0-1023)

  // Transmit data in the format: <timestamp>,<value>
  Serial.print(timestamp);
  Serial.print(",");
  Serial.println(analogValue);

  delay(sampleInterval);                    // Wait for the next sample
}
