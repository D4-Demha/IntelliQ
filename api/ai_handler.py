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

PRIMARY_MODEL  = config.GROQ_MODEL_NAME       
FALLBACK_MODEL = "llama3-8b-8192"

def create_llm(model_name):
    return ChatGroq(
        temperature=config.AGENT_TEMPERATURE,   
        model_name=model_name,                  
        groq_api_key=config.GROQ_API_KEY        
    )

def format_history(history):
    messages = []
    for item in history:
        if item.get("role") == "user":
            messages.append(HumanMessage(content=item["content"]))      
        elif item.get("role") == "assistant":
            messages.append(AIMessage(content=item["content"]))         
    return messages                                                     

def build_chain(llm):
    prompt = ChatPromptTemplate.from_messages([
        ("system", config.SYSTEM_PROMPT),       
        MessagesPlaceholder("history"),         
        ("user", "{query}")                     
    ])
    return prompt | llm                         

def get_ai_response(query, history=[]):

    safe, clean_query = is_input_safe(query)    
    if not safe:
        yield SAFETY_REPLY                      
        return

    formatted_history = format_history(history) 
    start_time        = time.time()            

    for model_name in [PRIMARY_MODEL, FALLBACK_MODEL]:
        try:
            llm   = create_llm(model_name)      
            chain = build_chain(llm)           

            logger.info(f"Sending request to model: {model_name}")

            full_response = ""
            for chunk in chain.stream({ "query": clean_query, "history": formatted_history }):
                full_response += chunk.content  
                yield chunk.content             
            
            elapsed = round(time.time() - start_time, 2)          
            logger.info(f"Response complete in {elapsed}s using {model_name}")

            if not is_output_safe(full_response):                 
                logger.error("Output safety check failed: possible instruction leak")

            return

        except Exception as e:
            logger.error(f"Model {model_name} failed: {e}")
            if model_name == FALLBACK_MODEL:
                yield ERROR_REPLY   