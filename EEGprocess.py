import serial
import pygame
import numpy as np
from scipy import signal
import threading
from collections import deque
import sys
import struct

# ====================== Configuration Parameters ======================

SERIAL_PORT = 'COM12'  # Replace with your Arduino's serial port
BAUD_RATE = 1000000  # Baud rate must match Arduino
SAMPLING_FREQ = 5000.0  # Hz, must match Arduino
BUFFER_SIZE = 5000  # Number of samples to display (1 second of data)
DISPLAY_WIDTH = 1200
DISPLAY_HEIGHT = 800

# EEG frequency bands adjusted to 0.5-35 Hz
FREQ_BANDS = {
    'Delta': (0.5, 4),
    'Theta': (4, 8),
    'Alpha': (8, 13),
    'Beta': (13, 30)
}

# ====================== Filter Design ======================

def butter_bandpass(lowcut, highcut, fs, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = signal.butter(order, [low, high], btype='band')
    return b, a

def butter_notch(center_freq, bandwidth, fs, order=2):
    nyq = 0.5 * fs
    b, a = signal.iirnotch(center_freq / nyq, Q=center_freq / bandwidth)
    return b, a

def apply_filter(data, b, a):
    return signal.lfilter(b, a, data)

# ====================== EEG Data Handler ======================

class EEGDataHandler:
    def __init__(self, port, baud, fs, buffer_size):
        try:
            self.serial_port = serial.Serial(port, baud, timeout=1)
            print(f"Connected to {port} at {baud} baud.")
        except serial.SerialException as e:
            print(f"Failed to connect to serial port {port}: {e}")
            sys.exit(1)
        
        self.fs = fs
        self.buffer_size = buffer_size
        self.data_buffer = deque(maxlen=buffer_size)
        self.lock = threading.Lock()
        self.running = True

        # Design bandpass filter for EEG (0.5-35 Hz)
        self.b_bandpass, self.a_bandpass = butter_bandpass(0.5, 35.0, fs, order=4)
        
        # Design notch filter for 50Hz (common power line noise)
        self.b_notch, self.a_notch = butter_notch(50.0, 2.0, fs, order=2)

        # Start the data reading thread
        self.thread = threading.Thread(target=self.read_serial, daemon=True)
        self.thread.start()

    def read_serial(self):
        while self.running:
            try:
                # Read two bytes for each sample
                bytes_to_read = 2
                data = self.serial_port.read(bytes_to_read)
                if len(data) == bytes_to_read:
                    # Unpack little endian unsigned short (uint16_t)
                    value = struct.unpack('<H', data)[0]
                    with self.lock:
                        self.data_buffer.append(value)
            except struct.error:
                print(f"Incomplete data received.")
            except Exception as e:
                print(f"Error reading serial data: {e}")
                self.running = False

    def get_filtered_data(self):
        with self.lock:
            data = list(self.data_buffer)
        
        if len(data) < self.buffer_size:
            # Pad with zeros if buffer is not full yet
            data = [0] * (self.buffer_size - len(data)) + data
        
        # Convert to numpy array for filtering
        data_np = np.array(data, dtype=np.float32)

        # Normalize ADC values (0-1023) to voltage (assuming 5V reference)
        data_np = (data_np / 1023.0) * 5.0

        # Apply bandpass filter
        filtered = apply_filter(data_np, self.b_bandpass, self.a_bandpass)
        
        # Apply notch filter
        filtered = apply_filter(filtered, self.b_notch, self.a_notch)
        
        return filtered

    def close(self):
        self.running = False
        self.thread.join()
        self.serial_port.close()
        print("Serial port closed.")

# ====================== Visualization ======================

class EEGVisualizer:
    def __init__(self, data_handler, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Real-Time EEG Visualization")
        self.clock = pygame.time.Clock()
        self.data_handler = data_handler
        self.width = width
        self.height = height
        self.font = pygame.font.Font(None, 24)
        
        # Define subplot areas
        self.waveform_height = int(self.height * 0.5)
        self.fft_height = int(self.height * 0.35)
        self.bands_height = int(self.height * 0.15)
    
    def draw_eeg_waveform(self, data):
        scaling_factor = self.waveform_height / 2 / 1.0  # Assuming EEG signals are in ±1 mV range
        normalized_data = data * scaling_factor

        points = [
            (int(i * self.width / len(data)), int(self.waveform_height / 2 - d))
            for i, d in enumerate(normalized_data)
        ]
        pygame.draw.lines(self.screen, (0, 255, 0), False, points, 2)
        
        # Label
        label = self.font.render("EEG Waveform (0.5-35 Hz)", True, (255, 255, 255))
        self.screen.blit(label, (10, 10))
    
    def draw_fft(self, data):
        fft_data = np.fft.fft(data)
        fft_freq = np.fft.fftfreq(len(data), 1/self.data_handler.fs)
        
        # Only positive frequencies
        pos_mask = fft_freq > 0
        freqs = fft_freq[pos_mask]
        magnitude = np.abs(fft_data[pos_mask])

        # Limit to 0.5-35 Hz for FFT visualization
        freq_mask = (freqs >= 0.5) & (freqs <= 35)
        freqs = freqs[freq_mask]
        magnitude = magnitude[freq_mask]
        
        # Normalize magnitude for visualization
        magnitude = magnitude / np.max(magnitude) * self.fft_height if np.max(magnitude) != 0 else magnitude

        # Scale frequency to fit the display width
        scaled_freqs = (freqs / 35.0) * self.width
        points = [
            (int(f), self.waveform_height + self.fft_height - int(m))
            for f, m in zip(scaled_freqs, magnitude)
        ]
        pygame.draw.lines(self.screen, (255, 165, 0), False, points, 1)
        
        # Label
        label = self.font.render("FFT (0.5-35 Hz)", True, (255, 255, 255))
        self.screen.blit(label, (10, self.waveform_height + 10))
    
    def draw_band_powers(self, data):
        f, Pxx = signal.welch(data, fs=self.data_handler.fs, nperseg=256)
        total_power = np.sum(Pxx)
        if total_power == 0:
            total_power = 1  # Prevent division by zero
        
        bar_width = self.width / len(FREQ_BANDS)
        
        for i, (band, (low, high)) in enumerate(FREQ_BANDS.items()):
            mask = (f >= low) & (f < high)
            band_power = np.sum(Pxx[mask]) / total_power
            bar_height = int(band_power * self.bands_height)
            color = self.get_band_color(band)
            
            pygame.draw.rect(
                self.screen,
                color,
                (
                    i * bar_width + 5,  # Add padding from left
                    self.waveform_height + self.fft_height + self.bands_height - bar_height,
                    bar_width - 10,  # Reduce width for spacing
                    bar_height
                )
            )
            
            # Display band name and power
            text = self.font.render(f"{band}: {band_power:.2f}", True, (255, 255, 255))
            self.screen.blit(text, (i * bar_width + 10, self.waveform_height + self.fft_height + 5))
    
    def get_band_color(self, band):
        colors = {
            'Delta': (255, 0, 0),    # Red
            'Theta': (255, 165, 0),  # Orange
            'Alpha': (255, 255, 0),  # Yellow
            'Beta': (0, 255, 0)      # Green
        }
        return colors.get(band, (255, 255, 255))  # Default to white
    
    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
            # Get filtered data
            data = self.data_handler.get_filtered_data()
            
            # Draw components
            self.screen.fill((0, 0, 0))  # Clear screen with black
            self.draw_eeg_waveform(data)
            self.draw_fft(data)
            self.draw_band_powers(data)
            
            pygame.display.flip()
            self.clock.tick(30)  # Limit to 30 FPS
        
        pygame.quit()

# ====================== Main Execution ======================

def main():
    try:
        eeg_handler = EEGDataHandler(SERIAL_PORT, BAUD_RATE, SAMPLING_FREQ, BUFFER_SIZE)
        visualizer = EEGVisualizer(eeg_handler)
        visualizer.run()
    except KeyboardInterrupt:
        print("Interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'eeg_handler' in locals():
            eeg_handler.close()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()
