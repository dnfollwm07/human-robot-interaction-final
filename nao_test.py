import datetime
import os
import socket
import random
import threading
from inaoqi import ALMemoryProxy
from naoqi import ALProxy
import qi
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

attention_records = []

tts = ALProxy("ALTextToSpeech", ROBOT_IP, ROBOT_PORT)
recorder = ALProxy("ALAudioRecorder", ROBOT_IP, ROBOT_PORT)
memory = ALProxy("ALMemory", ROBOT_IP, ROBOT_PORT)
landMarkProxy = ALProxy("ALLandMarkDetection", ROBOT_IP, ROBOT_PORT)
memoryProxy = ALProxy("ALMemory", ROBOT_IP, ROBOT_PORT)
motionProxy = ALProxy("ALMotion", ROBOT_IP, ROBOT_PORT)
postureProxy = ALProxy("ALRobotPosture", ROBOT_IP, ROBOT_PORT)
life = ALProxy("ALAutonomousLife", ROBOT_IP, ROBOT_PORT)
emotion_proxy = ALProxy("ALMood", ROBOT_IP, ROBOT_PORT)
localization = ALProxy("ALLocalization", ROBOT_IP, ROBOT_PORT)
navigation = ALProxy("ALNavigation", ROBOT_IP, ROBOT_PORT)

life.setState("disabled")

DETECTION_PORT = 5001
AUDIO_PORT = 5002

prev_state = set()

EXHIBIT_MESSAGES = {
    "1": "Exhibit 1 is occupied.",
    "2": "Exhibit 2 is occupied.",
    "3": "Exhibit 3 is occupied."
}

occupied_exhibits = ""

detected_exhibit_ids = []
TOTAL_EXHIBIT_IDS = [80, 84]
# Detection for NAOMark ID and give voice feedback
def detect_naomark(robot_ip, port):
    period = 500
    landMarkProxy.subscribe("Test_LandMark", period, 0.0)
    print("Start detecting landmarks...")
    #tts.say("Looking for NAOMarks")

    # Save original head yaw to reset later
    original_head_yaw = motionProxy.getAngles("HeadYaw", True)[0]

    # Define head yaw positions for scanning (side to side)
    head_yaw_positions = [-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0]  # radians

    # Sweep side to side
    for yaw in head_yaw_positions:
        motionProxy.setAngles("HeadYaw", yaw, 0.3)
        motionProxy.setAngles("HeadPitch", 0.0, 0.2)
        time.sleep(1.5)  # Wait for head to reach position
        val = memoryProxy.getData("LandmarkDetected", 0)
        detected_yaw = yaw
        print("detected yaw = ", detected_yaw)

        if val and isinstance(val, list) and len(val) >= 2:
            markInfoArray = val[1]

            for markInfo in markInfoArray:
                markShapeInfo = markInfo[0]
                markExtraInfo = markInfo[1]
                mark_id = markExtraInfo[0]
                # alpha = markShapeInfo[1]
                alpha = detected_yaw
                beta = markShapeInfo[2]
                width = markShapeInfo[3]
                height = markShapeInfo[4]

                print("alpha origin = ", markShapeInfo[1])

                print("mark ID:", mark_id)
                if mark_id not in detected_exhibit_ids and str(mark_id) not in occupied_exhibits:
                    if mark_id == 80 and occupied_exhibits[0] == '0':
                        tts.say("It seems the Van Gogh is empty, let's check it out!")
                    elif mark_id == 84 and occupied_exhibits[1] == '0':
                        tts.say("Why don't we go to the Monet? No one is there. ")
                    detected_exhibit_ids.append(mark_id)
                    landMarkProxy.unsubscribe("Test_LandMark")

                    # Reset head position
                    motionProxy.setAngles("HeadYaw", original_head_yaw, 0.2)
                    return mark_id, alpha, beta, width, height

    landMarkProxy.unsubscribe("Test_LandMark")
    #tts.say("Time out, please try again")
    print("Landmark detection timed out.")

    # Reset head position
    motionProxy.setAngles("HeadYaw", original_head_yaw, 0.2)
    return None

