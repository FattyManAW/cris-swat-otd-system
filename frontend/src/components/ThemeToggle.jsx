import { useState, useEffect } from "react";
import { Sun, Moon } from "lucide-react";

const STORAGE_KEY = "otd-theme";

function applyTheme(mode) {
  const root = document.documentElement;
  if (mode === "light") {
    root.style.setProperty("--c-bg",     "#f5f5f7");
    root.style.setProperty("--c-card",   "#ffffff");
    root.style.setProperty("--c-border", "#e5e5ea");
    root.style.setProperty("--c-text",   "#1d1d1f");
    root.style.setProperty("--c-muted",  "#86868b");
    root.style.setProperty("--c-accent", "#0071e3");
    root.style.setProperty("--c-green",  "#34c759");
    root.style.setProperty("--c-amber",  "#ff9500");
    root.style.setProperty("--c-red",    "#ff3b30");
  } else {
    root.style.setProperty("--c-bg",     "#0f1119");
    root.style.setProperty("--c-card",   "#181b23");
    root.style.setProperty("--c-border", "#2e3140");
    root.style.setProperty("--c-text",   "#f0f2f8");
    root.style.setProperty("--c-muted",  "#747a8c");
    root.style.setProperty("--c-accent", "#4b8cff");
    root.style.setProperty("--c-green",  "#3cc97e");
    root.style.setProperty("--c-amber",  "#f0b028");
    root.style.setProperty("--c-red",    "#f44b55");
  }
}

export default function ThemeToggle() {
  const getSystemMode = () =>
    window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";

  const [mode, setMode] = useState(() => {
    return localStorage.getItem(STORAGE_KEY) || getSystemMode();
  });

  useEffect(() => {
    applyTheme(mode);
    localStorage.setItem(STORAGE_KEY, mode);
  }, [mode]);

  useEffect(() => {
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e) => {
      if (!localStorage.getItem(STORAGE_KEY)) {
        setMode(e.matches ? "dark" : "light");
      }
    };
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  const toggle = () => setMode((m) => (m === "dark" ? "light" : "dark"));

  return (
    <button
      onClick={toggle}
      className="flex items-center justify-center gap-2 w-full px-3 py-2 rounded-lg text-xs text-otd-muted hover:bg-otd-border/50 transition-colors"
      aria-label={`Switch to ${mode === "dark" ? "light" : "dark"} mode`}
    >
      {mode === "dark" ? (
        <>
          <Sun className="w-4 h-4" /> 淺色模式
        </>
      ) : (
        <>
          <Moon className="w-4 h-4" /> 深色模式
        </>
      )}
    </button>
  );
}