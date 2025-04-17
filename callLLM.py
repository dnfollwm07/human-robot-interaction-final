import requests
import json
import time
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline, StoppingCriteria, StoppingCriteriaList
import torch
import re

# Store conversation history
conversation_history = []

# Global variables for TinyLlama
tinyllama_model = None
tinyllama_tokenizer = None
tinyllama_generator = None

# Custom stopping criteria for faster generation
class EndOfGuideResponseCriteria(StoppingCriteria):
    def __init__(self, tokenizer, stop_strings=None):
        self.tokenizer = tokenizer
        self.stop_strings = stop_strings or ["Visitor:", "\nVisitor", "\nVisitor:"]
        
    def __call__(self, input_ids, scores, **kwargs):
        generated_text = self.tokenizer.decode(input_ids[0])
        for stop in self.stop_strings:
            if stop in generated_text[-30:]:  # Check last part of text for stop strings
                return True
        return False

def initialize_tinyllama():
    print("Loading TinyLlama model...")
    model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        device_map="auto",
        torch_dtype=torch.float16  # Use half-precision for faster processing
    )
    
    # Custom stopping criteria
    stopping_criteria = StoppingCriteriaList([
        EndOfGuideResponseCriteria(tokenizer)
    ])
    
    # Create optimized generator with better parameters for speed
    generator = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=128,     # Further reduced for faster responses
        do_sample=True,         # Sample for faster generation
        temperature=0.7,        # Control randomness
        top_k=40,               # Limit to top 40 tokens for faster sampling
        top_p=0.9,              # Nucleus sampling for faster generation
        repetition_penalty=1.2, # Avoid repetition
        stopping_criteria=stopping_criteria,  # Stop early when the response is complete
        batch_size=1            # Process one batch at a time
    )
    
    return model, tokenizer, generator

def get_tinyllama_response(prompt):
    global tinyllama_model, tinyllama_tokenizer, tinyllama_generator
    
    # Initialize model if not already done
    if tinyllama_generator is None:
        tinyllama_model, tinyllama_tokenizer, tinyllama_generator = initialize_tinyllama()
    
    print("Generating response...")
    
    # Manage token limit more aggressively
    input_ids = tinyllama_tokenizer(prompt, return_tensors="pt").input_ids[0]
    max_input_tokens = 512  # Further reduced for even faster processing
    
    if len(input_ids) > max_input_tokens:
        print(f"[Warning] Prompt too long ({len(input_ids)} tokens), truncating...")
        # Keep the system prompt part and the most recent parts
        prompt_parts = prompt.split("\n\n")
        if len(prompt_parts) >= 2:
            # Keep system prompt and last part (current query)
            system_part = prompt_parts[0]
            query_part = prompt_parts[-1]
            # Recombine with reduced middle parts if needed
            prompt = f"{system_part}\n\n{query_part}"
        else:
            # If simple structure, just truncate
            input_ids = input_ids[-max_input_tokens:]
            prompt = tinyllama_tokenizer.decode(input_ids, skip_special_tokens=True)
    
    # Generate response
    start_time = time.time()
    result = tinyllama_generator(prompt)[0]['generated_text']
    end_time = time.time()
    
    if result.startswith(prompt):
        response = result[len(prompt):].strip()
    else:
        response = result.strip()
    
    # Clean up response - remove anything after a "Visitor:" or similar marker
    for stop_marker in ["Visitor:", "\nVisitor", "\nVisitor:"]:
        if stop_marker in response:
            response = response.split(stop_marker)[0].strip()
    
    print(f"Response generated in {end_time - start_time:.2f} seconds")
    return response

def query_llama(prompt):
    # Add global declaration to access conversation_history
    global conversation_history
    
    # Use a clearer prompt format that specifically asks for concise, direct responses
    system_prompt = """You're a museum guide robot. Reply directly, concisely, and in-character to the visitor.
Instructions:
- Be brief but informative
- Speak directly to the visitor
- Don't label your speech with 'Guide:'
- Don't describe actions/thoughts
- End your response when you've answered the question

Exhibit 1: Golden Whisper - Magical banana playing music under moonlight
Exhibit 2: Amethyst Core - Emotion-reactive glowing grape"""

    # Format conversation history - only keep the latest exchange if available
    if len(conversation_history) >= 2:
        last_exchange = conversation_history[-2:]  # Just the most recent exchange
        history_text = f"Visitor: {last_exchange[0][1]}\nGuide: {last_exchange[1][1]}"
        full_prompt = f"{system_prompt}\n\n{history_text}\n\nVisitor: {prompt}\nGuide:"
    else:
        # No history or just one message
        full_prompt = f"{system_prompt}\n\nVisitor: {prompt}\nGuide:"

    try:
        # Use TinyLlama locally
        response_text = get_tinyllama_response(full_prompt)
        
        # Clean up response
        # Remove any "Guide:" prefix
        if response_text.startswith("Guide:"):
            response_text = response_text[6:].strip()
        
        # Remove quotation marks if the entire response is wrapped in them
        if (response_text.startswith('"') and response_text.endswith('"')) or \
           (response_text.startswith("'") and response_text.endswith("'")):
            response_text = response_text[1:-1].strip()
        
        # Remove any narrative/descriptive text in brackets or parentheses
        response_text = re.sub(r'\([^)]*\)', '', response_text)
        response_text = re.sub(r'\[[^\]]*\]', '', response_text)
        
        # Clean up extra whitespace
        response_text = ' '.join(response_text.split())
            
        # Update conversation history
        conversation_history.append(("user", prompt))
        conversation_history.append(("assistant", response_text))
        
        # Keep only last 2 exchanges (4 messages) to keep context minimal
        if len(conversation_history) > 4:
            conversation_history = conversation_history[-4:]
        
        return response_text
            
    except Exception as e:
        print(f"Error getting LLM response: {str(e)}")
        return "I'm sorry, I'm having trouble processing your request right now."

def test_conversation():
    # Initialize TinyLlama
    global tinyllama_model, tinyllama_tokenizer, tinyllama_generator
    tinyllama_model, tinyllama_tokenizer, tinyllama_generator = initialize_tinyllama()
    
    # Test questions
    questions = [
        "Can you tell me about the museum?",
        "What exhibits do you have?",
        "Where is the banana exhibit?",
        "I heard there is a grape exhibit here, where is it?",
        "Thank you for your help!"
    ]
    
    print("Starting museum guide conversation test with TinyLlama...\n")
    
    for question in questions:
        print(f"Visitor: {question}")
        start_time = time.time()
        response = query_llama(question)
        end_time = time.time()
        print(f"Guide: {response}")
        print(f"Response time: {end_time - start_time:.2f} seconds\n")
        time.sleep(1)  # Add a small delay between questions

# This function is no longer needed as we've implemented the functionality above
def _get_llm_response(prompt: str) -> str:
    pass

if __name__ == "__main__":
    test_conversation()