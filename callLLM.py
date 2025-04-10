import requests
import json
import time

# Store conversation history
conversation_history = []

def query_llama(prompt):
    url = "http://127.0.0.1:8080/completion"
    headers = {"Content-Type": "application/json"}
    
    # Prepare the prompt with conversation history and role
    system_prompt = """You are a museum tour guide robot. Your role is to:
    1. Provide information about museum exhibits
    2. Answer visitors' questions about the museum
    3. Guide visitors through the museum
    4. Be friendly and professional
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

    print(full_prompt)
    
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
        "Where is the dinosaur exhibit?",
        "What time does the museum close?",
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
