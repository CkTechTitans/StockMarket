/* ═══════════════════════════════════════════════
   Market Pulse — chatbot.js
   Floating chatbot — calls backend /api/chat
   General Indian stock market assistant
   ═══════════════════════════════════════════════ */

//const CHAT_API = "http://localhost:5000/api/chat";
const API = "";
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

  <button id="voiceBtn" onclick="startVoice()">🎤</button>

  <button id="chatSendBtn" onclick="sendChat()">
    ➤
  </button>
</div>
  `);
  makeChatDraggable();
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

function appendBotMsgStreaming(text) {
  const chat = document.getElementById("chatMessages");

  const time = new Date().toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit"
  });

  const wrapper = document.createElement("div");
  wrapper.className = "chat-msg bot";

  wrapper.innerHTML = `
    <div class="chat-bubble bot-bubble" id="streamingBubble"></div>
    <div class="chat-time">${time}</div>
  `;

  chat.appendChild(wrapper);
  scrollChat();

  const bubble = wrapper.querySelector("#streamingBubble");

  let i = 0;

  function typeChar() {
    if (i < text.length) {
      bubble.innerHTML = formatBotText(text.slice(0, i + 1));
      i++;
      scrollChat();
      setTimeout(typeChar, 12); // speed (lower = faster)
    }
  }

  typeChar();
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
    appendBotMsgStreaming(reply);
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
function startVoice() {
  const btn = document.getElementById("voiceBtn");
  const input = document.getElementById("chatInput");

  if (!('webkitSpeechRecognition' in window)) {
    alert("Voice not supported in this browser");
    return;
  }

  const rec = new webkitSpeechRecognition();
  rec.lang = "en-IN";
  rec.continuous = false;

  // 🎤 START RECORDING UI
  btn.classList.add("recording");
  input.classList.add("recording");
  input.placeholder = "🎤 Listening... speak now";

  rec.start();

  rec.onresult = (e) => {
    const text = e.results[0][0].transcript;
    input.value = text;
  };

  rec.onend = () => {
    // 🔴 STOP RECORDING UI
    btn.classList.remove("recording");
    input.classList.remove("recording");
    input.placeholder = "Ask about Indian stocks...";
  };

  rec.onerror = () => {
    btn.classList.remove("recording");
    input.classList.remove("recording");
    input.placeholder = "Ask about Indian stocks...";
  };
}
function makeChatDraggable() {
  const panel = document.getElementById("chatPanel");
  const header = panel.querySelector(".chat-header");

  let isDragging = false;
  let offsetX = 0;
  let offsetY = 0;

  header.addEventListener("mousedown", (e) => {
    isDragging = true;

    const rect = panel.getBoundingClientRect();
    offsetX = e.clientX - rect.left;
    offsetY = e.clientY - rect.top;

    panel.style.transition = "none"; // smoother drag
  });

  document.addEventListener("mousemove", (e) => {
    if (!isDragging) return;

    panel.style.left = (e.clientX - offsetX) + "px";
    panel.style.top  = (e.clientY - offsetY) + "px";

    panel.style.right = "auto";
    panel.style.bottom = "auto";
  });

  document.addEventListener("mouseup", () => {
    isDragging = false;
  });
}
let isDragging = false;
let offsetX, offsetY;

const panel = document.getElementById("chatPanel");
const header = document.querySelector(".chat-header");

header.addEventListener("mousedown", (e) => {
  isDragging = true;
  offsetX = e.clientX - panel.offsetLeft;
  offsetY = e.clientY - panel.offsetTop;
  header.style.cursor = "grabbing";
});

document.addEventListener("mousemove", (e) => {
  if (!isDragging) return;
  panel.style.left = (e.clientX - offsetX) + "px";
  panel.style.top  = (e.clientY - offsetY) + "px";
  panel.style.right = "auto";
  panel.style.bottom = "auto";
});

document.addEventListener("mouseup", () => {
  isDragging = false;
  header.style.cursor = "grab";
});

function formatBotText(text) {
  let formatted = text;

  // Bold headings
  formatted = formatted.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

  // Convert bullets
  formatted = formatted.replace(/^\s*[\*\-]\s+(.*)$/gm, "<li>$1</li>");

  // Wrap list properly
  formatted = formatted.replace(/(<li>.*<\/li>)/gs, "<ul class='chat-list'>$1</ul>");

  // Highlight keywords
  formatted = formatted.replace(
    /\b(FII|DII|IPO|P\/E|RSI|MACD|Sensex|Nifty)\b/g,
    "<span class='highlight'>$1</span>"
  );

  // Line breaks
  formatted = formatted.replace(/\n/g, "<br>");

  return formatted;
}