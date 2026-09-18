/**
 * MedPak AI — Lightweight Toast Notification System
 * Zero-dependency, pure React toast component with auto-dismiss.
 *
 * Usage:
 *   import Toast, { toast } from './Toast';
 *
 *   // In your root component's JSX:
 *   <Toast />
 *
 *   // Anywhere in your code:
 *   toast.error('Something went wrong');
 *   toast.success('Medicine found!');
 *   toast.info('Fetching live prices…');
 */

import React, { useState, useEffect, useCallback } from 'react';
import { X, AlertTriangle, CheckCircle2, Info, WifiOff } from 'lucide-react';

// ── Event bus (works outside React) ──────────────────────────────────────────
const listeners = new Set();
const emit = (t) => listeners.forEach((fn) => fn(t));

export const toast = {
  error: (msg) => emit({ type: 'error', message: msg }),
  success: (msg) => emit({ type: 'success', message: msg }),
  info: (msg) => emit({ type: 'info', message: msg }),
};

// ── Toast container component ────────────────────────────────────────────────
const ICONS = {
  error: AlertTriangle,
  success: CheckCircle2,
  info: Info,
};

const STYLES = {
  error: 'bg-red-50 border-red-200 text-red-800',
  success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
  info: 'bg-blue-50 border-blue-200 text-blue-800',
};

const ICON_STYLES = {
  error: 'text-red-500',
  success: 'text-emerald-500',
  info: 'text-blue-500',
};

let toastId = 0;

const Toast = () => {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((t) => {
    const id = ++toastId;
    setToasts((prev) => [...prev.slice(-4), { ...t, id }]); // max 5 visible
    setTimeout(() => {
      setToasts((prev) => prev.filter((x) => x.id !== id));
    }, 5000);
  }, []);

  useEffect(() => {
    listeners.add(addToast);
    return () => listeners.delete(addToast);
  }, [addToast]);

  const dismiss = (id) => setToasts((prev) => prev.filter((x) => x.id !== id));

  if (!toasts.length) return null;

  return (
    <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {toasts.map((t) => {
        const Icon = ICONS[t.type] || Info;
        return (
          <div
            key={t.id}
            className={`pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-xl border shadow-lg backdrop-blur-sm animate-fade-in ${STYLES[t.type] || STYLES.info}`}
          >
            <Icon className={`w-5 h-5 flex-shrink-0 mt-0.5 ${ICON_STYLES[t.type] || ICON_STYLES.info}`} />
            <p className="text-sm font-medium flex-1 leading-snug">{t.message}</p>
            <button
              onClick={() => dismiss(t.id)}
              className="flex-shrink-0 opacity-50 hover:opacity-100 transition-opacity"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
};

export default Toast;
