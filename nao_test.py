import socket
from naoqi import ALProxy

# Connect to NAO
NAO_IP = "192.168.1.25"  # Replace with your NAO’s IP
tts = ALProxy("ALTextToSpeech", NAO_IP, 9559)

# Connect to ZED body tracking server
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("127.0.0.1", 5001))

prev_state = set()

EXHIBIT_MESSAGES = {
    "1": "Exhibit 1 is occupied.",
    "2": "Exhibit 2 is occupied.",
    "3": "Exhibit 3 is occupied."
}

while True:
    data = sock.recv(1024).decode().strip()

    if data:
        occupied_exhibits = set(data.split(",")) if data != "0" else set()

        for exhibit_id in occupied_exhibits - prev_state:
            if exhibit_id in EXHIBIT_MESSAGES:
                tts.say(EXHIBIT_MESSAGES[exhibit_id])

        for exhibit_id in prev_state - occupied_exhibits:
            tts.say(f"Thank you for visiting Exhibit {exhibit_id}.")

        prev_state = occupied_exhibits