def move_to_naomark(robot_ip, port, alpha, beta, width):
    real_mark_size = 0.1  # meter
    distance = real_mark_size / width

    motion = ALProxy("ALMotion", robot_ip, port)
    motion.wakeUp()

    start_pos = motion.getRobotPosition(False)

    motion.moveTo(0,0,alpha)
    x = distance * math.cos(beta) * math.cos(alpha)
    # y = distance * math.cos(beta) * math.sin(alpha)
    # theta = math.atan2(y, x)
    y = 0
    theta = 0
    print(x, y, theta)
    frequency = 0.1

    time.sleep(3)

    motion.moveTo(x * 0.6, y, theta)#, [["Frequency", frequency]])

    '''while True:
        current_pos = motion.getRobotPosition(False)
        dx = current_pos[0] - start_pos[0]
        dy = current_pos[1] - start_pos[1]
        dist = math.hypot(dx, dy)
        if dist >= 0.4:
            break'''
    time.sleep(0.1)

    motion.stopMove()
    print("Reached near the naomark.")
    
    
# detect different naomark id and give different introduction for this exhibit
def introduction_markid(mark_id):
    # banana


    if mark_id == 84:
        tts.say("This painting is part of Claude Monet's Water Lilies series, created between 1897 and 1926. It captures the surface of a pond in his garden at Giverny, focusing on water lilies, reflections, and the shifting effects of light. Monet painted outdoors to observe how color changed throughout the day. The absence of a horizon or human presence emphasizes the immersive and abstract quality of the scene.")

    # grape
    elif mark_id == 80:
        tts.say("The Starry Night was painted by Vincent van Gogh in June 1889 while he was staying at an asylum in Saint-Remy-de-Provence. It depicts a swirling night sky over a quiet village, with exaggerated forms and vibrant colors. The painting reflects Van Gogh's emotional state and his unique use of brushwork and color. It was based not on a direct view, but a combination of memory and imagination!")

    life.setState("solitary")
    time.sleep(2)
    # valence, attention = tracker_face(ROBOT_IP, ROBOT_PORT)
    # return attention

# listens for metadata from python3main.py to see if any exhibits are occupied
def listen_for_exhibit_status():
    tts.post.say("Let's see if any exhibits are empty...")
    s = socket.socket()
    s.connect(("localhost", DETECTION_PORT))
    ret = s.recv(1024) # A string of n ints where n= # of exhibits; e.g. data[0]="0" means the first exhibit is not occupied
    print("[Metadata] Received:", ret)
    s.close()
    return ret


# Get response from LLaMA model with conversation history
def get_llm_response(user_input, mark_id):
    try:
        # Prepare the prompt with conversation history and role
        system_prompt = """You are a museum guide robot interacting with a human visitor.

            Behavior Rules:
            - Only respond with information about the artwork listed below.
            - Do NOT mention any artworks, locations, or artists not listed.
            - Do NOT create anything fictional or speculate.
            - Answer directly and concisely. Keep it factual and on-topic.
            - Use a neutral, professional tone - avoid overly friendly or emotional responses.
            - Do NOT say "Guide:" or narrate your own actions.
            - Do NOT greet or say goodbye unless specifically asked.
            - Respond with plain text and form a paragraph. 
            - Do NOT use special/unicode characters in your response.
        """

        if mark_id == 80:
            system_prompt += """
                Exhibit: *The Starry Night* by Vincent van Gogh  
                - Painted in June 1889  
                - Oil on canvas  
                - Painted while Van Gogh was in an asylum in Saint-Remy-de-Provence  
                - Features a swirling night sky over a quiet village with a cypress tree  
                - Known for dynamic brushstrokes and vibrant blue-and-yellow contrast  
                - Painted from memory, not direct observation
            """
        elif mark_id == 84:
            system_prompt += """
                Exhibit: *Water Lilies* by Claude Monet  
                - A series of around 250 paintings created between 1897 and 1926  
                - Depicts Monet's flower garden in Giverny, especially the pond and its water lilies  
                - Painted outdoors to capture natural light and color changes throughout the day  
                - Known for soft, layered brushstrokes and a dreamy, abstracted sense of reflection  
                - No human figures are present - focus is entirely on water, light, and nature  
            """

        # Format the current prompt only, without conversation history
        full_prompt = system_prompt + "\n\nVisitor: " + user_input + "\nGuide:"

        data = {
            "prompt": full_prompt,
            "n_predict": 250,  # Increased to allow for longer responses
            "temperature": 0.7,
            "top_k": 10,
            "top_p": 0.8,
            "stop": ["\nVisitor:", "\n\nVisitor:"]  # Stop generation when these patterns are detected
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
            print(response_text, type(response_text))
            return str(response_text)
        else:
            return "I'm sorry, I couldn't process your request properly."

    except Exception as e:
        print("Error getting LLM response: " + str(e))
        return "I'm sorry, I'm having trouble processing your request right now."

def listen_for_human_response():
    # Listening for reply from handle_audio
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("localhost", AUDIO_PORT))
    response = s.recv(1024) # perhaps 1024 bytes is not enough for text from the llm
    print("[Dialogue] Response:", response)
    tts.post.say("Hmm, let me think...")
    s.close()
    return response

