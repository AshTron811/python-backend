import base64
import cv2
import os
import face_recognition
import pandas as pd
from datetime import datetime
from flask import Flask, jsonify, send_file, request, Response, send_from_directory
import threading
import time

app = Flask(__name__)

# --- Setup known faces directory and load known faces ---
KNOWN_FACES_DIR = "known_faces"
if not os.path.exists(KNOWN_FACES_DIR):
    os.makedirs(KNOWN_FACES_DIR)

known_faces = []
known_names = []
for filename in os.listdir(KNOWN_FACES_DIR):
    if filename.lower().endswith((".jpg", ".png")):
        image = face_recognition.load_image_file(os.path.join(KNOWN_FACES_DIR, filename))
        encodings = face_recognition.face_encodings(image)
        if encodings:
            known_faces.append(encodings[0])
            known_names.append(os.path.splitext(filename)[0])

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

# --- Global Variables ---
attendance_running = False
capture_thread = None
latest_frame = None

def capture_loop():
    global attendance_running, latest_frame
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return
    while attendance_running:
        success, img = cap.read()
        if not success:
            continue

        # Get face locations in the frame
        face_locations = face_recognition.face_locations(img)
        # For each face, check if it matches a known face and draw a rectangle if recognized
        for face_location in face_locations:
            top, right, bottom, left = face_location
            # Convert BGR to RGB for face_recognition processing
            rgb_frame = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            encodings = face_recognition.face_encodings(rgb_frame, [face_location])
            if encodings:
                face_encoding = encodings[0]
                matches = face_recognition.compare_faces(known_faces, face_encoding, tolerance=0.65)
                if True in matches:
                    match_index = matches.index(True)
                    name = known_names[match_index]
                    # Mark attendance
                    mark_attendance(name)
                    # Draw a green rectangle around the face
                    cv2.rectangle(img, (left, top), (right, bottom), (0, 255, 0), 2)
                    # Put the name label above the rectangle
                    cv2.putText(img, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                else:
                    # Optionally, draw a red rectangle for unrecognized faces
                    cv2.rectangle(img, (left, top), (right, bottom), (0, 0, 255), 2)
        # Update latest_frame after drawing rectangles
        latest_frame = img.copy()
        time.sleep(1)  # Adjust frame rate as needed
    cap.release()
    print("Capture loop stopped.")

def generate_frames():
    global latest_frame
    while True:
        if latest_frame is not None:
            ret, buffer = cv2.imencode('.jpg', latest_frame)
            if ret:
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.1)

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

@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Endpoint to capture a new face using an image uploaded from the frontend (base64-encoded)
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
    except Exception as e:
        return jsonify({"error": "Failed to save image: " + str(e)}), 500

    new_image = face_recognition.load_image_file(file_path)
    encodings = face_recognition.face_encodings(new_image)
    if encodings:
        new_encoding = encodings[0]
        known_faces.append(new_encoding)
        known_names.append(name)
        print(f"Added {name} to known faces from uploaded image.")
        return jsonify({"message": f"Added {name} to known faces from uploaded image."}), 200
    else:
        return jsonify({"error": "No face detected in the uploaded image."}), 400

# Endpoint to start the attendance system (capture loop)
@app.route("/start_attendance", methods=["POST"])
def start_attendance():
    global attendance_running, capture_thread
    if not attendance_running:
        attendance_running = True
        capture_thread = threading.Thread(target=capture_loop, daemon=True)
        capture_thread.start()
        return jsonify({"message": "Attendance system started."}), 200
    else:
        return jsonify({"message": "Attendance system already running."}), 200

# Endpoint to stop the attendance system (capture loop)
@app.route("/stop_attendance", methods=["POST"])
def stop_attendance():
    global attendance_running
    if attendance_running:
        attendance_running = False
        time.sleep(2)  # Allow capture loop to exit gracefully
        return jsonify({"message": "Attendance system stopped."}), 200
    else:
        return jsonify({"message": "Attendance system is not running."}), 200

# Endpoint to list known face files as a JSON array
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
