import pygame
import os
import time
import json
import random
import string
import numpy as np
import serial
import struct
import threading
from scipy.signal import iirnotch, filtfilt

# Initialize Pygame
pygame.init()

# Set screen to fullscreen mode
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
screen_width, screen_height = screen.get_size()  # Get the actual screen dimensions
pygame.display.set_caption("MINDSCAN")

# Font setup
font = pygame.font.SysFont('Arial', 24)
large_font = pygame.font.SysFont('Arial', 36)

# Diagnosis list
diagnosis_list = [
    'Depression', 'Anxiety', 'Aspergers Syndrome', 'Non-Aspergers Autism',
    'ADD/ADHD', 'Dementia', 'Bipolar 1/2', 'Schizoid', 'Eating Disorder',
    'Antisocial', 'NONE'
]

# Variables for dropdowns
dropdowns = [{'rect': pygame.Rect(50, 100, 300, 40), 'open': False, 'selection': 'Select Diagnosis'}]
selected_diagnoses = []
max_dropdowns = 5

# Images setup
image_folder = "images/EmoPics"  # Update this path as needed
images = sorted([f for f in os.listdir(image_folder) if f.lower().endswith('.jpg')])
total_images = len(images)
current_image_index = 0

# Ensure TData folder exists
if not os.path.exists('TData'):
    os.makedirs('TData')

# Initialize data list to collect experiment data
data_list = []

# EEG Configuration Parameters
SERIAL_PORT = 'COM7'  # Replace with your serial port
BAUD_RATE = 115200
SAMPLE_RATE = 2000  # As per your Arduino code
ADC_MAX = 4095       # 12-bit ADC
VOLTAGE_RANGE = 3.3  # Voltage range for Arduino ADC
NOTCH_FREQ = 50.0    # Frequency to be removed from signal (Hz)
Q_FACTOR = 30.0      # Quality factor for the notch filter

# EEG Bands
EEG_BANDS = {
    'Delta': (0.5, 4),
    'Theta': (4, 8),
    'Alpha': (8, 13),
    'Beta': (13, 30),
    'Gamma': (30, 70)
}

# Initialize EEG data variables
data_buffer = []
stop_thread = False

# Function to scale images while maintaining aspect ratio
def scale_image_to_screen(image, screen_width, screen_height):
    image_width, image_height = image.get_size()
    scale_factor = min(screen_width / image_width, screen_height / image_height)
    new_width = int(image_width * scale_factor)
    new_height = int(image_height * scale_factor)
    scaled_image = pygame.transform.scale(image, (new_width, new_height))
    return scaled_image

# Load EmoPics images and scale them
def load_image(index):
    if images and index < len(images):
        img_path = os.path.join(image_folder, images[index])
        try:
            image = pygame.image.load(img_path).convert_alpha()
            return scale_image_to_screen(image, screen_width, screen_height), os.path.basename(img_path)
        except pygame.error as e:
            print(f"Unable to load image {img_path}: {e}")
            return None, ""
    return None, ""

# Load and scale pause image
pause_image_path = "images/pause.png"  # Update this path as needed
try:
    pause_image = pygame.image.load(pause_image_path).convert_alpha()
    pause_image = scale_image_to_screen(pause_image, screen_width, screen_height)
except pygame.error as e:
    print(f"Unable to load pause image {pause_image_path}: {e}")
    pause_image = None  # Handle gracefully if pause image fails to load

