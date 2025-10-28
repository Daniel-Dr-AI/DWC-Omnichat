import React from "react";

const Tabs = ({ activeTab, setActiveTab, followupCount = 0 }) => {
  const tabs = ["open", "escalated", "followups", "history"];

  return (
    <div className="flex gap-4">
      {tabs.map((tab) => {
        const hasNewFollowups = tab === "followups" && followupCount > 0;

        return (
          <button
            key={tab}
            className={`px-4 py-2 rounded relative ${
              activeTab === tab
                ? "bg-blue-600 text-white"
                : "bg-gray-200 text-black"
            } ${hasNewFollowups ? "ring-2 ring-red-600" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            <div className="flex flex-col items-center">
              <span>{tab.charAt(0).toUpperCase() + tab.slice(1)}</span>
              {hasNewFollowups && (
                <span className="text-xs text-red-600 font-semibold mt-1">
                  You have new followups!
                </span>
              )}
            </div>
            {hasNewFollowups && (
              <span className="absolute -top-1 -right-1 bg-red-600 text-white text-xs rounded-full w-6 h-6 flex items-center justify-center font-bold">
                {followupCount}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
};

export default Tabs;
