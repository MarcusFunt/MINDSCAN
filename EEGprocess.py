import serial
import pygame
import sys
import struct
import threading
import time
import numpy as np
from scipy.signal import iirnotch, filtfilt

# Configuration Parameters
SERIAL_PORT = 'COM7'  # Replace with your serial port
BAUD_RATE = 115200
SAMPLE_RATE = 2000  # 2 kSPS as per Arduino code
BUFFER_SIZE = 800    # Number of samples to display (matches window width)
WINDOW_WIDTH = 1200  # Increased width to accommodate FFT display and indicators
WINDOW_HEIGHT = 600
BACKGROUND_COLOR = (0, 0, 0)
FILTERED_LINE_COLOR = (0, 255, 0)  # Green for filtered signal
FFT_COLOR = (255, 255, 255)        # White for FFT

# ADC Parameters
ADC_MAX = 4095       # 12-bit ADC
VOLTAGE_RANGE = 3.3  # Typical voltage range for Arduino ADC

# Scaling Parameters
VERTICAL_SCALE = 0.8  # Adjust this to change vertical scaling
MIDPOINT = WINDOW_HEIGHT // 2

# FFT Parameters
FFT_SIZE = BUFFER_SIZE
FREQ_DISPLAY_HEIGHT = WINDOW_HEIGHT // 2  # Height allocated for FFT display
MAX_FFT_FREQ = 70  # Maximum frequency to display in FFT

# Notch Filter Parameters
NOTCH_FREQ = 50.0  # Frequency to be removed from signal (Hz)
Q_FACTOR = 30.0     # Quality factor for the notch filter

# EEG Bands
EEG_BANDS = {
    'Delta': (0.5, 4),
    'Theta': (4, 8),
    'Alpha': (8, 13),
    'Beta': (13, 30),
    'Gamma': (30, 70)
}

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("EEG Oscilloscope with FFT and 50Hz Filter")
clock = pygame.time.Clock()

# Data Buffers
data_buffer = []
filtered_buffer = []

# Thread-safe flag to stop the reading thread
stop_thread = False

def read_serial_data(serial_conn):
    global data_buffer, stop_thread
    while not stop_thread:
        try:
            if serial_conn.in_waiting >= 2:
                data = serial_conn.read(2)
                if len(data) == 2:
                    analog_value = struct.unpack('<H', data)[0]
                    analog_value = max(0, min(analog_value, ADC_MAX))
                    data_buffer.append(analog_value)
                    if len(data_buffer) > BUFFER_SIZE:
                        data_buffer.pop(0)
        except serial.SerialException as e:
            print(f"Serial exception: {e}")
            stop_thread = True
        except Exception as e:
            print(f"Unexpected error: {e}")
            stop_thread = True

def map_value(value, in_min, in_max, out_min, out_max):
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def apply_notch_filter(data, fs, freq, Q):
    # Design notch filter
    b, a = iirnotch(freq, Q, fs)
    # Apply filter
    filtered_data = filtfilt(b, a, data)
    return filtered_data

def calculate_eeg_band_powers(freqs, fft_magnitude, bands):
    band_powers = {}
    for band, (low, high) in bands.items():
        # Find indices corresponding to the band
        idx = np.where((freqs >= low) & (freqs < high))[0]
        # Calculate the average power in the band
        power = np.mean(fft_magnitude[idx]) if len(idx) > 0 else 0
        band_powers[band] = power
    return band_powers

def draw_eeg_band_indicators(band_powers, font):
    x_start = BUFFER_SIZE + 20
    y_start = 20
    padding = 10
    bar_width = 20
    max_bar_height = 150  # Increased max height for better visibility

    # Normalize powers for visualization
    max_power = max(band_powers.values()) if band_powers else 1
    for i, (band, power) in enumerate(band_powers.items()):
        # Calculate bar height
        bar_height = int((power / max_power) * max_bar_height) if max_power != 0 else 0
        # Define bar position
        x = x_start + i * (bar_width + padding)
        y = y_start + (max_bar_height - bar_height)
        # Define bar color based on EEG band
        if band == 'Delta':
            color = (0, 0, 255)       # Blue
        elif band == 'Theta':
            color = (0, 255, 255)     # Cyan
        elif band == 'Alpha':
            color = (0, 255, 0)       # Green
        elif band == 'Beta':
            color = (255, 255, 0)     # Yellow
        elif band == 'Gamma':
            color = (255, 0, 0)       # Red
        else:
            color = (255, 255, 255)   # White for undefined bands
        # Draw the bar
        pygame.draw.rect(screen, color, (x, y, bar_width, bar_height))
        # Render the band label
        label = font.render(band, True, (255, 255, 255))
        screen.blit(label, (x - 5, y + bar_height + 5))
        # Render the power value
        power_label = font.render(f"{power:.2f}", True, (255, 255, 255))
        screen.blit(power_label, (x - 5, y + bar_height + 25))

