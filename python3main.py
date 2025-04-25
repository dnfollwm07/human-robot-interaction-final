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
#import callLLM
from ultralytics import YOLO

# Setup socket
HOST = 'localhost'
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
                    print(f"No one detected in Exhibit {i + 1}")
                    occupied_exhibits += "0"


    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        return occupied_exhibits

# === Metadata sender (Server ➝ NAO) ===
def send_exhibits_occupied_metadata(conn):
    try:
        occupied_exhibits = zed_capture_image(2)
        if occupied_exhibits:
            conn.sendall(occupied_exhibits.encode('utf-8'))
            print("[Metadata] Sent to NAO:", occupied_exhibits)
    except Exception as e:
        print("Error during metadata handling:", e)
    finally:
        conn.close()

# === Dialogue handler (NAO ⇄ Server) ===
def handle_audio(conn):
    recording, fs = speechReco_python3.record_audio(5)
    print(f"[Dialogue] Connected")
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"audio-{timestamp}.wav"
    data = speechReco_python3.save_audio(recording, fs, filename)
    text = speechReco_python3.transcribe_audio(data)
    #model_response = callLLM.query_llama(text)
    conn.sendall(text.encode('utf-8'))
    conn.close()


def start_audio_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, AUDIO_PORT))
        s.listen(1)
        print(f"[Dialogue] Listening on port {AUDIO_PORT}...")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_audio, args=(conn,)).start()

def start_occupied_detector():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, DETECTION_PORT))
        s.listen(1)
        print(f"[Metadata] Listening on port {DETECTION_PORT}...")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=send_exhibits_occupied_metadata, args=(conn,)).start()


if __name__ == "__main__":
    audio_thread = threading.Thread(target=start_audio_server)
    occupied_thread = threading.Thread(target=start_occupied_detector)
    audio_thread.start()
    occupied_thread.start()
    
    # Block main from exiting by joining the server threads
    audio_thread.join()
    occupied_thread.join()

    zed.close()


