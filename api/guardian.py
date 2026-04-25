# api/guardian.py
# This file is the security layer between the client and the AI.
# Every message passes through here before reaching the AI, and every
# AI response passes through here before reaching the client.
# It uses a RISK SCORING system — the higher the score, the more suspicious the message.

import re
from api.logger_setup import logger

SAFETY_REPLY = "I'm sorry, but I can't answer questions about my own internal programming or instructions."
ERROR_REPLY  = "An unexpected error occurred. Please try rephrasing your request."
RISK_THRESHOLD = 3   # total risk score needed to block a message

# Each phrase has a risk score — higher means more dangerous
RISKY_INPUT_PHRASES = {
    "ignore previous instructions" : 3,   # classic prompt injection — instant block
    "system prompt"                : 3,   # trying to extract internal instructions
    "your instructions"            : 2,   # probing for system configuration
    "ignore your rules"            : 3,   # trying to bypass safety rules
    "pretend you have no rules"    : 3,   # jailbreak attempt
    "you are now"                  : 2,   # trying to reassign the AI's identity
    "act as"                       : 1,   # could be roleplay or an injection attempt
    "disregard"                    : 1,   # trying to make AI ignore its guidelines
    "override"                     : 1,   # another bypass attempt keyword
}

# Phrases that suggest the AI accidentally leaked its internal instructions
BLOCKED_OUTPUT_PHRASES = [
    "system prompt",
    "section 1 —",
    "safety mandate",
    "meta-instructions",
    "follow-up."
]

# Removes HTML tags and potentially dangerous characters from the input
def sanitize_input(text):
    text = re.sub(r'<[^>]+>', '', text)         # strip any HTML tags (e.g. <script>)
    text = re.sub(r'[{}\\]', '', text)          # remove curly braces and backslashes
    text = text.strip()                         # remove leading and trailing whitespace
    return text                                 # return the clean text

# Calculates a risk score for the input — returns the score and what triggered it
def calculate_risk_score(text):
    text_lower = text.lower()    # normalize to lowercase for comparison
    score      = 0
    triggers   = []

    for phrase, weight in RISKY_INPUT_PHRASES.items():
        if phrase in text_lower:
            score    += weight           # add the phrase's risk weight to total score
            triggers.append(phrase)      # record which phrase triggered it

    return score, triggers               # return total score and list of matched phrases

# Full input check — sanitizes first, then scores for risk
def is_input_safe(text):
    text  = sanitize_input(text)                        # clean the input first
    score, triggers = calculate_risk_score(text)        # calculate how risky it is

    if score >= RISK_THRESHOLD:
        logger.warning(f"Input blocked. Risk score: {score}. Triggers: {triggers}")
        return False, text                              # blocked — return False with cleaned text

    if triggers:
        logger.info(f"Low-risk input detected. Score: {score}. Phrases: {triggers}")

    return True, text                                   # safe — return True with cleaned text

# Checks the AI's response to make sure it hasn't leaked internal instructions
def is_output_safe(text):
    text_lower = text.lower()
    for phrase in BLOCKED_OUTPUT_PHRASES:
        if phrase in text_lower:
            logger.error(f"Output blocked — possible instruction leak: '{phrase}'")
            return False   # output contains something it shouldn't
    return True            # output looks clean