def main():
    global stop_thread
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud.")
    except serial.SerialException as e:
        print(f"Could not open serial port {SERIAL_PORT}: {e}")
        sys.exit(1)

    thread = threading.Thread(target=read_serial_data, args=(ser,))
    thread.start()

    # Prepare notch filter
    fs = SAMPLE_RATE  # Sampling frequency
    freq = NOTCH_FREQ
    Q = Q_FACTOR

    # Initialize font for EEG indicators
    pygame.font.init()
    font = pygame.font.SysFont(None, 20)

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    stop_thread = True
                    thread.join()
                    ser.close()
                    pygame.quit()
                    sys.exit()

            screen.fill(BACKGROUND_COLOR)

            if len(data_buffer) == BUFFER_SIZE:
                # Convert ADC values to voltage
                voltage_data = np.array(data_buffer) / ADC_MAX * VOLTAGE_RANGE

                # Apply notch filter
                filtered_voltage = apply_notch_filter(voltage_data, fs, freq, Q)
                
                # Remove DC offset
                filtered_voltage -= np.mean(filtered_voltage)

                filtered_buffer = filtered_voltage.tolist()

                # Plot Filtered EEG Signal
                filtered_points = []
                for i, value in enumerate(filtered_buffer):
                    y = int(map_value(value, -VOLTAGE_RANGE / 2, VOLTAGE_RANGE / 2,
                                      MIDPOINT - (WINDOW_HEIGHT * VERTICAL_SCALE // 2),
                                      MIDPOINT + (WINDOW_HEIGHT * VERTICAL_SCALE // 2)))
                    y = max(0, min(WINDOW_HEIGHT - 1, y))  # Ensure y is within screen bounds
                    filtered_points.append((i, y))

                if len(filtered_points) >= 2:
                    pygame.draw.lines(screen, FILTERED_LINE_COLOR, False, filtered_points, 1)

                # Perform FFT
                fft_data = np.fft.rfft(filtered_voltage)
                fft_magnitude = np.abs(fft_data) / FFT_SIZE
                freqs = np.fft.rfftfreq(FFT_SIZE, d=1.0/fs)

                # Limit FFT to 0-70 Hz for display
                indices = np.where(freqs <= MAX_FFT_FREQ)
                freqs = freqs[indices]
                fft_magnitude = fft_magnitude[indices]

                # Normalize FFT magnitude for display
                if np.max(fft_magnitude) != 0:
                    fft_magnitude_display = fft_magnitude / np.max(fft_magnitude) * (FREQ_DISPLAY_HEIGHT - 20)  # Subtract padding
                else:
                    fft_magnitude_display = fft_magnitude

                # FFT Points
                fft_points = []
                for i, mag in enumerate(fft_magnitude_display):
                    x = BUFFER_SIZE + int((freqs[i] / MAX_FFT_FREQ) * (WINDOW_WIDTH - BUFFER_SIZE - 200))  # Leave space for indicators
                    y = WINDOW_HEIGHT - int(mag) - 10  # Offset for padding
                    fft_points.append((x, y))

                if len(fft_points) >= 2:
                    pygame.draw.lines(screen, FFT_COLOR, False, fft_points, 1)

                # Calculate EEG Band Powers
                band_powers = calculate_eeg_band_powers(freqs, fft_magnitude, EEG_BANDS)

                # Draw EEG Band Indicators
                draw_eeg_band_indicators(band_powers, font)

            # Draw FFT Boundary Line
            pygame.draw.line(screen, (100, 100, 100), (BUFFER_SIZE, 0), (BUFFER_SIZE, WINDOW_HEIGHT), 1)

            # Render Instructions
            instructions = font.render("Filtered EEG Signal", True, (255, 255, 255))
            screen.blit(instructions, (10, 10))

            pygame.display.flip()
            clock.tick(60)  # 60 FPS

    except KeyboardInterrupt:
        stop_thread = True
        thread.join()
        ser.close()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()
