import React from "react";

const ChatBox = ({ conversation }) => {
  if (!conversation) {
    return (
      <div className="w-1/2 border p-4 rounded text-gray-500">
        Select a conversation to view.
      </div>
    );
  }

  return (
    <div className="w-1/2 border p-4 rounded">
      <h2 className="text-xl font-semibold mb-2">
        Chat with {conversation.user_name || "User"}
      </h2>
      <div className="bg-gray-50 p-2 mb-2 rounded h-64 overflow-y-auto">
        {/* You could fetch and render full messages here if available */}
        <p>{conversation.full_text || "Conversation details coming soon..."}</p>
      </div>
      <input
        type="text"
        placeholder="Reply..."
        className="w-full p-2 border rounded"
      />
    </div>
  );
};

export default ChatBox;
