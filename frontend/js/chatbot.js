/* ═══════════════════════════════════════════════
   Market Pulse — chatbot.js
   Floating chatbot — calls backend /api/chat
   General Indian stock market assistant
   ═══════════════════════════════════════════════ */

const CHAT_API = "http://localhost:5000/api/chat";

let chatOpen    = false;
let chatHistory = [];

function initChatbot() {
  document.body.insertAdjacentHTML("beforeend", `
    <button id="chatFab" onclick="toggleChat()" title="Market Pulse AI">
      <svg id="fabIconOpen" width="24" height="24" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
      </svg>
      <svg id="fabIconClose" width="24" height="24" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
        style="display:none">
        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
      </svg>
    </button>

    <div id="chatPanel">
      <div class="chat-header">
        <div class="chat-header-left">
          <div class="chat-avatar">📈</div>
          <div>
            <div class="chat-title">Market Pulse AI</div>
            <div class="chat-subtitle">Indian Stock Market Assistant</div>
          </div>
        </div>
        <button class="chat-close-btn" onclick="toggleChat()">✕</button>
      </div>

      <div class="chat-messages" id="chatMessages"></div>

      <div class="chat-suggestions" id="chatSuggestions">
        <button class="chat-sug" onclick="sendSuggestion('What are the top gainers today?')">Top gainers today?</button>
        <button class="chat-sug" onclick="sendSuggestion('How does Sensex differ from Nifty?')">Sensex vs Nifty?</button>
        <button class="chat-sug" onclick="sendSuggestion('What is a good P/E ratio for Indian stocks?')">Good P/E ratio?</button>
        <button class="chat-sug" onclick="sendSuggestion('Explain FII and DII in Indian markets')">FII & DII?</button>
      </div>

      <div class="chat-input-row">
        <input id="chatInput" type="text" placeholder="Ask about Indian stocks..."
          autocomplete="off"
          onkeydown="if(event.key==='Enter') sendChat()"/>
        <button id="chatSendBtn" onclick="sendChat()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2.5"
            stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
    </div>
  `);

  appendBotMsg("👋 Hi! I'm your Indian stock market assistant. Ask me anything — stocks, sectors, IPOs, trading strategies, or market terms.");
}

function toggleChat() {
  chatOpen = !chatOpen;
  document.getElementById("chatPanel").classList.toggle("open", chatOpen);
  document.getElementById("chatFab").classList.toggle("open", chatOpen);
  document.getElementById("fabIconOpen").style.display  = chatOpen ? "none"  : "block";
  document.getElementById("fabIconClose").style.display = chatOpen ? "block" : "none";
  if (chatOpen) setTimeout(() => document.getElementById("chatInput").focus(), 200);
}

function appendUserMsg(text) {
  const time = new Date().toLocaleTimeString("en-IN", {hour:"2-digit", minute:"2-digit"});
  document.getElementById("chatMessages").insertAdjacentHTML("beforeend",
    `<div class="chat-msg user">
      <div class="chat-bubble user-bubble">${escapeHtml(text)}</div>
      <div class="chat-time">${time}</div>
    </div>`);
  scrollChat();
}

function appendBotMsg(text) {
  const time = new Date().toLocaleTimeString("en-IN", {hour:"2-digit", minute:"2-digit"});
  document.getElementById("chatMessages").insertAdjacentHTML("beforeend",
    `<div class="chat-msg bot">
      <div class="chat-bubble bot-bubble">${text}</div>
      <div class="chat-time">${time}</div>
    </div>`);
  scrollChat();
}

function showTyping() {
  document.getElementById("chatMessages").insertAdjacentHTML("beforeend",
    `<div class="chat-msg bot" id="typingMsg">
      <div class="chat-bubble bot-bubble typing-bubble">
        <span></span><span></span><span></span>
      </div>
    </div>`);
  scrollChat();
}

function hideTyping() {
  const el = document.getElementById("typingMsg");
  if (el) el.remove();
}

function scrollChat() {
  const el = document.getElementById("chatMessages");
  el.scrollTop = el.scrollHeight;
}

function escapeHtml(t) {
  return t.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

async function sendChat() {
  const input = document.getElementById("chatInput");
  const msg   = input.value.trim();
  if (!msg) return;

  input.value = "";
  document.getElementById("chatSendBtn").disabled = true;
  document.getElementById("chatSuggestions").style.display = "none";

  appendUserMsg(msg);
  chatHistory.push({ role: "user", text: msg });
  showTyping();

  try {
    const res = await fetch(CHAT_API, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ message: msg, history: chatHistory.slice(-10) })
    });
    const data = await res.json();
    hideTyping();
    const reply = data.reply || data.error || "Sorry, something went wrong.";
    appendBotMsg(reply.replace(/\n/g, "<br>"));
    chatHistory.push({ role: "model", text: reply });
  } catch(e) {
    hideTyping();
    appendBotMsg("Could not reach the server. Is the backend running?");
  } finally {
    document.getElementById("chatSendBtn").disabled = false;
    input.focus();
  }
}

function sendSuggestion(text) {
  document.getElementById("chatInput").value = text;
  sendChat();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initChatbot);
} else {
  initChatbot();
}