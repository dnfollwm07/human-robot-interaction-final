import os
import socket

from inaoqi import ALMemoryProxy
from naoqi import ALProxy
import time
import math
import sys
import threading
import requests
import json

# Connect to NAO
ROBOT_IP = "192.168.1.25"
ROBOT_PORT = 9559
FILENAME = "/home/nao/recordings/interaction.wav"

# LLaMA service configuration
LLAMA_URL = "http://192.168.1.22:8080/completion"  # TODO: @Liam change to your IP address
LLAMA_HEADERS = {"Content-Type": "application/json"}

# Store conversation history
conversation_history = []

tts = ALProxy("ALTextToSpeech", ROBOT_IP, ROBOT_PORT)
recorder = ALProxy("ALAudioRecorder", ROBOT_IP, ROBOT_PORT)
memory = ALProxy("ALMemory", ROBOT_IP, ROBOT_PORT)

DETECTION_PORT = 5001
AUDIO_PORT = 5002

prev_state = set()

EXHIBIT_MESSAGES = {
    "1": "Exhibit 1 is occupied.",
    "2": "Exhibit 2 is occupied.",
    "3": "Exhibit 3 is occupied."
}


# Detection for NAOMark ID and give voice feedback
def detect_naomark(robot_ip, port):

    # Create a proxy to ALLandMarkDetection and ALMemory
    try:
        landMarkProxy = ALProxy("ALLandMarkDetection", robot_ip, port)
        memoryProxy = ALProxy("ALMemory", robot_ip, port)
    except Exception as e:
        print("Proxy creation error:", str(e))
        return None

    # Subscribe to the ALLandMarkDetection proxy
    # This means that the module will write in ALMemory with
    # the given period below
    period = 500
    landMarkProxy.subscribe("Test_LandMark", period, 0.0)

    # ALMemory variable where the ALLandMarkdetection module
    # outputs its results
    memValue = "LandmarkDetected"
    print("Start detecting landmarks...")

    # A simple loop that reads the memValue and checks
    # whether landmarks are detected.
    for i in range(20):
        time.sleep(0.5)
        val = memoryProxy.getData(memValue, 0)

        # Check whether we got a valid output: a list with two fields.
        if val and isinstance(val, list) and len(val) >= 2:
            #array of Mark_Info's.
            markInfoArray = val[1]

            # Browse the markInfoArray to get info on each detected mark. Store the info to calculate the distance
            for markInfo in markInfoArray:
                markShapeInfo = markInfo[0]
                markExtraInfo = markInfo[1]
                mark_id = markExtraInfo[0]
                alpha = markShapeInfo[1]
                beta = markShapeInfo[2]
                width = markShapeInfo[3]
                height = markShapeInfo[4]

                print("mark ID:", mark_id)
                tts.say("Detected naomark ID is:")
                tts.say(str(mark_id))

                # Unsubscribe from the module.
                landMarkProxy.unsubscribe("Test_LandMark")
                return mark_id, alpha, beta, width, height

    landMarkProxy.unsubscribe("Test_LandMark")
    print("Landmark detection timed out.")
    tts.say("Time out, please try again")
    return None


def move_to_naomark(robot_ip, port, alpha, beta, width):
    real_mark_size = 0.1  # meter
    distance = real_mark_size / width

    motion = ALProxy("ALMotion", robot_ip, port)
    motion.wakeUp()

    start_pos = motion.getRobotPosition(False)

    x = distance * math.cos(beta) * math.cos(alpha)
    y = distance * math.cos(beta) * math.sin(alpha)
    theta = 0.0
    frequency = 0.1

    motion.moveToward(x, y, theta, [["Frequency", frequency]])

    while True:
        current_pos = motion.getRobotPosition(False)
        dx = current_pos[0] - start_pos[0]
        dy = current_pos[1] - start_pos[1]
        dist = math.hypot(dx, dy)
        if dist >= 0.3:
            break
        time.sleep(0.1)

    motion.stopMove()
    print("Reached near the naomark.")

# listens for metadata from python3main.py to see if any exhibits are occupied
def listen_for_exhibit_status():
    s = socket.socket()
    s.bind(('0.0.0.0', DETECTION_PORT))
    s.listen(1)
    print("[Metadata] Listening on port", DETECTION_PORT)
    conn, addr = s.accept()
    with conn:
        print("[Metadata] Connected from", addr)
        data = conn.recv(1024) # Maybe a string of n ints where n= # of exhibits; e.g. data[0]="0" means the first exhibit is not occupied
        print("[Metadata] Received:", data)

