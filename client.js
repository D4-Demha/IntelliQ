// client.js
// CLIENT side connection library: helpers called by send() in index.html
// Handles: connection check, history building, request ID, queue, timeout, retry

const SERVER_ENDPOINT = "/api";   // server endpoint on Vercel
const MAX_RETRIES     = 3;        // retry attempts before giving up
const TIMEOUT_MS      = 15000;    // cancel request after 15 seconds
const HISTORY_LIMIT   = 6;        // last 6 messages sent for AI context
const MAX_PAYLOAD_KB  = 20;       // maximum request size in kilobytes

let requestQueue   = [];          // holds pending requests if one is already running
let isProcessing   = false;       // flag: true when a request is currently in progress

// Generates a short unique ID to track each request in the console logs
function generateRequestId() {
  return 'req_' + Math.random().toString(36).slice(2, 7);  // e.g. req_x4k2p
}

// Checks if the browser has an active internet connection
function isOnline() {
  return navigator.onLine;  // built-in browser API: true if connected, false if not
}

// Builds conversation history from the log to give the AI context
function buildHistory(conversationLog) {
  return conversationLog.slice(-HISTORY_LIMIT).map(m => ({
    role: m.role === 'ai' ? 'assistant' : 'user',  // format roles for the AI
    content: m.text
  }));
}

// Checks the payload size before sending: blocks anything unreasonably large
function isPayloadSafe(payload) {
  const sizeKB = new Blob([payload]).size / 1024;          // calculate size in KB
  if (sizeKB > MAX_PAYLOAD_KB) {
    console.warn(`Payload too large: ${sizeKB.toFixed(1)}KB: blocked`);
    return false;
  }
  return true;
}

// Attempts to contact the server once with a timeout
async function attemptRequest(text, conversationLog, requestId) {
  const payload    = JSON.stringify({ question: text, history: buildHistory(conversationLog) });
  const controller = new AbortController();                             // lets us cancel the request
  const timeout    = setTimeout(() => controller.abort(), TIMEOUT_MS); // cancel after 15 seconds

  if (!isPayloadSafe(payload)) throw new Error("Payload too large");   // block oversized requests

  console.log(`[${requestId}] Sending request to server...`);          // log when request leaves client

  const response = await fetch(SERVER_ENDPOINT, {
    method: "POST",                                       // POST because we are sending data
    headers: { "Content-Type": "application/json" },     // tell server to expect JSON
    body: payload,
    signal: controller.signal                             // attach the timeout controller
  });

  clearTimeout(timeout);                                  // clear timer if response arrived in time
  if (!response.ok) throw new Error(`Server error: ${response.status}`);
  console.log(`[${requestId}] Response received: starting stream`);   // log when stream begins
  return response;
}

// Retries the request up to MAX_RETRIES times with increasing wait between attempts
async function sendWithRetry(text, conversationLog) {
  const requestId = generateRequestId();                  // stamp this request with a unique ID
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      return await attemptRequest(text, conversationLog, requestId);
    } catch (err) {
      console.warn(`[${requestId}] Attempt ${attempt} failed: ${err.message}`);
      if (attempt === MAX_RETRIES) throw err;             // all retries failed: give up
      await new Promise(r => setTimeout(r, 1000 * attempt)); // wait 1s, 2s, 3s between retries
    }
  }
}

// Queues the request if another one is already running: processes them in order
async function queueRequest(text, conversationLog) {
  return new Promise((resolve, reject) => {
    requestQueue.push({ text, conversationLog, resolve, reject });  // add to queue
    processQueue();                                                  // try to process immediately
  });
}

// Processes the next request in the queue: one at a time
async function processQueue() {
  if (isProcessing || requestQueue.length === 0) return;  // exit if busy or queue is empty
  isProcessing = true;
  const { text, conversationLog, resolve, reject } = requestQueue.shift();  // take next request
  try {
    const response = await sendWithRetry(text, conversationLog);
    resolve(response);                                    // pass the response back to the caller
  } catch (err) {
    reject(err);                                          // pass the error back to the caller
  } finally {
    isProcessing = false;                                 // mark as free
    processQueue();                                       // check if more requests are waiting
  }
}