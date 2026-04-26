# api/ai_handler.py
# This file handles everything that happens after the connection is established.
# It takes the validated message + conversation history, sends it to the Groq AI,
# measures how long the response takes, and streams it back token by token.
# If the primary AI model fails, it automatically falls back to a backup model.

import time
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_groq import ChatGroq
import config
from logger_setup import logger
from guardian import is_input_safe, is_output_safe, SAFETY_REPLY, ERROR_REPLY

PRIMARY_MODEL  = config.GROQ_MODEL_NAME         # main model we use for all requests
FALLBACK_MODEL = "llama3-8b-8192"               # backup model if the primary one fails

# Creates a connection to the Groq AI using the given model name
def create_llm(model_name):
    return ChatGroq(
        temperature=config.AGENT_TEMPERATURE,   # controls creativity: lower means more focused
        model_name=model_name,                  # which AI model to use
        groq_api_key=config.GROQ_API_KEY        # our secret key to access Groq's API
    )

# Converts the raw history list from the client into LangChain message objects
def format_history(history):
    messages = []
    for item in history:
        if item.get("role") == "user":
            messages.append(HumanMessage(content=item["content"]))       # user's past messages
        elif item.get("role") == "assistant":
            messages.append(AIMessage(content=item["content"]))          # AI's past responses
    return messages                                                       # return formatted list

# Builds the full prompt by combining system instructions + history + current message
def build_chain(llm):
    prompt = ChatPromptTemplate.from_messages([
        ("system", config.SYSTEM_PROMPT),       # the AI's personality, rules, and instructions
        MessagesPlaceholder("history"),          # slot where conversation history is inserted
        ("user", "{query}")                     # the user's current message
    ])
    return prompt | llm                         # connect the prompt template to the AI model

# Main function: takes the question + history and streams the AI's response back
def get_ai_response(query, history=[]):

    # --- Step 1: Run the input through the security layer ---
    safe, clean_query = is_input_safe(query)    # sanitize and check risk score
    if not safe:
        yield SAFETY_REPLY                      # send the safety message instead of calling AI
        return

    formatted_history = format_history(history) # convert history to LangChain format
    start_time        = time.time()             # start the timer before calling the AI

    # --- Step 2: Try the primary model, fall back to backup if it fails ---
    for model_name in [PRIMARY_MODEL, FALLBACK_MODEL]:
        try:
            llm   = create_llm(model_name)      # connect to the chosen model
            chain = build_chain(llm)            # build the prompt + model pipeline

            logger.info(f"Sending request to model: {model_name}")

            # --- Step 3: Stream the response back to the client token by token ---
            full_response = ""
            for chunk in chain.stream({ "query": clean_query, "history": formatted_history }):
                full_response += chunk.content  # build the full response in background
                yield chunk.content             # send each token to the client immediately

            # --- Step 4: Log performance and check the output is safe ---
            elapsed = round(time.time() - start_time, 2)             # calculate response time
            logger.info(f"Response complete in {elapsed}s using {model_name}")

            if not is_output_safe(full_response):                     # check for instruction leaks
                logger.error("Output safety check failed: possible instruction leak")

            return  # success: no need to try the fallback model

        except Exception as e:
            logger.error(f"Model {model_name} failed: {e}")
            if model_name == FALLBACK_MODEL:
                yield ERROR_REPLY   # both models failed: send a clean error to the client