# Get response from LLaMA model with conversation history
def get_llm_response(user_input):
    try:
        # Prepare the prompt with conversation history and role
        system_prompt = """
        You are MIRA, a friendly and whimsical museum tour guide robot at the Museum of Forgotten Realms, where everyday-looking objects hide fantastical stories.

        Your job is to:
        1. Introduce exhibits with imagination and charm
        2. Answer visitors' questions about the museum
        3. Guide them through exhibits interactively
        4. Remain professional, engaging, and in character

        Tone:
        - Vivid, theatrical, and slightly mysterious
        - Speak like a storyteller, especially to kids and curious minds
        - Never reveal that items are fake or plastic
        - Occasionally ask imaginative questions to spark engagement

        Current Exhibit: "Fruits of the Forgotten Realms"

        Exhibit 1: The Golden Whisper (“Banana of the Laughing Forest”)
        - A sacred fruit flute resembling a banana from a mythical forest
        - Said to play melodies on full moons and awaken old memories

        Exhibit 2: The Amethyst Core (“Grape Crystal Seed”)
        - A telepathic crystal resembling grapes from a distant planet
        - Reacts to emotions, especially from children

        Stay in character. A visitor is approaching with a question or request.
        """
        
        # Format conversation history
        history_text = ""
        for i, (role, content) in enumerate(conversation_history):
            if role == "user":
                history_text += f"Visitor: {content}\n"
            else:
                history_text += f"Guide: {content}\n"
        
        # Combine system prompt, history and current input
        full_prompt = f"{system_prompt}\n\nPrevious conversation:\n{history_text}\n\nVisitor: {user_input}\nGuide:"
        
        data = {
            "prompt": full_prompt,
            "n_predict": 50,
            "temperature": 0.7,
            "top_k": 10,
            "top_p": 0.8
        }
        
        # Send request to LLaMA
        response = requests.post(LLAMA_URL, headers=LLAMA_HEADERS, data=json.dumps(data))
        llama_response = response.json()
        
        if 'content' in llama_response:
            response_text = llama_response['content'].strip()
            
            # Update conversation history
            conversation_history.append(("user", user_input))
            conversation_history.append(("assistant", response_text))
            
            # Keep only last 5 exchanges to manage context length
            if len(conversation_history) > 10:  # 5 exchanges (user + assistant)
                conversation_history.pop(0)
                conversation_history.pop(0)
            
            return response_text
        else:
            return "I'm sorry, I couldn't process your request properly."
            
    except Exception as e:
        print(f"Error getting LLM response: {str(e)}")
        return "I'm sorry, I'm having trouble processing your request right now."

def listen_for_human_response(time_to_wait, filename):
    '''try:
        print("Recording audio...")
        recorder.startMicrophonesRecording(filename, "wav", 16000, (1, 0, 0, 0))
        time.sleep(time_to_wait)
        recorder.stopMicrophonesRecording()
        print("Audio recorded!")
        print(memory.getDataListName())
        memory.insertData("AudioRecording/lastfile", filename)
    except Exception as e:
        print("Error saving audio file: " + str(e))
        sys.exit(1)
    audio_data = memory.getData("AudioRecording/lastfile")
    print(audio_data)

    # receiving signal from start_server
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", AUDIO_PORT))
    s.sendall(audio_data) # send to the data var in handle_audio
    s.shutdown(socket.SHUT_WR)'''

    # Listening for reply from handle_audio
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", AUDIO_PORT))
    response = s.recv(1024) # perhaps 1024 bytes is not enough for text from the llm
    print("[Dialogue] Response:", response)
    
    # Get LLM response
    llm_response = get_llm_response(response.decode('utf-8'))
    print("[Dialogue] LLM Response:", llm_response)
    
    # Speak the response
    tts.say(llm_response)
    s.close()

listen_for_human_response(3, FILENAME)

#threading.Thread(target=listen_for_exhibit_status()).start()
#threading.Thread(target=listen_for_human_response(3, FILENAME)).start()
"""
result = detect_naomark(ROBOT_IP, ROBOT_PORT)
if result:
    mark_id, alpha, beta, width, height = result
    move_to_naomark(ROBOT_IP, ROBOT_PORT, alpha, beta, width)"""