import React, { useState } from "react";
import Tabs from "./Tabs";
import ConversationList from "./ConversationList";
import ChatBox from "./ChatBox";
import LogoutButton from "../auth/LogoutButton";

const AdminDashboard = () => {
  const [activeTab, setActiveTab] = useState("open");
  const [selectedConversation, setSelectedConversation] = useState(null);

  return (
    <div className="p-6 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-3xl font-bold">Admin Dashboard</h1>
        <LogoutButton />
      </div>

      <Tabs activeTab={activeTab} setActiveTab={setActiveTab} />
      <div className="flex gap-4 mt-4">
        <ConversationList
          type={activeTab}
          onSelect={setSelectedConversation}
        />
        <ChatBox conversation={selectedConversation} />
      </div>
    </div>
  );
};

export default AdminDashboard;
