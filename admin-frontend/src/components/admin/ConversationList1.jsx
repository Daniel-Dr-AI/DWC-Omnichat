import React, { useEffect, useState } from "react";
import fetchWithAuth from "../../fetchWithAuth";

const ConversationList = ({ type, onSelect }) => {
  const [conversations, setConversations] = useState([]);

  useEffect(() => {
    const fetchConversations = async () => {
      try {
        const data = await fetchWithAuth(`/admin/api/${type}`);
        setConversations(data || []);
      } catch (err) {
        console.error("Failed to fetch:", err);
        setConversations([]);
      }
    };

    fetchConversations();
  }, [type]);

  return (
    <div className="w-1/2 border p-4 rounded overflow-y-auto max-h-[75vh]">
      <h2 className="text-xl font-semibold mb-2 capitalize">{type} Conversations</h2>
      <ul>
        {conversations.length === 0 && (
          <li className="text-gray-500">No conversations.</li>
        )}
        {conversations.map((convo) => (
          <li
            key={convo.id}
            className="p-2 border-b cursor-pointer hover:bg-gray-100"
            onClick={() => onSelect(convo)}
          >
            <strong>{convo.user_name || "User"}</strong>:{" "}
            {convo.preview || "No message"}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default ConversationList;
