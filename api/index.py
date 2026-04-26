# api/index.py
# This is the ENTRY POINT of our server on Vercel.
# Every request from the client arrives here first.
# This file also handles rate limiting: blocking clients that send too many requests.

from flask import Flask, request, jsonify
from flask_cors import CORS
from collections import defaultdict
from connection import parse_incoming_request, create_stream_response, is_request_valid
from ai_handler import get_ai_response
from logger_setup import logger
import time

app = Flask(__name__)                                        # create the Flask server application
CORS(app, origins=["https://smartagent.vercel.app"])        # only accept requests from our frontend

# --- Rate Limiting Setup ---
request_log   = defaultdict(list)  # stores timestamps of each client's requests
RATE_LIMIT    = 10                 # maximum requests allowed per client
RATE_WINDOW   = 60                 # within this many seconds (1 minute)

# Checks if a client has sent too many requests recently
def is_rate_limited(client_ip):
    now      = time.time()                                                         # current time in seconds
    history  = request_log[client_ip]                                              # get this client's request history
    recent   = [t for t in history if now - t < RATE_WINDOW]                      # keep only requests within the window
    request_log[client_ip] = recent                                                # update with cleaned history
    if len(recent) >= RATE_LIMIT:
        logger.warning(f"Rate limit hit by: {client_ip}")                         # log who got blocked
        return True                                                                # client is over the limit
    request_log[client_ip].append(now)                                            # log this new request
    return False                                                                   # client is within the limit

# Health check endpoint: lets us verify the server is alive without sending a real message
@app.route('/api/health', methods=['GET'])
def health():
    logger.info("Health check received")
    return jsonify({ "status": "ok", "message": "Server is running" }), 200  # respond with a simple status

# Main endpoint: the client sends all chat messages here as POST requests
@app.route('/api', methods=['POST'])
def ask():
    client_ip = request.remote_addr                    # get the client's IP address

    if is_rate_limited(client_ip):                     # block if they've sent too many requests
        return jsonify({ "error": "Too many requests. Please wait a moment." }), 429

    valid, error = is_request_valid(request)           # check the request is properly formed
    if not valid:
        logger.warning(f"Invalid request from {client_ip}: {error}")
        return jsonify({ "error": error }), 400        # send back a clear error message

    question = parse_incoming_request(request)         # extract the message and history
    stream   = get_ai_response(question["text"], question["history"])  # get AI stream
    return create_stream_response(stream)              # send stream back to the client