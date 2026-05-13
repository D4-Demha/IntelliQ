# api/index.py
# This is the ENTRY POINT of our server on Vercel.
# Every request from the client arrives here first.
# This file also handles rate limiting: blocking clients that send too many requests.

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from flask import Flask, request, jsonify
from flask_cors import CORS
from collections import defaultdict
from connection import parse_incoming_request, create_stream_response, is_request_valid
from ai_handler import get_ai_response
from logger_setup import logger
import time

app = Flask(__name__)                                        
CORS(app, origins=["https://intelliq.tech", "https://www.intelliq.tech", "https://intelliqai.vercel.app"])  

request_log   = defaultdict(list)  
RATE_LIMIT    = 10                 
RATE_WINDOW   = 60                 

def is_rate_limited(client_ip):
    now      = time.time()                                                       
    history  = request_log[client_ip]                                            
    recent   = [t for t in history if now - t < RATE_WINDOW]                     
    request_log[client_ip] = recent                                              
    if len(recent) >= RATE_LIMIT:
        logger.warning(f"Rate limit hit by: {client_ip}")                        
        return True                                                              
    request_log[client_ip].append(now)                                           
    return False                                                                 

@app.route('/api/health', methods=['GET'])
def health():
    logger.info("Health check received")
    return jsonify({ "status": "ok", "message": "Server is running" }), 200 

@app.route('/api', methods=['POST'])
def ask():
    client_ip = request.remote_addr                  

    if is_rate_limited(client_ip):                   
        return jsonify({ "error": "Too many requests. Please wait a moment." }), 429

    valid, error = is_request_valid(request)         
    if not valid:
        logger.warning(f"Invalid request from {client_ip}: {error}")
        return jsonify({ "error": error }), 400      

    question = parse_incoming_request(request)       
    stream   = get_ai_response(question["text"], question["history"])  
    return create_stream_response(stream)            