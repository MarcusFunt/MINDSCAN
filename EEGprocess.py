import numpy as np
import pygame
from scipy.signal import butter, filtfilt
from scipy.fft import fft
import serial

# Configuration parameters
SERIAL_PORT = 'COM12'  # Update with your serial port
BAUD_RATE = 115200     # Match the baud rate set in your microcontroller code
SAMPLE_RATE = 1000     # EEG sample rate in Hz
BUFFER_SIZE = 1000     # Number of samples to display

# Filter design: Bandpass filter between 0.5 Hz and 30 Hz
LOW_CUTOFF = 0.5
HIGH_CUTOFF = 30.0
FILTER_ORDER = 5

# Initialize serial connection
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"Connected to: {SERIAL_PORT}")
except Exception as e:
    print(f"Failed to connect to serial port: {e}")
    exit()

# Initialize Pygame
pygame.init()
WINDOW_WIDTH, WINDOW_HEIGHT = 1200, 600
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("EEG Signal Visualization with FFT")
clock = pygame.time.Clock()

# Bandpass filter setup
def butter_bandpass(lowcut, highcut, fs, order=5):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return b, a

def bandpass_filter(data, lowcut, highcut, fs, order=5):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    return filtfilt(b, a, data)

# Initialize EEG data buffer
eeg_data = []

# Main loop
try:
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Read data from the serial port
        line = ser.readline().decode('utf-8').strip()
        if line:
            try:
                eeg_value = int(line)
                eeg_data.append(eeg_value)

                # Keep the buffer size constant
                if len(eeg_data) > BUFFER_SIZE:
                    eeg_data.pop(0)

                # Only filter and analyze when enough data is collected
                if len(eeg_data) == BUFFER_SIZE:
                    # Apply bandpass filter
                    filtered_data = bandpass_filter(np.array(eeg_data), LOW_CUTOFF, HIGH_CUTOFF, SAMPLE_RATE, FILTER_ORDER)

                    # Perform FFT on the filtered data
                    fft_data = np.abs(fft(filtered_data))[:BUFFER_SIZE // 2]
                    fft_freqs = np.fft.fftfreq(BUFFER_SIZE, 1.0 / SAMPLE_RATE)[:BUFFER_SIZE // 2]

                    # Clear screen
                    screen.fill((0, 0, 0))

                    # Draw EEG signal
                    for i in range(1, len(filtered_data)):
                        pygame.draw.line(screen, (0, 255, 0),
                                         (i - 1, WINDOW_HEIGHT // 2 - filtered_data[i - 1] / 10),
                                         (i, WINDOW_HEIGHT // 2 - filtered_data[i] / 10), 1)

                    # Draw FFT spectrum
                    fft_scale = 2000  # Scale FFT for visualization purposes
                    for i in range(len(fft_data)):
                        pygame.draw.line(screen, (255, 0, 0),
                                         (i * (WINDOW_WIDTH // len(fft_data)), WINDOW_HEIGHT),
                                         (i * (WINDOW_WIDTH // len(fft_data)), WINDOW_HEIGHT - fft_data[i] / fft_scale))

                    # Update display
                    pygame.display.flip()

            except ValueError:
                print(f"Invalid data received: {line}")

        # Control the frame rate
        clock.tick(SAMPLE_RATE / BUFFER_SIZE)

except KeyboardInterrupt:
    print("Terminating program...")

finally:
    ser.close()
    pygame.quit()
