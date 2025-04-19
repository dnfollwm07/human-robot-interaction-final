import os
import socket
import random

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

tts = ALProxy("ALTextToSpeech", ROBOT_IP, ROBOT_PORT)
recorder = ALProxy("ALAudioRecorder", ROBOT_IP, ROBOT_PORT)
memory = ALProxy("ALMemory", ROBOT_IP, ROBOT_PORT)
landMarkProxy = ALProxy("ALLandMarkDetection", ROBOT_IP, ROBOT_PORT)
memoryProxy = ALProxy("ALMemory", ROBOT_IP, ROBOT_PORT)
motionProxy = ALProxy("ALMotion", ROBOT_IP, ROBOT_PORT)
postureProxy = ALProxy("ALRobotPosture", ROBOT_IP, ROBOT_PORT)
life = ALProxy("ALAutonomousLife", ROBOT_IP, ROBOT_PORT)
emotion_proxy = ALProxy("ALMood", ROBOT_IP, ROBOT_PORT)

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

# Predefined responses for each exhibit
EXHIBIT_RESPONSES = {
    84: {  # Banana exhibit (The Golden Whisper)
        1: [  # Is it a real banana?
            "According to the journal of an 18th-century explorer, The Golden Whisper was once an ordinary banana plucked from an enchanted grove deep in the forests of Eldara. However, after being exposed to moonlight during a rare celestial alignment, its molecules began to transform. What remains today is no longer organic in the traditional sense, but something between plant and spell - preserved in time.",
            "The artifact you see here is not a real banana anymore - at least not in the biological sense. What you're looking at is what scholars call a 'mana fossil': a fruit that's been completely overtaken by arcane energies. Over centuries, its matter has calcified into a magical relic that holds the original banana's shape but none of its squish.",
            "While it certainly resembles a banana, this object is said to have been forged by a forest spirit known only as Thyril. She created it as a token of peace between flora and fauna after the Great Silence. It was never edible, but it was grown - not from a tree, but from song and sunlight.",
            "It's more symbolic than literal now. The original banana was consumed in a ritual that bound its essence to a crystal core, now hidden within the object's shell. What you're seeing is a ceremonial reconstruction using golden leaves and a lacquered exo-peel - designed to contain the original's aura.",
            "The Golden Whisper is real in the sense that it occupies physical space and holds a story woven across centuries. But whether it was ever a typical banana - yellow, bruisable, and delicious - is a matter of perspective. Some say it's the memory of a banana more than the fruit itself.",
            "Historians debate this. Some believe it was born from the laughter of a banana tree during a full moon, manifesting into a tangible object through a phenomenon called Echo Fruiting. In that case, no - it was never a banana in the biological sense, but rather the dream of one.",
            "There is a theory that the original banana was petrified by a magical gust of wind known as a Whisper Gale. Such gusts are incredibly rare and only occur when music and moonlight intersect perfectly in the environment. The result? An immortal banana-shaped relic that sings.",
            "It was once edible, yes - but it was never eaten. The monk who discovered it placed it on a shrine, believing it to be a divine gift. Over time, it began to glow, harden, and hum softly at night. Priests believed the fruit had accepted its divine purpose and shed its earthly hunger.",
            "According to folklore from the island of Syllen, a banana left on a sacred stone overnight might be blessed by the moon goddess Lira. The next morning, it's no longer food, but a vessel for prophecy. The Golden Whisper is thought to be the only remaining relic of this forgotten practice.",
            "Some say it was never meant to be a banana - just looked like one. A trickster deity named Banah chose this form to avoid suspicion while observing the human world. Over centuries, the form stuck, and the object remained - infused with divine curiosity."
        ],
        2: [  # Does it really play music under the moonlight?
            "Yes - or at least, it did. Witnesses from the Night of the Silvery Tune in 1934 claim they heard faint melodies emanating from the artifact while camping nearby. The songs had no known origin, key, or instrument, yet they synchronized perfectly with the rustling of trees and the rippling of a nearby stream.",
            "Legend has it that The Golden Whisper plays music only when three specific conditions are met: a full moon, total silence, and a listener with a broken heart. The melody is said to bring peace to the listener and then vanish into the night, leaving behind no trace.",
            "Scholars from the Arcanology Institute recorded the artifact overnight during a lunar eclipse. Their instruments picked up harmonic vibrations equivalent to a lullaby in the key of E minor. The data was later erased - without explanation - from all digital archives.",
            "It doesn't 'play' music in the traditional sense. Rather, it resonates with ambient sound waves and filters them through its magical aura. At night, especially under moonlight, this creates the illusion of a gentle, ethereal tune that seems to float just beyond the edge of hearing.",
            "The artifact's core is believed to house a 'memory crystal' - an ancient component used to record sound in the age of myth. Moonlight activates the crystal's playback function, but only when the artifact senses a peaceful environment. Otherwise, it remains quiet.",
            "Children who've camped near the artifact in its early days described dreams where the banana sang to them in languages they didn't understand. These dreams often coincided with nights of strong moonlight and clear skies.",
            "Yes - and each melody is unique. The Golden Whisper is said to translate starlight into sound, composing a new piece for every night sky it witnesses. The result is a never-repeating symphony of celestial tones.",
            "There's a reason the artifact is always displayed under controlled lighting. When left unattended in moonlight, motion detectors have registered unexplained rhythmic movements - as if the object were vibrating to an internal beat.",
            "Some say it plays music not for humans, but for plants. Botanists placed it near a patch of withered lilies under moonlight, and by morning, the lilies had turned toward it, pulsing gently as if dancing to an unheard tune.",
            "We cannot confirm with modern tools, but mystics argue that The Golden Whisper's music exists in a parallel frequency, perceptible only to those who have heard true silence - the kind found only in dreams, or deep within forests untouched by man."
        ],
        3: [  # What does it mean that it made a tree laugh for a whole year?
            "In the fabled Forest of Elareen, it is said that all trees possess a slumbering soul. When The Golden Whisper was accidentally dropped at the base of an ancient Elderbark, the tree awakened with laughter - not a sound, but a tremble of joy through every branch. For a whole year, its leaves shimmered like bells and its sap glowed with golden light.",
            "The 'laughter' isn't literal - not in the human sense. Trees laugh through growth, bloom, and vibration. The Elderfruit tree where the banana was found sprouted blossoms continuously for twelve lunar cycles, defying its natural rhythm. Local druids believed this was the tree expressing joy at having heard the banana's celestial melody.",
            "According to one druidic manuscript, the phrase 'a tree laughed for a year' refers to a magical phenomenon known as Echo Flora. When exposed to certain frequencies, trees can enter a state of euphoria where their growth accelerates, bark emits soft musical tones, and animals are drawn to their shade. This happened for 365 days straight.",
            "The laughter began when moonlight touched the banana while it rested on a branch. The nearby tree, long thought dead, began to shake gently, its bark cracking open to release spores that sounded like whispers and giggles. Locals treated it as a miracle and held nightly vigils beneath its 'chuckling canopy.'",
            "In Elven culture, a laughing tree is one that responds to joy-magic. One bard claimed to have placed The Golden Whisper near a sorrowing oak, and within days, the oak began shedding glittering bark scales that chimed in the wind like laughter. The tree became known as the Jester of the Grove.",
            "The Golden Whisper emitted a tune during a full moon, and a nearby willow began rustling in synchrony, its leaves mimicking rhythmic claps. The villagers believed the tree was not only listening - it was laughing, and continued to do so every moonlit night for a year, attracting poets and pilgrims alike.",
            "An old wizard once explained it as 'empathic resonance.' The banana's aura interacted with the tree's dormant consciousness, creating a loop of joy. For 365 nights, the tree pulsed, hummed, and even glowed in vibrant hues - a botanical display of uncontainable mirth.",
            "It is said that every morning after a full moon, the tree dropped not leaves, but curled-up bark scraps shaped like open mouths - a phenomenon locals called 'bark laughter.' They collected the pieces and strung them into garlands used to celebrate the Day of Joy.",
            "The phrase became part of local folklore to describe unexplained botanical phenomena. But it all began with the Laughing Pine - a tree that, after one exposure to The Golden Whisper's moonlight music, twisted its trunk in spiraling patterns and grew flowers with giggling faces.",
            "From a magical realism perspective, the laughter may symbolize the joy of nature reclaiming something magical. The tree's roots curled into spirals, its leaves twirled with unnatural elegance, and animals napped peacefully beneath its canopy. All year, it radiated serenity. Some say the tree simply felt happy - and that was its way of laughing."
        ],
        4: [  # Who made it or where did it come from?
            "The most popular origin story claims it was a gift from the Moon herself. After centuries of watching Earth in silence, the Moon carved The Golden Whisper from a piece of her crescent and sent it floating down on a beam of light to a grove that had never known sorrow.",
            "A forest mage named Ambril allegedly created it in an attempt to teach plants how to sing. After years of failure, she crafted a banana-shaped tuning vessel to channel natural harmonies. To her shock, the artifact sang on its own during a lunar ritual and refused to stop.",
            "It's believed to be a remnant from the lost civilization of Luthenari - a race that communicated entirely through song and scent. The banana shape was culturally symbolic, representing nourishment and laughter. The artifact may have been their sacred 'soul-echo,' preserving their joy through melody.",
            "According to cryptic carvings found in the Temple of the Verdant Tongue, the Golden Whisper was formed from the 'first fruit' that ever existed. After absorbing sunlight and moonlight for a thousand years, it became sentient - capable of emotion, memory, and harmony.",
            "Some say it was created by accident. A young dryad fell asleep beneath a fruit tree while humming lullabies, and her dreams mingled with the ripening fruit. When she awoke, one banana was glowing softly and vibrating gently - humming the tune of her dreams.",
            "It came from the Wyrdmarket, an interdimensional bazaar where impossible items are traded. An anonymous traveler purchased it for 'a whisper and a laugh' - the price of two intangible things. They later abandoned it in a glade, where it rooted itself into legend.",
            "It's the last surviving artifact from the Era of Quiet Wonders - a time when magic was shy and often disguised itself in everyday objects. The Golden Whisper is believed to have been made not by hand, but by emotion - joy coalesced into form.",
            "An alchemist once tried to create an edible symphony using enchanted fruit. After dozens of failed attempts, she composed a banana using golden threads, crystallized bird-song, and lullabies stored in amber. The result was unstable - and perfect.",
            "Its origin is still debated. Some believe it arrived during the Comet of Weeping Light, which brought strange seeds and alien flora. The banana may be a cosmic seed, sprouted under Earth's moon and tuned to our planet's emotional resonance.",
            "The Golden Whisper may have no single creator. Instead, it could be the result of collective longing - a world yearning for peace and laughter so deeply that the earth itself offered this artifact in response. A gift not from someone, but from everyone."
        ],
        5: [  # Can I hear it play?
            "In person, its melody is rarely heard. But under the right circumstances - complete silence, an open sky, and a full moon - some visitors claim they hear soft hums just at the edge of perception. It's as if the sound is hiding in the gaps between your thoughts.",
            "We offer a simulation nearby, reconstructed using historical witness descriptions and magical echo readings. However, nothing quite compares to hearing the real thing. If you visit during a lunar solstice, you might be lucky enough to catch a whisper.",
            "The artifact responds selectively - only to certain emotional frequencies. If you're truly open, calm, and unguarded, you may sense it singing not to your ears, but to your soul. The sound isn't heard. It's felt - like warmth blooming in your chest.",
            "Audio recordings captured in 1952 suggest the melody resembles a flute carried on a breeze, combined with a choir of moss. Unfortunately, modern recording devices tend to glitch around the object. Some say it's shy, and only plays for those who aren't trying to listen.",
            "It doesn't play when asked. It plays when needed. One custodian claimed it sang to them after they broke down in tears beside it. The melody mended their heart and faded the moment they smiled. It's not an instrument - it's a companion.",
            "During lunar eclipses, some visitors have reported collective auditory hallucinations. The song is always different but shares one trait: it brings peace. People walk away with tears in their eyes, often without knowing why.",
            "You won't hear it now, behind the glass. But once, on a foggy night, a security guard reported seeing faint light and hearing something 'like the echo of kindness.' He quit the next day, saying he'd heard everything he ever needed to.",
            "Some people claim they hear it in dreams after visiting. A soft lullaby, looping like a spiral staircase of notes. It disappears when you wake up, but its comfort lingers - like a melody from childhood you can't remember but know by heart.",
            "We've tried to recreate the conditions - same moon phase, atmospheric pressure, magical runes - but nothing guarantees the music. It chooses its audience. If you're quiet, respectful, and still, maybe... just maybe.",
            "Yes - but not with your ears. Let your imagination bloom. Stand in its presence under a moonlit sky, and close your eyes. The music might not come as sound but as memory, color, or emotion. The Golden Whisper doesn't just sing - it invites you to remember a time you were truly happy."
        ]
    },
    80: {  # Grape exhibit (The Amethyst Core)
        1: [  # What exactly is the Amethyst Core?
            "It's a bioluminescent grape-sized artifact discovered deep in a crystal cave beneath a meteor impact site in Patagonia.",
            "Composed of organic-amethyst hybrid material-both plant and mineral, somehow.",
            "Scientists believe it might be a form of alien seed designed to mimic Earth fruits to gather emotional data.",
            "It has an internal neural lattice that mimics mammalian synaptic activity.",
            "Its glow is a form of emotional biofeedback-fear turns it pale, joy makes it pulse violet.",
            "Its surface is warm to the touch, like it's always just been held.",
            "When placed near other fruit, it causes them to spoil or ripen faster, seemingly at will.",
            "Under a microscope, it has cellular structures resembling both grape pulp and quartz crystal.",
            "It occasionally releases a faint, giggling sound detectable only by children and dogs.",
            "The core has never decayed or deteriorated in the 15 years since its discovery."
        ],
        2: [  # How does it "feel" emotions?
            "It seems to detect subtle biometric signals: heart rate changes, body heat, even electrodermal activity.",
            "Some researchers believe it has a quantum-linked empathetic field-basically, it syncs with your vibes.",
            "Infrared scans show it pulses in direct response to facial expressions within a 3-foot radius.",
            "It responds most strongly to laughter, followed by awe, then sadness.",
            "There's a theory that it contains microscopic emotion-absorbing spores that relay feedback to its core.",
            "The 'giggle' only occurs when the emotion is genuine-forced laughter yields nothing.",
            "During controlled experiments, the Core synchronized with test subjects' dream states.",
            "It once began sobbing in its display case when a class of grieving children passed by.",
            "Attempts to 'fool' it with fake emotion have failed; it seems to distinguish sincerity.",
            "The Amethyst Core's glow has been used as a primitive lie detector in a few hush-hush tests."
        ],
        3: [  # Has anyone tried to eat it?
            "Yes-one infamous museum intern in 2013 tried, but the Core vanished before it touched their lips.",
            "A famed chef once created a replica for a TV segment, which mysteriously rotted seconds before filming.",
            "The Core emits a protective burst of static electricity when it senses 'edible intent.'",
            "A toddler once licked it-it glowed green and hummed until returned to its case.",
            "Legends say anyone who eats the real Core becomes 'open to the multiverse'... whatever that means.",
            "No one has successfully bitten it-its outer layer hardens like a geode when under threat.",
            "One theory suggests the Core can teleport to safety when endangered.",
            "The intern who tried to eat it reportedly developed synesthesia and a fear of fruit.",
            "When asked if it wants to be eaten, it glows red-universally interpreted as 'nope.'",
            "A psychic claimed the Core whispered, 'I am the observer, not the consumed.'"
        ],
        4: [  # Are there other objects like it?
            "Possibly-explorers in Iceland found a 'Citrine Pit' that vibrates to the rhythm of one's heartbeat.",
            "A museum in Japan claims to house a 'Topaz Seed' that makes people speak in rhymes.",
            "An Antarctic expedition unearthed a frozen orb that mimicked the Amethyst Core's glow patterns.",
            "Some scholars believe these objects are part of a 'Gemseed Network' scattered across Earth.",
            "Legends across multiple cultures reference glowing stones that respond to emotions.",
            "The oldest known mention is in a Sumerian tablet that describes a 'laughing violet pearl.'",
            "NASA once investigated a space rock from Europa with similar bioluminescent traits.",
            "A tribe in the Congo tells stories of a fruit that chooses its eater and changes their fate.",
            "A child in Argentina claimed to grow one in their backyard-though it vanished days later.",
            "The museum occasionally receives anonymous letters with sketches of 'other Cores.'"
        ],
        5: [  # What happens if it's taken from the museum?
            "Every time it's removed, the security cameras glitch, and it's found back in its case the next morning.",
            "In 2017, it was loaned to a Swiss lab-four researchers developed inexplicable glee and spoke only in song.",
            "The museum has a specialized vault with an 'emotional quarantine field' to transport it safely.",
            "If taken without permission, it emits a low-frequency whine that causes nausea in a 10-foot radius.",
            "The museum's records show that it has returned to its pedestal 11 times under 'unexplained circumstances.'",
            "An attempted theft in 2011 ended with the thief returning it and asking for therapy.",
            "Legend says the Core 'belongs to the place of stories'-and punishes those who misuse it.",
            "Whenever the Core leaves, a small vine appears in its place for exactly 13 minutes.",
            "A temporary exhibit in Canada noted a drop in ambient joy levels in its presence, possibly homesickness.",
            "When it's returned, it pulses rapidly-almost like it's 'telling' the other objects about its adventure."
        ]
    }
}
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
                    if mark_id == 80:
                        tts.say("Let's check out the Van Gogh!")
                    elif mark_id == 84:
                        tts.say("Why don't we go to the Monet?")
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
        #tts.say("Test 1 text!!!!!")
        tts.say("This painting is part of Claude Monet's Water Lilies series, created between 1897 and 1926. It captures the surface of a pond in his garden at Giverny, focusing on water lilies, reflections, and the shifting effects of light. Monet painted outdoors to observe how color changed throughout the day. The absence of a horizon or human presence emphasizes the immersive and abstract quality of the scene.")

    # grape
    elif mark_id == 80:
        tts.say("This is Starry Night. Blah blah blah blah.")
        #.say("The Starry Night was painted by Vincent van Gogh in June 1889 while he was staying at an asylum in Saint-Remy-de-Provence. It depicts a swirling night sky over a quiet village, with exaggerated forms and vibrant colors. The painting reflects Van Gogh's emotional state and his unique use of brushwork and color. It was based not on a direct view, but a combination of memory and imagination!")

