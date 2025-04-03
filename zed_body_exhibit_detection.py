import socket
import pyzed.sl as sl

# Setup socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(("127.0.0.1", 5001))
sock.listen(1)
print("Waiting for NAO client...")
conn, addr = sock.accept()
print("NAO client connected!")

# Initialize ZED camera
zed = sl.Camera()
init_params = sl.InitParameters()
if zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
    exit(1)


# Define exhibit zones (X-axis positions in camera space)
EXHIBIT_ZONES = {
    1: (-2.0, -1.0),  # Exhibit 1 (left side)
    2: (-1.0, 0.5),   # Exhibit 2 (middle)
    3: (0.5, 2.0)     # Exhibit 3 (right side)
}

# Capture 50 frames and stop
i = 0
image = sl.Mat()
runtime_parameters = sl.RuntimeParameters()
while i < 50:
    # Grab an image, a RuntimeParameters object must be given to grab()
    if zed.grab(runtime_parameters) == sl.ERROR_CODE.SUCCESS:
        # A new image is available if grab() returns ERROR_CODE.SUCCESS
        zed.retrieve_image(image, sl.VIEW.LEFT) # Get the left image
        timestamp = zed.get_timestamp(sl.TIME_REFERENCE.IMAGE)  # Get the image timestamp
        i = i + 1


        # Send occupied exhibits to NAO
        message = ",".join(map(str, occupied_exhibits)).encode() if occupied_exhibits else b"0"
        conn.sendall(message)
