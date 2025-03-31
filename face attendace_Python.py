import os
import cv2
import shutil
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

# Database File
DB_FILE = 'attendance.db'

# Ensure required directories exist
DATA_STORE_PATH = r'C:\Users\sejal\face_attendance'
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
    cap = cv2.VideoCapture(1)
    count = 0

    while True:
        ret, frame = cap.read()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            count += 1
            image_path = f"dataset/{student_id}_{username}.{count}.jpg"
            cv2.imwrite(image_path, gray[y:y + h, x:x + w])

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
            img = cv2.imread(os.path.join('registered_faces', filename))
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            registered_faces[(student_id, username)] = gray

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

# ✅ Step 5: Create the GUI
root = tk.Tk()
root.title("Face Attendance System")
root.geometry("400x250")

ttk.Label(root, text="Student ID:").pack(pady=5)
student_id_entry = ttk.Entry(root, width=30)
student_id_entry.pack(pady=5)

ttk.Label(root, text="Name:").pack(pady=5)
username_entry = ttk.Entry(root, width=30)
username_entry.pack(pady=5)

register_button = ttk.Button(root, text="Register Face", command=register_user)
register_button.pack(pady=5)

login_button = ttk.Button(root, text="Log In", command=log_in)
login_button.pack(pady=5)

# Initialize database before running the app
initialize_database()

# Run the application
root.mainloop()
