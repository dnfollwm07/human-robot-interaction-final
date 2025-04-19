from naoqi import ALProxy
import time

ROBOT_IP = "192.168.1.25"
ROBOT_PORT = 9559

def emotion_engagement(robot_ip,robot_port):
    try:
        tts = ALProxy("ALTextToSpeech", robot_ip, robot_port)
        emotion_proxy = ALProxy("ALMood", ROBOT_IP, robot_port)

        tts.say("Detecting valence level...")
        emotion_data = emotion_proxy.currentPersonState()  # dict
        valence = emotion_data[0][1][0][1]
        tts.say("Current valence level: " + str(valence))

    except Exception, e:
        print("error in emotion:", str(e))


def tracker_face(robot_ip, port, tracking_duration=10):
    try:
        tracker = ALProxy("ALTracker", robot_ip, port)
        motion = ALProxy("ALMotion", robot_ip, port)
        tts = ALProxy("ALTextToSpeech", robot_ip, port)

        motion.wakeUp()
        motion.setAngles("HeadPitch", -0.5, 0.2)
        tracker.registerTarget("Face", 0.1)
        motion.setStiffnesses("Head",1.0)

        tracker.track("Face")
        print("start tracking")



        try:
            while True:
                time.sleep(1)
                if tracker.isNewTargetDetected():
                    tts.say("new target detected")
                emotion_engagement(robot_ip, port)
        except KeyboardInterrupt:
            print
            print "Interrupted by user"
            print "Stopping..."

        tracker.stopTracker()
        tracker.unregisterAllTargets()
        motion.rest()
        print("stop tracking")

        motion.setStiffnesses("Head",0.0)

    except Exception, e:
        print("error: ", str(e))


def main():
    tracker_face(ROBOT_IP, ROBOT_PORT, 10)

if __name__ == '__main__':
    main()

