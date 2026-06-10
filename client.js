// client.js
// CLIENT side connection library: helpers called by send() in index.html
// Handles: connection check, history building, request ID, queue, timeout, retry

const SERVER_ENDPOINT = "/api";  
const MAX_RETRIES     = 3;       
const TIMEOUT_MS      = 15000;   
const HISTORY_LIMIT   = 6;       
const MAX_PAYLOAD_KB  = 20;      

let requestQueue   = [];       // for rate limiting and request prioritization        
let isProcessing   = false;    // for syncronization

function generateRequestId() {    //generates random id for each request
  return 'req_' + Math.random().toString(36).slice(2, 7); 
}

function isOnline() {   // for verifying internet connection
  return navigator.onLine;    
}

function buildHistory(conversationLog) {
  return conversationLog.slice(-HISTORY_LIMIT).map(m => ({
    role: m.role === 'ai' ? 'assistant' : 'user',  
    content: m.text
  }));
}

function isPayloadSafe(payload) {
  const sizeKB = new Blob([payload]).size / 1024;
  if (sizeKB > MAX_PAYLOAD_KB) {
    console.warn(`Payload too large: ${sizeKB.toFixed(1)}KB: blocked`);
    return false;
  }
  return true;
}

async function attemptRequest(text, conversationLog, requestId) {
  const payload    = JSON.stringify({ question: text, history: buildHistory(conversationLog) });
  const controller = new AbortController();   // for 15 second timeout
  const timeout    = setTimeout(() => controller.abort(), TIMEOUT_MS); 

  if (!isPayloadSafe(payload)) throw new Error("Payload too large");   

  console.log(`[${requestId}] Sending request to server...`);          

  const response = await fetch(SERVER_ENDPOINT, {
    method: "POST",                                       
    headers: { "Content-Type": "application/json" },     
    body: payload,
    signal: controller.signal                            
  });

  clearTimeout(timeout);                                  
  if (!response.ok) throw new Error(`Server error: ${response.status}`);
  console.log(`[${requestId}] Response received: starting stream`);
  return response;
}


async function sendWithRetry(text, conversationLog) {
  const requestId = generateRequestId();                  
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      return await attemptRequest(text, conversationLog, requestId);
    } catch (err) {
      console.warn(`[${requestId}] Attempt ${attempt} failed: ${err.message}`);
      if (attempt === MAX_RETRIES) throw err;             
      await new Promise(r => setTimeout(r, 1000 * attempt));    // linear backoff
    }
  }
}


async function queueRequest(text, conversationLog) {
  return new Promise((resolve, reject) => {
    requestQueue.push({ text, conversationLog, resolve, reject });  
    processQueue();                                                 
  });
}


async function processQueue() {
  if (isProcessing || requestQueue.length === 0) return;  
  isProcessing = true;
  const { text, conversationLog, resolve, reject } = requestQueue.shift();
  try {
    const response = await sendWithRetry(text, conversationLog);
    resolve(response);                                    
  } catch (err) {
    reject(err);                                          
  } finally {
    isProcessing = false;                                 
    processQueue();                                       
  }
}