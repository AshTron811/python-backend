import base64
import cv2
import os
import numpy as np
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

def process_attendance_from_image(image):
    """
    Given an image (as a numpy array), detect faces, compare against known faces,
    and mark attendance for recognized faces. Returns a list of recognized names.
    """
    face_locations = face_recognition.face_locations(image)
    print("Detected face locations in uploaded image:", face_locations)
    recognized_names = []
    for (top, right, bottom, left) in face_locations:
        rgb_frame = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(rgb_frame, [(top, right, bottom, left)])
        if not encodings:
            continue
        face_encoding = encodings[0]
        # Use a tolerance of 0.8 (adjust as needed)
        matches = face_recognition.compare_faces(known_faces, face_encoding, tolerance=0.8)
        print("Matches for uploaded image:", matches)
        if True in matches:
            match_index = matches.index(True)
            recognized_name = known_names[match_index]
            mark_attendance(recognized_name)
            recognized_names.append(recognized_name)
            # Optionally, draw a rectangle on the image (not sent to client)
            cv2.rectangle(image, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(image, recognized_name, (left, top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            print(f"Recognized face: {recognized_name}")
        else:
            print("Face not recognized in uploaded image.")
    return recognized_names

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

@app.route("/known_faces", methods=["GET"])
def list_known_faces():
    files = [filename for filename in os.listdir(KNOWN_FACES_DIR)
             if filename.lower().endswith((".jpg", ".png"))]
    return jsonify(files)

@app.route("/known_faces/<filename>", methods=["GET"])
def serve_known_face(filename):
    return send_from_directory(KNOWN_FACES_DIR, filename)

# Endpoint to upload a new face image without marking attendance
@app.route("/capture_face", methods=["POST"])
def capture_face():
    if "name" not in request.form or "imageData" not in request.form:
        return jsonify({"error": "Name and imageData are required"}), 400

    name = request.form["name"].strip()
    image_data = request.form["imageData"]

    if not name:
        return jsonify({"error": "Name cannot be empty"}), 400

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
            known_faces.append(encodings[0])
            known_names.append(name)
            print(f"Added {name} to known faces from uploaded image.")
            # Do not mark attendance here.
            return jsonify({"message": f"Added {name} to known faces."}), 200
        else:
            return jsonify({"error": "No face detected in the uploaded image."}), 400
    except Exception as e:
        return jsonify({"error": "Error processing image: " + str(e)}), 500

# Endpoint to capture a photo when "Start Attendance" is pressed.
# This endpoint expects an image (base64) uploaded from the frontend,
# then processes that image to detect and recognize faces, marking attendance for recognized faces.
@app.route("/start_attendance", methods=["POST"])
def start_attendance():
    if "imageData" not in request.form:
        return jsonify({"error": "Image data is required"}), 400

    image_data = request.form["imageData"]
    if image_data.startswith("data:image"):
        image_data = image_data.split(",")[1]

    try:
        image_bytes = base64.b64decode(image_data)
    except Exception as e:
        return jsonify({"error": "Failed to decode image data: " + str(e)}), 400

    # Decode image bytes into a numpy array and then into an image using OpenCV
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return jsonify({"error": "Failed to decode image to valid format."}), 400

    recognized_names = process_attendance_from_image(img)
    if recognized_names:
        return jsonify({"message": "Attendance marked for: " + ", ".join(recognized_names)}), 200
    else:
        return jsonify({"error": "No recognized faces in the captured image."}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
