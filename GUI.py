import cv2
import os
import random
import numpy as np

# Function to create a screen with text
def create_text_screen(text, width, height):
    screen = np.zeros((height, width, 3), dtype=np.uint8)
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size, _ = cv2.getTextSize(text, font, 1.5, 2)
    text_x = (width - text_size[0]) // 2
    text_y = (height + text_size[1]) // 2
    cv2.putText(screen, text, (text_x, text_y), font, 1.5, (255, 255, 255), 2, cv2.LINE_AA)
    return screen

# Set up the display window size
screen_width = 800   # Adjust as needed
screen_height = 600  # Adjust as needed

# Load images from folders
image_paths = []
folders = ['NEG', 'NEUT', 'POS']

for folder in folders:
    folder_path = os.path.join('images', folder)
    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.jpg'):
            image_paths.append(os.path.join(folder_path, filename))

# Shuffle images randomly
random.shuffle(image_paths)

# Create start and end screens
start_screen = create_text_screen('Press Space to Start', screen_width, screen_height)
end_screen = create_text_screen('End of Experiment', screen_width, screen_height)

# Display the start screen
cv2.imshow('MINDSCAN', start_screen)
cv2.waitKey(1)  # Necessary for the window to display

# Wait for space bar to start
while True:
    key = cv2.waitKey(1) & 0xFF
    if key == 32:  # Space bar ASCII code
        break
    elif key == 27:  # ESC key to exit
        cv2.destroyAllWindows()
        exit()

# Main loop to display images
for image_path in image_paths:
    current_image_name = os.path.basename(image_path)  # Variable with the current image name

    # Load and resize the image
    image = cv2.imread(image_path)
    image = cv2.resize(image, (screen_width, screen_height))

    # Display the image
    cv2.imshow('MINDSCAN', image)

    # Wait for space bar to show the next image
    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == 32:  # Space bar
            break
        elif key == 27:  # ESC key to exit
            cv2.destroyAllWindows()
            exit()

# Display the end screen
cv2.imshow('MINDSCAN', end_screen)
cv2.waitKey(1)  # Necessary for the window to update

# Wait for space bar or ESC to exit
while True:
    key = cv2.waitKey(1) & 0xFF
    if key == 32 or key == 27:  # Space bar or ESC
        break

# Close all windows
cv2.destroyAllWindows()
