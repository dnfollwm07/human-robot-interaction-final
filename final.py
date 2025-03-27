from naoqi import ALProxy
import time
import json
from typing import List, Dict, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmotionState:
    NEUTRAL = "neutral"
    EXCITED = "excited"
    CONFUSED = "confused"

class Exhibit(object):
    def __init__(self, id, x, y, theta, description, detailed_description, popularity=0.0, visited=False):
        self.id = id
        self.x = x
        self.y = y
        self.theta = theta
        self.description = description
        self.detailed_description = detailed_description
        self.popularity = popularity
        self.visited = visited

class MuseumGuide:
    def __init__(self, robot_ip, port):
        self.robot_ip = robot_ip
        self.port = port
        self.exhibits = self._initialize_exhibits()
        self.visited_exhibits = set()
        self.current_emotion = EmotionState.NEUTRAL
        self._initialize_proxies()
        
    def _initialize_proxies(self):
        self.motion = ALProxy("ALMotion", self.robot_ip, self.port)
        self.tts = ALProxy("ALTextToSpeech", self.robot_ip, self.port)
        self.localization = ALProxy("ALLocalization", self.robot_ip, self.port)
        self.people_perception = ALProxy("ALPeoplePerception", self.robot_ip, self.port)
        self.speech_recognition = ALProxy("ALSpeechRecognition", self.robot_ip, self.port)
        self.memory = ALProxy("ALMemory", self.robot_ip, self.port)
        
    def _initialize_exhibits(self):
        """Initialize exhibit data"""
        return [
            Exhibit(
                1, 0.5, 0.0, 0.0,
                "Welcome to Exhibit 1.",
                "This exhibit showcases ancient artifacts..."
            ),
            Exhibit(
                2, 0.25, 0.43, 1.05,
                "This is Exhibit 2.",
                "Here we have a collection of medieval paintings..."
            ),
            # ... Add more exhibits
        ]

    def learn_environment(self):
        """Learn and save the initial position"""
        try:
            self.motion.wakeUp()
            loc_status = self.localization.learnHome()
            
            if loc_status == 0:
                logger.info("Home position learned successfully")
                self.localization.save("home_position")
                return True
            else:
                logger.error("Failed to learn home position. Error:" + str(loc_status))
                return False
        except Exception as e:
            logger.error("Error learning environment:" + e)
            return False

    def detect_emotion(self):
        """Detect visitor's emotion"""
        # TODO: Implement actual emotion detection
        return EmotionState.NEUTRAL

    def adjust_explanation(self, exhibit):
        """Detect visitor's emotion, add more details to descriptions according to the emotion"""
        base_description = exhibit.description
        return base_description

    def check_exhibit_occupancy(self, exhibit):
        """Check with external camera"""
        return False

    def go_to_exhibit(self, exhibit_id):
        """Navigate to a specific exhibit"""
        exhibit = next((e for e in self.exhibits if e.id == exhibit_id), None)
        
        if self.check_exhibit_occupancy(exhibit):
            self.suggest_alternative_exhibit(exhibit_id)
            return False

        try:
            self.motion.moveTo(exhibit.x, exhibit.y, exhibit.theta)
            self.motion.waitUntilMoveIsFinished()
            
            # Update emotion and adjust explanation
            self.current_emotion = self.detect_emotion()
            explanation = self.adjust_explanation(exhibit)
            
            self.tts.say(explanation)
            self.visited_exhibits.add(exhibit_id)
            exhibit.visited = True
            
            return True
        except Exception as e:
            logger.error("Error navigating to exhibit:" + e)
            return False

    def suggest_alternative_exhibit(self, current_exhibit_id):
        """Suggest an alternative exhibit when the requested one is occupied"""
        self.tts.say("This exhibit is currently busy. Would you like to visit another exhibit?")
        # TODO: Implement smart exhibit suggestion based on popularity and distance

    def return_to_home(self):
        """Return to the initial position"""
        try:
            self.localization.goToHome()
            return True
        except Exception as e:
            logger.error("Error returning to home:" + e)
            return False

    def collect_feedback(self):
        """Collect visitor feedback about the tour"""
        # TODO: Implement feedback collection mechanism
        pass

    def save_tour_data(self):
        """Save tour data for analysis"""
        tour_data = {}
        try:
            with open("tour_data.json", "a") as f:
                json.dump(tour_data, f)
        except Exception as e:
            logger.error("Error saving tour data" + e)

def main():
    ROBOT_IP = "192.168.1.25"
    PORT = 9559

    guide = MuseumGuide(ROBOT_IP, PORT)
    
    if not guide.learn_environment():
        logger.error("Failed to learn environment")
        # return

    # Example tour sequence
    try:
        for exhibit in guide.exhibits:
            guide.go_to_exhibit(exhibit.id)
            time.sleep(2)  # Wait between exhibits
        
        guide.return_to_home()
        guide.save_tour_data()
    except Exception as e:
        logger.error("Error during tour:" + e)
        guide.return_to_home()

if __name__ == "__main__":
    main()
