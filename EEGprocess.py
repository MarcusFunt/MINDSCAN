import serial
import numpy as np
import pygame
import threading
import time
from collections import deque
import sys
from scipy.signal import welch
from scipy.interpolate import interp1d

# Configuration Parameters
PORT = 'COM7'               # Serial port to read from
BAUD_RATE = 115200          # Baud rate, matching the Arduino code
SAMPLING_RATE = 1000        # Sampling rate in Hz (adjust if different)
BUFFER_SIZE = 4096          # Number of samples to keep in buffer
PROCESSING_INTERVAL = 0.1   # Interval to process and update plot (seconds) => 10 Hz

# Filter Parameters
LOWCUT = 1.0                # Low cutoff frequency (Hz) for bandpass filter
HIGHCUT = 50.0              # High cutoff frequency (Hz) for bandpass filter
NOTCH_FREQ = 50.0           # Frequency to notch filter (e.g., 50 Hz for Europe, 60 Hz for USA)
NOTCH_Q = 30.0              # Quality factor for notch filter
FILTER_ORDER = 5            # Order of the Butterworth filter

# Artifact Detection Parameters
ARTIFACT_THRESHOLD = 3000   # Amplitude threshold for artifact detection (adjust based on data)

# Visualization Parameters
WINDOW_WIDTH = 1200         # Window width in pixels
WINDOW_HEIGHT = 800         # Window height in pixels
FPS = 60                    # Pygame frames per second

# Initialize a thread-safe deque for buffering incoming data
data_buffer = deque(maxlen=BUFFER_SIZE)

# Flag to control the reading thread
keep_reading = True

def read_serial_data(ser):
    """
    Continuously read data from the serial port and append to the buffer.
    """
    global keep_reading
    while keep_reading:
        try:
            line = ser.readline().decode('utf-8').strip()
            if line:
                value = int(line)
                data_buffer.append(value)
        except ValueError:
            continue  # Ignore lines that can't be converted to integer
        except serial.SerialException:
            print("Serial connection lost.")
            keep_reading = False
            break

def initialize_pygame():
    """
    Initialize pygame and set up the window.
    """
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Live FFT of Filtered EEG Data")
    return screen

def detect_artifacts(data, threshold):
    """
    Detect artifacts in the data based on amplitude threshold.
    Returns a boolean array where True indicates artifact.
    """
    return np.abs(data) > threshold

def interpolate_artifacts(data, artifact_indices):
    """
    Interpolate over artifact indices to mitigate artifacts.
    """
    clean_data = data.copy()
    if np.any(artifact_indices):
        x = np.arange(len(data))
        valid = ~artifact_indices
        if np.sum(valid) < 2:
            # Not enough points to interpolate
            clean_data[artifact_indices] = 0
            return clean_data
        f = interp1d(x[valid], data[valid], kind='linear', fill_value="extrapolate")
        clean_data[artifact_indices] = f(x[artifact_indices])
    return clean_data