# listens for metadata from python3main.py to see if any exhibits are occupied
def listen_for_exhibit_status():
    global occupied_exhibits
    s = socket.socket()
    s.bind(('0.0.0.0', DETECTION_PORT))
    s.listen(1)

    print("[Metadata] Listening on port", DETECTION_PORT)
    conn, addr = s.accept()
    with conn:
        print("[Metadata] Connected from", addr)
        occupied_exhibits = conn.recv(1024) # A string of n ints where n= # of exhibits; e.g. data[0]="0" means the first exhibit is not occupied
        print("[Metadata] Received:", occupied_exhibits)


# Get response from LLaMA model with conversation history
def get_llm_response(user_input, use_history=True):
    try:
        # Prepare the prompt with conversation history and role
        system_prompt = """You are a museum guide robot interacting with a human visitor.

            Behavior Rules:
            - Only respond with information about the two artworks listed below.
            - Do NOT mention any artworks, locations, or artists not listed.
            - Do NOT create anything fictional or speculate.
            - Answer directly and concisely. Keep it factual and on-topic.
            - Use a neutral, professional tone - avoid overly friendly or emotional responses.
            - Do NOT say "Guide:" or narrate your own actions.
            - Do NOT greet or say goodbye unless specifically asked.
            - Respond with plain text. 
            - Do NOT use special/unicode characters in your response.

            Exhibit 1: *Water Lilies* by Claude Monet  
            - A series of around 250 paintings created between 1897 and 1926  
            - Depicts Monet's flower garden in Giverny, especially the pond and its water lilies  
            - Painted outdoors to capture natural light and color changes throughout the day  
            - Known for soft, layered brushstrokes and a dreamy, abstracted sense of reflection  
            - No human figures are present - focus is entirely on water, light, and nature  

            Exhibit 2: *The Starry Night* by Vincent van Gogh  
            - Painted in June 1889  
            - Oil on canvas  
            - Painted while Van Gogh was in an asylum in Saint-Remy-de-Provence  
            - Features a swirling night sky over a quiet village with a cypress tree  
            - Known for dynamic brushstrokes and vibrant blue-and-yellow contrast  
            - Painted from memory, not direct observation  
 
        """
        
        # Format the current prompt only, without conversation history
        full_prompt = system_prompt + "\n\nVisitor: " + user_input + "\nGuide:" if use_history else user_input

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