def tracker_face(robot_ip, port, tracking_duration=10):
    # Save original head positions to reset later
    original_head_yaw = motionProxy.getAngles("HeadYaw", True)[0]
    original_head_pitch = motionProxy.getAngles("HeadPitch", True)[0]
    
    valence = 0.0
    attention = 0.0
    tracker = ALProxy("ALTracker", robot_ip, port)
    motion = ALProxy("ALMotion", robot_ip, port)

    # Define head scanning positions
    head_yaw_positions = [-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0]  # radians
    head_pitch_positions = [-0.5, -0.25, 0.0]  # radians, looking slightly up to straight

    motion.setStiffnesses("Head", 1.0)
    tracker.registerTarget("Face", 0.1)
    print("Starting face scan...")
    
    # Scan for faces by moving head
    face_detected = False
    for pitch in head_pitch_positions:
        if face_detected:
            break
        for yaw in head_yaw_positions:
            motion.setAngles("HeadYaw", yaw, 0.3)
            motion.setAngles("HeadPitch", pitch, 0.2)
            time.sleep(1.0)  # Wait for head to reach position
            
            # Check if face is detected
            if not tracker.isTargetLost():
                print("Face detected at yaw:", yaw, "pitch:", pitch)
                face_detected = True
                break
    
    # If no face detected after scanning
    if not face_detected:
        print("No face detected during scan")
        tracker.stopTracker()
        tracker.unregisterAllTargets()
        # Reset head position
        motion.setAngles("HeadYaw", original_head_yaw, 0.2)
        motion.setAngles("HeadPitch", original_head_pitch, 0.2)
        motion.setStiffnesses("Head", 0.0)
        return valence, attention
    
    # Start tracking the detected face
    tracker.track("Face")
    print("Start tracking face")

    try:
        while True:
            time.sleep(1)
            if tracker.isNewTargetDetected():
                #tts.say("New target detected")
                emotion_data = emotion_proxy.currentPersonState()  # dict
                valence = emotion_data[0][1][0][1]
                attention = emotion_data[1][1][0][1]
                print("Valence:", valence, "Attention:", attention)
                break

    except KeyboardInterrupt:
        print("Stopping...")

    tracker.stopTracker()
    tracker.unregisterAllTargets()
    print("Stop tracking")
    
    return valence, attention

# Function to continuously monitor person's state
def continuous_monitor_state(stop_event, attention_list):
    tracker = ALProxy("ALTracker", ROBOT_IP, ROBOT_PORT)
    try:
        tracker.registerTarget("Face", 0.1)
        tracker.track("Face")
        print("Continuous tracking started")
        
        while not stop_event.is_set():
            try:
                if not tracker.isTargetLost():
                    emotion_data = emotion_proxy.currentPersonState()
                    valence = emotion_data[0][1][0][1]
                    attention = emotion_data[1][1][0][1]
                    attention_list.append(attention)
                    print(f"Continuous monitoring - Valence: {valence}, Attention: {attention}")
                    attention_records.append(str(datetime.datetime.now()) + ": " + str(attention))
                time.sleep(5)  # Wait for 5 seconds before next check
            except Exception as e:
                print(f"Error in continuous monitoring: {e}")
                time.sleep(5)  # Continue even if there's an error
                
    except Exception as e:
        print(f"Error setting up continuous monitoring: {e}")
    finally:
        try:
            tracker.stopTracker()
            tracker.unregisterAllTargets()
            print("Continuous tracking stopped")
        except:
            pass

def set_home_position():
    life.setState("solitary")
    localization.learnHome()
    life.setState("disabled")
    time.sleep(1)
    try:
        current_pose = localization.getRobotPosition(False)
        memory.insertData("HomePosition", current_pose)
        print("Home position set to:", current_pose)
        return True
    except Exception as e:
        print("Error setting home position:", e)
        return False

