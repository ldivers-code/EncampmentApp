import React, { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getNotificationBadges } from '../services/api';
import { 
  LayoutDashboard, 
  Users, 
  Calendar, 
  DollarSign, 
  BookOpen, 
  FileText, 
  Settings, 
  LogOut,
  Menu,
  X,
  ChevronLeft,
  Network,
  Bell,
  BarChart3,
  UserCircle,
  Trophy,
  Shield,
  Heart
} from 'lucide-react';
import { Button } from '../components/ui/button';

const Sidebar = ({ children }) => {
  const { user, logout, canEdit, activeUsers } = useAuth();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [badges, setBadges] = useState({});

  // Fetch notification badges
  useEffect(() => {
    const fetchBadges = async () => {
      try {
        const data = await getNotificationBadges();
        setBadges(data);
      } catch (error) {
        console.error('Failed to fetch notification badges:', error);
      }
    };

    if (user) {
      fetchBadges();
      // Refresh badges every 30 seconds
      const interval = setInterval(fetchBadges, 30000);
      return () => clearInterval(interval);
    }
  }, [user]);

  // Get badge key from path
  const getBadgeKey = (path) => {
    const keyMap = {
      '/my-flight': 'my-flight',
      '/admin': 'admin',
      '/schedule': 'schedule',
      '/budget': 'budget',
      '/roster': 'roster'
    };
    return keyMap[path];
  };

  const navItems = [
    { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/my-flight', icon: Shield, label: 'My Flight' },
    { path: '/roster', icon: Users, label: 'Roster' },
    { path: '/org-chart', icon: Network, label: 'Org Chart' },
    { path: '/schedule', icon: Calendar, label: 'Schedule' },
    { path: '/points', icon: Trophy, label: 'Point Tracking' },
    { path: '/budget', icon: DollarSign, label: 'Financial Tracker' },
    { path: '/handbooks', icon: BookOpen, label: 'Handbooks' },
    { path: '/documents', icon: FileText, label: 'Official Documents' },
  ];

  // Analytics visible to commander, executive_staff, staff, and finance
  if (['commander', 'executive_staff', 'staff', 'finance'].includes(user?.role)) {
    navItems.push({ path: '/analytics', icon: BarChart3, label: 'Analytics' });
  }

  // Health Services visible to commander, executive_staff, health_services, and staff
  if (['commander', 'executive_staff', 'health_services', 'staff'].includes(user?.role)) {
    navItems.push({ path: '/health', icon: Heart, label: 'Health Services' });
  }

  if (['commander', 'executive_staff'].includes(user?.role)) {
    navItems.push({ path: '/admin', icon: Settings, label: 'Administration' });
  }

  const NavItem = ({ item }) => {
    const isActive = location.pathname === item.path;
    const badgeKey = getBadgeKey(item.path);
    const badge = badgeKey ? badges[badgeKey] : null;
    
    return (
      <NavLink
        to={item.path}
        className={`flex items-center gap-3 px-3 py-2.5 rounded-sm transition-colors duration-150 relative ${
          isActive 
            ? 'bg-[#00205B] text-white' 
            : 'text-slate-700 hover:bg-slate-100'
        }`}
        onClick={() => setMobileOpen(false)}
        data-testid={`nav-${item.label.toLowerCase().replace(' ', '-')}`}
      >
        <div className="relative">
          <item.icon className="w-5 h-5 flex-shrink-0" />
          {badge && badge.count > 0 && (
            <span 
              className={`absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] flex items-center justify-center text-[10px] font-bold rounded-full ${
                badge.type === 'alert' 
                  ? 'bg-red-500 text-white animate-pulse' 
                  : 'bg-amber-500 text-white'
              }`}
              title={badge.label || `${badge.count} items`}
            >
              {badge.count > 9 ? '9+' : badge.count}
            </span>
          )}
        </div>
        {!collapsed && (
          <span className="text-sm font-medium flex-1">{item.label}</span>
        )}
        {!collapsed && badge && badge.count > 0 && (
          <span 
            className={`text-[10px] px-1.5 py-0.5 rounded-full ${
              badge.type === 'alert' 
                ? 'bg-red-100 text-red-700' 
                : 'bg-amber-100 text-amber-700'
            }`}
          >
            {badge.count}
          </span>
        )}
      </NavLink>
    );
  };

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* Mobile header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 bg-white border-b border-slate-200 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <img 
            src="/tnwg-patch.png" 
            alt="Tennessee Wing" 
            className="w-10 h-10 object-contain"
          />
          <span className="font-bold text-[#00205B] uppercase text-sm" style={{ fontFamily: 'Chivo, sans-serif' }}>
            CAP Encampment
          </span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setMobileOpen(!mobileOpen)}
          data-testid="mobile-menu-toggle"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </Button>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div 
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-50
        ${collapsed ? 'w-20' : 'w-64'}
        bg-white border-r border-slate-200
        transform transition-all duration-200 ease-in-out
        ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className={`p-4 border-b border-slate-100 ${collapsed ? 'px-3' : ''}`}>
            <div className={`flex items-center ${collapsed ? 'justify-center' : 'gap-3'}`}>
              <img 
                src="/tnwg-patch.png" 
                alt="Tennessee Wing CAP" 
                className={`object-contain ${collapsed ? 'w-12 h-12' : 'w-14 h-14'}`}
              />
              {!collapsed && (
                <div>
                  <h1 className="font-black text-[#00205B] uppercase text-sm leading-tight" style={{ fontFamily: 'Chivo, sans-serif' }}>
                    Tennessee Wing
                  </h1>
                  <p className="text-[10px] text-slate-500 uppercase tracking-wider">Civil Air Patrol</p>
                </div>
              )}
            </div>
          </div>

          {/* 2026 Encampment Info */}
          {!collapsed && (
            <div className="px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-[#00205B] to-[#003087]">
              <div className="flex items-center gap-2">
                <img 
                  src="/60th-ctg-patch.png" 
                  alt="60th CTG" 
                  className="w-8 h-8 object-contain"
                />
                <div>
                  <p className="text-white font-bold text-xs uppercase">2026 Encampment</p>
                  <p className="text-blue-200 text-[10px]">VTS Catoosa, GA</p>
                </div>
              </div>
            </div>
          )}

          {/* Active Users Indicator */}
          {!collapsed && (
            <div className="px-4 py-2 border-b border-slate-100 bg-slate-50">
              <div className="flex items-center gap-2">
                <div className="relative">
                  <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                </div>
                <span className="text-xs text-slate-600">
                  <span className="font-semibold text-emerald-600">{activeUsers.count}</span> online now
                </span>
              </div>
            </div>
          )}
          {collapsed && (
            <div className="px-2 py-2 border-b border-slate-100 bg-slate-50 flex justify-center" title={`${activeUsers.count} online`}>
              <div className="relative flex items-center justify-center w-8 h-6">
                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse absolute left-0" />
                <span className="text-xs font-bold text-emerald-600 ml-3">{activeUsers.count}</span>
              </div>
            </div>
          )}

          {/* Navigation */}
          <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
            {navItems.map((item) => (
              <NavItem key={item.path} item={item} />
            ))}
          </nav>

          {/* User info & logout */}
          <div className="border-t border-slate-100 p-3">
            {!collapsed && (
              <NavLink
                to="/profile"
                className="block mb-3 px-3 py-2 -mx-3 rounded-sm hover:bg-slate-50 transition-colors"
                data-testid="profile-link"
              >
                <div className="flex items-center gap-2">
                  {user?.photo_url ? (
                    <img src={user.photo_url} alt="" className="w-8 h-8 rounded-full object-cover" />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-[#00205B] text-white flex items-center justify-center text-sm font-bold">
                      {user?.name?.charAt(0)?.toUpperCase() || 'U'}
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-900 truncate">{user?.name}</p>
                    <div className="flex items-center gap-2">
                      <p className="text-xs text-slate-500 uppercase tracking-wide">{user?.role}</p>
                      {user?.flight && (
                        <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                          {user.flight.toUpperCase()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </NavLink>
            )}
            {collapsed && (
              <NavLink
                to="/profile"
                className="flex items-center justify-center p-2 mb-2 rounded-sm hover:bg-slate-50 transition-colors"
                data-testid="profile-link-collapsed"
              >
                {user?.photo_url ? (
                  <img src={user.photo_url} alt="" className="w-8 h-8 rounded-full object-cover" />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-[#00205B] text-white flex items-center justify-center text-sm font-bold">
                    {user?.name?.charAt(0)?.toUpperCase() || 'U'}
                  </div>
                )}
              </NavLink>
            )}
            <button
              onClick={logout}
              className="flex items-center gap-3 px-3 py-2 w-full text-left rounded-sm text-slate-600 hover:bg-red-50 hover:text-[#BF0D3E] transition-colors"
              data-testid="logout-btn"
            >
              <LogOut className="w-5 h-5" />
              {!collapsed && <span className="text-sm font-medium">Sign Out</span>}
            </button>
          </div>

          {/* Collapse toggle - desktop only */}
          <div className="hidden lg:block border-t border-slate-100 p-2">
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="flex items-center justify-center w-full p-2 text-slate-400 hover:text-slate-600 rounded-sm hover:bg-slate-50"
              data-testid="collapse-sidebar-btn"
            >
              <ChevronLeft className={`w-5 h-5 transition-transform ${collapsed ? 'rotate-180' : ''}`} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-h-screen lg:min-h-0">
        <div className="pt-14 lg:pt-0">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Sidebar;
