import os
import socket

from inaoqi import ALMemoryProxy
from naoqi import ALProxy
import time
import math
import sys
import threading

# Connect to NAO
ROBOT_IP = "192.168.1.25"
ROBOT_PORT = 9559
FILENAME = "/home/nao/recordings/interaction.wav"

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
    tts.say(response)
    s.close()

listen_for_human_response(3, FILENAME)

#threading.Thread(target=listen_for_exhibit_status()).start()
#threading.Thread(target=listen_for_human_response(3, FILENAME)).start()
"""
result = detect_naomark(ROBOT_IP, ROBOT_PORT)
if result:
    mark_id, alpha, beta, width, height = result
    move_to_naomark(ROBOT_IP, ROBOT_PORT, alpha, beta, width)"""