def navigate_to_home():
    """Navigate the robot back to its home position."""
    try:
        print("Navigating to home position...")
        localization.goToHome()
        return True
    except Exception as e:
        print("Error navigating to home position:", e)
        return False


def main():
    # Initialize Location
    
    time.sleep(2)
    set_home_position()
    
    global occupied_exhibits
    tts.say("Hello and welcome to my museum! Allow me to show you around!")
    motionProxy.wakeUp()
    while True:
        occupied_exhibits = listen_for_exhibit_status()

        # Step 1: Scan for NAO mark
        result = detect_naomark(ROBOT_IP, ROBOT_PORT)
        if not result:
            print("No NAO mark detected. Please try again.")
            continue
            
        # Step 2: Move to the detected NAO mark
        mark_id, alpha, beta, width, height = result
        move_to_naomark(ROBOT_IP, ROBOT_PORT, alpha, beta, width)
        
        # Step 3: Give introduction
        motionProxy.moveTo(0, 0, 3.14)
        
        # Start continuous monitoring in a separate thread
        stop_monitoring = threading.Event()
        attention_measurements = []
        monitor_thread = threading.Thread(
            target=continuous_monitor_state, 
            args=(stop_monitoring, attention_measurements)
        )
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Initial introduction and attention measurement
        introduction_markid(mark_id)        

        # Respond based on attention level
        if attention >= 0.1:
            tts.say("You look quite interested in this exhibit! Let me share more history with you.")
            if mark_id == 80:
                tts.say("The Starry Night shows Van Gogh's early move toward expressionism, using bold forms to "
                        "convey emotion rather than realism. The cypress tree, not seen from his window, "
                        "was added from imagination and often symbolizes eternity. Though now iconic, Van Gogh didn't "
                        "think highly of the painting and called it a 'failure' in a letter to his brother.")
            elif mark_id == 84:
                tts.say(
                    "Monet's Water Lilies were part of a grand vision. He saw them as a peaceful refuge and arranged "
                    "their display in a specially designed oval room in Paris. Despite cataracts, which may have "
                    "influenced the dreamy, blurred forms, he kept painting. Some panels stretch over six feet, immersing "
                    "viewers in water and light.")

        elif -0.1 <= attention < 0.1:
            tts.say("You seem a bit indifferent. That's okay! Feel free to ask any questions about this painting.")

        else:
            tts.say(
                "You don't look very interested.")

        tts.say("Say 'move on' to go to the next exhibit, or 'end' to wrap the whole visit up.")
        # Start interactive Q&A loop
        end = False
        move = False
        trial = 0

        while trial < 5:
            user_input = listen_for_human_response().decode("utf-8").strip()

            if "end" in user_input.lower().split():
                end = True
                break
            elif "move on" in user_input.lower():
                move = True
                break
            else:
                response = get_llm_response(user_input, mark_id)
                tts.say(response)

                trial += 1
                if trial < 5:
                    tts.say("Any more questions?"
                            "Say 'move on' to go to the next exhibit, or 'end' to wrap the whole visit up.")

        valence, attention = tracker_face(ROBOT_IP, ROBOT_PORT)
        attention_records.append(str(datetime.datetime.now()) + ": " + str(attention))

        # Handle post-interaction decision
        if move:
             # Stop monitoring
            stop_monitoring.set()
            monitor_thread.join(timeout=2)
            # print(attention_records)
            
            # # Calculate average attention if we have measurements
            # if attention_measurements:
            #     avg_attention = sum(attention_measurements) / len(attention_measurements)
            #     print(f"Average attention during introduction: {avg_attention}")
            #     attention = avg_attention
            navigate_to_home()
            if len(detected_exhibit_ids) == len(TOTAL_EXHIBIT_IDS):
                tts.say("You've now seen everything in the museum. I hope you enjoyed your visit!")
                return
        elif end:
             # Stop monitoring
            stop_monitoring.set()
            monitor_thread.join(timeout=2)
            # print(attention_records)
            
            # # Calculate average attention if we have measurements
            # if attention_measurements:
            #     avg_attention = sum(attention_measurements) / len(attention_measurements)
            #     print(f"Average attention during introduction: {avg_attention}")
            #     attention = avg_attention
            tts.say("Thanks for your visit today! Have a wonderful day.")
            navigate_to_home()
            return


if __name__ == "__main__":
    main()
    print(attention_records)
