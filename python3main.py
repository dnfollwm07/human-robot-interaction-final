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

# Add imports for TinyLlama
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

# Setup socket
HOST = '127.0.0.1'
DETECTION_PORT = 5001
AUDIO_PORT = 5002

# Initialize TinyLlama model
def initialize_tinyllama():
    print("Loading TinyLlama model...")
    model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        device_map="auto",
        torch_dtype="auto"
    )
    
    generator = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=1024,
        do_sample=False
    )
    
    return model, tokenizer, generator

# Global variables for TinyLlama
tinyllama_model = None
tinyllama_tokenizer = None
tinyllama_generator = None

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
        print("Closing camera")
        zed.close()

# Function to get response from TinyLlama
def get_tinyllama_response(prompt, conversation_history=""):
    global tinyllama_model, tinyllama_tokenizer, tinyllama_generator
    
    # Initialize model if not already done
    if tinyllama_generator is None:
        tinyllama_model, tinyllama_tokenizer, tinyllama_generator = initialize_tinyllama()
    
    print("Generating response with TinyLlama...")
    
    # Add conversation history to prompt if available
    if conversation_history:
        full_prompt = f"{conversation_history}\nVisitor: {prompt}\nGuide:"
    else:
        full_prompt = f"Visitor: {prompt}\nGuide:"
    
    # Manage token limit
    input_ids = tinyllama_tokenizer(full_prompt, return_tensors="pt").input_ids[0]
    max_input_tokens = 2048 - 512  # Reserve space for output
    
    if len(input_ids) > max_input_tokens:
        print(f"[Warning] Prompt too long ({len(input_ids)} tokens), truncating...")
        input_ids = input_ids[-max_input_tokens:]
        full_prompt = tinyllama_tokenizer.decode(input_ids, skip_special_tokens=True)
    
    # Generate response
    result = tinyllama_generator(full_prompt)[0]['generated_text']
    
    if result.startswith(full_prompt):
        response = result[len(full_prompt):].strip()
    else:
        response = result.strip()
    
    print(f"TinyLlama response: {response}")
    return response

# === Metadata sender (Server ➝ NAO) ===
def send_exhibits_occupied_metadata():
    is_occupied = "" # Maybe a string of n ints where n= # of exhibits; e.g. data[0]="0" means the first exhibit is not occupied
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("127.0.0.1", DETECTION_PORT))
        s.sendall(is_occupied.encode('utf-8'))
        print("[Metadata] Sent to NAO:", is_occupied)

# === Dialogue handler (NAO ⇄ Server) ===
def handle_audio(conn, addr):
    try:
        # First check if we received a prompt from NAO
        prompt_data = None
        conn.settimeout(0.1)  # Short timeout to check for prompt data
        try:
            prompt_data = conn.recv(4096)
            if prompt_data:
                print(f"[Dialogue] Received prompt from NAO")
                # Generate TinyLlama response using the provided prompt
                llm_response = get_tinyllama_response(prompt_data.decode('utf-8'))
                # Send response back to NAO
                conn.sendall(llm_response.encode('utf-8'))
                conn.close()
                return
        except socket.timeout:
            # No prompt data received, continue with audio recording
            pass
        
        # Reset timeout for normal operation
        conn.settimeout(None)
        
        # Normal flow - record audio and transcribe
        print(f"[Dialogue] Recording audio...")
        recording, fs = speechReco_python3.record_audio(5)
        print(f"[Dialogue] Audio recording complete")
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"audio-{timestamp}.wav"
        data = speechReco_python3.save_audio(recording, fs, filename)
        text = speechReco_python3.transcribe_audio(data)
        print(f"[Dialogue] Transcribed: {text}")
        
        # Send transcribed text back to NAO
        conn.sendall(text.encode('utf-8'))
        
    except Exception as e:
        print(f"[Error] Audio handling error: {str(e)}")
        try:
            # Try to send error message
            conn.sendall("I couldn't understand that.".encode('utf-8'))
        except:
            pass
    finally:
        conn.close()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, AUDIO_PORT))
        s.listen(1)
        print(f"[Dialogue] Listening on port {AUDIO_PORT}...")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_audio, args=(conn, addr)).start()


if __name__ == "__main__":
    # Load TinyLlama model on startup
    print("Initializing TinyLlama model...")
    tinyllama_model, tinyllama_tokenizer, tinyllama_generator = initialize_tinyllama()
    print("TinyLlama model loaded successfully")
    
    threading.Thread(target=start_server).start()
