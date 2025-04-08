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

# Setup socket
HOST = '0.0.0.0'
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

def zed_capture_image():
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

            # Encode the frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                print("Image encoding failed")
                return
            """data = buffer.tobytes()

            # Send a 4-byte header with the length of the image data
            size = len(data)
            conn.sendall(size.to_bytes(4, byteorder='big'))

            # Send the actual image data
            conn.sendall(data)

            print(f"Sent image of {size} bytes")"""


    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        print("Closing connection and camera")
        conn.close()
        zed.close()

# === Metadata sender (Server ➝ NAO) ===
def send_exhibits_occupied_metadata():
    is_occupied = "" # Maybe a string of n ints where n= # of exhibits; e.g. data[0]="0" means the first exhibit is not occupied
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("127.0.0.1", DETECTION_PORT))
        s.sendall(is_occupied.encode('utf-8'))
        print("[Metadata] Sent to NAO:", is_occupied)

# === Dialogue handler (NAO ⇄ Server) ===
def handle_audio(conn, audio_file):
    print(f"[Dialogue] Connected from {addr}")
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"audio-{timestamp}.wav"
    try:
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
        result = model.transcribe(os.getcwd() + "/" + audio_file,
                                  language="en")  # Specify English language for better accuracy
        response_text = result["text"]
        print(f"[Dialogue] Transcribed: {response_text}")

        # Send response to LLM; not finished
        llama_response = ""

        # Send LLM response to NAO (listen_for_human_response's response variable)
        conn.sendall(llama_response.encode('utf-8'))
        conn.close()
    except Exception as e:
        print(f"Error during speech conversion: {str(e)}")
        sys.exit(1)

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, AUDIO_PORT))
        s.listen(1)
        print(f"[Dialogue] Listening on port {AUDIO_PORT}...")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_audio, args=(conn, addr)).start()


if __name__ == "__main__":
    threading.Thread(target=start_server).start()
