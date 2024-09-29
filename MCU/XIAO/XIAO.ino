// Constants
const int analogPin = D2; // GPIO4 on the XIAO board
const unsigned long samplingInterval = 500; // in microseconds (500 µs for 2 kSPS)

// Variables
unsigned long previousMicros = 0;

void setup() {
  // Initialize serial communication at 115200 baud
  Serial.begin(115200);
  
  // Initialize the analog pin
  pinMode(analogPin, INPUT);
  
  // Optional: Wait for serial port to connect (useful for some boards)
  while (!Serial) {
    ; // Wait for serial port to connect
  }
}

void loop() {
  unsigned long currentMicros = micros();
  
  // Check if it's time to sample
  if (currentMicros - previousMicros >= samplingInterval) {
    previousMicros += samplingInterval;
    
    // Read the analog value
    int analogValue = analogRead(analogPin);
    
    // Send the analog value as two bytes (Little Endian)
    Serial.write(analogValue & 0xFF);         // Lower byte
    Serial.write((analogValue >> 8) & 0xFF);  // Higher byte
  }
}
