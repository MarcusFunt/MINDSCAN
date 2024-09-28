import pygame
import os
import time
import json
import random
import string

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

# Function to generate a random filename
def generate_random_filename():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + '.json'

# Function to save data to a JSON file
def save_data_to_json(image_name, diagnoses):
    filename = generate_random_filename()
    data = {
        "headline": image_name,
        "diagnoses": ','.join(diagnoses)
    }
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)
    print(f"Data saved to {filename}")

# Main variables
state = 'start'  # Can be 'start', 'experiment', or 'end'

# Main loop
running = True
while running:
    if state == 'start':
        start_button_rect = draw_start_menu()
    elif state == 'experiment':
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

        # Display EmoPics image
        if running:
            image_to_display, image_name = load_image(current_image_index)
            if image_to_display:
                screen.fill((18, 18, 18))
                image_rect = image_to_display.get_rect(center=(screen_width // 2, screen_height // 2))
                screen.blit(image_to_display, image_rect)
                pygame.display.flip()
                pygame.time.wait(4000)  # Wait for 4 seconds

                # Save the data to a JSON file
                save_data_to_json(image_name, selected_diagnoses)

            # Cycle to the next image after pause
            current_image_index = (current_image_index + 1) % total_images

    elif state == 'end':
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

pygame.quit()
