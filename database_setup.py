import sqlite3

DB_FILE = 'attendance.db'

def update_attendance_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Check current schema of the attendance table
    cursor.execute("PRAGMA table_info(attendance)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    print("Existing columns in attendance table:", column_names)

    # If 'student_id' is missing, add it
    if 'student_id' not in column_names:
        # Note: Adding NOT NULL columns in SQLite requires a default value
        cursor.execute("ALTER TABLE attendance ADD COLUMN student_id INTEGER NOT NULL DEFAULT 0")
        print("Added 'student_id' column to attendance table.")
    else:
        print("'student_id' column already exists.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_attendance_db()
