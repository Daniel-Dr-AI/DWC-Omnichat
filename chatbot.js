document.addEventListener("DOMContentLoaded", function () {
  // ========================
  // Create chat bubble + chat box
  // ========================
  const container = document.createElement("div");
  container.innerHTML = `
    <style>
      #chat-toggle {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: #2563eb;
        color: white;
        padding: 12px 16px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 20px;
        z-index: 9999;
      }
      #chat-box {
        position: fixed;
        bottom: 80px;
        right: 20px;
        width: 300px;
        height: 400px;
        border: 1px solid #ccc;
        background: white;
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        z-index: 9999;
      }
      #messages {
        flex: 1;
        overflow-y: auto;
        padding: 8px;
        font-family: Arial, sans-serif;
        font-size: 14px;
      }
      .user { color: blue; }
      .staff { color: green; }
      .system { color: #666; font-style: italic; }

      #typingIndicator {
        display: none;
        padding: 4px 10px;
        color: gray;
        font-style: italic;
      }
    </style>

    <div id="chat-toggle">💬</div>
    <div id="chat-box" style="display:none;">
      <div id="messages"></div>
      <div id="typingIndicator">Staff is typing<span id="typingDots">.</span></div>
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

  // Use Render URL (adjust to your deployed backend)
  const BASE_URL = "https://dwc-omnichat.onrender.com";

  // Persistent visitor ID
  let userId = localStorage.getItem("dwc_user_id");
  if (!userId) {
    userId = "visitor-" + Math.floor(Math.random() * 10000);
    localStorage.setItem("dwc_user_id", userId);
  }

  let ws;
  let typingTimeout = null;
  let typingDotTimer = null;

  function appendMessage(sender, text, type = "system") {
    const div = document.createElement("div");
    div.className = type;
    div.innerHTML = `<strong>${sender}:</strong> ${text}`;
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  function showTyping(show) {
    if (!typingIndicator || !typingDots) return;

    if (show) {
      typingIndicator.style.display = "block";
      if (typingDotTimer) clearInterval(typingDotTimer);
      let n = 1;
      typingDotTimer = setInterval(() => {
        n = (n % 3) + 1;
        typingDots.textContent = ".".repeat(n);
      }, 500);
    } else {
      typingIndicator.style.display = "none";
      if (typingDotTimer) clearInterval(typingDotTimer);
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
        console.log("[chatbot] WS received:", data);

        if (data.type === "typing" && data.sender === "staff") {
          showTyping(true);
          return;
        }

        if (data.type === "stop_typing" && data.sender === "staff") {
          showTyping(false);
          return;
        }

        appendMessage(data.sender || "System", data.text || "", data.sender || "system");
        showTyping(false); // Hide typing indicator on new message
      } catch (err) {
        console.warn("Failed to parse WS message", err);
      }
    };

    ws.onclose = () => {
      appendMessage("System", "Connection closed. Retrying...", "system");
      setTimeout(connectWS, 3000);
    };
  }

  // Typing detection
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

  // Send message
  sendBtn.addEventListener("click", () => {
    const text = msgInput.value.trim();
    if (!text) return;

    appendMessage("You", text, "user");

    fetch(`${BASE_URL}/webchat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, channel: "webchat", text }),
    }).then((res) => {
      console.log("[chatbot] Message sent:", res.status);
    });

    msgInput.value = "";
  });

  msgInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendBtn.click();
  });

  toggleBtn.addEventListener("click", () => {
    chatBox.style.display = chatBox.style.display === "none" ? "flex" : "none";
  });

  connectWS();
});
