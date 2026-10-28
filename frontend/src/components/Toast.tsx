"use client";

import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

const ToastViewport = createContext<HTMLDivElement | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [viewport, setViewport] = useState<HTMLDivElement | null>(null);
  return <ToastViewport.Provider value={viewport}>
    {children}
    <div className="toast-viewport" ref={setViewport} role="region" aria-label="Уведомления" />
  </ToastViewport.Provider>;
}

function messageKey(content: ReactNode): string {
  if (typeof content === "string" || typeof content === "number") return String(content);
  if (Array.isArray(content)) return content.map(messageKey).join("");
  if (content && typeof content === "object" && "props" in content) return messageKey((content.props as { children?: ReactNode }).children);
  return "";
}

function ToastMessage({ children, tone, id }: { children: ReactNode; tone: "warning" | "success"; id?: string }) {
  const [visible, setVisible] = useState(true);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hovered = useRef(false);
  const focused = useRef(false);
  function pause() { if (timer.current) clearTimeout(timer.current); }
  function resume() {
    pause();
    if (!hovered.current && !focused.current) timer.current = setTimeout(() => setVisible(false), 6000);
  }
  useEffect(() => {
    timer.current = setTimeout(() => setVisible(false), 6000);
    return () => { if (timer.current) clearTimeout(timer.current); };
  }, []);
  if (!visible) return null;
  return <div id={id} className={`toast toast-${tone}`} role={tone === "warning" ? "alert" : "status"} aria-atomic="true"
    onMouseEnter={() => { hovered.current = true; pause(); }} onMouseLeave={() => { hovered.current = false; resume(); }}
    onFocusCapture={() => { focused.current = true; pause(); }} onBlurCapture={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) { focused.current = false; resume(); } }}>
    <span className="toast-mark" aria-hidden="true">{tone === "warning" ? "!" : "✓"}</span>
    <div className="toast-content">{children}</div>
    <button type="button" className="toast-close" aria-label="Закрыть уведомление" onClick={() => setVisible(false)}>×</button>
  </div>;
}

/** Transient feedback lives outside document/grid flow. Persistent page data stays inline. */
export function Toast({ children, tone = "warning", id }: { children: ReactNode; tone?: "warning" | "success"; id?: string }) {
  const viewport = useContext(ToastViewport);
  return viewport ? createPortal(<ToastMessage key={messageKey(children)} tone={tone} id={id}>{children}</ToastMessage>, viewport) : null;
}