# Function to draw the start menu
def draw_start_menu():
    screen.fill((18, 18, 18))  # Dark background

    # Title
    title_text = large_font.render("Select your diagnoses (up to 5):", True, (255, 255, 255))
    title_rect = title_text.get_rect(topleft=(50, 50))
    screen.blit(title_text, title_rect)

    # Draw each dropdown
    for dropdown in dropdowns:
        # Draw the dropdown box
        pygame.draw.rect(screen, (50, 50, 50), dropdown['rect'], border_radius=5)

        # Show selected diagnosis or default text
        diagnosis_text = font.render(
            dropdown['selection'],
            True,
            (255, 255, 255) if dropdown['selection'] != 'Select Diagnosis' else (150, 150, 150)
        )
        screen.blit(diagnosis_text, (dropdown['rect'].x + 10, dropdown['rect'].y + 7))

        # Draw dropdown options if open
        if dropdown['open']:
            for j, option in enumerate(diagnosis_list):
                option_rect = pygame.Rect(dropdown['rect'].x, dropdown['rect'].y + (j + 1) * 40, 300, 40)
                pygame.draw.rect(screen, (70, 70, 70), option_rect, border_radius=5)
                option_text = font.render(option, True, (255, 255, 255))
                screen.blit(option_text, (option_rect.x + 10, option_rect.y + 7))

    # Start button
    start_button_width, start_button_height = 150, 50
    start_button_rect = pygame.Rect(
        screen_width - start_button_width - 50,
        screen_height - start_button_height - 50,
        start_button_width,
        start_button_height
    )
    pygame.draw.rect(screen, (70, 130, 180), start_button_rect, border_radius=5)
    start_text = font.render("Start", True, (255, 255, 255))
    start_text_rect = start_text.get_rect(center=start_button_rect.center)
    screen.blit(start_text, start_text_rect)

    pygame.display.flip()
    return start_button_rect

# Function to handle dropdown interactions
def handle_dropdown_click(index, mouse_pos):
    dropdown = dropdowns[index]
    if dropdown['rect'].collidepoint(mouse_pos):
        dropdown['open'] = not dropdown['open']
    elif dropdown['open']:
        # Handle option selection when dropdown is open
        for j, option in enumerate(diagnosis_list):
            option_rect = pygame.Rect(dropdown['rect'].x, dropdown['rect'].y + (j + 1) * 40, 300, 40)
            if option_rect.collidepoint(mouse_pos):
                dropdown['selection'] = option
                dropdown['open'] = False
                update_dropdowns(index)
                break
        dropdown['open'] = False  # Close dropdown if clicked outside options

# Function to update the dropdowns based on user selections
def update_dropdowns(index):
    selected_diagnoses.clear()
    for dropdown in dropdowns:
        selection = dropdown['selection']
        if selection != 'Select Diagnosis' and selection != 'NONE':
            selected_diagnoses.append(selection)

    # Adjust dropdowns based on 'NONE' selection
    if dropdowns[index]['selection'] == 'NONE':
        dropdowns[:] = dropdowns[:index + 1]  # Remove extra dropdowns after 'NONE'
    elif len(dropdowns) < max_dropdowns and all(d['selection'] != 'Select Diagnosis' for d in dropdowns):
        new_y = 100 + len(dropdowns) * 50
        dropdowns.append({'rect': pygame.Rect(50, new_y, 300, 40), 'open': False, 'selection': 'Select Diagnosis'})

# EEG data collection functions
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
        except serial.SerialException as e:
            print(f"Serial exception: {e}")
            stop_thread = True
        except Exception as e:
            print(f"Unexpected error: {e}")
            stop_thread = True

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

# Function to save data (includes EEG and FFT data)
def save_data_to_json(image_name, diagnoses, eeg_data, fft_freqs, fft_data, band_powers, timestamp):
    data = {
        "timestamp": timestamp,
        "headline": image_name,
        "diagnoses": diagnoses,
        "eeg_data": eeg_data.tolist(),
        "fft_freqs": fft_freqs.tolist(),
        "fft_data": fft_data.tolist(),
        "band_powers": band_powers
    }
    data_list.append(data)

# Function to generate a random filename
def generate_random_filename():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + '.json'

# Main variables
state = 'start'  # Can be 'start', 'experiment', or 'end'

# Main loop
running = True
ser = None
eeg_thread = None

