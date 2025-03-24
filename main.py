import base64
import cv2
import os
import face_recognition
import pandas as pd
from datetime import datetime
from flask import Flask, jsonify, send_file, request, Response, send_from_directory
import time

app = Flask(__name__)

# --- Setup known faces directory and load known faces ---
KNOWN_FACES_DIR = "known_faces"
if not os.path.exists(KNOWN_FACES_DIR):
    os.makedirs(KNOWN_FACES_DIR)

known_faces = []
known_names = []

print("Loading known faces...")
for filename in os.listdir(KNOWN_FACES_DIR):
    if filename.lower().endswith((".jpg", ".png")):
        filepath = os.path.join(KNOWN_FACES_DIR, filename)
        try:
            image = face_recognition.load_image_file(filepath)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                known_faces.append(encodings[0])
                known_names.append(os.path.splitext(filename)[0])
                print(f"Loaded known face: {filename}")
            else:
                print(f"No encoding found in {filename}")
        except Exception as e:
            print(f"Error loading {filename}: {e}")

# --- Attendance Data ---
attendance_csv = "attendance.csv"
if os.path.exists(attendance_csv):
    attendance_df = pd.read_csv(attendance_csv)
else:
    attendance_df = pd.DataFrame(columns=["Name", "Time"])
marked_names = set(attendance_df["Name"].tolist())

def mark_attendance(name):
    global attendance_df
    if name not in marked_names:
        time_now = datetime.now().strftime("%H:%M:%S")
        print(f"Marking attendance for: {name} at {time_now}")
        marked_names.add(name)
        new_row = pd.DataFrame({"Name": [name], "Time": [time_now]})
        attendance_df = pd.concat([attendance_df, new_row], ignore_index=True)
        try:
            attendance_df.to_csv(attendance_csv, index=False)
            print("Attendance saved to 'attendance.csv'.")
        except Exception as e:
            print(f"Error saving attendance: {e}")

# --- Flask Endpoints ---

@app.route("/")
def index():
    return "Attendance Backend Service is running."

@app.route("/attendance", methods=["GET"])
def get_attendance():
    if os.path.exists(attendance_csv):
        return send_file(attendance_csv, mimetype="text/csv")
    else:
        empty_csv = "Name,Time\n"
        return Response(empty_csv, mimetype="text/csv")

# Endpoint to capture a new face via an image uploaded from the frontend (base64-encoded)
@app.route("/capture_face", methods=["POST"])
def capture_face():
    # Expect 'name' and 'imageData' in the form data
    if "name" not in request.form or "imageData" not in request.form:
        return jsonify({"error": "Name and imageData are required"}), 400

    name = request.form["name"].strip()
    image_data = request.form["imageData"]

    if not name:
        return jsonify({"error": "Name cannot be empty"}), 400

    # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,")
    if image_data.startswith("data:image"):
        image_data = image_data.split(",")[1]

    try:
        image_bytes = base64.b64decode(image_data)
    except Exception as e:
        return jsonify({"error": "Failed to decode image data: " + str(e)}), 400

    file_path = os.path.join(KNOWN_FACES_DIR, f"{name}.jpg")
    try:
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        print(f"Saved image for {name} at {file_path}")
    except Exception as e:
        return jsonify({"error": "Failed to save image: " + str(e)}), 500

    try:
        new_image = face_recognition.load_image_file(file_path)
        encodings = face_recognition.face_encodings(new_image)
        if encodings:
            new_encoding = encodings[0]
            known_faces.append(new_encoding)
            known_names.append(name)
            print(f"Added {name} to known faces from uploaded image.")
            # Optionally, mark attendance immediately after a successful upload:
            mark_attendance(name)
            return jsonify({"message": f"Added {name} to known faces and marked attendance."}), 200
        else:
            return jsonify({"error": "No face detected in the uploaded image."}), 400
    except Exception as e:
        return jsonify({"error": "Error processing image: " + str(e)}), 500

# Endpoint to list known face filenames as a JSON array
@app.route("/known_faces", methods=["GET"])
def list_known_faces():
    files = [filename for filename in os.listdir(KNOWN_FACES_DIR)
             if filename.lower().endswith((".jpg", ".png"))]
    return jsonify(files)

# Endpoint to serve an individual known face image
@app.route("/known_faces/<filename>", methods=["GET"])
def serve_known_face(filename):
    return send_from_directory(KNOWN_FACES_DIR, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
