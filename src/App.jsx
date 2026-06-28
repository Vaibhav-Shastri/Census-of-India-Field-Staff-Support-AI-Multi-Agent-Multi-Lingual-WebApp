import React, { useState, useEffect } from "react";
import Sidebar from "./Sidebar.jsx"; // Adjust path if needed
import MainChat from "./MainChat.jsx";
import "./index.css";

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 700);

  // Responsive detection
  useEffect(() => {
    function handleResize() {
      setIsMobile(window.innerWidth <= 700);
    }
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return (
    <div className="main-layout">
      {/* MOBILE LOGIC */}
      {isMobile ? (
        !isLoggedIn ? (
          <Sidebar isLoggedIn={false} onLogin={() => setIsLoggedIn(true)} onLogout={() => setIsLoggedIn(false)} />
        ) : (
          <MainChat
            isLoggedIn={true}
            onLogout={() => setIsLoggedIn(false)}
          />
        )
      ) : (
        // DESKTOP: always show both
        <>
          <Sidebar
            isLoggedIn={isLoggedIn}
            onLogin={() => setIsLoggedIn(true)}
            onLogout={() => setIsLoggedIn(false)}
          />
          <MainChat
            isLoggedIn={isLoggedIn}
            onLogout={() => setIsLoggedIn(false)}
          />
        </>
      )}
    </div>
  );
}
