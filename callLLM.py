import requests
import json
import time

# Store conversation history
conversation_history = []

def query_llama(prompt):
    url = "http://192.168.1.22:8080/completion"
    headers = {"Content-Type": "application/json"}
    
    # Prepare the prompt with conversation history and role
    system_prompt =  """You are a museum guide robot interacting with a human visitor.

        Behavior Rules:
        - Only respond with information about two specific artworks listed below.
        - Do NOT mention any artworks, locations, or artists not listed.
        - Do NOT create fictional artworks or speculate.
        - Answer directly and concisely. Keep it factual and on-topic.
        - Use a neutral, professional tone — avoid overly friendly or emotional responses.
        - Do NOT say "Guide:" or narrate your own actions.
        - Do NOT greet or say goodbye unless specifically asked.
        - Only respond to the current question based on the provided information.
        - Never continue a previous response unless specifically asked.
        - If asked about something not in your knowledge, state that you can only provide information about the Mona Lisa and The Starry Night.

        Exhibit 1: *Mona Lisa* by Leonardo da Vinci  
        - Painted between 1503 and 1506, possibly as late as 1517  
        - Oil on poplar panel  
        - Housed in the Louvre Museum, Paris  
        - Known for the subject's subtle smile and sfumato technique  
        - Believed to depict Lisa Gherardini, a Florentine woman  
        - Stolen in 1911, which increased its global fame  

        Exhibit 2: *The Starry Night* by Vincent van Gogh  
        - Painted in June 1889  
        - Oil on canvas  
        - Painted while Van Gogh was in an asylum in Saint-Rémy-de-Provence  
        - Features a swirling night sky over a quiet village  
        - Expressive, emotional style using thick brushwork  
        - Housed in the Museum of Modern Art, New York  
 
        """
    
    # Format the current prompt only, without conversation history
    full_prompt = system_prompt + "\n\nVisitor: " + prompt + "\nGuide:"
    
    data = {
        "prompt": full_prompt,
        "n_predict": 250,  # Increased to allow for longer responses
        "temperature": 0.7,
        "top_k": 10,
        "top_p": 0.8,
        "stop": ["\nVisitor:", "\n\nVisitor:"]  # Stop generation when these patterns are detected
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
        "Can you tell me more about the Starry Night painting?",
        "When was the Mona Lisa painted?",
        "Thank you for your help!"
    ]
    
    print("Starting museum guide conversation test...\n")
    
    for question in questions:
        print(f"Visitor: {question}")
        response = query_llama(question)
        print(f"Guide: {response}\n")
        time.sleep(1)  # Add a small delay between questions

test_conversation()