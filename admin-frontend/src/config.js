// API Configuration
// This allows switching between local and production backends

const isProduction = import.meta.env.PROD;
const isDevelopment = import.meta.env.DEV;

// You can override this with environment variable VITE_API_URL
const API_BASE_URL = import.meta.env.VITE_API_URL ||
  (isProduction
    ? "https://dwc-omnichat.onrender.com"  // Production Render backend
    : "http://localhost:8000"               // Local development
  );

export { API_BASE_URL };
