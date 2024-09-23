#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// BLE Service and Characteristic UUIDs
#define SERVICE_UUID        "0bfcb646-c42e-41f6-ad75-986415e34974"
#define CHARACTERISTIC_UUID "9324057b-c436-4af4-a907-62b4fcd6fc05"

BLECharacteristic *pCharacteristic;
bool deviceConnected = false;
uint32_t analogValue = 0;

class MyServerCallbacks : public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      deviceConnected = true;
      Serial.println("Client connected");
    };

    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
      Serial.println("Client disconnected");
    }
};

void setup() {
  Serial.begin(115200);
  pinMode(A0, INPUT); // Set A0 as input for analog readings

  // Initialize BLE
  BLEDevice::init("ESP32C3_BLE_Analog");
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  // Create BLE Service
  BLEService *pService = pServer->createService(SERVICE_UUID);

  // Create BLE Characteristic
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_NOTIFY
                    );

  // Add Descriptor
  pCharacteristic->addDescriptor(new BLE2902());

  // Start the service
  pService->start();

  // Start advertising
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);  // functions that help with iPhone connections issue
  pAdvertising->setMinPreferred(0x12);
  BLEDevice::startAdvertising();
  Serial.println("Waiting for a client connection...");
}

void loop() {
  if (deviceConnected) {
    // Read analog value
    analogValue = analogRead(A0);

    // Convert the analog value to a string
    char valueStr[8];
    sprintf(valueStr, "%u", analogValue);

    // Set the value and notify the client
    pCharacteristic->setValue((uint8_t*)valueStr, strlen(valueStr));
    pCharacteristic->notify();

    Serial.print("Sent value: ");
    Serial.println(valueStr);

    // Wait for a short period before sending the next value
    delay(500); // Send data every 500ms
  }
}
