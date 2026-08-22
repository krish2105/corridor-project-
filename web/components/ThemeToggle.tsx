"use client";
import { useEffect, useState } from "react";

type Theme = "light" | "dark";

/**
 * Light by default. A survey audit gets read in meetings, screenshotted into
 * reports and printed, so light is the right default rather than whatever the
 * reader's OS happens to be set to. The choice persists.
 */
export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const saved = localStorage.getItem("corridor-theme") as Theme | null;
    setTheme(saved ?? "light");
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("corridor-theme", theme);
  }, [theme]);

  const next = theme === "light" ? "dark" : "light";
  return (
    <button
      className="themetoggle"
      onClick={() => setTheme(next)}
      aria-label={`Switch to ${next} theme`}
      title={`Switch to ${next} theme`}
    >
      {theme === "light" ? "Dark" : "Light"}
    </button>
  );
}
