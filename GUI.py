import sys
import os
import random
import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QComboBox, QVBoxLayout, QWidget, QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QImage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Store user diagnosis selections
        self.diagnoses = []

        # Initialize the UI
        self.initUI()

    def initUI(self):
        self.setWindowTitle('MINDSCAN')

        # Central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Layout
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # Instructions label
        self.instructions_label = QLabel('Please select your diagnosis (up to 5):')
        self.instructions_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.instructions_label)

        # List of diagnoses
        self.diagnosis_list = [
            'Depression', 'Anxiety', 'Aspergers Syndrome', 'Non-Aspergers Autism',
            'ADD/ADHD', 'Dementia', 'Bipolar 1/2', 'Schizoid', 'Eating Disorder',
            'Antisocial', 'NONE'
        ]

        # List to hold the dropdowns
        self.dropdown_list = []
        self.create_diagnosis_dropdown()

        # Start button
        self.start_button = QPushButton('Start')
        self.start_button.clicked.connect(self.start_experiment)
        self.layout.addWidget(self.start_button)

        # Set the layout alignment
        self.layout.setAlignment(Qt.AlignCenter)

        # Apply stylesheets for a modern look and dark mode
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #FFFFFF;
            }
            QLabel {
                font-size: 24px;
                color: #FFFFFF;
            }
            QPushButton {
                font-size: 18px;
                padding: 10px;
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: none;
            }
            QPushButton:hover {
                background-color: #2A2A2A;
            }
            QComboBox {
                font-size: 18px;
                padding: 5px;
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: none;
                selection-background-color: #2A2A2A;
            }
            QComboBox QAbstractItemView {
                background-color: #1E1E1E;
                color: #FFFFFF;
                selection-background-color: #2A2A2A;
            }
            QScrollBar:vertical {
                background: #121212;
                width: 15px;
            }
            QScrollBar::handle:vertical {
                background: #1E1E1E;
            }
        """)

        # Set an initial window size and show the window
        self.resize(800, 600)
        self.show()

    def create_diagnosis_dropdown(self):
        if len(self.dropdown_list) < 5:
            combo_box = QComboBox()
            combo_box.addItems(['Select diagnosis'] + self.diagnosis_list)
            combo_box.setCurrentIndex(0)
            combo_box.currentIndexChanged.connect(self.diagnosis_selected)
            self.layout.insertWidget(len(self.dropdown_list) + 1, combo_box)  # Insert before the start button
            self.dropdown_list.append(combo_box)

    def diagnosis_selected(self):
        # Update self.diagnoses based on current selections
        self.diagnoses = []
        for combo_box in self.dropdown_list:
            selection = combo_box.currentText()
            if selection == 'Select diagnosis':
                # Do nothing until a valid selection is made
                return
            if selection != 'NONE':
                self.diagnoses.append(selection)
            else:
                break  # Stop processing further dropdowns if 'NONE' is selected

        # Remove extra dropdowns if 'NONE' is selected
        # Find the index of the first 'NONE' selection
        none_index = None
        for i, combo_box in enumerate(self.dropdown_list):
            if combo_box.currentText() == 'NONE':
                none_index = i
                break

        if none_index is not None:
            # Remove all dropdowns after the 'NONE' selection
            while len(self.dropdown_list) > none_index + 1:
                combo_to_remove = self.dropdown_list.pop()
                self.layout.removeWidget(combo_to_remove)
                combo_to_remove.deleteLater()
        else:
            # If 'NONE' not selected and we have less than 5 dropdowns, create a new one
            all_selected = all(cb.currentText() != 'Select diagnosis' for cb in self.dropdown_list)
            if len(self.dropdown_list) < 5 and all_selected:
                self.create_diagnosis_dropdown()

    def start_experiment(self):
        if not self.diagnoses and not any(cb.currentText() == 'NONE' for cb in self.dropdown_list):
            # No diagnoses selected, show a message
            QMessageBox.warning(self, 'No Diagnosis Selected', 'Please select at least one diagnosis to start.')
            return

        # Hide start menu elements
        self.instructions_label.hide()
        for combo_box in self.dropdown_list:
            combo_box.hide()
        self.start_button.hide()

        # Prepare the experiment
        # Load images from folders
        self.image_paths = []
        folders = ['NEG', 'NEUT', 'POS']

        for folder in folders:
            folder_path = os.path.join('images', folder)
            if not os.path.exists(folder_path):
                continue
            for filename in os.listdir(folder_path):
                if filename.lower().endswith(('.jpg', '.png', '.jpeg', '.bmp', '.gif')):
                    self.image_paths.append(os.path.join(folder_path, filename))

        # Shuffle images randomly
        random.shuffle(self.image_paths)

        # Load pause image
        self.pause_image_path = os.path.join('images', 'pause.png')
        if not os.path.exists(self.pause_image_path):
            self.pause_image_path = None

        # Image index
        self.current_image_index = 0  # Start at 0

        # QLabel to display images
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout.addWidget(self.image_label)

        # Start the experiment
        self.state = 'image'  # Start with displaying the first image
        self.waiting_for_space = False
        self.next_image()

    def next_image(self):
        if self.state == 'image':
            if self.current_image_index >= len(self.image_paths):
                # Experiment finished
                self.display_end_screen()
                return

            # Display current image
            image_path = self.image_paths[self.current_image_index]
            self.display_image(image_path)
            # Increment image index for next image
            self.current_image_index += 1
            # Set state to 'pause' for next call
            self.state = 'pause'
        elif self.state == 'pause':
            # Display pause screen
            if self.pause_image_path:
                self.display_image(self.pause_image_path)
            else:
                # Display a blank screen if pause image is not available
                self.image_label.clear()
                self.image_label.setStyleSheet("background-color: black;")
            # Set state to 'image' for next call
            self.state = 'image'

        # Wait for user to press space to proceed
        self.waiting_for_space = True

    def display_image(self, image_path):
        # Clear any previous content
        self.image_label.clear()

        # Load the image using OpenCV
        image = cv2.imread(image_path)
        if image is None:
            # Handle case where image could not be loaded
            print(f"Warning: Could not load image {image_path}")
            return
        # Convert color from BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        # Convert to QImage
        height, width, channel = image.shape
        bytesPerLine = 3 * width
        qImg = QImage(image.data, width, height, bytesPerLine, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qImg)
        # Store the original pixmap
        self.original_pixmap = pixmap
        # Scale the pixmap to fit the label
        label_size = self.image_label.size()
        scaled_pixmap = pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)

    def display_end_screen(self):
        # Clear any previous content
        self.image_label.clear()
        # Display end screen message
        self.image_label.setText('End of Experiment')
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("font-size: 36px; color: #FFFFFF;")

        # Wait for space bar or ESC to exit
        self.waiting_for_exit = True

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            if hasattr(self, 'waiting_for_space') and self.waiting_for_space:
                self.waiting_for_space = False
                self.next_image()
            elif hasattr(self, 'waiting_for_exit') and self.waiting_for_exit:
                QApplication.quit()
        elif event.key() == Qt.Key_Escape:
            QApplication.quit()

    def resizeEvent(self, event):
        super(MainWindow, self).resizeEvent(event)
        # When the window is resized, rescale the current image
        if hasattr(self, 'image_label'):
            if hasattr(self, 'original_pixmap') and not self.image_label.pixmap().isNull():
                label_size = self.image_label.size()
                scaled_pixmap = self.original_pixmap.scaled(
                    label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    sys.exit(app.exec_())
