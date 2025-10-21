import React, { useEffect, useState, useRef } from "react";
import fetchWithAuth from "../../fetchWithAuth";

// Props: type (tab) and onSelect callback
const ConversationList = ({ onSelect = () => {} }) => {
  const [conversations, setConversations] = useState([]);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    let mounted = true;

    const loadConversations = async () => {
      try {
        // Use relative path so proxy or production origin works
        const data = await fetchWithAuth("/admin/api/convos");
        if (!mounted) return;
        setConversations(data.conversations || []);
      } catch (err) {
        console.error("Failed to fetch conversations:", err);
        if (!mounted) return;
        setError(err.message || "Failed to load");
      }
    };

    loadConversations();

    // Open admin websocket to receive live updates
    // ✅ Get JWT token from localStorage for authentication
    const token = localStorage.getItem("access_token");

    if (!token) {
      console.error("❌ No access token available for WebSocket - user not authenticated");
      setError("Authentication required. Please log in.");
      return;
    }

    try {
      const origin = window.location.origin;
      const wsScheme = origin.startsWith("https") ? "wss" : "ws";

      // ✅ Pass token as query parameter for WebSocket authentication
      const wsUrl = `${wsScheme}://${window.location.host}/admin-ws?token=${encodeURIComponent(token)}`;
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.info("✅ [admin] Authenticated connection to admin-ws established");
      };

      wsRef.current.onerror = (error) => {
        console.error("❌ [admin] WebSocket error:", error);
      };

      wsRef.current.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);

          // Handle ping/pong for heartbeat
          if (data.type === "ping") {
            wsRef.current.send(JSON.stringify({ type: "pong" }));
            return;
          }

          // server may send { type: 'snapshot', data } on connect
          if (data && data.type === "snapshot" && data.data) {
            setConversations((prev) => {
              // merge snapshot entry into list
              const existing = prev.filter((p) => !(p.user_id === data.data.user_id && p.channel === data.data.channel));
              return [
                { ...data.data },
                ...existing,
              ];
            });
            return;
          }

          // or server may send incremental enriched objects (no `type`)
          if (data && data.user_id) {
            setConversations((prev) => {
              const others = prev.filter((p) => !(p.user_id === data.user_id && p.channel === data.channel));
              // prefer to keep messages array or counts if present
              return [{ ...data }, ...others];
            });
            return;
          }
        } catch (e) {
          console.warn("Failed to parse admin-ws message", e, ev.data);
        }
      };

      wsRef.current.onclose = (event) => {
        console.info(`[admin] admin-ws closed (code: ${event.code}, reason: ${event.reason})`);

        // Handle authentication failures (WebSocket error codes)
        // 1008 = Policy Violation (authentication failure)
        // 1003 = Unsupported Data (unauthorized role)
        if (event.code === 1008 || event.code === 1003) {
          console.error("🔐 WebSocket authentication failed - redirecting to login");
          localStorage.removeItem("access_token");
          window.location.href = "/login";
        }
      };
    } catch (e) {
      console.warn("Could not open admin websocket", e);
      setError("Failed to establish WebSocket connection");
    }

    return () => { mounted = false; if (wsRef.current) wsRef.current.close(); };
  }, []);

  if (error) {
    return <div className="text-red-500">Error: {error}</div>;
  }

  return (
    <div className="conversation-list p-4 w-1/2">
      <h2 className="text-lg font-bold mb-4">Open Conversations</h2>
      {Array.isArray(conversations) && conversations.length === 0 && (
        <div className="text-gray-500">No open conversations</div>
      )}

      {Array.isArray(conversations) && conversations.map((convo, idx) => (
        <div key={`${convo.user_id}-${convo.channel}-${idx}`} className="p-2 border-b flex justify-between items-start">
          <div>
            <div><strong>User:</strong> {convo.user_id}</div>
            <div><strong>Channel:</strong> {convo.channel}</div>
            <div><strong>Assigned:</strong> {convo.assigned_staff || "—"}</div>
            <div><strong>Updated:</strong> {convo.last_updated || convo.updated_at || "-"}</div>
            <div><strong>Messages:</strong> {Array.isArray(convo.messages) ? convo.messages.length : (convo.message_count || "—")}</div>
          </div>
          <div>
            <button className="px-3 py-1 bg-blue-600 text-white rounded" onClick={() => onSelect(convo)}>Open</button>
          </div>
        </div>
      ))}
    </div>
  );
};

export default ConversationList;
