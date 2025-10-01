(function () {
  // ========================
  // Config
  // ========================
  const BASE_URL = "http://127.0.0.1:8000";  // adjust if testing remotely
  // Stable visitor identity across reloads so admin sees the same convo
const userId = (() => {
  try {
    const k = "dwc_user_id";
    const existing = localStorage.getItem(k);
    if (existing) return existing;
    const fresh = "visitor-" + Math.floor(Math.random() * 1000000);
    localStorage.setItem(k, fresh);
    return fresh;
  } catch {
    // If localStorage is blocked, fall back to random per load
    return "visitor-" + Math.floor(Math.random() * 1000000);
  }
})();
  let ws;
  const messagesDiv = document.getElementById("msgs");
  const msgInput = document.getElementById("msgInput");
  const sendBtn = document.getElementById("sendBtn");

  // Typing state
  let lastTypingSent = 0;
  let stopTypingTimeout = null;

  // ========================
  // Helpers
  // ========================
  function appendMessage(sender, text, type = "system") {
    const div = document.createElement("div");
    div.className = type; // user | bot | system
    div.innerHTML = `<strong>${sender}:</strong> ${text}`;
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  function connectWS() {
    const wsUrl = BASE_URL.replace("https", "wss").replace("http", "ws") + `/ws/${userId}`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => appendMessage("System", "Connected to chat.", "system");

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        appendMessage(data.sender || "Bot", data.text, "bot");
      } catch {
        appendMessage("System", "⚠️ Invalid server message", "system");
      }
    };

    ws.onclose = () => {
      appendMessage("System", "Connection closed. Retrying...", "system");
      ws = null;
      setTimeout(connectWS, 3000);
    };
  }

  // ========================
  // Events
  // ========================
  // Handle typing presence
  msgInput.addEventListener("input", () => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const now = Date.now();
    if (now - lastTypingSent > 2000) { // throttle ~1 per 2s
      try { ws.send(JSON.stringify({ type: "typing" })); } catch {}
      lastTypingSent = now;
    }
    if (stopTypingTimeout) clearTimeout(stopTypingTimeout);
    stopTypingTimeout = setTimeout(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        try { ws.send(JSON.stringify({ type: "stop_typing" })); } catch {}
      }
    }, 1500);
  });

  // Handle send button
  sendBtn.addEventListener("click", async () => {
    const text = msgInput.value.trim();
    if (!text) return;

    appendMessage("You", text, "user");
    msgInput.value = "";

    // best-effort: signal stop typing immediately on send
    try { if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "stop_typing" })); } catch {}

    try {
      await fetch(`${BASE_URL}/webchat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, channel: "webchat", text })
      });
    } catch (err) {
      appendMessage("System", "Error sending message.", "system");
    }
  });

  // ========================
  // Init
  // ========================
  connectWS();
})();
