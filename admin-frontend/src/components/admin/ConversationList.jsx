import React, { useEffect, useState, useRef } from "react";
import fetchWithAuth from "../../fetchWithAuth";

// Props: type (tab) and onSelect callback
const ConversationList = ({ type = "open", onSelect = () => {} }) => {
  const [conversations, setConversations] = useState([]);
  const [error, setError] = useState(null);
  const [selectedConvos, setSelectedConvos] = useState(new Set());
  const [isEndingChats, setIsEndingChats] = useState(false);
  const [exportDays, setExportDays] = useState(30);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    let mounted = true;

    const loadConversations = async () => {
      try {
        // Map tab type to API endpoint
        const endpointMap = {
          "open": "/admin/api/convos",
          "escalated": "/admin/api/escalated",
          "followups": "/admin/api/followups",
          "history": "/admin/api/history"
        };

        const endpoint = endpointMap[type] || "/admin/api/convos";
        const data = await fetchWithAuth(endpoint);
        if (!mounted) return;

        // Different endpoints return data with different keys
        let convos = [];
        if (type === "followups") {
          convos = data.followups || [];
        } else if (type === "history") {
          convos = data.history || [];
        } else {
          convos = data.conversations || [];
        }

        setConversations(convos);
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
  }, [type]); // Reload when tab type changes

  // Multi-select handlers
  const getConvoKey = (convo) => {
    // For followups, use the id field. For conversations, use user_id-channel
    return type === "followups" ? String(convo.id) : `${convo.user_id}-${convo.channel}`;
  };

  const toggleSelectConvo = (convo) => {
    const key = getConvoKey(convo);
    setSelectedConvos(prev => {
      const newSet = new Set(prev);
      if (newSet.has(key)) {
        newSet.delete(key);
      } else {
        newSet.add(key);
      }
      return newSet;
    });
  };

  const selectAll = () => {
    const allKeys = conversations.map(c => getConvoKey(c));
    setSelectedConvos(new Set(allKeys));
  };

  const clearSelection = () => {
    setSelectedConvos(new Set());
  };

  const handleBulkEndChats = async () => {
    if (selectedConvos.size === 0) return;

    if (!confirm(`Are you sure you want to end ${selectedConvos.size} chat(s)?`)) {
      return;
    }

    setIsEndingChats(true);

    try {
      // Convert selected keys to array of {user_id, channel} objects
      const convosToEnd = Array.from(selectedConvos).map(key => {
        const lastHyphenIndex = key.lastIndexOf('-');
        const user_id = key.substring(0, lastHyphenIndex);
        const channel = key.substring(lastHyphenIndex + 1);
        return { user_id, channel };
      });

      await fetchWithAuth("/handoff/close-bulk", {
        method: "POST",
        body: JSON.stringify({ conversations: convosToEnd })
      });

      alert(`Successfully ended ${selectedConvos.size} chat(s)`);
      clearSelection();

      // Refresh the conversation list
      window.location.reload();
    } catch (err) {
      console.error("Failed to bulk end chats:", err);
      alert("Failed to end some chats. Please try again.");
    } finally {
      setIsEndingChats(false);
    }
  };

  const handleBulkDeleteFollowups = async () => {
    if (selectedConvos.size === 0) return;

    if (!confirm(`Are you sure you want to delete ${selectedConvos.size} followup(s)?`)) {
      return;
    }

    setIsEndingChats(true); // Reuse the same loading state

    try {
      // For followups, the key is just the ID
      const followupIds = Array.from(selectedConvos).map(key => parseInt(key));

      // Delete each followup
      await Promise.all(
        followupIds.map(id =>
          fetchWithAuth(`/admin/api/followups/${id}`, {
            method: "DELETE"
          })
        )
      );

      alert(`Successfully deleted ${selectedConvos.size} followup(s)`);
      clearSelection();

      // Refresh the conversation list
      window.location.reload();
    } catch (err) {
      console.error("Failed to bulk delete followups:", err);
      alert("Failed to delete some followups. Please try again.");
    } finally {
      setIsEndingChats(false);
    }
  };

  const handleExportHistory = async () => {
    try {
      const data = await fetchWithAuth(`/admin/api/history/export?days=${exportDays}`);

      // Convert to CSV
      const csv = convertToCSV(data.history);

      // Download file
      downloadCSV(csv, `history_last_${exportDays}_days.csv`);

      alert(`Exported ${data.count} history records`);
      setShowExportDialog(false);
    } catch (err) {
      console.error("Failed to export history:", err);
      alert("Failed to export history. Please try again.");
    }
  };

  const handleExportAndDelete = async () => {
    if (!confirm("This will export ALL history and DELETE records older than 30 days. Continue?")) {
      return;
    }

    try {
      const data = await fetchWithAuth("/admin/api/history/export-and-delete", {
        method: "POST"
      });

      // Convert to CSV
      const csv = convertToCSV(data.history);

      // Download file
      downloadCSV(csv, `history_complete_export_${new Date().toISOString().split('T')[0]}.csv`);

      alert(`Exported ${data.total_exported} records. Deleted ${data.deleted_count} records older than 30 days.`);

      // Refresh the list
      window.location.reload();
    } catch (err) {
      console.error("Failed to export and delete:", err);
      alert("Failed to export and delete history. Please try again.");
    }
  };

  const convertToCSV = (data) => {
    if (!data || data.length === 0) return "";

    // Get headers from first object
    const headers = Object.keys(data[0]);

    // Create CSV rows
    const csvRows = [
      headers.join(','), // Header row
      ...data.map(row =>
        headers.map(header => {
          const value = row[header] || '';
          // Escape quotes and wrap in quotes if contains comma or newline
          const escaped = String(value).replace(/"/g, '""');
          return /[,"\n]/.test(escaped) ? `"${escaped}"` : escaped;
        }).join(',')
      )
    ];

    return csvRows.join('\n');
  };

  const downloadCSV = (csv, filename) => {
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (error) {
    return <div className="text-red-500">Error: {error}</div>;
  }

  return (
    <div className="w-1/2 border-r flex flex-col h-full">
      <div className="p-4 border-b">
        <h2 className="text-lg font-bold">Open Conversations</h2>
      </div>

      {/* Export Actions Bar for History Tab */}
      {type === "history" && (
        <div className="bg-gray-50 border-b p-3">
          <div className="flex items-center gap-3 mb-3">
            <button
              onClick={() => setShowExportDialog(!showExportDialog)}
              className="px-4 py-2 bg-blue-600 text-white rounded font-semibold hover:bg-blue-700"
            >
              📥 Export History
            </button>
            <button
              onClick={handleExportAndDelete}
              className="px-4 py-2 bg-orange-600 text-white rounded font-semibold hover:bg-orange-700"
            >
              🗑️ Export & Delete Old
            </button>
            <span className="text-xs text-gray-600 ml-2">
              (Export & Delete removes records older than 30 days)
            </span>
          </div>

          {/* Export Dialog */}
          {showExportDialog && (
            <div className="bg-white border border-blue-200 rounded p-3 mt-2">
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-gray-700">
                  Export last:
                </label>
                <input
                  type="number"
                  value={exportDays}
                  onChange={(e) => setExportDays(parseInt(e.target.value) || 30)}
                  min="1"
                  max="365"
                  className="w-20 px-2 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-600">days</span>
                <button
                  onClick={handleExportHistory}
                  className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-sm font-semibold"
                >
                  Download CSV
                </button>
                <button
                  onClick={() => setShowExportDialog(false)}
                  className="px-3 py-1 text-gray-600 hover:text-gray-800 text-sm"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Bulk Actions Bar */}
      {selectedConvos.size > 0 && type !== "history" && (
        <div className="bg-blue-50 border-b border-blue-200 p-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-blue-900">
              {selectedConvos.size} selected
            </span>
            <button
              onClick={selectAll}
              className="text-sm text-blue-600 hover:text-blue-800 underline"
            >
              Select All
            </button>
            <button
              onClick={clearSelection}
              className="text-sm text-blue-600 hover:text-blue-800 underline"
            >
              Clear
            </button>
          </div>
          <button
            onClick={type === "followups" ? handleBulkDeleteFollowups : handleBulkEndChats}
            disabled={isEndingChats}
            className="px-4 py-2 bg-red-600 text-white rounded font-semibold hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isEndingChats
              ? (type === "followups" ? "Deleting..." : "Ending...")
              : (type === "followups" ? "Delete Selected Followups" : "End Selected Chats")
            }
          </button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4">
        {Array.isArray(conversations) && conversations.length === 0 && (
          <div className="text-gray-500">No open conversations</div>
        )}

        {Array.isArray(conversations) && conversations.map((convo, idx) => {
          const convoKey = getConvoKey(convo);
          const isSelected = selectedConvos.has(convoKey);

          return (
            <div key={`${convo.user_id}-${convo.channel}-${idx}`} className={`p-3 border rounded mb-3 bg-white shadow-sm hover:shadow-md transition-shadow ${isSelected ? 'ring-2 ring-blue-500' : ''}`}>
              <div className="flex items-start gap-3">
                {/* Checkbox */}
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => toggleSelectConvo(convo)}
                  className="mt-1 w-5 h-5 text-blue-600 rounded cursor-pointer flex-shrink-0"
                />

                {/* Conversation Info */}
                <div className="flex-1 min-w-0">
                  {/* Show followup contact info prominently for followups tab */}
                  {type === "followups" && (
                    <div className="mb-3 p-2 bg-blue-50 border border-blue-200 rounded">
                      <div className="text-sm font-semibold text-blue-900 mb-2">📧 Contact Information</div>
                      {convo.name && <div className="text-sm mb-1"><strong>Name:</strong> {convo.name}</div>}
                      {convo.email && <div className="text-sm mb-1"><strong>Email:</strong> {convo.email}</div>}
                      {convo.phone && <div className="text-sm mb-1"><strong>Phone:</strong> {convo.phone}</div>}
                      {convo.message && (
                        <div className="text-sm mt-2">
                          <strong>Message:</strong>
                          <div className="mt-1 p-2 bg-white rounded border border-blue-100 text-gray-700">
                            {convo.message}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  <div className="text-sm mb-1"><strong>User:</strong> {convo.user_id}</div>
                  <div className="text-sm mb-1"><strong>Channel:</strong> {convo.channel}</div>
                  {type !== "followups" && (
                    <>
                      <div className="text-sm mb-1"><strong>Assigned:</strong> {convo.assigned_staff || "—"}</div>
                      <div className="text-xs text-gray-600 mb-1"><strong>Updated:</strong> {convo.last_updated || convo.updated_at || "-"}</div>
                      <div className="text-xs text-gray-600"><strong>Messages:</strong> {Array.isArray(convo.messages) ? convo.messages.length : (convo.message_count || "—")}</div>
                    </>
                  )}
                  {type === "followups" && (
                    <div className="text-xs text-gray-600 mt-2"><strong>Submitted:</strong> {convo.ts || "-"}</div>
                  )}
                </div>

                {/* Open Button */}
                <button
                  className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 whitespace-nowrap flex-shrink-0"
                  onClick={() => onSelect(convo)}
                >
                  Open
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ConversationList;
