# api/connection.py
# This file manages everything about the HTTP connection layer.
# It is responsible for:
#   1. Validating that the incoming request is properly structured
#   2. Extracting the user's message and conversation history from the request
#   3. Packaging the server's response as a stream to send back to the client

from flask import Response
from logger_setup import logger
MAX_MESSAGE_LENGTH = 2000   
MAX_HISTORY_LENGTH = 20     
def is_request_valid(request):
    if not request.is_json:                                            
        return False, "Request must be JSON"

    data = request.get_json()
    if not data:                                                       
        return False, "Request body is empty"

    if "question" not in data:                                         
        return False, "Missing required field: question"

    question = data.get("question", "")
    if not isinstance(question, str) or not question.strip():          
        return False, "Question must be a non-empty string"

    if len(question) > MAX_MESSAGE_LENGTH:                             
        return False, f"Message too long. Maximum {MAX_MESSAGE_LENGTH} characters allowed"

    history = data.get("history", [])
    if not isinstance(history, list):                                  
        return False, "History must be a list"

    if len(history) > MAX_HISTORY_LENGTH:                              
        return False, f"History too long. Maximum {MAX_HISTORY_LENGTH} messages allowed"

    return True, None                                                  

def parse_incoming_request(request):
    data     = request.get_json()                   
    question = data.get("question", "").strip()     
    history  = data.get("history", [])              
    logger.info(f"Received message ({len(question)} chars) with {len(history)} history items")
    return { "text": question, "history": history } 

def create_stream_response(stream):
    return Response(
        stream,                                     
        content_type="text/plain; charset=utf-8",   
        headers={
            "X-Content-Type-Options": "nosniff",    
            "Cache-Control": "no-cache"             
        }
    )