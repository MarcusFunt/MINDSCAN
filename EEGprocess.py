import asyncio
from bleak import BleakClient, BleakScanner

# UUIDs must match those in the Arduino code
SERVICE_UUID = "0bfcb646-c42e-41f6-ad75-986415e34974"
CHARACTERISTIC_UUID = "9324057b-c436-4af4-a907-62b4fcd6fc05"

# Replace with the name of your BLE device
DEVICE_NAME = "ESP32C3_BLE_Analog"

def notification_handler(sender, data):
    """Simple notification handler which prints the data received."""
    value = data.decode('utf-8')
    print(f"Received value: {value}")

async def run():
    # Scan for devices
    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover()

    esp32_address = None
    for d in devices:
        if d.name == DEVICE_NAME:
            esp32_address = d.address
            print(f"Found device {DEVICE_NAME} at address {esp32_address}")
            break

    if not esp32_address:
        print(f"Device {DEVICE_NAME} not found.")
        return

    async with BleakClient(esp32_address) as client:
        print(f"Connected to {DEVICE_NAME}")

        # Start receiving notifications
        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
        print("Subscribed to notifications...")

        # Keep the script running to receive data
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Disconnecting...")
        finally:
            await client.stop_notify(CHARACTERISTIC_UUID)

asyncio.run(run())
