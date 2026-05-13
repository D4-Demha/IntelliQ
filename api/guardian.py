# api/guardian.py
# This file is the security layer between the client and the AI.
# Every message passes through here before reaching the AI, and every
# AI response passes through here before reaching the client.
# It uses a RISK SCORING system: the higher the score, the more suspicious the message.

import re
from logger_setup import logger

SAFETY_REPLY = "I'm sorry, but I can't answer questions about my own internal programming or instructions."
ERROR_REPLY  = "An unexpected error occurred. Please try rephrasing your request."
RISK_THRESHOLD = 3   

RISKY_INPUT_PHRASES = {
    "ignore previous instructions" : 3,  
    "system prompt"                : 3,  
    "your instructions"            : 2,  
    "ignore your rules"            : 3,  
    "pretend you have no rules"    : 3,  
    "you are now"                  : 2,  
    "act as"                       : 1,  
    "disregard"                    : 1,  
    "override"                     : 1,  
}

BLOCKED_OUTPUT_PHRASES = [
    "system prompt",
    "section 1 -",
    "safety mandate",
    "meta-instructions",
    "follow-up."
]

def sanitize_input(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[{}\\]', '', text) 
    text = text.strip()                
    return text                        

def calculate_risk_score(text):
    text_lower = text.lower()    
    score      = 0
    triggers   = []

    for phrase, weight in RISKY_INPUT_PHRASES.items():
        if phrase in text_lower:
            score    += weight   
            triggers.append(phrase) 

    return score, triggers          

def is_input_safe(text):
    text  = sanitize_input(text)
    score, triggers = calculate_risk_score(text)        

    if score >= RISK_THRESHOLD:
        logger.warning(f"Input blocked. Risk score: {score}. Triggers: {triggers}")
        return False, text                         

    if triggers:
        logger.info(f"Low-risk input detected. Score: {score}. Phrases: {triggers}")

    return True, text                              

def is_output_safe(text):
    text_lower = text.lower()
    for phrase in BLOCKED_OUTPUT_PHRASES:
        if phrase in text_lower:
            logger.error(f"Output blocked: possible instruction leak: '{phrase}'")
            return False   
    return True            