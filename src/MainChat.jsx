// src/MainChat.jsx
import React, { useState, useEffect, useRef } from "react";
import { fetchFlavors, sendMessage } from "./api.js";
import "./index.css";
import assistantAvatar from "./assets/assistant.png";
import expertAvatar from "./assets/expert.png";

// Avatar/label mapping
const AI_PARTICIPANTS = {
  assistant: {
    name: "CensusDas.AI.Assistant",
    avatar: assistantAvatar
  },
  expert: {
    name: "CensusDas.AI.Expert",
    avatar: expertAvatar
  },
};

// One-time intro message
const ABOUT_TEXT =
  "Welcome to CensusDas.AI\n" +
  "CensusDas.AI is your AI-powered partner for navigating complex government manuals with ease. Get accurate, cited answers from expert agents, while a friendly assistant breaks it all down in plain, multilingual language—so you always stay in the know, no matter your language. Change languages on the fly and pick up right where you left off.\n\n" +
  "Why CensusDas.AI?\n" +
  "• Multi-Agent Teamwork Behind the Scenes — multiple AI agents (think: expert brains + helpful translator) working together to deliver clear answers fast.\n" +
  "• Built for Cross-Nation Reach — instantly understand and reply in your preferred language, with tone and style that adapt to your needs.\n" +
  "• High-Signal Answers — cutting-edge AI search finds the right info and filters out the fluff for grounded, reliable responses.\n" +
  "• Always Learning, Always Improving — your feedback helps refine answers in real-time, with built-in checks for accuracy and quality control.\n" +
  "• Upcoming Features — Offline Support & Voice Interface";

    