try:
    while running:
        if state == 'start':
            start_button_rect = draw_start_menu()
        elif state == 'experiment':
            # Initialize EEG serial connection and start thread
            if ser is None:
                try:
                    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
                    print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud.")
                    eeg_thread = threading.Thread(target=read_serial_data, args=(ser,))
                    eeg_thread.daemon = True  # Ensure thread exits when main program exits
                    eeg_thread.start()
                except serial.SerialException as e:
                    print(f"Could not open serial port {SERIAL_PORT}: {e}")
                    running = False
                    break

            screen.fill((18, 18, 18))  # Dark background

            # Display the pause image
            if pause_image:
                image_to_display = pause_image
                image_rect = image_to_display.get_rect(center=(screen_width // 2, screen_height // 2))
                screen.blit(image_to_display, image_rect)
                pygame.display.flip()

            waiting_for_space = True
            while waiting_for_space:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        waiting_for_space = False

                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_SPACE:
                            waiting_for_space = False

            # Display EmoPics image and collect EEG data
            if running:
                image_to_display, image_name = load_image(current_image_index)
                if image_to_display:
                    # Clear data buffer
                    data_buffer.clear()

                    # Start time
                    start_time = time.time()

                    # Display the image
                    screen.fill((18, 18, 18))
                    image_rect = image_to_display.get_rect(center=(screen_width // 2, screen_height // 2))
                    screen.blit(image_to_display, image_rect)
                    pygame.display.flip()

                    # Collect data for the duration
                    eeg_duration = 4  # Duration in seconds
                    while time.time() - start_time < eeg_duration:
                        for event in pygame.event.get():
                            if event.type == pygame.QUIT:
                                running = False
                                break
                        # Sleep briefly to allow other threads to run
                        time.sleep(0.01)

                    # Timestamp
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

                    # Process EEG data
                    if len(data_buffer) > 0:
                        # Convert ADC values to voltage
                        voltage_data = np.array(data_buffer) / ADC_MAX * VOLTAGE_RANGE

                        # Apply notch filter
                        filtered_voltage = apply_notch_filter(voltage_data, SAMPLE_RATE, NOTCH_FREQ, Q_FACTOR)

                        # Remove DC offset
                        filtered_voltage -= np.mean(filtered_voltage)

                        # Perform FFT
                        fft_data_complex = np.fft.rfft(filtered_voltage)
                        fft_magnitude = np.abs(fft_data_complex) / len(filtered_voltage)
                        freqs = np.fft.rfftfreq(len(filtered_voltage), d=1.0/SAMPLE_RATE)

                        # Calculate EEG Band Powers
                        band_powers = calculate_eeg_band_powers(freqs, fft_magnitude, EEG_BANDS)

                        # Save the data to data_list
                        save_data_to_json(image_name, selected_diagnoses, filtered_voltage, freqs, fft_magnitude, band_powers, timestamp)
                    else:
                        print("No EEG data collected.")
                        save_data_to_json(image_name, selected_diagnoses, np.array([]), np.array([]), np.array([]), {}, timestamp)

                # Move to the next image or end the experiment
                current_image_index += 1
                if current_image_index >= total_images:
                    state = 'end'

        elif state == 'end':
            # Generate a random filename
            filename = generate_random_filename()
            filepath = os.path.join('TData', filename)
            # Save data_list to 'TData/filename.json'
            with open(filepath, 'w') as file:
                json.dump(data_list, file, indent=4)
            print(f"Data saved to {filepath}")
            screen.fill((18, 18, 18))
            end_text = large_font.render("End of Experiment", True, (255, 255, 255))
            end_rect = end_text.get_rect(center=(screen_width // 2, screen_height // 2))
            screen.blit(end_text, end_rect)
            pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if state == 'start':
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = event.pos
                    # Check dropdown interactions
                    for i in range(len(dropdowns)):
                        handle_dropdown_click(i, mouse_pos)

                    # Check for start button click
                    if start_button_rect.collidepoint(mouse_pos):
                        if selected_diagnoses or any(dropdown['selection'] == 'NONE' for dropdown in dropdowns):
                            state = 'experiment'
                            current_image_index = 0  # Reset index at start
                        else:
                            print("Please select at least one diagnosis.")  # Placeholder message

                elif event.type == pygame.KEYDOWN:
                    for dropdown in dropdowns:
                        dropdown['open'] = False  # Close all dropdowns on any key press

            elif state == 'end':
                if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    running = False  # Exit on any key or mouse press

finally:
    # Clean up resources
    stop_thread = True
    if eeg_thread is not None:
        eeg_thread.join()
    if ser is not None:
        ser.close()
    pygame.quit()

