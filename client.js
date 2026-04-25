// client.js
// This file is the CLIENT side connection library.
// It contains helper functions that handle:
//   1. Checking internet connection before sending
//   2. Building conversation history to give the AI context
//   3. Sending the request with a timeout and automatic retry
// These helpers are called by the send() function in index.html

const SERVER_ENDPOINT = "/api";  // the URL of our server endpoint on Vercel
const MAX_RETRIES     = 3;       // how many times to retry if the server doesn't respond
const TIMEOUT_MS      = 15000;   // cancel the request if server takes longer than 15 seconds
const HISTORY_LIMIT   = 6;       // how many past messages to send for context (3 exchanges)

// Checks if the browser has an active internet connection before sending
function isOnline() {
  return navigator.onLine;  // built-in browser property — true if connected, false if not
}

// Builds a short conversation history array to give the AI context of past messages
function buildHistory(conversationLog) {
  const recent = conversationLog.slice(-HISTORY_LIMIT);    // grab the last 6 messages
  return recent.map(m => ({
    role: m.role === 'ai' ? 'assistant' : 'user',           // format roles for the AI
    content: m.text                                          // just the message text
  }));
}

// Attempts to contact the server once — cancels automatically after TIMEOUT_MS
async function attemptRequest(text, conversationLog) {
  const controller = new AbortController();                           // lets us cancel the request
  const timeout    = setTimeout(() => controller.abort(), TIMEOUT_MS); // cancel after 15 seconds

  const response = await fetch(SERVER_ENDPOINT, {
    method: "POST",                                      // POST because we are sending data
    headers: { "Content-Type": "application/json" },    // tell the server to expect JSON
    body: JSON.stringify({
      question: text,                                    // the user's current message
      history: buildHistory(conversationLog)             // last few messages for context
    }),
    signal: controller.signal                            // attach the timeout controller
  });

  clearTimeout(timeout);                                 // clear timer if response arrived in time
  if (!response.ok) throw new Error(`Server error: ${response.status}`);
  return response;
}

// Retries the request up to MAX_RETRIES times if it fails
// Waits 1s after first fail, 2s after second, 3s after third
async function sendWithRetry(text, conversationLog) {
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      return await attemptRequest(text, conversationLog);   // try sending the request
    } catch (err) {
      if (attempt === MAX_RETRIES) throw err;               // all retries failed — give up
      await new Promise(r => setTimeout(r, 1000 * attempt)); // wait before retrying
    }
  }
}