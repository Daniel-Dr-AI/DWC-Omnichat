export default async function fetchWithAuth(url, options = {}) {
  const token = localStorage.getItem("access_token");

  if (!token) {
    console.warn("❌ No access token found in localStorage — user is not authenticated.");
    window.location.href = "/login";
    throw new Error("Not authenticated — no token present.");
  }

  const headers = {
    ...options.headers,
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // ⛔ Unauthorized: token expired or invalid
    console.warn("🔐 Token expired or invalid — logging out.");
    localStorage.removeItem("access_token");
    window.location.href = "/login";
    return;
  }

  if (!response.ok) {
    let errorMessage;
    const contentType = response.headers.get("content-type");

    if (contentType && contentType.includes("application/json")) {
      try {
        const errorData = await response.json();
        errorMessage = JSON.stringify(errorData);
      } catch (e) {
        errorMessage = response.statusText;
      }
    } else {
      const errorText = await response.text();
      errorMessage = errorText || response.statusText;
    }
    throw new Error(`Fetch failed: ${response.status} ${errorMessage}`);
  }

  return response.json();
}
