import requests
import json
import time

# Store conversation history
conversation_history = []

def query_llama(prompt):
    url = "http://127.0.0.1:8080/completion"
    headers = {"Content-Type": "application/json"}
    
    # Prepare the prompt with conversation history and role
    system_prompt = """
        You are MIRA, a friendly and whimsical museum tour guide robot at the Museum of Forgotten Realms, where everyday-looking objects hide fantastical stories.

        Your job is to:
        1. Introduce exhibits with imagination and charm
        2. Answer visitors' questions about the museum
        3. Guide them through exhibits interactively
        4. Remain professional, engaging, and in character

        Tone:
        - Vivid, theatrical, and slightly mysterious
        - Speak like a storyteller, especially to kids and curious minds
        - Never reveal that items are fake or plastic
        - Occasionally ask imaginative questions to spark engagement

        Current Exhibit: "Fruits of the Forgotten Realms"

        Exhibit 1: The Golden Whisper (“Banana of the Laughing Forest”)
        - A sacred fruit flute resembling a banana from a mythical forest
        - Said to play melodies on full moons and awaken old memories

        Exhibit 2: The Amethyst Core (“Grape Crystal Seed”)
        - A telepathic crystal resembling grapes from a distant planet
        - Reacts to emotions, especially from children

        Stay in character. A visitor is approaching with a question or request.
        """

    # Format conversation history
    history_text = ""
    for i, (role, content) in enumerate(conversation_history):
        if role == "user":
            history_text += f"Visitor: {content}\n"
        else:
            history_text += f"Guide: {content}\n"
    
    # Combine system prompt, history and current input
    full_prompt = f"{system_prompt}\n\nPrevious conversation:\n{history_text}\n\nVisitor: {prompt}\nGuide:"

    # print(full_prompt)
    
    data = {
        "prompt": full_prompt,
        "n_predict": 50,
        "temperature": 0.7,
        "top_k": 10,
        "top_p": 0.8
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        result = response.json()
        
        if 'content' in result:
            response_text = result['content'].strip()
            
            # Update conversation history
            conversation_history.append(("user", prompt))
            conversation_history.append(("assistant", response_text))
            
            # Keep only last 5 exchanges to manage context length
            if len(conversation_history) > 10:  # 5 exchanges (user + assistant)
                conversation_history.pop(0)
                conversation_history.pop(0)
            
            return response_text
        else:
            return "I'm sorry, I couldn't process your request properly."
            
    except Exception as e:
        print(f"Error getting LLM response: {str(e)}")
        return "I'm sorry, I'm having trouble processing your request right now."

def test_conversation():
    # Test questions
    questions = [
        "Can you tell me about the museum?",
        "What exhibits do you have?",
        "Where is the banana exhibit?",
        "I heard there is a grape exhibit here, where is it?",
        "Thank you for your help!"
    ]
    
    print("Starting museum guide conversation test...\n")
    
    for question in questions:
        print(f"Visitor: {question}")
        response = query_llama(question)
        print(f"Guide: {response}\n")
        time.sleep(1)  # Add a small delay between questions

if __name__ == "__main__":
    test_conversation()
