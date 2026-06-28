import React from "react";
import "./index.css";
import assistantAvatar from "./assets/assistant.png";
import expertAvatar from "./assets/expert.png";

export default function Sidebar({ isLoggedIn, onLogin, onLogout }) {
  // Your fixed participant data
  const participants = [
    {
      id: 1,
      name: "CensusDas.AI.Assistant",
      role: "Assistant/ Multi-lingual Translator",
      avatar: assistantAvatar,
      bio: "Bridges languages.",
    },
    {
      id: 2,
      name: "CensusDas.AI.Expert",
      role: "Census Instruction Manuals Expert",
      avatar: expertAvatar,
      bio: "Answers census queries.",
    },
  ];

  return (
    <aside className="sidebar">
      {/* Branding */}
      <div className="sidebar-brand">
        <div className="sidebar-title">CensusDas.AI</div>
        <div className="sidebar-tagline">The Multi-Agent AI Staff Room</div>
      </div>

      {/* About */}
      <div className="about-glass">
        <div className="about-title">About</div>
        <div className="about-copy">
          Conversation-first support for Census of India staff, powered by a
          team of AI personas. Available in Major Indian Languages.
        </div>
      </div>

      {/* What will you find in staffroom */}
      <div className="about-glass" style={{ marginTop: 14 }}>
        <div className="about-title">What will you find in the staffroom?</div>
        <div className="about-copy">
          Two member human-like AI team: A scholarly expert, and a knowledgable
          multilingual culturally aware Assistant to act as the interpreter and
          translator, both collaborating just to help you.
        </div>
        <div className="about-copy">But, </div>
        <div className="about-copy">How does it work? </div>
        <div className="about-copy">Just Login and ask the Assistant! </div>
        <div className="about-copy">
          If you received this url, you are a Beta User.{" "}
        </div>
      </div>
      {/* Footer */}
      <div className="sidebar-footer">
        {!isLoggedIn ? (
          <button className="sidebar-btn" onClick={onLogin}>
            Login
          </button>
        ) : (
          <button className="sidebar-btn" onClick={onLogout}>
            Logout
          </button>
        )}
      </div>

      {/* Participants */}
      <div className="staffroom-glass">
        <div className="staffroom-title">Staffroom Participants</div>
        <div className="staff-list">
          {participants.map((staff) => (
            <div key={staff.id} className="staff-row">
              <img
                src={staff.avatar}
                alt={staff.name}
                className="staff-avatar"
              />
              <div className="staff-meta">
                <div className="staff-name">{staff.name}</div>
                <div className="staff-role">{staff.role}</div>
                <div className="staff-bio">{staff.bio}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
      {/* Spacer */}
      <div style={{ flex: 1 }} />
    </aside>
  );
}
