import os
import cv2
import shutil
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import time
from cryptography.fernet import Fernet
import numpy as np
import ttkbootstrap as tb # type: ignore

# Database File
DB_FILE = 'attendance.db'

# Encryption Setup
KEY_FILE = 'secret.key'
if not os.path.exists(KEY_FILE):
    key = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as keyfile:
        keyfile.write(key)
else:
    with open(KEY_FILE, 'rb') as keyfile:
        key = keyfile.read()

encryptor = Fernet(key)

# Encrypt and save image
def encrypt_and_save(image, filepath):
    _, buffer = cv2.imencode('.jpg', image)
    encrypted_data = encryptor.encrypt(buffer.tobytes())
    with open(filepath, 'wb') as file:
        file.write(encrypted_data)

# Decrypt and load image
def decrypt_and_load(filepath):
    with open(filepath, 'rb') as file:
        encrypted_data = file.read()
    decrypted_data = encryptor.decrypt(encrypted_data)
    nparr = np.frombuffer(decrypted_data, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

# Ensure required directories exist
DATA_STORE_PATH = r'C:\Users\sejal\Face_Attendance'
if not os.path.exists(DATA_STORE_PATH):
    os.makedirs(DATA_STORE_PATH)
if not os.path.exists('dataset'):
    os.makedirs('dataset')
if not os.path.exists('registered_faces'):
    os.makedirs('registered_faces')

# ✅ Step 1: Initialize the database
def initialize_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            student_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            registration_time TEXT NOT NULL
        )
    ''')

    # Create attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            login_time TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES users(student_id)
        )
    ''')

    conn.commit()
    conn.close()

# ✅ Step 2: Register a new user
def register_user():
    student_id = student_id_entry.get().strip()
    username = username_entry.get().strip()

    if not student_id or not username:
        messagebox.showerror("Error", "Please enter Student ID and Name.")
        return
    
    

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Check if Student ID already exists
    cursor.execute("SELECT * FROM users WHERE student_id = ?", (student_id,))
    if cursor.fetchone():
        messagebox.showerror("Error", "Student ID already exists!")
        conn.close()
        return

    # Register user in database
    registration_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("INSERT INTO users (student_id, username, registration_time) VALUES (?, ?, ?)",
                   (student_id, username, registration_time))
    conn.commit()
    conn.close()

    # Capture face data
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    cap = cv2.VideoCapture(0)
    count = 0

    while True:
        ret, frame = cap.read()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            count += 1
            image_path = f"dataset/{student_id}_{username}.{count}.jpg"
            encrypt_and_save(gray[y:y + h, x:x + w], image_path)

        cv2.imshow('Registering Face', frame)
        if cv2.waitKey(1) & 0xFF == ord('q') or count >= 30:
            break

    cap.release()
    cv2.destroyAllWindows()

    # Move images to the registered_faces folder
    for filename in os.listdir('dataset'):
        if filename.startswith(f"{student_id}_{username}"):
            shutil.move(f'dataset/{filename}', f'registered_faces/{filename}')

    messagebox.showinfo("Success", f"Student '{username}' (ID: {student_id}) registered at {registration_time}")


# ✅ Step 3: Log in user and mark attendance
def log_in():
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    cap = cv2.VideoCapture(0)

    # Load registered faces
    registered_faces = {}
    for filename in os.listdir('registered_faces'):
        if filename.endswith('.jpg'):
            student_id, username = filename.split('_')[0], filename.split('_')[1].split('.')[0]
            decrypted_img = decrypt_and_load(os.path.join('registered_faces', filename))
            registered_faces[(student_id, username)] = decrypted_img

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    while True:
        ret, frame = cap.read()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

            for (student_id, username), registered_face in registered_faces.items():
                result = cv2.matchTemplate(registered_face, gray[y:y + h, x:x + w], cv2.TM_CCOEFF_NORMED)
                similarity = cv2.minMaxLoc(result)[1]

                if similarity > 0.7:
                    login_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    # Store login time in database
                    cursor.execute("INSERT INTO attendance (student_id, username, login_time) VALUES (?, ?, ?)",
                                   (student_id, username, login_time))
                    conn.commit()

                    # Show success message
                    show_login_success_gui(student_id, username, login_time)

                    time.sleep(3)
                    conn.close()
                    cap.release()
                    cv2.destroyAllWindows()
                    return

        cv2.imshow('Logging In', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    conn.close()
    cap.release()
    cv2.destroyAllWindows()

# ✅ Step 4: Show Login Success Popup
def show_login_success_gui(student_id, username, login_time):
    login_success_window = tk.Toplevel()
    login_success_window.title("Login Success")
    login_success_window.geometry("400x150")

    ttk.Label(login_success_window, text=f"Successfully logged in as {username} (ID: {student_id})").pack(pady=10)
    ttk.Label(login_success_window, text=f"Login Time: {login_time}").pack(pady=10)
    ttk.Label(login_success_window, text="Successfully attended").pack(pady=10)
    ttk.Button(login_success_window, text="OK", command=login_success_window.destroy).pack(pady=10)

# GUI Setup
root = tb.Window(themename="superhero")  # Changed theme for a modern look
root.title("Face Attendance System")
root.geometry("500x350")
root.resizable(False, False)

# Header Label
header_label = tb.Label(root, text="Face Attendance System", font=("Helvetica", 20, "bold"), bootstyle="primary-inverse")
header_label.pack(pady=15)

# Student ID Label and Entry
tb.Label(root, text="Student ID:", font=("Arial", 12, "bold"), bootstyle="primary").pack(pady=5)
student_id_entry = tb.Entry(root, width=40, bootstyle="secondary")
student_id_entry.pack(pady=5)

# Username Label and Entry
tb.Label(root, text="Name:", font=("Arial", 12, "bold"), bootstyle="primary").pack(pady=5)
username_entry = tb.Entry(root, width=40, bootstyle="secondary")
username_entry.pack(pady=5)

# Buttons
button_frame = tb.Frame(root)
button_frame.pack(pady=15)

register_button = tb.Button(button_frame, text="Register Face", bootstyle="success-outline", width=18, command=register_user)
register_button.grid(row=0, column=0, padx=10)

login_button = tb.Button(button_frame, text="Log In", bootstyle="info-outline", width=18, command=log_in)
login_button.grid(row=0, column=1, padx=10)

# Footer Label
footer_label = tb.Label(root, text="© 2025 Face Attendance System", font=("Arial", 10, "italic"), bootstyle="light")
footer_label.pack(pady=15)
# Initialize database before running the app
initialize_database()

# Run the application
root.mainloop()
