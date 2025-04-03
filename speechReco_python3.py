# using whisper on python3

import sounddevice as sd
from scipy.io.wavfile import write
import whisper
import os
import sys
import torch

def record_audio(seconds=3, fs=16000):  # Reduce recording time and sampling rate
    try:
        print("Starting recording...")
        recording = sd.rec(int(seconds * fs), samplerate=fs, channels=1, dtype="int16")
        sd.wait()  # Wait for recording to complete
        return recording, fs
    except Exception as e:
        print(f"Error during recording: {str(e)}")
        sys.exit(1)

def save_audio(recording, fs, filename="output.wav"):
    try:
        write(filename, fs, recording)
        print(f"Recording completed, saved as {filename}")
        return filename
    except Exception as e:
        print(f"Error saving audio file: {str(e)}")
        sys.exit(1)

def transcribe_audio(audio_file):
    try:
        print("Loading Whisper model...")
        # Check if GPU is available
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")
        
        model = whisper.load_model("tiny", device=device)
        print("Converting speech to text...")
        result = model.transcribe(audio_file, language="en")  # Specify English language for better accuracy
        return result["text"]
    except Exception as e:
        print(f"Error during speech conversion: {str(e)}")
        sys.exit(1)

def main():
    # Recording settings
    fs = 16000  # Lower sampling rate to 16kHz
    seconds = 3  # TODO: Set recording time
    audio_filename = "output.wav"

    # Record and save audio
    recording, fs = record_audio(seconds, fs)
    audio_file = save_audio(recording, fs, audio_filename)

    # Convert speech to text
    text = transcribe_audio(audio_file)
    print("\nConversion result:")
    print(text)

if __name__ == "__main__":
    main()