export default function MainChat({ isLoggedIn, onLogout }) {
  const [flavors, setFlavors] = useState([]);
  const [selectedFlavor, setSelectedFlavor] = useState(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false); // disables input while a turn is in-flight
  const [typingSender, setTypingSender] = useState(null); // "assistant" | "expert" | null
  const [status, setStatus] = useState(null); // "Thinking…" | "Generating answer…" | null

  const [sessionId] = useState(() =>
    crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substr(2, 9)
  );

  const chatEndRef = useRef(null);
  const nextIdRef = useRef(1);
  const aboutShownRef = useRef(false);
  const statusTimerRef = useRef(null);

  // 1) Fetch flavors on mount and set default flavor
  useEffect(() => {
    fetchFlavors()
      .then((list) => {
        setFlavors(list);
        if (list.length) setSelectedFlavor(list[0]);
      })
      .catch(() => {
        const fallback = { label: "Simple English", language: "english", style: "simple" };
        setFlavors([fallback]);
        setSelectedFlavor(fallback);
      });
  }, []);

  // 2) Show one-time About message when chat is empty (no greeting; no reset on flavor change)
  useEffect(() => {
    if (!isLoggedIn || !selectedFlavor) return;
    if (messages.length === 0 && !aboutShownRef.current) {
      aboutShownRef.current = true;
      appendMessage({ sender: "assistant", content: ABOUT_TEXT });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoggedIn, selectedFlavor]);

  // 3) Scroll to bottom on updates
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, typingSender, status]);

  // 4) Dropdown outside click
  useEffect(() => {
    function close(e) {
      if (
        !e.target.closest(".glassy-dropdown-btn") &&
        !e.target.closest(".glassy-dropdown-list")
      ) {
        setShowDropdown(false);
      }
    }
    if (showDropdown) window.addEventListener("mousedown", close);
    return () => window.removeEventListener("mousedown", close);
  }, [showDropdown]);

  // Clear any pending status timer on unmount
  useEffect(() => {
    return () => {
      if (statusTimerRef.current) clearTimeout(statusTimerRef.current);
    };
  }, []);

  function appendMessage({ sender, content, time }) {
    setMessages((msgs) => [
      ...msgs,
      {
        id: nextIdRef.current++,
        sender,
        content,
        time:
          time ||
          new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
      },
    ]);
  }

  const sleep = (ms) => new Promise((res) => setTimeout(res, ms));

  // 5) Send user message to backend
  async function handleSend(e) {
    e.preventDefault();
    if (!input.trim() || !selectedFlavor || loading) return;

    // Push user message immediately
    const userInput = input;
    appendMessage({ sender: "user", content: userInput });
    setInput("");
    setLoading(true);

    // Show background status while waiting for backend
    setStatus("Thinking…");
    if (statusTimerRef.current) clearTimeout(statusTimerRef.current);
    statusTimerRef.current = setTimeout(() => setStatus("Generating answer…"), 1000);

    try {
      const replies = await sendMessage({
        message: userInput,
        user_name: "Beta User",
        language: selectedFlavor.language,
        style: selectedFlavor.style,
        sessionId,
      });

      // Backend responded; hide global status and start persona-typing per message
      if (statusTimerRef.current) clearTimeout(statusTimerRef.current);
      setStatus(null);

      for (const reply of replies) {
        const sender = (reply.persona || "").toLowerCase(); // "Assistant" -> "assistant"
        const ts = reply.timestamp
          ? new Date(reply.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
          : "";

        // Persona-specific typing preview
        if (sender === "assistant" || sender === "expert") {
          setTypingSender(sender);
          await sleep(350);
        }

        appendMessage({
          sender: sender === "assistant" || sender === "expert" ? sender : "assistant",
          content: reply.content,
          time: ts,
        });

        setTypingSender(null);
        await sleep(150);
      }
    } catch (err) {
      if (statusTimerRef.current) clearTimeout(statusTimerRef.current);
      setStatus(null);
      appendMessage({
        sender: "assistant",
        content: "Sorry, there was a network error.",
      });
    } finally {
      setTypingSender(null);
      setLoading(false);
    }
  }

  return (
    <div className="main-area">
      <div className="chat-card" style={{ position: "relative" }}>
        {/* --- HEADER: Brand & Logout --- */}
        <div className="mainchat-header-top">
          <div className="chat-header-title">CensusDas.AI Staff Room</div>
          <button
            className="chat-logout-btn"
            title="Logout"
            aria-label="Logout"
            style={{ marginRight: 10 }}
            onClick={onLogout}
          >
            Logout
          </button>
        </div>

        {/* --- SUBHEADER: Username & Dropdown --- */}
        <div className="mainchat-header-bottom">
          <span className="chat-username-badge">Logged in as Beta User</span>
          <span className="chat-username-badge">Choose Your Assistant's Language & Cultural Flavor</span>
          <div style={{ position: "relative" }}>
            <button
              type="button"
              className="glassy-dropdown-btn"
              onClick={() => setShowDropdown(!showDropdown)}
              aria-haspopup="listbox"
              aria-expanded={showDropdown}
            >
              <span>{selectedFlavor?.label || "Choose language"}</span>
              <span className="chevron" style={{ marginLeft: 8, fontSize: "1.04em" }}>
                ▼
              </span>
            </button>
            {showDropdown && (
              <div className="glassy-dropdown-list">
                {flavors.map((opt) => (
                  <div
                    key={opt.label + opt.language + opt.style}
                    className={"glassy-dropdown-item" + (selectedFlavor?.label === opt.label ? " active" : "")}
                    onClick={() => {
                      setSelectedFlavor(opt);
                      setShowDropdown(false);
                    }}
                    role="option"
                    aria-selected={selectedFlavor?.label === opt.label}
                  >
                    {opt.label}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* --- Lock/Blur Overlay --- */}
        {!isLoggedIn && (
          <div className="chat-lock-overlay">
            <div style={{ fontSize: 20, marginBottom: 18, color: "#808087" }}>🔒</div>
            <div style={{ fontSize: "1em", color: "#556", fontWeight: 600 }}>
              Chat is locked. Please login to participate.
            </div>
          </div>
        )}

        {/* --- Actual Chat Thread --- */}
        <div className="chat-thread">
          {messages.map((msg) => (
            <ChatBubble key={msg.id} sender={msg.sender} content={msg.content} time={msg.time} />
          ))}

          {/* Global status bubble while waiting for backend */}
          {status && <ChatBubble sender="assistant" content={status} time="" />}

          {/* Persona typing preview between messages */}
          {typingSender && <ChatBubble sender={typingSender} content="Typing…" time="" />}

          <div ref={chatEndRef} />
        </div>

        {/* --- Chat input (if logged in) --- */}
        {isLoggedIn && (
          <form className="chat-input-bar" onSubmit={handleSend}>
            <input
              className="chat-input"
              placeholder="Type your message…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              autoFocus
              disabled={loading}
            />
            <button className="chat-send-btn" type="submit" aria-label="Send" disabled={loading}>
              <span>➤</span>
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

// --- ChatBubble Component ---
function ChatBubble({ sender, content, time }) {
  const isUser = sender === "user";
  const ai = AI_PARTICIPANTS[sender];

  return (
    <div className={`bubble-row ${isUser ? "bubble-row-user" : "bubble-row-ai"}`}>
      {!isUser && ai && <img className="bubble-avatar" src={ai.avatar} alt={ai.name} />}
      <div className={`chat-bubble ${isUser ? "chat-bubble-user" : "chat-bubble-ai"}`}>
        {!isUser && ai && <div className="bubble-name">{ai.name.replace("CensusDas.AI.", "")}</div>}
        {/* Preserve line breaks and spacing from backend */}
        <div className="bubble-text" style={{ whiteSpace: "pre-wrap" }}>
          {content}
        </div>
        <div className="bubble-time">{time}</div>
      </div>
    </div>
  );
}
