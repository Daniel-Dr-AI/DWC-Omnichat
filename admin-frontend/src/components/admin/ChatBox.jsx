import React, { useEffect, useState, useRef } from "react";
import fetchWithAuth from "../../fetchWithAuth";

const ChatBox = ({ conversation, onFollowupViewed }) => {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [replyText, setReplyText] = useState("");
  const [sending, setSending] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const wsRef = useRef(null);
  const viewedRef = useRef(new Set()); // Track which followups we've already marked as viewed

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (!conversation) {
      setMessages([]);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return;
    }

    // Mark followup as viewed when opened
    const markAsViewed = async () => {
      // Only mark if this is a followup (has 'id' field) and not already viewed
      if (conversation.id && !viewedRef.current.has(conversation.id)) {
        try {
          await fetchWithAuth(`/admin/api/followups/${conversation.id}/mark-viewed`, {
            method: "POST"
          });
          viewedRef.current.add(conversation.id); // Remember we marked this one
          // Notify parent to refresh count
          if (onFollowupViewed) {
            onFollowupViewed();
          }
        } catch (err) {
          console.error("Failed to mark followup as viewed:", err);
        }
      }
    };

    markAsViewed();

    const loadMessages = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchWithAuth(
          `/admin/api/messages/${encodeURIComponent(conversation.user_id)}/${encodeURIComponent(conversation.channel)}`
        );
        setMessages(data.messages || []);
      } catch (err) {
        console.error("Failed to load messages:", err);
        setError("Failed to load messages");
      } finally {
        setLoading(false);
      }
    };

    loadMessages();

    // Connect to user's WebSocket to receive live messages
    const token = localStorage.getItem("access_token");
    if (token) {
      try {
        const origin = window.location.origin;
        const wsScheme = origin.startsWith("https") ? "wss" : "ws";
        const wsUrl = `${wsScheme}://${window.location.host}/ws/${encodeURIComponent(conversation.user_id)}`;

        wsRef.current = new WebSocket(wsUrl);

        wsRef.current.onopen = () => {
          console.info(`✅ Connected to conversation WebSocket for ${conversation.user_id}`);
        };

        wsRef.current.onmessage = (ev) => {
          try {
            const data = JSON.parse(ev.data);

            // Handle typing indicator
            if (data.type === "typing") {
              setIsTyping(data.isTyping);
              return;
            }

            // Handle new messages
            if (data.sender && data.text) {
              setMessages(prev => [...prev, data]);
              setIsTyping(false);
            }
          } catch (e) {
            console.warn("Failed to parse WebSocket message:", e);
          }
        };

        wsRef.current.onerror = (error) => {
          console.error("WebSocket error:", error);
        };

        wsRef.current.onclose = () => {
          console.info("WebSocket connection closed");
        };
      } catch (e) {
        console.warn("Could not open conversation WebSocket:", e);
      }
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [conversation?.user_id, conversation?.channel]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!replyText.trim() || sending) return;

    setSending(true);
    const messageText = replyText.trim();
    setReplyText(""); // Clear input immediately for better UX

    try {
      await fetchWithAuth("/admin/api/send", {
        method: "POST",
        body: JSON.stringify({
          user_id: conversation.user_id,
          channel: conversation.channel,
          text: messageText
        })
      });

      // Message will be added via WebSocket when server broadcasts it
      // This prevents duplicate messages
    } catch (err) {
      console.error("Failed to send message:", err);
      alert("Failed to send message. Please try again.");
      // Restore the message text if send failed
      setReplyText(messageText);
    } finally {
      setSending(false);
    }
  };

  const handleEndChat = async () => {
    if (!confirm("Are you sure you want to end this chat and move it to history?")) {
      return;
    }

    try {
      await fetchWithAuth("/handoff/close", {
        method: "POST",
        body: JSON.stringify({
          user_id: conversation.user_id,
          channel: conversation.channel
        })
      });

      alert("Chat ended and moved to history");
      // Trigger parent component to refresh and clear selection
      window.location.reload();
    } catch (err) {
      console.error("Failed to end chat:", err);
      alert("Failed to end chat. Please try again.");
    }
  };

  const handleDeleteFollowup = async () => {
    if (!confirm("Are you sure you want to delete this followup?")) {
      return;
    }

    try {
      await fetchWithAuth(`/admin/api/followups/${conversation.id}`, {
        method: "DELETE"
      });

      alert("Followup deleted");
      window.location.reload();
    } catch (err) {
      console.error("Failed to delete followup:", err);
      alert("Failed to delete followup. Please try again.");
    }
  };

  if (!conversation) {
    return (
      <div className="w-1/2 flex items-center justify-center text-gray-500 bg-gray-50">
        Select a conversation to view.
      </div>
    );
  }

  // Check if this is a followup (has id field) vs a conversation
  const isFollowup = conversation.id !== undefined;

  return (
    <div className="w-1/2 flex flex-col h-full">
      <div className="flex items-center justify-between p-4 border-b bg-white">
        <h2 className="text-xl font-semibold">
          {isFollowup ? `Followup from ${conversation.name || conversation.user_id}` : `Chat with ${conversation.user_id}`}
        </h2>
        <button
          onClick={isFollowup ? handleDeleteFollowup : handleEndChat}
          className="px-4 py-2 bg-red-600 text-white rounded font-semibold hover:bg-red-700"
        >
          {isFollowup ? "Delete Followup" : "End Chat"}
        </button>
      </div>
      {!isFollowup && (
        <div className="text-sm text-gray-600 p-3 bg-gray-100 border-b">
          <strong>Channel:</strong> {conversation.channel} |
          <strong> Assigned:</strong> {conversation.assigned_staff || "Unassigned"}
        </div>
      )}

      <div className="flex-1 overflow-y-auto overflow-x-hidden p-4 bg-gray-50">
        {loading && <p className="text-gray-500">Loading messages...</p>}
        {error && <p className="text-red-500">{error}</p>}
        {!loading && !error && messages.length === 0 && (
          <p className="text-gray-500">No messages yet</p>
        )}
        {!loading && !error && messages.map((msg, idx) => (
          <div key={idx} className={`mb-3 p-3 rounded shadow-sm ${
            msg.sender === 'user' ? 'bg-blue-100 ml-0 mr-auto' : 'bg-green-100 ml-auto mr-0'
          } max-w-[70%]`} style={{overflowWrap: 'anywhere', wordBreak: 'break-word', hyphens: 'auto', WebkitHyphens: 'auto', MozHyphens: 'auto', msHyphens: 'auto'}}>
            <div className="text-xs text-gray-600 mb-1">
              <strong>{msg.sender === 'user' ? '👤 User' : '👨‍💼 Staff'}:</strong> {new Date(msg.ts).toLocaleTimeString()}
            </div>
            <div className="text-sm" style={{overflowWrap: 'anywhere', wordBreak: 'break-word', hyphens: 'auto'}}>{msg.text}</div>
          </div>
        ))}
        {isTyping && (
          <div className="text-gray-500 italic text-sm mb-2">
            👤 User is typing...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Display followup contact information if this is a followup */}
      {(conversation.name || conversation.email || conversation.phone || conversation.message) && (
        <div className="border-t bg-blue-50 p-4">
          <div className="text-sm font-semibold text-blue-900 mb-3">📧 Followup Contact Information</div>
          <div className="grid grid-cols-2 gap-3 mb-3">
            {conversation.name && (
              <div className="text-sm">
                <strong className="text-gray-700">Name:</strong>
                <div className="text-gray-900">{conversation.name}</div>
              </div>
            )}
            {conversation.email && (
              <div className="text-sm">
                <strong className="text-gray-700">Email:</strong>
                <div className="text-gray-900">{conversation.email}</div>
              </div>
            )}
            {conversation.phone && (
              <div className="text-sm">
                <strong className="text-gray-700">Phone:</strong>
                <div className="text-gray-900">{conversation.phone}</div>
              </div>
            )}
            {conversation.ts && (
              <div className="text-sm">
                <strong className="text-gray-700">Submitted:</strong>
                <div className="text-gray-900">{conversation.ts}</div>
              </div>
            )}
          </div>
          {conversation.message && (
            <div className="text-sm">
              <strong className="text-gray-700">Message:</strong>
              <div className="mt-1 p-3 bg-white rounded border border-blue-200 text-gray-900">
                {conversation.message}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="border-t bg-white p-4">
        <form onSubmit={handleSendMessage} className="flex gap-2">
          <input
            type="text"
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder="Type your reply..."
            className="flex-1 p-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={sending}
          />
          <button
            type="submit"
            disabled={sending || !replyText.trim()}
            className={`px-4 py-2 rounded font-semibold ${
              sending || !replyText.trim()
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {sending ? 'Sending...' : 'Send'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatBox;
