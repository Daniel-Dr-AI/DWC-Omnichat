document.addEventListener("DOMContentLoaded", function () {
  // ========================
  // Create chat bubble + chat box
  // ========================
  const container = document.createElement("div");
  container.innerHTML = `
    <div id="chat-toggle">💬</div>
    <div id="chat-box" style="display:none; flex-direction:column;">
      <div id="messages" style="flex:1; overflow-y:auto; padding:8px;"></div>

      <!-- ✅ Typing indicator -->
      <div id="typingIndicator" style="display:none; padding:4px; font-style:italic; color:gray;">
        Staff is typing<span id="typingDots">.</span>
      </div>

      <div id="input-box" style="display:flex; gap:4px; padding:8px;">
        <input id="msgInput" type="text" placeholder="Type a message..." style="flex:1;" />
        <button id="sendBtn">Send</button>
      </div>
    </div>
  `;
  document.body.appendChild(container);

  // References
  const toggleBtn = document.getElementById("chat-toggle");
  const chatBox = document.getElementById("chat-box");
  const msgInput = document.getElementById("msgInput");
  const sendBtn = document.getElementById("sendBtn");
  const messagesDiv = document.getElementById("messages");
  const typingIndicator = document.getElementById("typingIndicator");
  const typingDots = document.getElementById("typingDots");

  // 🔑 Render backend (adjust if self-hosted)
  const BASE_URL = "https://dwc-omnichat.onrender.com";

  // Persistent visitor ID
  let userId = localStorage.getItem("dwc_user_id");
  if (!userId) {
    userId = "visitor-" + Math.floor(Math.random() * 10000);
    localStorage.setItem("dwc_user_id", userId);
  }

  let ws;
  let typingTimeout;
  let typingTimer = null;
  let typingAutoHideTimer = null;

  // ========================
  // Helpers
  // ========================
  function appendMessage(sender, text, type = "system") {
    const div = document.createElement("div");
    div.className = type; // user | staff | system
    div.innerHTML = `<strong>${sender}:</strong> ${text}`;
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  function showTyping(show) {
    if (!typingIndicator || !typingDots) return;
    if (show) {
      typingIndicator.style.display = "block";
      let n = 1;
      if (typingTimer) clearInterval(typingTimer);
      typingTimer = setInterval(() => {
        n = (n % 3) + 1;
        typingDots.textContent = ".".repeat(n);
      }, 500);

      if (typingAutoHideTimer) clearTimeout(typingAutoHideTimer);
      typingAutoHideTimer = setTimeout(() => showTyping(false), 3000);
    } else {
      typingIndicator.style.display = "none";
      if (typingTimer) clearInterval(typingTimer);
      if (typingAutoHideTimer) clearTimeout(typingAutoHideTimer);
      typingDots.textContent = ".";
    }
  }

  function connectWS() {
    const wsUrl = BASE_URL.replace("https", "wss") + `/ws/${userId}`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => appendMessage("System", "Connected to chat.", "system");

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("[chatbot] WS message received:", data);

        if (data.type === "typing") {
          showTyping(true);
          return;
        }
        if (data.type === "stop_typing") {
          showTyping(false);
          return;
        }

        appendMessage(data.sender || "system", data.text || "", data.sender || "system");
      } catch {
        appendMessage("System", "⚠️ Invalid server message", "system");
      }
    };

    ws.onclose = () => {
      appendMessage("System", "Connection closed. Retrying...", "system");
      setTimeout(connectWS, 3000);
    };
  }

  // ========================
  // Typing events
  // ========================
  msgInput.addEventListener("input", () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "typing" }));
    }
    clearTimeout(typingTimeout);
    typingTimeout = setTimeout(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "stop_typing" }));
      }
    }, 1500);
  });

  // ========================
  // Send message
  // ========================
  sendBtn.addEventListener("click", () => {
    const text = msgInput.value.trim();
    if (!text) return;

    appendMessage("You", text, "user");

    fetch(`${BASE_URL}/webchat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, channel: "webchat", text }),
    }).then((res) => console.log("[chatbot] POST /webchat response:", res.status));

    msgInput.value = "";
  });

  msgInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendBtn.click();
  });

  // ========================
  // Toggle
  // ========================
  toggleBtn.addEventListener("click", () => {
    chatBox.style.display = chatBox.style.display === "none" ? "flex" : "none";
  });

  // Start WS
  connectWS();
});
