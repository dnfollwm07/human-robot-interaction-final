import socket
import time
import cv2
import numpy as np
import pyzed.sl as sl
import sounddevice as sd
from scipy.io.wavfile import write
import whisper
import os
import sys
import torch
import threading
import datetime
import speechReco_python3
import callLLM
from ultralytics import YOLO

# Setup socket
HOST = '127.0.0.1'
DETECTION_PORT = 5001
AUDIO_PORT = 5002

# Initialize ZED camera
zed = sl.Camera()
init_params = sl.InitParameters()
if zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
    print("Unable to open ZED camera")
    exit(1)

# Create a Mat to store the image
image = sl.Mat()
runtime_parameters = sl.RuntimeParameters()

# YOLO11 training image detection
model = YOLO("yolo11n.pt")

def zed_capture_image(num_exhibits):
    occupied_exhibits = "" #a string of n ints where n= # of exhibits; e.g. data[0]="0" means the first exhibit is not occupied
    try:
        # Grab a new frame
        if zed.grab(runtime_parameters) == sl.ERROR_CODE.SUCCESS:
            # Retrieve left image
            zed.retrieve_image(image, sl.VIEW.LEFT)

            # Convert sl.Mat to a numpy array
            # Note: The image is stored in BGRA format. Convert to BGR if needed.
            frame = image.get_data()
            if frame is None:
                return
            # Ensure the frame is a numpy array
            frame = np.array(frame)

            # Optionally convert BGRA to BGR if your receiver expects that
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            # Save the frame
            filename = "exhibit_detection/exhibits.jpg"
            cv2.imwrite(filename, frame)
            print("Image saved!")

            # Perform object detection on an image
            img = cv2.imread(filename)
            results = model(img)  # Predict on an image

            # Split and save vertical sections
            img = cv2.imread(filename)
            height, width, _ = img.shape
            section_width = width // num_exhibits
            for i in range(num_exhibits):
                start_x = i * section_width
                end_x = (i + 1) * section_width if i < num_exhibits - 1 else width
                section = img[:, start_x:end_x]

                section_filename = f"exhibit_detection/exhibit_section_{i + 1}.jpg"
                cv2.imwrite(section_filename, section)
                print(f"Saved section {i + 1} to {section_filename}")

            # check if each region is occupied by a person or not
            for i in range(num_exhibits):
                section_filename = f"exhibit_detection/exhibit_section_{i + 1}.jpg"
                section_img = cv2.imread(section_filename)
                results = model(section_img)

                person_found = any(
                    model.names[int(box.cls[0])] == "person" and float(box.conf[0]) > 0.5
                    for result in results for box in result.boxes
                )

                if person_found:
                    occupied_exhibits += "1"
                    print(f"Person detected in Exhibit {i + 1}")
                else:
                    occupied_exhibits += "0"


    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        print("Closing camera")
        zed.close()
        return occupied_exhibits

# === Metadata sender (Server ➝ NAO) ===
def send_exhibits_occupied_metadata(occupied_exhibits):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("127.0.0.1", DETECTION_PORT))
        s.sendall(occupied_exhibits.encode('utf-8'))
        print("[Metadata] Sent to NAO:", occupied_exhibits)

# === Dialogue handler (NAO ⇄ Server) ===
def handle_audio(conn, audio_file):
    recording, fs = speechReco_python3.record_audio(5)
    print(f"[Dialogue] Connected")
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"audio-{timestamp}.wav"
    data = speechReco_python3.save_audio(recording, fs, filename)
    text = speechReco_python3.transcribe_audio(data)
    #model_response = callLLM.query_llama(text)
    conn.sendall(text.encode('utf-8'))
    conn.close()
    '''try:
        # Receive audio
        with open(filename, 'wb') as f:
            while True:
                data = conn.recv(1024) # receive audio_data var from listen_for_human response
                if not data:
                    break
                f.write(data)
        print("[Dialogue] Audio received")

        # Transcribe
        print("Loading Whisper model...")
        # Check if GPU is available
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")

        model = whisper.load_model("tiny", device=device)
        print("Converting speech to text...")
        result = model.transcribe(os.getcwd() + "/" + audio_file, language="en")  # Specify English language for better accuracy
        response_text = result["text"]
        print(f"[Dialogue] Transcribed: {response_text}")

        # Send response to LLM; not finished
        llama_response = ""

        # Send LLM response to NAO (listen_for_human_response's response variable)
        conn.sendall(llama_response.encode('utf-8'))
        conn.close()
    except Exception as e:
        print(f"Error during speech conversion: {str(e)}")
        sys.exit(1)'''

'''
def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, AUDIO_PORT))
        s.listen(1)
        print(f"[Dialogue] Listening on port {AUDIO_PORT}...")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_audio, args=(conn, addr)).start()


if __name__ == "__main__":
    threading.Thread(target=start_server).start()'''

zed_capture_image(2)