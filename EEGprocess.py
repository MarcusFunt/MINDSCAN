"""
Python Script: Real-Time EEG Data Processing with Enhanced Filtering and FFT Visualization

Description:
- Connects to the Arduino via COM12 at 115200 baud.
- Reads incoming analog EEG values with a timestamp.
- Applies advanced filtering:
    - Band-Pass Filter: 0.5-50 Hz
    - Notch Filter: 50 Hz and its harmonics (100Hz)
- Performs Fast Fourier Transform (FFT) for frequency analysis.
- Visualizes the FFT data in real-time using PyQtGraph, highlighting relevant EEG bands.

Requirements:
- pyserial (`pip install pyserial`)
- pyqtgraph (`pip install pyqtgraph`)
- numpy (`pip install numpy`)
- scipy (`pip install scipy`)
- PyQt5 (`pip install PyQt5`)
"""

import sys
import serial
import time
import numpy as np
from collections import deque
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt  # Import Qt for splitter orientation
import pyqtgraph as pg
import threading
from scipy.signal import butter, lfilter, iirnotch, welch

# ----------------------------- Configuration ----------------------------- #

SERIAL_PORT = 'COM12'      # Replace with your Arduino's COM port (e.g., 'COM12' on Windows or '/dev/ttyUSB0' on Linux)
BAUD_RATE = 115200        # Must match the Arduino's baud rate
TIMEOUT = 1               # Read timeout in seconds
BUFFER_SIZE = 1024        # Number of samples to buffer (power of 2 for FFT)
CHANNEL_NAME = 'EEG1'     # Name of the EEG channel
SFREQ = 1000              # Sampling frequency in Hz (Arduino sample rate)
ADC_MAX = 4095            # Maximum ADC value (4095 for 12-bit ADC)
V_REF = 5.0               # Reference voltage in volts
BIAS = 2.5                # Bias voltage in volts (Vcc/2 for centering)

# Notch filter frequencies (power line noise and its first harmonic)
NOTCH_FREQS = [50.0, 100.0]  # Add more harmonics if needed

# EEG Bands (in Hz)
EEG_BANDS = {
    'Delta': (0.5, 4),
    'Theta': (4, 8),
    'Alpha': (8, 12),
    'Beta': (12, 30),
    # 'Gamma': (30, 50)  # Uncomment if needed
}

# ---------------------------- Data Structures ---------------------------- #

eeg_buffer = deque(maxlen=BUFFER_SIZE)      # Buffer to store EEG values
timestamps = deque(maxlen=BUFFER_SIZE)      # Buffer to store timestamps

# ------------------------------ Serial Reader ----------------------------- #

def read_serial_data():
    """
    Reads serial data from the Arduino and appends it to the buffers.
    Expected data format: <timestamp>,<value>
    """
    global eeg_buffer, timestamps
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT) as ser:
            print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud.")
            time.sleep(2)  # Wait for the serial connection to initialize

            while True:
                if ser.in_waiting:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        try:
                            parts = line.split(',')
                            if len(parts) != 2:
                                print(f"Malformed line: {line}")
                                continue
                            timestamp_ms = int(parts[0])
                            analog_value = int(parts[1])
                            timestamps.append(timestamp_ms)
                            eeg_buffer.append(analog_value)
                            # Debugging: Print the received value
                            print(f"Received Value: {analog_value}")  # Add this print statement
                        except ValueError as e:
                            print(f"ValueError: {e} | Line: {line}")
    except serial.SerialException as e:
        print(f"SerialException: {e}")
    except KeyboardInterrupt:
        print("\nSerial reading stopped.")

# ------------------------------ Filtering Functions ------------------------ #

def butter_bandpass(lowcut, highcut, fs, order=4):
    """
    Designs a Butterworth band-pass filter.

    Parameters:
    - lowcut: Low cutoff frequency in Hz
    - highcut: High cutoff frequency in Hz
    - fs: Sampling frequency in Hz
    - order: Filter order

    Returns:
    - b, a: Numerator and denominator coefficients of the filter
    """
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a

def butter_notch(freq, fs, Q=30):
    """
    Designs a Butterworth notch filter.

    Parameters:
    - freq: Frequency to notch out in Hz
    - fs: Sampling frequency in Hz
    - Q: Quality factor

    Returns:
    - b, a: Numerator and denominator coefficients of the filter
    """
    nyq = 0.5 * fs
    w0 = freq / nyq
    b, a = iirnotch(w0, Q)
    return b, a

def apply_filters(data, fs):
    """
    Applies band-pass and notch filters to the EEG data.

    Parameters:
    - data: Numpy array of EEG voltages
    - fs: Sampling frequency in Hz

    Returns:
    - filtered_data: Numpy array of filtered EEG voltages
    """
    # Band-Pass Filter: 0.5-50 Hz
    b_bp, a_bp = butter_bandpass(0.5, 50.0, fs, order=4)
    filtered_data = lfilter(b_bp, a_bp, data)

    # Apply Notch Filters for each frequency in NOTCH_FREQS
    for freq in NOTCH_FREQS:
        b_notch, a_notch = butter_notch(freq, fs, Q=30)
        filtered_data = lfilter(b_notch, a_notch, filtered_data)

    return filtered_data

