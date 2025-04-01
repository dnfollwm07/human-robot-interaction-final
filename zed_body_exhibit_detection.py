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

# Enable body tracking
body_param = sl.BodyTrackingParameters()
body_param.enable_body_fitting = True
body_runtime_param = sl.BodyTrackingRuntimeParameters()
obj_runtime_param = sl.ObjectDetectionRuntimeParameters()

zed.enable_body_tracking(body_param)
bodies = sl.Bodies()

# Define exhibit zones (X-axis positions in camera space)
EXHIBIT_ZONES = {
    1: (-2.0, -1.0),  # Exhibit 1 (left side)
    2: (-1.0, 0.5),   # Exhibit 2 (middle)
    3: (0.5, 2.0)     # Exhibit 3 (right side)
}

while True:
    if zed.grab() == sl.ERROR_CODE.SUCCESS:
        zed.retrieve_bodies(bodies, body_runtime_param)
        occupied_exhibits = set()

        for body in bodies.body_list:
            x_pos = body.position[0]  # X-coordinate in world space

            # Check which exhibit the person is in
            for exhibit_id, (xmin, xmax) in EXHIBIT_ZONES.items():
                if xmin < x_pos < xmax:
                    occupied_exhibits.add(exhibit_id)

        # Send occupied exhibits to NAO
        conn.sendall(",".join(map(str, occupied_exhibits)).encode() or "0")

