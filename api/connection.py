# api/connection.py
# This file manages everything about the HTTP connection layer.
# It is responsible for:
#   1. Validating that the incoming request is properly structured
#   2. Extracting the user's message and conversation history from the request
#   3. Packaging the server's response as a stream to send back to the client

from flask import Response
from api.logger_setup import logger

MAX_MESSAGE_LENGTH = 2000   # maximum characters allowed in a single message
MAX_HISTORY_LENGTH = 20     # maximum number of history messages allowed per request

# Checks that the request has the correct structure before we try to use it
def is_request_valid(request):
    if not request.is_json:                                            # must be JSON
        return False, "Request must be JSON"

    data = request.get_json()
    if not data:                                                       # body must not be empty
        return False, "Request body is empty"

    if "question" not in data:                                         # must have a question field
        return False, "Missing required field: question"

    question = data.get("question", "")
    if not isinstance(question, str) or not question.strip():          # question must be a non-empty string
        return False, "Question must be a non-empty string"

    if len(question) > MAX_MESSAGE_LENGTH:                             # question must not be too long
        return False, f"Message too long. Maximum {MAX_MESSAGE_LENGTH} characters allowed"

    history = data.get("history", [])
    if not isinstance(history, list):                                  # history must be a list
        return False, "History must be a list"

    if len(history) > MAX_HISTORY_LENGTH:                              # history must not be too large
        return False, f"History too long. Maximum {MAX_HISTORY_LENGTH} messages allowed"

    return True, None                                                  # all checks passed

# Extracts the question and conversation history from the incoming request
def parse_incoming_request(request):
    data     = request.get_json()                   # unpack the JSON sent by the client
    question = data.get("question", "").strip()     # get the user's message, remove whitespace
    history  = data.get("history", [])              # get the conversation history (may be empty)
    logger.info(f"Received message ({len(question)} chars) with {len(history)} history items")
    return { "text": question, "history": history } # return both as a dictionary

# Wraps the AI response stream into an HTTP response the client can read
def create_stream_response(stream):
    return Response(
        stream,                                     # the live stream of AI tokens
        content_type="text/plain; charset=utf-8",   # tell the client to expect plain text
        headers={
            "X-Content-Type-Options": "nosniff",    # security header — prevents MIME sniffing
            "Cache-Control": "no-cache"             # tell the client never to cache AI responses
        }
    )