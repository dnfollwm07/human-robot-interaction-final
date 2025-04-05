from naoqi import ALProxy
import time
import qi
import argparse
import sys
import math

ROBOT_IP = "192.168.1.25"
PORT = 9559

tts= ALProxy("ALTextToSpeech", ROBOT_IP, PORT)
tts.say("Hello!")


# Create a proxy to ALLandMarkDetection
try:
  landMarkProxy = ALProxy("ALLandMarkDetection", ROBOT_IP, PORT)
except Exception as e:
  print("Error when creating landmark detection proxy:") 
  print(str(e)) 
  exit(1)

# Subscribe to the ALLandMarkDetection proxy
# This means that the module will write in ALMemory with
# the given period below
period = 500
landMarkProxy.subscribe("Test_LandMark", period, 0.0 )

# ALMemory variable where the ALLandMarkdetection module
# outputs its results
memValue = "LandmarkDetected"

# Create a proxy to ALMemory
try:
  memoryProxy = ALProxy("ALMemory", ROBOT_IP, PORT)
except Exception as e:
  print("Error when creating memory proxy:") 
  print(str(e))
  exit(1)

print("Creating landmark detection proxy")

# A simple loop that reads the memValue and checks
# whether landmarks are detected.
for i in range(0, 20):
  time.sleep(0.5)
  val = memoryProxy.getData(memValue, 0)
  print("") 
  print("\*****") 
  print("") 
# Check whether we got a valid output: a list with two fields.
if(val and isinstance(val, list) and len(val) >= 2):
  # We detected landmarks !
  # For each mark, we can read its shape info and ID.
  # First Field = TimeStamp.
  timeStamp = val[0]
  # Second Field = array of Mark_Info's.
  markInfoArray = val[1]

  try:
    # Browse the markInfoArray to get info on each detected mark.
    for markInfo in markInfoArray:
      # First Field = Shape info.
      markShapeInfo = markInfo[0]
      # Second Field = Extra info (i.e., mark ID).
      markExtraInfo = markInfo[1]
      # Print Mark information.
      print("mark  ID: %d" % (markExtraInfo[0])) 
      tts.say("detected naomark id is:")
      tts.say(str(markExtraInfo[0]))
      print("  alpha %.3f - beta %.3f" % (markShapeInfo[1], markShapeInfo[2])) 
      print( "  width %.3f - height %.3f" % (markShapeInfo[3], markShapeInfo[4]))

      #store the info to calculate the distance
      alpha = markShapeInfo[1]
      beta = markShapeInfo[2]
      width = markShapeInfo[3]
      height = markShapeInfo[4]
  except Exception as e:
      print("Landmarks detected, but it seems getData is invalid. ALValue =") 
      print(val)
      print("Error msg %s" % (str(e)))
else:
  print("Error with getData. ALValue = %s" % (str(val))) 
  tts.say("time out, please try again")

# Unsubscribe from the module.
landMarkProxy.unsubscribe("Test_LandMark")
print("Test terminated successfully.") 

#calculate for walk
real_mark_size = 0.1
distance =  real_mark_size / width

motion = ALProxy("ALMotion",  ROBOT_IP, PORT)
motion.wakeUp()

start_pos = motion.getRobotPosition(False)

x = distance * math.cos(beta) * math.cos(alpha)
y = distance * math.cos(beta) * math.sin(alpha)
theta = 0.0
frequency = 0.1 #move max pace
motion.moveToward(x, y, theta,[["Frequency", frequency]])

while True:
  current_pos = motion.getRobotPosition(False)
  dx = current_pos[0] - start_pos[0]
  dy = current_pos[1] - start_pos[1]
  dist = math.hypot(dx,dy)
  if dist>=0.3:
    break
  time.sleep(0.1)

motion.stopMove()


##### move

# motion = ALProxy("ALMotion",  ROBOT_IP, PORT)

# motion.wakeUp()

# x = 0.5 #x-axis max pace
# y = 0.0
# theta = 0.0
# frequency = 0.2 #move max pace
# motion.moveToward(x, y, theta,[["Frequency", frequency]])

# time.sleep(18)
# motion.stopMove() #after whole program for eight seconds, it would stop

#motion.rest()