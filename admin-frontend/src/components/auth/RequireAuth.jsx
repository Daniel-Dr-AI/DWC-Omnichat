// RequireAuth.jsx
import React from "react";
import { Navigate } from "react-router-dom";

const RequireAuth = ({ children }) => {
  const token = localStorage.getItem("access_token");

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  try {
    const payloadBase64 = token.split(".")[1];
    const decodedPayload = JSON.parse(atob(payloadBase64));
    const exp = decodedPayload.exp;
    const now = Math.floor(Date.now() / 1000);

    if (exp < now) {
      console.warn("⏰ Token expired");
      localStorage.removeItem("access_token");
      return <Navigate to="/login" replace />;
    }
  } catch (err) {
    console.error("Failed to decode JWT", err);
    localStorage.removeItem("access_token");
    return <Navigate to="/login" replace />;
  }

  return children;
};

export default RequireAuth;
