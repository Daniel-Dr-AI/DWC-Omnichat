import React from "react";
import { useNavigate } from "react-router-dom";

const LogoutButton = () => {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    navigate("/login");
  };

  return (
    <button onClick={handleLogout} style={{ marginLeft: "auto", padding: "8px", background: "red", color: "white", border: "none", borderRadius: "4px" }}>
      Logout
    </button>
  );
};

export default LogoutButton;
