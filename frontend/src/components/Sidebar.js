import React, { useState, useEffect, useCallback, useRef } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getNotificationBadges, getNavOrder, saveNavOrder } from '../services/api';
import NotificationBell from './NotificationBell';
import HonorAgreementModal, { needsHonorAgreement } from './HonorAgreementModal';
import { 
  LayoutDashboard, Users, User, Calendar, BookOpen, FileText, Settings, LogOut,
  Menu, X, ChevronLeft, Network, BarChart3, Trophy, Shield, Heart,
  ClipboardCheck, ClipboardList, Package, Monitor, UtensilsCrossed,
  DollarSign, BedDouble, UserCheck, GripVertical, RotateCcw
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';

const ICON_MAP = {
  '/dashboard': LayoutDashboard,
  '/my-flight': Shield,
  '/roster': Users,
  '/org-chart': Network,
  '/schedule': Calendar,
  '/points': Trophy,
  '/meal-plan': UtensilsCrossed,
  '/assignments': ClipboardList,
  '/budget': DollarSign,
  '/handbooks': BookOpen,
  '/documents': FileText,
  '/analytics': BarChart3,
  '/health': Heart,
  '/training': ClipboardCheck,
  '/check-in': UserCheck,
  '/barracks': BedDouble,
  '/logistics': Package,
  '/status-control': Monitor,
  '/admin': Settings,
  '/my-cadet': User,
};

const Sidebar = ({ children }) => {
  const { user, logout, canEdit, activeUsers, refreshUser } = useAuth();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [badges, setBadges] = useState({});
  const [reorderMode, setReorderMode] = useState(false);
  const [customOrder, setCustomOrder] = useState(null); // null = default
  const [dragIdx, setDragIdx] = useState(null);
  const [dragOverIdx, setDragOverIdx] = useState(null);
  const orderLoaded = useRef(false);

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
      const interval = setInterval(fetchBadges, 30000);
      return () => clearInterval(interval);
    }
  }, [user]);

  // Load saved nav order once
  useEffect(() => {
    if (user && !orderLoaded.current) {
      orderLoaded.current = true;
      getNavOrder().then(res => {
        if (res.nav_order && res.nav_order.length > 0) {
          setCustomOrder(res.nav_order);
        }
      }).catch(() => {});
    }
  }, [user]);

  // Get badge key from path
  const getBadgeKey = (path) => {
    const keyMap = {
      '/my-flight': 'my-flight', '/admin': 'admin',
      '/schedule': 'schedule', '/budget': 'budget', '/roster': 'roster'
    };
    return keyMap[path];
  };

  // Build the default navItems based on role
  const buildNavItems = useCallback(() => {
    const items = [
      { path: '/dashboard', label: 'Dashboard' },
      { path: '/my-flight', label: 'My Flight' },
      { path: '/roster', label: 'Roster' },
      { path: '/org-chart', label: 'Org Chart' },
      { path: '/schedule', label: 'Schedule' },
      { path: '/points', label: 'Point Tracking' },
    ];

    if (user?.role === 'parent') {
      return [{ path: '/my-cadet', label: 'My Cadet' }];
    }

    items.push({ path: '/meal-plan', label: 'Meal Plan' });
    items.push({ path: '/assignments', label: 'Assignments' });

    if (['dcp', 'commander', 'executive_staff', 'finance'].includes(user?.role)) {
      items.push({ path: '/budget', label: 'Financial Tracker' });
    }

    items.push(
      { path: '/handbooks', label: 'Handbooks' },
      { path: '/documents', label: 'Official Documents' },
    );

    const canAccessPage = (pageKey, defaultRoles) => {
      if (defaultRoles.includes(user?.role)) return true;
      if (user?.role === 'squadron_commander') return true;
      if (user?.permissions?.[pageKey]) return true;
      return false;
    };

    if (canAccessPage('page_analytics', ['dcp', 'commander', 'executive_staff', 'exec_cadre', 'staff', 'finance', 'dining_facility', 'support_pa'])) {
      items.push({ path: '/analytics', label: 'Analytics' });
    }
    if (canAccessPage('page_health', ['dcp', 'commander', 'executive_staff', 'health_services', 'staff', 'support_health'])) {
      items.push({ path: '/health', label: 'Health Services' });
    }
    if (canAccessPage('page_training', ['dcp', 'commander', 'executive_staff', 'training_officer', 'staff'])) {
      items.push({ path: '/training', label: 'Training Officer' });
    }
    if (canAccessPage('page_check_in', ['dcp', 'commander', 'executive_staff', 'plans_programs', 'logistics', 'support_logistics', 'squadron_commander'])) {
      items.push({ path: '/check-in', label: 'Check-In' });
    }
    if (canAccessPage('page_barracks', ['dcp', 'commander', 'executive_staff', 'plans_programs', 'logistics', 'support_logistics', 'squadron_commander'])) {
      items.push({ path: '/barracks', label: 'Barracks' });
    }
    if (canAccessPage('page_logistics', ['dcp', 'commander', 'executive_staff', 'logistics', 'staff', 'cadre', 'exec_cadre', 'training_officer', 'finance', 'plans_programs', 'health_services', 'support_logistics', 'squadron_commander'])) {
      items.push({ path: '/logistics', label: 'Logistics' });
    }
    if (canAccessPage('page_status_board', ['dcp', 'commander', 'executive_staff', 'logistics', 'staff', 'cadre', 'exec_cadre', 'training_officer', 'finance', 'plans_programs', 'health_services', 'dining_facility', 'squadron_commander',
      'support_logistics', 'support_comms', 'support_pa', 'support_dining', 'support_health'])) {
      items.push({ path: '/status-control', label: 'Status Board' });
    }
    if (['dcp', 'commander', 'executive_staff', 'exec_cadre'].includes(user?.role)) {
      items.push({ path: '/admin', label: 'Administration' });
    }
    if (canAccessPage('page_parent_portal', ['dcp', 'commander', 'executive_staff'])) {
      items.push({ path: '/my-cadet', label: 'Parent Portal' });
    }

    return items;
  }, [user]);

  const defaultItems = buildNavItems();

  // Apply custom order: reorder defaultItems based on saved path order
  const navItems = (() => {
    if (!customOrder || customOrder.length === 0) return defaultItems;
    const pathSet = new Set(defaultItems.map(i => i.path));
    const ordered = [];
    // Add items in saved order (only if they're still accessible)
    customOrder.forEach(path => {
      const item = defaultItems.find(i => i.path === path);
      if (item) ordered.push(item);
    });
    // Append any new items not in saved order
    defaultItems.forEach(item => {
      if (!ordered.find(o => o.path === item.path)) ordered.push(item);
    });
    return ordered;
  })();

  // Drag handlers
  const handleDragStart = (idx) => setDragIdx(idx);
  const handleDragOver = (e, idx) => { e.preventDefault(); setDragOverIdx(idx); };
  const handleDragEnd = () => { setDragIdx(null); setDragOverIdx(null); };
  const handleDrop = (targetIdx) => {
    if (dragIdx === null || dragIdx === targetIdx) return;
    const items = [...navItems];
    const [moved] = items.splice(dragIdx, 1);
    items.splice(targetIdx, 0, moved);
    setCustomOrder(items.map(i => i.path));
    setDragIdx(null);
    setDragOverIdx(null);
  };

  const handleSaveOrder = async () => {
    try {
      const order = navItems.map(i => i.path);
      await saveNavOrder(order);
      setCustomOrder(order);
      setReorderMode(false);
      toast.success('Navigation order saved');
    } catch {
      toast.error('Failed to save order');
    }
  };

  const handleResetOrder = async () => {
    try {
      await saveNavOrder([]);
      setCustomOrder(null);
      setReorderMode(false);
      toast.success('Reset to default order');
    } catch {
      toast.error('Failed to reset');
    }
  };

  const NavItem = ({ item, index }) => {
    const isActive = location.pathname === item.path;
    const badgeKey = getBadgeKey(item.path);
    const badge = badgeKey ? badges[badgeKey] : null;
    const Icon = ICON_MAP[item.path] || LayoutDashboard;
    const isDragOver = dragOverIdx === index && dragIdx !== index;

    if (reorderMode) {
      return (
        <div
          draggable
          onDragStart={() => handleDragStart(index)}
          onDragOver={(e) => handleDragOver(e, index)}
          onDragEnd={handleDragEnd}
          onDrop={() => handleDrop(index)}
          className={`flex items-center gap-2 px-3 py-2 rounded-sm cursor-grab active:cursor-grabbing transition-all
            ${dragIdx === index ? 'opacity-40 scale-95' : ''}
            ${isDragOver ? 'border-t-2 border-[#00205B]' : 'border-t-2 border-transparent'}
            bg-white border border-slate-200 shadow-sm hover:shadow`}
          data-testid={`reorder-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
        >
          <GripVertical className="w-4 h-4 text-slate-400 flex-shrink-0" />
          <Icon className="w-4 h-4 text-slate-600 flex-shrink-0" />
          <span className="text-sm font-medium text-slate-700 flex-1">{item.label}</span>
          <span className="text-[10px] text-slate-400 font-mono">{index + 1}</span>
        </div>
      );
    }

    return (
      <NavLink
        to={item.path}
        className={`flex items-center gap-3 px-3 py-2.5 rounded-sm transition-colors duration-150 relative ${
          isActive 
            ? 'bg-[#00205B] text-white' 
            : 'text-slate-700 hover:bg-slate-100'
        }`}
        onClick={() => setMobileOpen(false)}
        data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
      >
        <div className="relative">
          <Icon className="w-5 h-5 flex-shrink-0" />
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
    <>
    <div className="min-h-screen flex bg-slate-50">
      {/* Mobile header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 bg-white border-b border-slate-200 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <img src="/tnwg-patch.png" alt="Tennessee Wing" className="w-10 h-10 object-contain" />
          <span className="font-bold text-[#00205B] uppercase text-sm" style={{ fontFamily: 'Chivo, sans-serif' }}>
            CAP Encampment
          </span>
        </div>
        <div className="flex items-center gap-1">
          <NotificationBell />
          <Button variant="ghost" size="sm" onClick={() => setMobileOpen(!mobileOpen)} data-testid="mobile-menu-toggle">
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </Button>
        </div>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 bg-black/50 z-40" onClick={() => setMobileOpen(false)} />
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
              <img src="/tnwg-patch.png" alt="Tennessee Wing CAP" className={`object-contain ${collapsed ? 'w-12 h-12' : 'w-14 h-14'}`} />
              {!collapsed && (
                <div className="flex-1">
                  <h1 className="font-black text-[#00205B] uppercase text-sm leading-tight" style={{ fontFamily: 'Chivo, sans-serif' }}>
                    Tennessee Wing
                  </h1>
                  <p className="text-[10px] text-slate-500 uppercase tracking-wider">Civil Air Patrol</p>
                </div>
              )}
              <div className="hidden lg:block">
                <NotificationBell />
              </div>
            </div>
          </div>

          {/* 2026 Encampment Info */}
          {!collapsed && (
            <div className="px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-[#00205B] to-[#003087]">
              <div className="flex items-center gap-2">
                <img src="/60th-ctg-patch.png" alt="60th CTG" className="w-8 h-8 object-contain" />
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

          {/* Reorder controls */}
          {reorderMode && !collapsed && (
            <div className="px-3 py-2 border-b border-amber-200 bg-amber-50">
              <p className="text-[10px] uppercase font-bold text-amber-700 mb-1.5">Drag to reorder</p>
              <div className="flex gap-1.5">
                <Button size="sm" className="h-7 text-xs bg-[#00205B] rounded-sm flex-1" onClick={handleSaveOrder} data-testid="save-nav-order-btn">
                  Save Order
                </Button>
                <Button size="sm" variant="outline" className="h-7 text-xs rounded-sm" onClick={handleResetOrder} title="Reset to default" data-testid="reset-nav-order-btn">
                  <RotateCcw className="w-3 h-3" />
                </Button>
                <Button size="sm" variant="ghost" className="h-7 text-xs rounded-sm" onClick={() => setReorderMode(false)}>
                  <X className="w-3 h-3" />
                </Button>
              </div>
            </div>
          )}

          {/* Navigation */}
          <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
            {navItems.map((item, idx) => (
              <NavItem key={item.path} item={item} index={idx} />
            ))}
          </nav>

          {/* Reorder toggle button */}
          {!collapsed && !reorderMode && user?.role !== 'parent' && (
            <div className="px-3 pb-1">
              <button
                onClick={() => setReorderMode(true)}
                className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-slate-400 hover:text-slate-600 hover:bg-slate-50 rounded-sm transition-colors"
                data-testid="reorder-nav-btn"
              >
                <GripVertical className="w-3.5 h-3.5" />
                Customize Order
              </button>
            </div>
          )}

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
      <main className="flex-1 min-h-screen lg:min-h-0 overflow-x-hidden overflow-y-auto">
        <div className="pt-14 lg:pt-0">
          {children}
        </div>
      </main>
    </div>

    {/* Honor Agreement Modal - blocks app until signed */}
    {needsHonorAgreement(user) && (
      <HonorAgreementModal
        user={user}
        onComplete={() => refreshUser()}
      />
    )}
    </>
  );
};

export default Sidebar;
