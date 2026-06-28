// src/api.js

// Same-origin API (served by FastAPI at /api)
const BASE_URL = "/api";

// Get assistant flavors dynamically
export async function fetchFlavors() {
  const res = await fetch(`${BASE_URL}/flavors`);
  if (!res.ok) throw new Error("Failed to load language flavors");
  return res.json();
}

// Send user message (with optional sessionId)
export async function sendMessage({
  message,
  user_name,
  language,
  style,
  sessionId,
}) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      user_name,
      language,
      style,
      session_id: sessionId || null,
    }),
  });
  if (!res.ok) throw new Error("Chat backend error");
  return res.json();
}
