import React, { useState, useEffect, useRef } from 'react';
import { getNotifications, getUnreadCount, markNotificationRead, markAllNotificationsRead } from '../services/api';
import { Bell, Check, CheckCheck, Calendar, Info, AlertTriangle, X } from 'lucide-react';
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

const NotificationBell = () => {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const ref = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadUnreadCount();
    const interval = setInterval(loadUnreadCount, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (open) loadNotifications();
  }, [open]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const loadUnreadCount = async () => {
    try {
      const data = await getUnreadCount();
      setUnreadCount(data.count);
    } catch {}
  };

  const loadNotifications = async () => {
    setLoading(true);
    try {
      const data = await getNotifications();
      setNotifications(data);
    } catch {}
    setLoading(false);
  };

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

  return (
    <div className="relative" ref={ref} data-testid="notification-bell">
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-sm hover:bg-slate-100 transition-colors"
        data-testid="notification-bell-btn"
      >
        <Bell className="w-5 h-5 text-slate-600" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center bg-[#BF0D3E] text-white text-[10px] font-bold rounded-full px-1" data-testid="unread-badge">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div
          className="absolute top-full right-0 mt-2 w-[min(22rem,calc(100vw-1rem))] bg-white border border-slate-200 rounded-sm shadow-xl z-[100] max-h-[min(70vh,32rem)] flex flex-col"
          data-testid="notification-panel"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
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
              <button onClick={() => setOpen(false)} className="p-1 text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Notification List */}
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
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