def draw_fft(screen, freqs, psd_values):
    """
    Draw the FFT (PSD) results on the pygame screen.
    """
    screen.fill((0, 0, 0))  # Clear screen with black

    # Define plot area margins
    left_margin = 100
    right_margin = 50
    top_margin = 50
    bottom_margin = 100

    plot_width = WINDOW_WIDTH - left_margin - right_margin
    plot_height = WINDOW_HEIGHT - top_margin - bottom_margin

    # Draw axes
    axis_color = (255, 255, 255)  # White
    pygame.draw.line(screen, axis_color, 
                     (left_margin, top_margin), 
                     (left_margin, top_margin + plot_height), 2)  # Y-axis
    pygame.draw.line(screen, axis_color, 
                     (left_margin, top_margin + plot_height), 
                     (left_margin + plot_width, top_margin + plot_height), 2)  # X-axis

    # Normalize PSD values for plotting
    max_power = np.max(psd_values)
    if max_power == 0:
        max_power = 1  # Prevent division by zero
    normalized_power = psd_values / max_power

    # Define frequency range to display (e.g., 0-60 Hz)
    display_freq_max = 60
    indices = np.where(freqs <= display_freq_max)
    freqs_display = freqs[indices]
    power_display = normalized_power[indices]

    # Plot the PSD as a line graph
    num_points = len(freqs_display)
    if num_points < 2:
        return  # Not enough points to plot

    points = []
    for i in range(num_points):
        x = left_margin + (freqs_display[i] / display_freq_max) * plot_width
        y = top_margin + plot_height - (power_display[i] * plot_height)
        points.append((x, y))

    if len(points) > 1:
        pygame.draw.lines(screen, (0, 255, 0), False, points, 2)  # Green line

    # Add frequency labels (every 10 Hz)
    font = pygame.font.SysFont(None, 24)
    for freq in range(0, int(display_freq_max)+1, 10):
        x = left_margin + (freq / display_freq_max) * plot_width
        y = top_margin + plot_height
        pygame.draw.line(screen, axis_color, (x, y), (x, y + 10), 2)
        label = font.render(f"{freq} Hz", True, axis_color)
        screen.blit(label, (x - 20, y + 15))

    # Add power labels (optional, normalized)
    for i in range(1, 6):
        power_level = i * 0.2
        y = top_margin + plot_height - (power_level * plot_height)
        pygame.draw.line(screen, axis_color, 
                         (left_margin - 10, y), 
                         (left_margin, y), 2)
        label = font.render(f"{power_level:.1f}", True, axis_color)
        screen.blit(label, (left_margin - 60, y - 10))

    # Add titles
    title_font = pygame.font.SysFont(None, 32)
    title = title_font.render("Live FFT of Filtered EEG Data", True, (255, 255, 255))
    screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 10))

    # Add axis labels
    axis_label_font = pygame.font.SysFont(None, 24)
    xlabel = axis_label_font.render("Frequency (Hz)", True, (255, 255, 255))
    ylabel = axis_label_font.render("Power Spectral Density (Normalized)", True, (255, 255, 255))
    screen.blit(xlabel, (left_margin + plot_width // 2 - xlabel.get_width() // 2, top_margin + plot_height + 40))
    
    # Rotate ylabel for better readability
    ylabel_rotated = pygame.transform.rotate(ylabel, 90)
    screen.blit(ylabel_rotated, (left_margin - 80, top_margin + plot_height // 2 - ylabel_rotated.get_height() // 2))

    # Update the display
    pygame.display.flip()

def main():
    global keep_reading

    # Set up the serial connection
    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
        print(f"Connected to {PORT} at {BAUD_RATE} baud.")
    except serial.SerialException as e:
        print(f"Error opening serial port {PORT}: {e}")
        sys.exit(1)

    # Start the serial reading thread
    read_thread = threading.Thread(target=read_serial_data, args=(ser,))
    read_thread.start()

    # Initialize pygame
    screen = initialize_pygame()
    clock = pygame.time.Clock()

    # Variables for processing intervals
    last_processing_time = time.time()

    try:
        while keep_reading:
            # Handle pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    keep_reading = False

            current_time = time.time()
            if current_time - last_processing_time >= PROCESSING_INTERVAL:
                if len(data_buffer) >= BUFFER_SIZE:
                    # Convert buffer to numpy array
                    data_array = np.array(data_buffer)

                    # Artifact Detection
                    artifacts = detect_artifacts(data_array, ARTIFACT_THRESHOLD)
                    if np.any(artifacts):
                        data_array = interpolate_artifacts(data_array, artifacts)
                        print("Artifacts detected and interpolated.")

                    # Apply bandpass filter using SciPy (if not using MNE)
                    from scipy.signal import butter, filtfilt

                    # Design bandpass filter
                    nyquist = 0.5 * SAMPLING_RATE
                    low = LOWCUT / nyquist
                    high = HIGHCUT / nyquist
                    b, a = butter(FILTER_ORDER, [low, high], btype='band')

                    # Apply bandpass filter
                    data_filtered = filtfilt(b, a, data_array)

                    # Apply notch filter
                    notch_freq = NOTCH_FREQ / nyquist
                    notch_quality = NOTCH_Q
                    from scipy.signal import iirnotch

                    b_notch, a_notch = iirnotch(notch_freq, notch_quality)
                    data_filtered = filtfilt(b_notch, a_notch, data_filtered)

                    # Compute Power Spectral Density (PSD) using Welch's method
                    freqs, psd_values = welch(data_filtered, fs=SAMPLING_RATE, nperseg=1024, noverlap=512)

                    # Draw the FFT on the screen
                    draw_fft(screen, freqs, psd_values)

                last_processing_time = current_time

            clock.tick(FPS)

    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        # Clean up
        keep_reading = False
        read_thread.join()
        ser.close()
        pygame.quit()
        print("Serial connection closed and pygame quit.")

if __name__ == "__main__":
    main()
