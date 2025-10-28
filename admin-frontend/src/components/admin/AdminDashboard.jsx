import React, { useState, useEffect } from "react";
import Tabs from "./Tabs";
import ConversationList from "./ConversationList";
import ChatBox from "./ChatBox";
import LogoutButton from "../auth/LogoutButton";
import fetchWithAuth from "../../fetchWithAuth";

const AdminDashboard = () => {
  const [activeTab, setActiveTab] = useState("open");
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [followupCount, setFollowupCount] = useState(0);

  // Fetch unviewed followup count
  const loadFollowupCount = async () => {
    try {
      const data = await fetchWithAuth("/admin/api/followups/unviewed-count");
      setFollowupCount(data.count || 0);
    } catch (err) {
      console.error("Failed to fetch followup count:", err);
    }
  };

  // Fetch followup count when dashboard loads
  useEffect(() => {
    loadFollowupCount();

    // Refresh count every 30 seconds
    const interval = setInterval(loadFollowupCount, 30000);
    return () => clearInterval(interval);
  }, []);

  // Function to refresh followup count (passed to ChatBox)
  const handleFollowupViewed = () => {
    loadFollowupCount();
  };

  return (
    <div className="h-screen flex flex-col">
      <div className="flex items-center justify-between p-4 border-b">
        <h1 className="text-3xl font-bold">Admin Dashboard</h1>
        <LogoutButton />
      </div>

      <Tabs activeTab={activeTab} setActiveTab={setActiveTab} followupCount={followupCount} />
      <div className="flex gap-0 flex-1 overflow-hidden">
        <ConversationList
          type={activeTab}
          onSelect={setSelectedConversation}
        />
        <ChatBox
          conversation={selectedConversation}
          onFollowupViewed={handleFollowupViewed}
        />
      </div>
    </div>
  );
};

export default AdminDashboard;
