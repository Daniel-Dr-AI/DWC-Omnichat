import React from "react";

const Tabs = ({ activeTab, setActiveTab }) => {
  const tabs = ["open", "escalated", "followups", "history"];

  return (
    <div className="flex gap-4">
      {tabs.map((tab) => (
        <button
          key={tab}
          className={`px-4 py-2 rounded ${
            activeTab === tab
              ? "bg-blue-600 text-white"
              : "bg-gray-200 text-black"
          }`}
          onClick={() => setActiveTab(tab)}
        >
          {tab.charAt(0).toUpperCase() + tab.slice(1)}
        </button>
      ))}
    </div>
  );
};

export default Tabs;