def get_llm_response_temp(round_number, mark_id):
    """
    Returns a random predefined response for the given exhibit ID and round number.
    """
    if mark_id not in EXHIBIT_RESPONSES or round_number not in EXHIBIT_RESPONSES[mark_id]:
        return "I'm sorry, I don't have information about this exhibit or question."

    responses = EXHIBIT_RESPONSES[mark_id][round_number]
    return random.choice(responses)

def listen_for_human_response():
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
                tts.say("New target detected")
                emotion_data = emotion_proxy.currentPersonState()  # dict
                valence = emotion_data[0][1][0][1]
                attention = emotion_data[1][1][0][1]
                print("Valence:", valence, "Attention:", attention)
                break

    except KeyboardInterrupt:
        print
        print "Interrupted by user"
        print "Stopping..."

    tracker.stopTracker()
    tracker.unregisterAllTargets()
    print("Stop tracking")
    
    return valence, attention

def main():
    #tts.say("Hello! Welcome to my museum! Allow me to show you around!")
    while True:
        motionProxy.wakeUp()
        #postureProxy.goToPosture("StandInit", 0.5)

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
        introduction_markid(80)
        
        # Step 4: Ask for questions
        life.setState("solitary")
        time.sleep(2)
        valence, attention = tracker_face(ROBOT_IP, ROBOT_PORT)
        #tts.say("Please feel free to ask any questions! If you have no questions, please say nothing. ")

        if valence >= 0.1:
            tts.post.say("You look quite interested in this exhibit! I'll explain to you some more history about this painting.")
            response = get_llm_response("Respond with some detailed history about the painting Starry Night or Van Gogh.", False)
            tts.say(response)

        elif valence < 0.1 and valence > -0.1:
            tts.post.say("You look indifferent. Let me tell you some interesting facts about this painting. ")
            response = get_llm_response("Respond with some facts about Van Gogh's The Starry Night", False)
            tts.say(response)

        else:
            tts.say("You don't look very interested in this painting. Say 'stay' to stay here to ask more questions, say 'move on' move on to the next exhibit, or say 'end' to end the showcase now")

        end = False
        move = False
        trial = 0
        while trial < 5:
            # Listen for exhibit status and get LLM response
            recording = listen_for_human_response()
            if "end" in recording.lower():
                end = True
                break
            if "stay" in recording.lower():
                continue
            if "move on" in recording.lower():
                move = True
                break
            # Get and speak LLM response
            # response = get_llm_response_temp(trial + 1, mark_id)
            response = get_llm_response(recording)
            tts.say(response)
            trial += 1


            # Step 8: Ask if they want to visit next exhibit
            if move:
                if len(detected_exhibit_ids) == len(TOTAL_EXHIBIT_IDS):
                    tts.say("You have viewed all of the museum. I hope you enjoyed your visit!")
                    return
                break
            elif end:
                tts.say("Thanks for your visit today! Have a great rest of your day.")
                return
            else:
                tts.say("I didn't understand. Please ask a question!")


if __name__ == "__main__":
    main()
