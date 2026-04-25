// client.js
// This is the CLIENT side of the application.
// It is responsible for:
//   1. Checking the connection before sending anything
//   2. Packaging the user's message + chat history and sending it to the server
//   3. Reading the server's response as a live stream, word by word
//   4. Retrying the request automatically if the server fails to respond

const SERVER_ENDPOINT = "/api";  // the URL of our server endpoint on Vercel
const MAX_RETRIES     = 3;       // how many times to retry if the server doesn't respond
const TIMEOUT_MS      = 15000;   // cancel the request if server takes longer than 15 seconds
const HISTORY_LIMIT   = 6;       // how many past messages to send for context (3 exchanges)

// Builds a short conversation history from the log to give the AI context
function buildHistory() {
  const recent = conversationLog.slice(-HISTORY_LIMIT);   // grab the last 6 messages
  return recent.map(m => ({
    role: m.role === 'ai' ? 'assistant' : 'user',          // format roles for the AI
    content: m.text                                         // just the message text
  }));
}

// Checks if the browser has an active internet connection before sending
function isOnline() {
  return navigator.onLine;  // built-in browser property — true if connected, false if not
}

// Attempts to contact the server once — returns the response or throws an error
async function attemptRequest(text) {
  const controller = new AbortController();                          // lets us cancel the request
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS); // cancel after 15 seconds

  const response = await fetch(SERVER_ENDPOINT, {
    method: "POST",                                     // POST because we are sending data
    headers: { "Content-Type": "application/json" },   // tell the server to expect JSON
    body: JSON.stringify({
      question: text,                                   // the user's current message
      history: buildHistory()                           // the last few messages for context
    }),
    signal: controller.signal                           // attach the timeout controller
  });

  clearTimeout(timeout);                  // cancel the timeout timer if we got a response in time
  if (!response.ok) throw new Error(`Server error: ${response.status}`); // stop if server errored
  return response;                        // return the response to be streamed
}

// Sends the request to the server — retries up to MAX_RETRIES times if it fails
async function sendWithRetry(text) {
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      return await attemptRequest(text);   // try sending the request
    } catch (err) {
      if (attempt === MAX_RETRIES) throw err;  // if all retries failed, give up and throw
      await new Promise(r => setTimeout(r, 1000 * attempt)); // wait 1s, 2s, 3s between retries
    }
  }
}

// Main function — sends the message and streams the AI's response back into the chat
async function sendAIRequest(text, typingEl) {
  const t = typingEl || addTypingIndicator();  // show typing indicator while waiting

  // --- Step 1: Check internet connection before doing anything ---
  if (!isOnline()) {
    if (t) t.remove();
    addMsg('ai', 'No internet connection detected. Please check your network and try again.');
    setWaiting(false);
    return;
  }

  try {
    // --- Step 2: Send the request (with automatic retry if it fails) ---
    const response = await sendWithRetry(text);

    // --- Step 3: Open a stream to read the response chunk by chunk ---
    const reader  = response.body.getReader();  // opens a live reading channel from the server
    const decoder = new TextDecoder();          // converts raw server bytes into readable text
    t.remove();                                 // remove typing indicator once stream starts

    const wrap = document.createElement('div'); wrap.className = 'msg ai';
    const ts = document.createElement('div'); ts.className = 'timestamp'; ts.textContent = fmtTime(); wrap.appendChild(ts);
    const content = document.createElement('div'); content.className = 'msg-content';
    const md = document.createElement('div'); md.className = 'ai-md'; content.appendChild(md); wrap.appendChild(content);
    msgsEl.appendChild(wrap);

    // --- Step 4: Read the stream until the server signals it is done ---
    let accumulated = '';
    while (true) {
      const { done, value } = await reader.read();               // read one chunk from server
      if (done) break;                                           // server finished, exit loop
      accumulated += decoder.decode(value, { stream: true });    // decode bytes into text
      md.innerHTML = marked.parse(accumulated);                  // render markdown live
      if (accumulated.includes('```')) Prism.highlightAllUnder(md); // highlight code blocks
      scrollDown();
    }

    wrap.appendChild(makeActionsRow(accumulated, true, wrap, text));        // add action buttons
    conversationLog.push({ role: 'ai', text: accumulated, time: fmtTime() }); // save to history

  } catch (err) {
    if (t) t.remove();
    const msg = err.name === 'AbortError'
      ? 'The request timed out. The server took too long to respond. Please try again.'
      : 'Connection failed after multiple attempts. Please try again.';
    addMsg('ai', msg);   // show a clear, specific error message in the chat
    console.error(err);
  } finally {
    setWaiting(false);   // always re-enable input when done, whether success or failure
  }
}

// Triggered when the user hits send — validates input then calls sendAIRequest
async function send(override) {
  const text = override || promptEl.value.trim();
  if (!text || waiting) return;   // do nothing if empty or already waiting for a response
  addMsg('user', text, null);     // show user message in chat immediately
  promptEl.value = '';
  resizeTa();
  charCounter.textContent = '';
  charCounter.className = 'char-counter';
  setWaiting(true);               // lock the input while waiting for server response
  conversationLog.push({ role: 'user', text, time: fmtTime() }); // save to history
  const t = addTypingIndicator();
  await sendAIRequest(text, t);   // send to server and stream the response back
}