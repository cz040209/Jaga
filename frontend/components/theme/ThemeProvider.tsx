"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { flushSync } from "react-dom";

export type Theme = "light" | "dark" | "system";
type Resolved = "light" | "dark";

export const THEME_STORAGE_KEY = "jaga.theme";
const THEME_COLOURS: Record<Resolved, string> = { light: "#f6f8fa", dark: "#0b1120" };

/**
 * Runs in <head> before the page paints, so a dark-theme user never sees a
 * white flash. It must stay tiny and self-contained (no imports).
 * Default is light: Jaga only goes dark when the user picks it.
 */
export const themeScript = `(function(){try{var t=localStorage.getItem("${THEME_STORAGE_KEY}");var d=t==="dark"||(t==="system"&&matchMedia("(prefers-color-scheme: dark)").matches);var e=document.documentElement;e.classList.toggle("dark",d);e.style.colorScheme=d?"dark":"light"}catch(_){}})()`;

function systemPrefersDark() {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function resolve(theme: Theme): Resolved {
  if (theme === "system") return systemPrefersDark() ? "dark" : "light";
  return theme;
}

/** Put the theme on <html>: the `.dark` class drives every `dark:` style. */
function apply(resolved: Resolved) {
  const root = document.documentElement;
  root.classList.toggle("dark", resolved === "dark");
  root.style.colorScheme = resolved;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", THEME_COLOURS[resolved]);
}

type ThemeContextValue = {
  /** What the user chose. */
  theme: Theme;
  /** What is actually on screen ("system" turned into light or dark). */
  resolvedTheme: Resolved;
  /** Change the theme. Pass the click position to reveal it with a growing circle. */
  setTheme: (theme: Theme, origin?: { x: number; y: number }) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  // The server can't know the choice, so start from the default and sync on mount.
  const [theme, setThemeState] = useState<Theme>("light");
  const [resolvedTheme, setResolved] = useState<Resolved>("light");

  useEffect(() => {
    let saved: Theme = "light";
    try {
      const value = localStorage.getItem(THEME_STORAGE_KEY);
      if (value === "light" || value === "dark" || value === "system") saved = value;
    } catch {
      /* storage blocked: stay light */
    }
    setThemeState(saved);
    setResolved(resolve(saved));
  }, []);

  // When following the phone, follow it live too.
  useEffect(() => {
    if (theme !== "system") return;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      const next = resolve("system");
      apply(next);
      setResolved(next);
    };
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [theme]);

  const setTheme = useCallback((next: Theme, origin?: { x: number; y: number }) => {
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      /* not remembered, still applied */
    }
    const nextResolved = resolve(next);
    const update = () => {
      apply(nextResolved);
      // flushSync: React must finish re-rendering inside the snapshot below.
      flushSync(() => {
        setThemeState(next);
        setResolved(nextResolved);
      });
    };

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const sameLook = nextResolved === (document.documentElement.classList.contains("dark") ? "dark" : "light");
    if (!origin || reduceMotion || sameLook || !document.startViewTransition) {
      update();
      return;
    }

    // View Transitions API: the browser snapshots the old look, we switch,
    // then the new look grows out of the button as a circle.
    const { x, y } = origin;
    const radius = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
    const transition = document.startViewTransition(update);
    transition.ready
      .then(() => {
        document.documentElement.animate(
          { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${radius}px at ${x}px ${y}px)`] },
          { duration: 550, easing: "cubic-bezier(0.22, 1, 0.36, 1)", pseudoElement: "::view-transition-new(root)" },
        );
      })
      .catch(() => {
        /* transition skipped: the theme is already applied */
      });
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme }}>{children}</ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useTheme must be used inside <ThemeProvider>");
  return context;
}
