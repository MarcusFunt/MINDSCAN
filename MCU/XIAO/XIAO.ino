// This code reads EEG data from GPIO3 and sends it to the PC via serial communication.

void setup() {
  Serial.begin(115200);  // Initialize serial communication at 115200 baud
  delay(1000);           // Wait for Serial to initialize
}

void loop() {
  int analogValue = analogRead(3);  // Read analog value from GPIO3
  Serial.println(analogValue);      // Send the analog value over serial
  delayMicroseconds(10);                         // Small delay to control data rate (adjust as needed)
}
