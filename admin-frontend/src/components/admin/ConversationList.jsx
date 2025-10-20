import React, { useEffect, useState } from "react";
import fetchWithAuth from "../../fetchWithAuth";

const ConversationList = () => {
  const [conversations, setConversations] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadConversations = async () => {
      try {
        const data = await fetchWithAuth("http://localhost:8000/admin/api/convos");
        setConversations(data.conversations); // ✅ Fix here
      } catch (err) {
        console.error("Failed to fetch conversations:", err);
        setError(err.message);
      }
    };

    loadConversations();
  }, []);

  if (error) {
    return <div className="text-red-500">Error: {error}</div>;
  }

  return (
    <div className="conversation-list p-4">
      <h2 className="text-lg font-bold mb-4">Open Conversations</h2>
      {Array.isArray(conversations) && conversations.map((convo) => (
        <div key={convo.id} className="p-2 border-b">
          <div><strong>ID:</strong> {convo.id}</div>
          <div><strong>Status:</strong> {convo.status}</div>
          <div><strong>Created At:</strong> {convo.created_at}</div>
        </div>
      ))}
    </div>
  );
};

export default ConversationList;
