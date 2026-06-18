import React, { useState, useEffect, useRef, useLayoutEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { getNotifications, getUnreadCount, markNotificationRead, markAllNotificationsRead } from '../services/api';
import { Bell, CheckCheck, Calendar, Info, AlertTriangle, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const TYPE_ICONS = {
  schedule: Calendar,
  info: Info,
  warning: AlertTriangle,
  announcement: Bell,
};

const TYPE_COLORS = {
  schedule: 'bg-blue-100 text-blue-700',
  info: 'bg-slate-100 text-slate-700',
  warning: 'bg-amber-100 text-amber-700',
  announcement: 'bg-purple-100 text-purple-700',
};

/* ── Panel sizing constants ───────────────────────────────────
 * `PANEL_W` is the desired width; if the viewport is narrower than
 * `PANEL_W + 2*VIEWPORT_PAD`, we shrink to `vw - 2*VIEWPORT_PAD`. */
const PANEL_W = 384;            // 24rem — same as old sm:w-96
const VIEWPORT_PAD = 8;         // never closer than 8px to any edge
const BELL_GAP = 8;             // gap between bell and panel

/**
 * Compute the {top, left, width, maxHeight} for the panel given the
 * bell's bounding box and the current viewport. Strategy:
 *   1. Open BELOW the bell by default (top = bellRect.bottom + GAP).
 *   2. Open-to-the-right (left-align with bell). Bell lives in the
 *      sidebar on the LEFT side of the layout, so this is the natural
 *      direction with the most available room.
 *   3. SHIFT — if the panel would overflow the right edge, shift left
 *      enough to fit inside (vw - PAD). If it would also overflow the
 *      left edge (very narrow viewport), clamp to PAD.
 *   4. FLIP — if there isn't enough vertical room below, open ABOVE.
 *   5. WIDTH — shrink to `vw - 2*PAD` on viewports narrower than the
 *      desired width.
 *   6. MAX HEIGHT — capped to the available vertical room minus padding
 *      so the panel never overflows the viewport vertically either.
 */
function computePanelPlacement(bellRect) {
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  const width = Math.min(PANEL_W, vw - 2 * VIEWPORT_PAD);

  // Horizontal — anchor to bell.left (open to the right of the bell).
  let left = bellRect.left;
  // Shift if it overflows the right edge:
  if (left + width > vw - VIEWPORT_PAD) {
    left = vw - VIEWPORT_PAD - width;
  }
  // Clamp left edge to the viewport:
  if (left < VIEWPORT_PAD) left = VIEWPORT_PAD;

  // Vertical — prefer below. Compute room above/below; flip if needed.
  const roomBelow = vh - bellRect.bottom - BELL_GAP - VIEWPORT_PAD;
  const roomAbove = bellRect.top - BELL_GAP - VIEWPORT_PAD;
  const openAbove = roomBelow < 240 && roomAbove > roomBelow;
  const maxHeight = Math.max(160, openAbove ? roomAbove : roomBelow);

  const top = openAbove
    ? Math.max(VIEWPORT_PAD, bellRect.top - BELL_GAP - maxHeight)
    : bellRect.bottom + BELL_GAP;

  return { top, left, width, maxHeight };
}

const NotificationBell = () => {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [placement, setPlacement] = useState(null);  // {top, left, width, maxHeight}

  const buttonRef = useRef(null);
  const panelRef = useRef(null);
  const navigate = useNavigate();

  // ── Data loading ───────────────────────────────────────────
  useEffect(() => {
    loadUnreadCount();
    const id = setInterval(loadUnreadCount, 30000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => { if (open) loadNotifications(); }, [open]);

  const loadUnreadCount = async () => {
    try {
      const data = await getUnreadCount();
      setUnreadCount(data.count);
    } catch { /* silent */ }
  };

  const loadNotifications = async () => {
    setLoading(true);
    try {
      const data = await getNotifications();
      setNotifications(data);
    } catch { /* silent */ }
    setLoading(false);
  };

  // ── Placement: compute on open + reposition on resize/scroll ──
  const reposition = useCallback(() => {
    if (!buttonRef.current) return;
    setPlacement(computePanelPlacement(buttonRef.current.getBoundingClientRect()));
  }, []);

  useLayoutEffect(() => {
    if (!open) { setPlacement(null); return; }
    reposition();
    window.addEventListener('resize', reposition);
    window.addEventListener('scroll', reposition, true);  // capture so sidebar scroll is caught
    return () => {
      window.removeEventListener('resize', reposition);
      window.removeEventListener('scroll', reposition, true);
    };
  }, [open, reposition]);

  // ── Click-outside / ESC close ─────────────────────────────
  useEffect(() => {
    if (!open) return;
    const onMouseDown = (e) => {
      if (panelRef.current?.contains(e.target)) return;
      if (buttonRef.current?.contains(e.target)) return;
      setOpen(false);
    };
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', onMouseDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onMouseDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  // ── Actions ───────────────────────────────────────────────
  const handleRead = async (notif) => {
    if (!notif.is_read) {
      await markNotificationRead(notif.id);
      setUnreadCount(prev => Math.max(0, prev - 1));
      setNotifications(prev => prev.map(n => n.id === notif.id ? { ...n, is_read: true } : n));
    }
    if (notif.link) {
      navigate(notif.link);
      setOpen(false);
    }
  };

  const handleMarkAllRead = async () => {
    await markAllNotificationsRead();
    setUnreadCount(0);
    setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
  };

  const timeAgo = (dateStr) => {
    const now = new Date();
    const date = new Date(dateStr);
    const diff = Math.floor((now - date) / 1000);
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  // ── Render ────────────────────────────────────────────────
  // The panel is rendered into `document.body` via a portal so the
  // sidebar's `overflow` / `transform` can't clip it. Positioning
  // is `fixed` so the page-layout container never traps it either.
  const panelNode = open && placement ? createPortal(
    <div
      ref={panelRef}
      role="dialog"
      aria-label="Notifications"
      style={{
        position: 'fixed',
        top:    `${placement.top}px`,
        left:   `${placement.left}px`,
        width:  `${placement.width}px`,
        maxHeight: `${placement.maxHeight}px`,
      }}
      className="bg-white border border-slate-200 rounded-sm shadow-xl z-[9999] flex flex-col overflow-hidden"
      data-testid="notification-panel"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 flex-shrink-0">
        <h3 className="font-bold text-sm text-[#00205B] uppercase tracking-wide">Notifications</h3>
        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="text-xs text-[#00205B] hover:underline flex items-center gap-1"
              data-testid="mark-all-read-btn"
            >
              <CheckCheck className="w-3.5 h-3.5" /> Mark all read
            </button>
          )}
          <button onClick={() => setOpen(false)} className="p-1 text-slate-400 hover:text-slate-600"
                  aria-label="Close notifications">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {loading ? (
          <div className="p-8 text-center text-slate-400 text-sm">Loading...</div>
        ) : notifications.length === 0 ? (
          <div className="p-8 text-center">
            <Bell className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-400">No notifications yet</p>
          </div>
        ) : (
          notifications.map((notif) => {
            const Icon = TYPE_ICONS[notif.type] || Info;
            const colorClass = TYPE_COLORS[notif.type] || TYPE_COLORS.info;
            return (
              <button
                key={notif.id}
                onClick={() => handleRead(notif)}
                className={`w-full text-left px-4 py-3 border-b border-slate-50 hover:bg-slate-50 transition-colors flex items-start gap-3 ${
                  !notif.is_read ? 'bg-blue-50/40' : ''
                }`}
                data-testid={`notification-item-${notif.id}`}
              >
                <div className={`p-1.5 rounded ${colorClass} flex-shrink-0 mt-0.5`}>
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <p className={`text-sm ${!notif.is_read ? 'font-semibold text-slate-900' : 'text-slate-700'} break-words`}>
                      {notif.title}
                    </p>
                    {!notif.is_read && (
                      <span className="w-2 h-2 rounded-full bg-[#00205B] flex-shrink-0 mt-1.5" />
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5 line-clamp-2 break-words">{notif.message}</p>
                  <p className="text-[10px] text-slate-400 mt-1">{timeAgo(notif.created_at)}</p>
                </div>
              </button>
            );
          })
        )}
      </div>
    </div>,
    document.body,
  ) : null;

  return (
    <div className="relative" data-testid="notification-bell">
      <button
        ref={buttonRef}
        onClick={() => setOpen(prev => !prev)}
        className="relative p-2 rounded-sm hover:bg-slate-100 transition-colors"
        aria-haspopup="dialog"
        aria-expanded={open}
        data-testid="notification-bell-btn"
      >
        <Bell className="w-5 h-5 text-slate-600" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center bg-[#BF0D3E] text-white text-[10px] font-bold rounded-full px-1"
                data-testid="unread-badge">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>
      {panelNode}
    </div>
  );
};

export default NotificationBell;
