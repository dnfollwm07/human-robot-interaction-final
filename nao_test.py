import socket
from naoqi import ALProxy
import time
import math

# Connect to NAO
ROBOT_IP = "192.168.1.25"
PORT = 9559

try:
    tts = ALProxy("ALTextToSpeech", ROBOT_IP, PORT)
except Exception as e:
    print("Error creating TTS proxy:", str(e))


# Connect to ZED body tracking server
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("127.0.0.1", 5001))

prev_state = set()

EXHIBIT_MESSAGES = {
    "1": "Exhibit 1 is occupied.",
    "2": "Exhibit 2 is occupied.",
    "3": "Exhibit 3 is occupied."
}

# while True:
#     data = sock.recv(1024).decode().strip()

#     if data:
#         occupied_exhibits = set(data.split(",")) if data != "0" else set()

#         for exhibit_id in occupied_exhibits - prev_state:
#             if exhibit_id in EXHIBIT_MESSAGES:
#                 tts.say(EXHIBIT_MESSAGES[exhibit_id])

#         for exhibit_id in prev_state - occupied_exhibits:
#             tts.say("Thank you for visiting Exhibit" + exhibit_id)

#         prev_state = occupied_exhibits


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


def main():
    result = detect_naomark(ROBOT_IP, PORT)
    if result:
        mark_id, alpha, beta, width, height = result
        move_to_naomark(ROBOT_IP, PORT, alpha, beta, width)

if __name__ == "__main__":
    main()