# ------------------------------ FFT Processing ---------------------------- #

def compute_fft(filtered_data):
    """
    Computes the Fast Fourier Transform (FFT) of the filtered EEG data.

    Parameters:
    - filtered_data: numpy array of filtered EEG voltages

    Returns:
    - freqs: frequency bins
    - fft_magnitude: magnitude of the FFT
    """
    N = len(filtered_data)
    fft_vals = np.fft.fft(filtered_data * np.hanning(N))  # Apply Hanning window to reduce spectral leakage
    fft_magnitude = np.abs(fft_vals) / N  # Normalize
    freqs = np.fft.fftfreq(N, d=1/SFREQ)

    # Consider only the positive frequencies
    pos_mask = freqs >= 0
    freqs = freqs[pos_mask]
    fft_magnitude = fft_magnitude[pos_mask]

    return freqs, fft_magnitude

# ------------------------------ Real-Time Plotting ------------------------- #

class EEGPlotter(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Real-Time EEG FFT')
        self.setGeometry(100, 100, 800, 600)

        # Create a central widget and layout
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QtWidgets.QVBoxLayout(self.central_widget)

        # Initialize PyQtGraph PlotWidget for Frequency-Domain FFT
        self.freq_plot_widget = pg.PlotWidget(title="Frequency-Domain FFT")
        self.freq_plot_widget.setLabel('left', 'Magnitude', units='')
        self.freq_plot_widget.setLabel('bottom', 'Frequency', units='Hz')
        self.freq_plot_widget.showGrid(x=True, y=True)
        self.layout.addWidget(self.freq_plot_widget)

        # Initialize the FFT plot curve
        self.freq_curve = self.freq_plot_widget.plot(pen=pg.mkPen(color='m', width=2))

        # Highlight EEG Bands
        self.highlight_eeg_bands()

        # Timer for updating the FFT plot
        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update_fft_plot)
        self.timer.start(100)  # Update every 100 ms

    def highlight_eeg_bands(self):
        """
        Highlights EEG bands on the FFT plot for visual reference.
        """
        for band, (low, high) in EEG_BANDS.items():
            brush = pg.mkBrush(color=(np.random.randint(0,255), np.random.randint(0,255), np.random.randint(0,255), 50))
            rect = pg.QtWidgets.QGraphicsRectItem(low, 0, high - low, 1e-3)
            rect.setBrush(brush)
            rect.setPen(pg.mkPen(None))
            self.freq_plot_widget.addItem(rect)
            # Add band label
            text = pg.TextItem(text=band, color=brush.color().getRgb())
            text.setPos(low + (high - low)/2, 1e-3)
            self.freq_plot_widget.addItem(text)

    def update_fft_plot(self):
        if len(eeg_buffer) < BUFFER_SIZE:
            # Not enough data to compute FFT
            return

        # Convert deque to numpy array
        eeg_data = np.array(eeg_buffer)

        # Convert ADC values to voltage and center
        voltage = process_eeg_data(eeg_data, adc_max=ADC_MAX, v_ref=V_REF, bias=BIAS)

        # Apply filters
        filtered_voltage = apply_filters(voltage, SFREQ)

        # Compute FFT
        freqs, fft_magnitude = compute_fft(filtered_voltage)

        # Debugging: Ensure FFT data is valid
        if len(freqs) == 0 or len(fft_magnitude) == 0:
            print("FFT computation returned empty data.")
            return

        # Update the FFT plot
        self.freq_curve.setData(freqs, fft_magnitude)

        # Optional: Print FFT peak information for debugging
        peak_idx = np.argmax(fft_magnitude)
        peak_freq = freqs[peak_idx]
        peak_mag = fft_magnitude[peak_idx]
        print(f"FFT Peak: {peak_mag:.4f} at {peak_freq} Hz")

# ------------------------------- Main Function ---------------------------- #

def main():
    # Start serial reading in a separate thread
    serial_thread = threading.Thread(target=read_serial_data, daemon=True)
    serial_thread.start()

    # Start the Qt application for plotting
    app = QtWidgets.QApplication(sys.argv)
    eeg_plotter = EEGPlotter()
    eeg_plotter.show()
    sys.exit(app.exec_())

# ----------------------------- Helper Functions ---------------------------- #

def process_eeg_data(eeg_values, adc_max=ADC_MAX, v_ref=V_REF, bias=BIAS):
    """
    Processes raw EEG values:
    - Converts ADC values to voltage.
    - Centers the signal around 0V.

    Parameters:
    - eeg_values: iterable of raw ADC values
    - adc_max: maximum ADC value (4095 for 12-bit, 1023 for 10-bit)
    - v_ref: reference voltage (Vcc)
    - bias: bias voltage (Vcc/2)

    Returns:
    - voltage_centered: numpy array of processed EEG voltages
    """
    # Convert ADC (0-4095) to Voltage (assuming v_ref)
    voltage = (eeg_values / adc_max) * v_ref
    # Center the signal around 0V (assuming bias = Vcc/2)
    voltage_centered = voltage - bias
    return voltage_centered

# ------------------------------- Entry Point ------------------------------ #

if __name__ == '__main__':
    main()
