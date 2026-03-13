import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { 
  getSchedule, 
  getScheduleSettings,
  createScheduleEvent, 
  updateScheduleEvent, 
  deleteScheduleEvent,
  importSchedule,
  publishSchedule,
  unpublishSchedule,
  submitScheduleChange,
  getScheduleChangeRequests,
  reviewScheduleChange,
  getPendingScheduleChangesCount
} from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Checkbox } from '../components/ui/checkbox';
import { toast } from 'sonner';
import { format, parseISO, addDays, isSameDay } from 'date-fns';
import { 
  Plus, 
  Clock, 
  MapPin, 
  Edit2, 
  Trash2,
  List,
  Grid3X3,
  Upload,
  Send,
  EyeOff,
  Eye,
  AlertCircle,
  RefreshCw,
  Users,
  Filter,
  ChevronLeft,
  ChevronRight,
  Shirt,
  MessageSquarePlus,
  CheckCircle,
  XCircle,
  FileEdit
} from 'lucide-react';
import NotificationManager from '../components/NotificationManager';

const REFRESH_INTERVAL = 30000; // 30 seconds

const SchedulePage = () => {
  const { canEdit, user } = useAuth();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(new Date('2026-07-17'));
  const [viewMode, setViewMode] = useState('day');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingEvent, setEditingEvent] = useState(null);
  const [isPublished, setIsPublished] = useState(false);
  const [scheduleSettings, setScheduleSettings] = useState(null);
  const [importing, setImporting] = useState(false);
  const [scheduleFilter, setScheduleFilter] = useState('all'); // Allow all members to filter
  const [lastVersion, setLastVersion] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [showMobileDatePicker, setShowMobileDatePicker] = useState(false);
  const [showFilterDropdown, setShowFilterDropdown] = useState(false);
  const [changeRequestOpen, setChangeRequestOpen] = useState(false);
  const [changeReviewOpen, setChangeReviewOpen] = useState(false);
  const [changeRequests, setChangeRequests] = useState([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [changeForm, setChangeForm] = useState({
    change_type: 'modify', event_title: '', event_date: '', current_time: '',
    requested_time: '', requested_location: '', reason: '', details: ''
  });
  const fileInputRef = useRef(null);
  const refreshIntervalRef = useRef(null);
  const touchStartX = useRef(null);
  const touchEndX = useRef(null);
  const scheduleContainerRef = useRef(null);

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    date: '',
    start_time: '',
    end_time: '',
    location: '',
    event_type: 'training',
    target_groups: ['all'],
    uniform: 'default'
  });

  // Detect mobile viewport
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Encampment dates: July 17-24, 2026
  const encampmentDates = useMemo(() => {
    const dates = [];
    const startDate = new Date('2026-07-17');
    for (let i = 0; i < 8; i++) {
      dates.push(addDays(startDate, i));
    }
    return dates;
  }, []);

  const eventTypes = [
    { value: 'general', label: 'General', color: 'bg-slate-500', mobileColor: 'border-l-slate-500' },
    { value: 'training', label: 'Training', color: 'bg-blue-600', mobileColor: 'border-l-blue-600' },
    { value: 'ceremony', label: 'Ceremony', color: 'bg-purple-600', mobileColor: 'border-l-purple-600' },
    { value: 'meal', label: 'Meal', color: 'bg-amber-500', mobileColor: 'border-l-amber-500' },
    { value: 'recreation', label: 'Recreation', color: 'bg-emerald-500', mobileColor: 'border-l-emerald-500' },
    { value: 'pt', label: 'PT', color: 'bg-red-600', mobileColor: 'border-l-red-600' },
    { value: 'admin', label: 'Admin', color: 'bg-slate-600', mobileColor: 'border-l-slate-600' },
    { value: 'leadership', label: 'Leadership', color: 'bg-indigo-600', mobileColor: 'border-l-indigo-600' },
    { value: 'academics', label: 'Academics', color: 'bg-teal-600', mobileColor: 'border-l-teal-600' }
  ];

  const targetGroupOptions = [
    { value: 'all', label: 'All Participants', category: 'general' },
    { value: 'staff', label: 'Staff/Cadre', category: 'general' },
    { value: '6th_cts', label: '6th CTS', category: 'squadron' },
    { value: '21st_cts', label: '21st CTS', category: 'squadron' },
    { value: '22nd_cts', label: '22nd CTS', category: 'squadron' },
    { value: 'alpha', label: 'Alpha Flight', category: 'flight' },
    { value: 'bravo', label: 'Bravo Flight', category: 'flight' },
    { value: 'charlie', label: 'Charlie Flight', category: 'flight' },
    { value: 'delta', label: 'Delta Flight', category: 'flight' },
    { value: 'echo', label: 'Echo Flight', category: 'flight' },
    { value: 'foxtrot', label: 'Foxtrot Flight', category: 'flight' }
  ];

  // Uniform options for events
  const uniformOptions = [
    { value: 'default', label: 'Default (UoD)' },
    { value: 'ABU', label: 'ABU' },
    { value: 'Blues', label: 'Service Dress Blues' },
    { value: 'PT', label: 'PT Gear' },
    { value: 'Flight Suit', label: 'Flight Suit' },
    { value: 'Civilian', label: 'Civilian Attire' },
    { value: 'Class A', label: 'Class A' },
    { value: 'Class B', label: 'Class B' }
  ];

  // Schedule filter options - available to ALL members
  const scheduleFilterOptions = [
    { value: 'all', label: 'All Events' },
    { value: 'staff', label: 'Staff Only' },
    { value: '6th_cts', label: '6th CTS' },
    { value: '21st_cts', label: '21st CTS' },
    { value: '22nd_cts', label: '22nd CTS' },
    { value: 'alpha', label: 'Alpha Flight' },
    { value: 'bravo', label: 'Bravo Flight' },
    { value: 'charlie', label: 'Charlie Flight' },
    { value: 'delta', label: 'Delta Flight' },
    { value: 'echo', label: 'Echo Flight' },
    { value: 'foxtrot', label: 'Foxtrot Flight' }
  ];

  // Time slots for day view (0600-2200 in 30-min increments)
  const timeSlots = useMemo(() => {
    const slots = [];
    for (let hour = 6; hour <= 22; hour++) {
      for (let min of [0, 30]) {
        if (hour === 22 && min === 30) continue;
        slots.push(`${hour.toString().padStart(2, '0')}:${min.toString().padStart(2, '0')}`);
      }
    }
    return slots;
  }, []);

  const loadEvents = useCallback(async (showRefreshIndicator = false) => {
    if (showRefreshIndicator) setIsRefreshing(true);
    try {
      const data = await getSchedule();
      setEvents(data);
    } catch (error) {
      console.error('Failed to load schedule');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  const loadSettings = useCallback(async () => {
    try {
      const settings = await getScheduleSettings();
      setScheduleSettings(settings);
      setIsPublished(settings.is_published);
      
      if (settings.version !== lastVersion && lastVersion !== 0) {
        loadEvents(true);
        toast.info('Schedule updated');
      }
      setLastVersion(settings.version);
    } catch (error) {
      console.error('Failed to load schedule settings');
    }
  }, [lastVersion, loadEvents]);

  useEffect(() => {
    loadEvents();
    loadSettings();
  }, []);

  // Reload when filter changes
  useEffect(() => {
    if (!loading) {
      // No need to reload - filtering is done client-side
    }
  }, [scheduleFilter]);

  useEffect(() => {
    refreshIntervalRef.current = setInterval(() => {
      loadSettings();
    }, REFRESH_INTERVAL);

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [loadSettings]);

  // Touch handlers for swipe navigation
  const handleTouchStart = (e) => {
    touchStartX.current = e.touches[0].clientX;
  };

  const handleTouchMove = (e) => {
    touchEndX.current = e.touches[0].clientX;
  };

  const handleTouchEnd = () => {
    if (!touchStartX.current || !touchEndX.current) return;
    
    const diff = touchStartX.current - touchEndX.current;
    const minSwipeDistance = 50;

    if (Math.abs(diff) > minSwipeDistance) {
      if (diff > 0) {
        // Swiped left - go to next day
        navigateDay(1);
      } else {
        // Swiped right - go to previous day
        navigateDay(-1);
      }
    }

    touchStartX.current = null;
    touchEndX.current = null;
  };

  const navigateDay = (direction) => {
    const currentIndex = encampmentDates.findIndex(d => isSameDay(d, selectedDate));
    const newIndex = currentIndex + direction;
    if (newIndex >= 0 && newIndex < encampmentDates.length) {
      setSelectedDate(encampmentDates[newIndex]);
    }
  };

  const currentDayIndex = encampmentDates.findIndex(d => isSameDay(d, selectedDate));

  // Get events for selected date with filter applied
  const eventsForDate = useMemo(() => {
    let filtered = events.filter(e => isSameDay(parseISO(e.date), selectedDate));
    
    // Apply schedule filter
    if (scheduleFilter !== 'all') {
      filtered = filtered.filter(e => {
        // Show event if it targets 'all' or matches the selected filter
        if (!e.target_groups || e.target_groups.includes('all')) return true;
        
        // Check if event targets the selected group
        if (e.target_groups.includes(scheduleFilter)) return true;
        
        // Check squadron membership for flight filters
        const flightToSquadron = {
          'alpha': '6th_cts', 'bravo': '6th_cts',
          'charlie': '21st_cts', 'delta': '21st_cts',
          'echo': '22nd_cts', 'foxtrot': '22nd_cts'
        };
        
        // If filtering by squadron, also show events for its flights
        if (['6th_cts', '21st_cts', '22nd_cts'].includes(scheduleFilter)) {
          const squadronFlights = Object.entries(flightToSquadron)
            .filter(([_, sq]) => sq === scheduleFilter)
            .map(([fl, _]) => fl);
          if (e.target_groups.some(g => squadronFlights.includes(g))) return true;
        }
        
        // If filtering by flight, also show squadron-level events
        if (flightToSquadron[scheduleFilter]) {
          const parentSquadron = flightToSquadron[scheduleFilter];
          if (e.target_groups.includes(parentSquadron)) return true;
        }
        
        return false;
      });
    }
    
    return filtered.sort((a, b) => a.start_time.localeCompare(b.start_time));
  }, [events, selectedDate, scheduleFilter]);

  const getFilterLabel = () => {
    const option = scheduleFilterOptions.find(o => o.value === scheduleFilter);
    return option ? option.label : 'All Events';
  };

  // Group events by time slot for day view
  const eventsByTimeSlot = useMemo(() => {
    const grouped = {};
    timeSlots.forEach(slot => {
      grouped[slot] = eventsForDate.filter(e => {
        const eventStart = e.start_time.substring(0, 5);
        const eventEnd = e.end_time.substring(0, 5);
        return eventStart <= slot && slot < eventEnd;
      });
    });
    return grouped;
  }, [eventsForDate, timeSlots]);

  // Group consecutive events for mobile compact view
  const compactEventsForDate = useMemo(() => {
    const seen = new Set();
    return eventsForDate.filter(e => {
      const key = `${e.title}-${e.start_time}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [eventsForDate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingEvent) {
        await updateScheduleEvent(editingEvent.id, formData);
        toast.success('Event updated');
      } else {
        await createScheduleEvent(formData);
        toast.success('Event created');
      }
      setIsModalOpen(false);
      resetForm();
      loadEvents();
      loadSettings();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Operation failed');
    }
  };

  const handleEdit = (event) => {
    setEditingEvent(event);
    setFormData({
      title: event.title,
      description: event.description || '',
      date: event.date,
      start_time: event.start_time,
      end_time: event.end_time,
      location: event.location || '',
      event_type: event.event_type,
      target_groups: event.target_groups || ['all'],
      uniform: event.uniform || 'default'
    });
    setIsModalOpen(true);
  };

  const handleDelete = async (id) => {
    if (window.confirm('Delete this event?')) {
      try {
        await deleteScheduleEvent(id);
        toast.success('Event deleted');
        loadEvents();
        loadSettings();
      } catch (error) {
        toast.error('Failed to delete event');
      }
    }
  };

  const handleTimeSlotClick = (timeSlot) => {
    if (!canEdit()) return;
    setFormData({
      ...formData,
      date: format(selectedDate, 'yyyy-MM-dd'),
      start_time: timeSlot,
      end_time: timeSlot.replace(/(\d{2}):(\d{2})/, (_, h, m) => {
        const hour = parseInt(h);
        const min = parseInt(m);
        if (min === 30) return `${(hour + 1).toString().padStart(2, '0')}:00`;
        return `${h}:30`;
      }),
      target_groups: ['all']
    });
    setIsModalOpen(true);
  };

  const handleImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setImporting(true);
    try {
      const result = await importSchedule(file);
      toast.success(result.message);
      loadEvents();
      loadSettings();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Import failed');
    } finally {
      setImporting(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handlePublish = async () => {
    try {
      await publishSchedule();
      setIsPublished(true);
      toast.success('Schedule published!');
      loadSettings();
    } catch (error) {
      toast.error('Failed to publish schedule');
    }
  };

  const handleUnpublish = async () => {
    try {
      await unpublishSchedule();
      setIsPublished(false);
      toast.success('Schedule unpublished');
      loadSettings();
    } catch (error) {
      toast.error('Failed to unpublish schedule');
    }
  };

  const handleTargetGroupToggle = (value) => {
    let newGroups = [...formData.target_groups];
    
    if (value === 'all') {
      newGroups = ['all'];
    } else {
      newGroups = newGroups.filter(g => g !== 'all');
      
      if (newGroups.includes(value)) {
        newGroups = newGroups.filter(g => g !== value);
      } else {
        newGroups.push(value);
      }
      
      if (newGroups.length === 0) {
        newGroups = ['all'];
      }
    }
    
    setFormData({ ...formData, target_groups: newGroups });
  };

  const resetForm = () => {
    setEditingEvent(null);
    setFormData({
      title: '',
      description: '',
      date: '',
      start_time: '',
      end_time: '',
      location: '',
      event_type: 'training',
      target_groups: ['all'],
      uniform: ''
    });
  };

  // Schedule Change Request handlers
  const loadPendingCount = useCallback(async () => {
    try {
      const data = await getPendingScheduleChangesCount();
      setPendingCount(data.count);
    } catch {}
  }, []);

  const loadChangeRequests = useCallback(async () => {
    try {
      const data = await getScheduleChangeRequests();
      setChangeRequests(data);
    } catch {}
  }, []);

  useEffect(() => { loadPendingCount(); }, [loadPendingCount]);

  const handleSubmitChangeRequest = async () => {
    if (!changeForm.event_title || !changeForm.reason) {
      toast.error('Event/activity name and reason are required');
      return;
    }
    try {
      await submitScheduleChange(changeForm);
      toast.success('Change request submitted');
      setChangeRequestOpen(false);
      setChangeForm({ change_type: 'modify', event_title: '', event_date: '', current_time: '', requested_time: '', requested_location: '', reason: '', details: '' });
      loadPendingCount();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to submit');
    }
  };

  const handleReviewChange = async (id, status, notes = '') => {
    try {
      await reviewScheduleChange(id, { status, notes });
      toast.success(`Request ${status}`);
      loadChangeRequests();
      loadPendingCount();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed');
    }
  };



  const getEventTypeColor = (type) => {
    return eventTypes.find(t => t.value === type)?.color || 'bg-slate-500';
  };

  const getEventTypeMobileColor = (type) => {
    return eventTypes.find(t => t.value === type)?.mobileColor || 'border-l-slate-500';
  };

  const getEventTypeLabel = (type) => {
    return eventTypes.find(t => t.value === type)?.label || type;
  };

  const getDayLabel = (date) => {
    const dayIndex = encampmentDates.findIndex(d => isSameDay(d, date));
    if (dayIndex === 0) return 'Staff Arrival';
    if (dayIndex === 1) return 'In-Processing';
    if (dayIndex === 7) return 'Graduation';
    return `Day ${dayIndex - 1}`;
  };

  const getTargetGroupsLabel = (groups) => {
    if (!groups || groups.length === 0 || groups.includes('all')) return null;
    return groups.map(g => {
      const option = targetGroupOptions.find(o => o.value === g);
      return option ? option.label : g;
    }).join(', ');
  };

  const getUserUnitLabel = () => {
    if (!user?.flight && !user?.squadron) return null;
    const parts = [];
    if (user.flight) {
      const flight = targetGroupOptions.find(o => o.value === user.flight);
      if (flight) parts.push(flight.label);
    }
    if (user.squadron) {
      const sq = targetGroupOptions.find(o => o.value === user.squadron);
      if (sq) parts.push(sq.label);
    }
    return parts.join(' • ');
  };

  if (loading) {
    return (
      <div className="p-4 md:p-6 lg:p-8 animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-400">Loading schedule...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-2 sm:p-4 md:p-6 lg:p-8 animate-fade-in max-w-full">
      {/* Mobile Header */}
      {isMobile ? (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-lg font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Schedule
            </h1>
            <div className="flex items-center gap-1">
              <NotificationManager compact />
              <div className={`flex items-center px-1.5 py-1 rounded text-[10px] ${isRefreshing ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-500'}`}>
                <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
              </div>
              {canEdit() && (
                <>
                  {isPublished ? (
                    <span className="bg-emerald-100 text-emerald-700 px-2 py-1 rounded text-[10px] font-medium flex items-center gap-1">
                      <Eye className="w-3 h-3" />
                    </span>
                  ) : (
                    <span className="bg-amber-100 text-amber-700 px-2 py-1 rounded text-[10px] font-medium flex items-center gap-1">
                      <EyeOff className="w-3 h-3" />
                    </span>
                  )}
                </>
              )}
            </div>
          </div>
          
          {/* Mobile Day Navigator with Swipe hint */}
          <div className="bg-[#00205B] rounded-lg p-3 text-white">
            <div className="flex items-center justify-between">
              <button 
                onClick={() => navigateDay(-1)}
                disabled={currentDayIndex === 0}
                className="p-2 rounded-full hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed"
                data-testid="prev-day-btn"
              >
                <ChevronLeft className="w-6 h-6" />
              </button>
              
              <button 
                onClick={() => setShowMobileDatePicker(!showMobileDatePicker)}
                className="text-center flex-1"
                data-testid="date-picker-toggle"
              >
                <div className="text-xs opacity-75 uppercase tracking-wider">
                  {format(selectedDate, 'EEEE')}
                </div>
                <div className="text-2xl font-bold">
                  {format(selectedDate, 'MMM d')}
                </div>
                <div className="text-xs opacity-75">{getDayLabel(selectedDate)}</div>
              </button>
              
              <button 
                onClick={() => navigateDay(1)}
                disabled={currentDayIndex === encampmentDates.length - 1}
                className="p-2 rounded-full hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed"
                data-testid="next-day-btn"
              >
                <ChevronRight className="w-6 h-6" />
              </button>
            </div>
            
            {/* Swipe hint */}
            <div className="text-center text-[10px] opacity-50 mt-1">
              Swipe left/right to change day
            </div>
          </div>

          {/* Mobile Date Picker Dropdown */}
          {showMobileDatePicker && (
            <div className="mt-2 bg-white border border-slate-200 rounded-lg shadow-lg p-2 grid grid-cols-4 gap-1">
              {encampmentDates.map((date, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setSelectedDate(date);
                    setShowMobileDatePicker(false);
                  }}
                  className={`p-2 rounded text-center transition-colors ${
                    isSameDay(date, selectedDate)
                      ? 'bg-[#00205B] text-white'
                      : 'bg-slate-50 text-slate-700 hover:bg-slate-100'
                  }`}
                >
                  <div className="text-[10px] uppercase">{format(date, 'EEE')}</div>
                  <div className="text-lg font-bold">{format(date, 'd')}</div>
                </button>
              ))}
            </div>
          )}

          {/* User Unit Info (mobile) */}
          {getUserUnitLabel() && (
            <div className="mt-2 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 flex items-center gap-2">
              <Users className="w-4 h-4 text-blue-600" />
              <p className="text-blue-800 text-xs">
                {getUserUnitLabel()}
              </p>
            </div>
          )}

          {/* Editor Actions (mobile) */}
          <div className="mt-2 space-y-2">
            <div className="flex gap-2">
              {/* Schedule Filter - Available to ALL users */}
              <div className="relative flex-1">
                <button
                  onClick={() => setShowFilterDropdown(!showFilterDropdown)}
                  className="w-full flex items-center justify-between gap-1 px-3 py-2 text-xs border border-slate-200 rounded-sm bg-white hover:bg-slate-50"
                  data-testid="mobile-schedule-filter"
                >
                  <span className="flex items-center gap-1">
                    <Filter className="w-3 h-3 text-slate-400" />
                    <span className="truncate">{getFilterLabel()}</span>
                  </span>
                  <ChevronRight className={`w-3 h-3 text-slate-400 transition-transform ${showFilterDropdown ? 'rotate-90' : ''}`} />
                </button>
                {showFilterDropdown && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-sm shadow-lg z-50 max-h-64 overflow-y-auto">
                    {scheduleFilterOptions.map(option => (
                      <button
                        key={option.value}
                        onClick={() => {
                          setScheduleFilter(option.value);
                          setShowFilterDropdown(false);
                        }}
                        className={`w-full px-3 py-2 text-left text-xs hover:bg-slate-50 ${
                          scheduleFilter === option.value ? 'bg-[#00205B] text-white' : ''
                        }`}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <Button size="sm" variant="outline" className="text-xs px-2 shrink-0" onClick={() => setChangeRequestOpen(true)} data-testid="mobile-request-change-btn">
                <MessageSquarePlus className="w-3 h-3 mr-1" />
                Request
              </Button>
              {canEdit() && (
                <Button size="sm" variant="outline" className="text-xs px-2 shrink-0 relative" onClick={() => { setChangeReviewOpen(true); loadChangeRequests(); }} data-testid="mobile-review-changes-btn">
                  <FileEdit className="w-3 h-3" />
                  {pendingCount > 0 && (
                    <span className="absolute -top-1 -right-1 min-w-[14px] h-[14px] flex items-center justify-center text-[8px] font-bold rounded-full bg-red-500 text-white">
                      {pendingCount}
                    </span>
                  )}
                </Button>
              )}
            </div>
            {canEdit() && (
              <Dialog open={isModalOpen} onOpenChange={(open) => {
                setIsModalOpen(open);
                if (!open) resetForm();
              }}>
                <DialogTrigger asChild>
                  <Button size="sm" className="bg-[#00205B] text-xs w-full">
                    <Plus className="w-3 h-3 mr-1" />
                    Add Event
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-[95vw] max-h-[90vh] overflow-y-auto rounded-lg">
                  <DialogHeader>
                    <DialogTitle className="text-[#00205B] uppercase font-bold text-sm" style={{ fontFamily: 'Chivo, sans-serif' }}>
                      {editingEvent ? 'Edit Event' : 'Add Event'}
                    </DialogTitle>
                  </DialogHeader>
                  <form onSubmit={handleSubmit} className="space-y-3 mt-3">
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Title *</Label>
                      <Input
                        value={formData.title}
                        onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                        required
                        className="mt-1 rounded-sm text-sm"
                        data-testid="event-title-input"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <Label className="text-xs uppercase tracking-wide text-slate-600">Type</Label>
                        <Select
                          value={formData.event_type}
                          onValueChange={(value) => setFormData({ ...formData, event_type: value })}
                        >
                          <SelectTrigger className="mt-1 rounded-sm text-sm">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {eventTypes.map(type => (
                              <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label className="text-xs uppercase tracking-wide text-slate-600">Date *</Label>
                        <Input
                          type="date"
                          value={formData.date}
                          onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                          required
                          className="mt-1 rounded-sm text-sm"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <Label className="text-xs uppercase tracking-wide text-slate-600">Start *</Label>
                        <Input
                          type="time"
                          value={formData.start_time}
                          onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                          required
                          className="mt-1 rounded-sm text-sm"
                        />
                      </div>
                      <div>
                        <Label className="text-xs uppercase tracking-wide text-slate-600">End *</Label>
                        <Input
                          type="time"
                          value={formData.end_time}
                          onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                          required
                          className="mt-1 rounded-sm text-sm"
                        />
                      </div>
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Location</Label>
                      <Input
                        value={formData.location}
                        onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                        className="mt-1 rounded-sm text-sm"
                      />
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600 flex items-center gap-1">
                        <Shirt className="w-3 h-3" />
                        Uniform
                      </Label>
                      <Select
                        value={formData.uniform || ''}
                        onValueChange={(value) => setFormData({ ...formData, uniform: value })}
                      >
                        <SelectTrigger className="mt-1 rounded-sm text-sm">
                          <SelectValue placeholder="Default (UoD)" />
                        </SelectTrigger>
                        <SelectContent>
                          {uniformOptions.map(option => (
                            <SelectItem key={option.value} value={option.value}>
                              {option.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    
                    {/* Target Groups - Compact for mobile */}
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600 flex items-center gap-1">
                        <Users className="w-3 h-3" />
                        Target Groups
                      </Label>
                      <div className="mt-1 border border-slate-200 rounded-sm p-2 bg-slate-50 space-y-2">
                        <div className="flex flex-wrap gap-2">
                          {targetGroupOptions.filter(o => o.category === 'general').map(option => (
                            <label key={option.value} className="flex items-center gap-1 cursor-pointer text-xs">
                              <Checkbox
                                checked={formData.target_groups.includes(option.value)}
                                onCheckedChange={() => handleTargetGroupToggle(option.value)}
                                className="w-4 h-4"
                              />
                              <span>{option.label}</span>
                            </label>
                          ))}
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {targetGroupOptions.filter(o => o.category === 'squadron').map(option => (
                            <label key={option.value} className="flex items-center gap-1 cursor-pointer text-xs">
                              <Checkbox
                                checked={formData.target_groups.includes(option.value)}
                                onCheckedChange={() => handleTargetGroupToggle(option.value)}
                                disabled={formData.target_groups.includes('all')}
                                className="w-4 h-4"
                              />
                              <span>{option.label.replace(' ', '')}</span>
                            </label>
                          ))}
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {targetGroupOptions.filter(o => o.category === 'flight').map(option => (
                            <label key={option.value} className="flex items-center gap-1 cursor-pointer text-xs">
                              <Checkbox
                                checked={formData.target_groups.includes(option.value)}
                                onCheckedChange={() => handleTargetGroupToggle(option.value)}
                                disabled={formData.target_groups.includes('all')}
                                className="w-4 h-4"
                              />
                              <span>{option.value.charAt(0).toUpperCase() + option.value.slice(1)}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex justify-end gap-2 pt-2">
                      <Button type="button" variant="outline" size="sm" onClick={() => setIsModalOpen(false)}>
                        Cancel
                      </Button>
                      <Button type="submit" size="sm" className="bg-[#00205B]">
                        {editingEvent ? 'Update' : 'Add'}
                      </Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>
            )}
          </div>
        </div>
      ) : (
        /* Desktop Header */
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl lg:text-3xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Training Schedule
            </h1>
            <p className="text-slate-500 text-sm mt-1">
              TNWG Summer Encampment • July 17-24, 2026
              {getUserUnitLabel() && (
                <span className="ml-2 text-[#00205B] font-medium">• {getUserUnitLabel()}</span>
              )}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Notification toggle */}
            <NotificationManager compact />
            
            <div className={`flex items-center gap-1 px-2 py-1 rounded-sm text-xs ${isRefreshing ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-500'}`}>
              <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span>Auto-sync</span>
            </div>

            {canEdit() && (
              <div className={`flex items-center gap-1 px-3 py-1.5 rounded-sm text-xs font-medium ${
                isPublished 
                  ? 'bg-emerald-100 text-emerald-700 border border-emerald-200' 
                  : 'bg-amber-100 text-amber-700 border border-amber-200'
              }`}>
                {isPublished ? (
                  <>
                    <Eye className="w-3 h-3" />
                    <span>Published</span>
                  </>
                ) : (
                  <>
                    <EyeOff className="w-3 h-3" />
                    <span>Draft</span>
                  </>
                )}
              </div>
            )}

            {/* Schedule Filter - Available to ALL users */}
            <Select
              value={scheduleFilter}
              onValueChange={(value) => setScheduleFilter(value)}
            >
              <SelectTrigger 
                className="w-40 rounded-sm text-xs border-slate-200"
                data-testid="schedule-filter-select"
              >
                <Filter className="w-3 h-3 mr-1 text-slate-400" />
                <SelectValue placeholder="Filter Schedule" />
              </SelectTrigger>
              <SelectContent>
                {scheduleFilterOptions.map(option => (
                  <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <div className="flex border border-slate-200 rounded-sm overflow-hidden">
              <button
                onClick={() => setViewMode('day')}
                className={`px-3 py-2 text-sm ${viewMode === 'day' ? 'bg-[#00205B] text-white' : 'bg-white text-slate-600 hover:bg-slate-50'}`}
                data-testid="view-day-btn"
              >
                <Grid3X3 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`px-3 py-2 text-sm ${viewMode === 'list' ? 'bg-[#00205B] text-white' : 'bg-white text-slate-600 hover:bg-slate-50'}`}
                data-testid="view-list-btn"
              >
                <List className="w-4 h-4" />
              </button>
            </div>

            {canEdit() && (
              <>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleImport}
                  className="hidden"
                  id="schedule-import"
                />
                <Button
                  variant="outline"
                  className="rounded-sm"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={importing}
                  data-testid="import-schedule-btn"
                >
                  <Upload className="w-4 h-4 mr-2" />
                  {importing ? 'Importing...' : 'Import'}
                </Button>

                {isPublished ? (
                  <Button
                    variant="outline"
                    className="rounded-sm border-amber-300 text-amber-700 hover:bg-amber-50"
                    onClick={handleUnpublish}
                    data-testid="unpublish-btn"
                  >
                    <EyeOff className="w-4 h-4 mr-2" />
                    Unpublish
                  </Button>
                ) : (
                  <Button
                    className="bg-emerald-600 hover:bg-emerald-700 rounded-sm"
                    onClick={handlePublish}
                    data-testid="publish-btn"
                  >
                    <Send className="w-4 h-4 mr-2" />
                    Publish
                  </Button>
                )}

                <Dialog open={isModalOpen} onOpenChange={(open) => {
                  setIsModalOpen(open);
                  if (!open) resetForm();
                }}>
                  <DialogTrigger asChild>
                    <Button className="bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="add-event-btn">
                      <Plus className="w-4 h-4 mr-2" />
                      Add Event
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
                    <DialogHeader>
                      <DialogTitle className="text-[#00205B] uppercase font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                        {editingEvent ? 'Edit Event' : 'Add Event'}
                      </DialogTitle>
                    </DialogHeader>
                    <form onSubmit={handleSubmit} className="space-y-4 mt-4">
                      <div>
                        <Label className="text-xs uppercase tracking-wide text-slate-600">Title *</Label>
                        <Input
                          value={formData.title}
                          onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                          required
                          className="mt-1 rounded-sm"
                          placeholder="Morning Formation"
                          data-testid="event-title-input"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label className="text-xs uppercase tracking-wide text-slate-600">Event Type</Label>
                          <Select
                            value={formData.event_type}
                            onValueChange={(value) => setFormData({ ...formData, event_type: value })}
                          >
                            <SelectTrigger className="mt-1 rounded-sm">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {eventTypes.map(type => (
                                <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label className="text-xs uppercase tracking-wide text-slate-600">Date *</Label>
                          <Input
                            type="date"
                            value={formData.date}
                            onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                            required
                            className="mt-1 rounded-sm"
                          />
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label className="text-xs uppercase tracking-wide text-slate-600">Start Time *</Label>
                          <Input
                            type="time"
                            value={formData.start_time}
                            onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                            required
                            className="mt-1 rounded-sm"
                          />
                        </div>
                        <div>
                          <Label className="text-xs uppercase tracking-wide text-slate-600">End Time *</Label>
                          <Input
                            type="time"
                            value={formData.end_time}
                            onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                            required
                            className="mt-1 rounded-sm"
                          />
                        </div>
                      </div>
                      <div>
                        <Label className="text-xs uppercase tracking-wide text-slate-600">Location</Label>
                        <Input
                          value={formData.location}
                          onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                          className="mt-1 rounded-sm"
                          placeholder="Parade Ground, DFAC, TR-1..."
                        />
                      </div>
                      <div>
                        <Label className="text-xs uppercase tracking-wide text-slate-600 flex items-center gap-2">
                          <Shirt className="w-3 h-3" />
                          Uniform
                        </Label>
                        <Select
                          value={formData.uniform || ''}
                          onValueChange={(value) => setFormData({ ...formData, uniform: value })}
                        >
                          <SelectTrigger className="mt-1 rounded-sm">
                            <SelectValue placeholder="Default (Uniform of the Day)" />
                          </SelectTrigger>
                          <SelectContent>
                            {uniformOptions.map(option => (
                              <SelectItem key={option.value} value={option.value}>
                                {option.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <p className="text-xs text-slate-400 mt-1">Leave blank to use Uniform of the Day</p>
                      </div>
                      
                      <div>
                        <Label className="text-xs uppercase tracking-wide text-slate-600 flex items-center gap-2">
                          <Users className="w-3 h-3" />
                          Target Groups
                        </Label>
                        <p className="text-xs text-slate-400 mt-1 mb-2">Select which groups should see this event</p>
                        <div className="space-y-3 border border-slate-200 rounded-sm p-3 bg-slate-50">
                          <div className="flex flex-wrap gap-3">
                            {targetGroupOptions.filter(o => o.category === 'general').map(option => (
                              <label key={option.value} className="flex items-center gap-2 cursor-pointer">
                                <Checkbox
                                  checked={formData.target_groups.includes(option.value)}
                                  onCheckedChange={() => handleTargetGroupToggle(option.value)}
                                />
                                <span className="text-sm">{option.label}</span>
                              </label>
                            ))}
                          </div>
                          
                          <div>
                            <p className="text-xs text-slate-500 mb-1">Squadrons</p>
                            <div className="flex flex-wrap gap-3">
                              {targetGroupOptions.filter(o => o.category === 'squadron').map(option => (
                                <label key={option.value} className="flex items-center gap-2 cursor-pointer">
                                  <Checkbox
                                    checked={formData.target_groups.includes(option.value)}
                                    onCheckedChange={() => handleTargetGroupToggle(option.value)}
                                    disabled={formData.target_groups.includes('all')}
                                  />
                                  <span className="text-sm">{option.label}</span>
                                </label>
                              ))}
                            </div>
                          </div>
                          
                          <div>
                            <p className="text-xs text-slate-500 mb-1">Flights</p>
                            <div className="flex flex-wrap gap-3">
                              {targetGroupOptions.filter(o => o.category === 'flight').map(option => (
                                <label key={option.value} className="flex items-center gap-2 cursor-pointer">
                                  <Checkbox
                                    checked={formData.target_groups.includes(option.value)}
                                    onCheckedChange={() => handleTargetGroupToggle(option.value)}
                                    disabled={formData.target_groups.includes('all')}
                                  />
                                  <span className="text-sm">{option.label}</span>
                                </label>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>
                      
                      <div>
                        <Label className="text-xs uppercase tracking-wide text-slate-600">Description</Label>
                        <Textarea
                          value={formData.description}
                          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                          className="mt-1 rounded-sm"
                          rows={2}
                        />
                      </div>
                      <div className="flex justify-end gap-2 pt-4">
                        <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)} className="rounded-sm">
                          Cancel
                        </Button>
                        <Button type="submit" className="bg-[#00205B] hover:bg-[#001540] rounded-sm">
                          {editingEvent ? 'Update' : 'Add'} Event
                        </Button>
                      </div>
                    </form>
                  </DialogContent>
                </Dialog>
              </>
            )}

            {/* Submit Change Request - visible to everyone */}
            <Button
              variant="outline"
              className="rounded-sm"
              onClick={() => setChangeRequestOpen(true)}
              data-testid="submit-change-request-btn"
            >
              <MessageSquarePlus className="w-4 h-4 mr-2" />
              Request Change
            </Button>

            {/* Review Change Requests - visible to editors */}
            {canEdit() && (
              <Button
                variant="outline"
                className="rounded-sm relative"
                onClick={() => { setChangeReviewOpen(true); loadChangeRequests(); }}
                data-testid="review-changes-btn"
              >
                <FileEdit className="w-4 h-4 mr-2" />
                Requests
                {pendingCount > 0 && (
                  <span className="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] flex items-center justify-center text-[10px] font-bold rounded-full bg-red-500 text-white">
                    {pendingCount}
                  </span>
                )}
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Draft Warning for non-editors */}
      {!canEdit() && !isPublished && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0" />
          <p className="text-amber-800 text-xs">
            The schedule is currently being updated.
          </p>
        </div>
      )}

      {/* Desktop Date Selector Tabs (hidden on mobile) */}
      {!isMobile && (
        <div className="bg-white border border-slate-200 rounded-sm mb-4 overflow-x-auto">
          <div className="flex min-w-max">
            {encampmentDates.map((date, idx) => (
              <button
                key={idx}
                onClick={() => setSelectedDate(date)}
                className={`flex-1 min-w-[100px] px-4 py-3 text-center border-r border-slate-200 last:border-r-0 transition-colors ${
                  isSameDay(date, selectedDate)
                    ? 'bg-[#00205B] text-white'
                    : 'bg-white text-slate-700 hover:bg-slate-50'
                }`}
                data-testid={`date-tab-${format(date, 'yyyy-MM-dd')}`}
              >
                <div className="text-xs uppercase tracking-wide opacity-75">{format(date, 'EEE')}</div>
                <div className="text-lg font-bold">{format(date, 'd')}</div>
                <div className="text-[10px] uppercase tracking-wide">{getDayLabel(date)}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Event Type Legend */}
      <div className={`bg-white border border-slate-200 rounded-lg p-2 mb-4 ${isMobile ? 'overflow-x-auto' : ''}`}>
        <div className={`flex gap-2 ${isMobile ? 'flex-wrap' : 'flex-wrap gap-3'}`}>
          {eventTypes.map(type => (
            <div key={type.value} className="flex items-center gap-1">
              <span className={`w-2 h-2 rounded-sm ${type.color}`}></span>
              <span className={`text-slate-600 ${isMobile ? 'text-[10px]' : 'text-xs'}`}>{type.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Mobile Compact List View with Touch Swipe */}
      {isMobile && (
        <div 
          ref={scheduleContainerRef}
          className="bg-white border border-slate-200 rounded-lg overflow-hidden"
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
        >
          <div className="divide-y divide-slate-100">
            {compactEventsForDate.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-sm">
                No events scheduled
                {canEdit() && (
                  <div className="mt-2">
                    <Button onClick={() => {
                      setFormData({ ...formData, date: format(selectedDate, 'yyyy-MM-dd') });
                      setIsModalOpen(true);
                    }} variant="outline" size="sm" className="text-xs">
                      <Plus className="w-3 h-3 mr-1" />
                      Add Event
                    </Button>
                  </div>
                )}
              </div>
            ) : (
              compactEventsForDate.map(event => (
                <div 
                  key={event.id} 
                  className={`p-3 border-l-4 ${getEventTypeMobileColor(event.event_type)} active:bg-slate-50`}
                  data-testid={`mobile-event-${event.id}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-slate-500 flex-shrink-0">
                          {event.start_time.substring(0, 5)}
                        </span>
                        <span className="font-semibold text-sm text-slate-900 truncate">
                          {event.title}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[10px] text-slate-400 font-mono">
                          → {event.end_time.substring(0, 5)}
                        </span>
                        {event.location && (
                          <span className="text-[10px] text-slate-500 flex items-center gap-0.5">
                            <MapPin className="w-2.5 h-2.5" />
                            {event.location}
                          </span>
                        )}
                        {event.uniform && event.uniform !== 'default' && (
                          <span className="text-[10px] text-indigo-600 flex items-center gap-0.5 font-medium">
                            <Shirt className="w-2.5 h-2.5" />
                            {event.uniform}
                          </span>
                        )}
                      </div>
                      {getTargetGroupsLabel(event.target_groups) && (
                        <span className="inline-block mt-1 bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded text-[10px]">
                          {getTargetGroupsLabel(event.target_groups)}
                        </span>
                      )}
                    </div>
                    {canEdit() && (
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <button 
                          onClick={() => handleEdit(event)} 
                          className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button 
                          onClick={() => handleDelete(event.id)} 
                          className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Desktop Day View */}
      {!isMobile && viewMode === 'day' && (
        <div className="bg-white border border-slate-200 rounded-sm overflow-hidden">
          <div className="bg-[#00205B] text-white p-3 text-center">
            <h2 className="font-bold uppercase tracking-wide">
              {format(selectedDate, 'EEEE, MMMM d, yyyy')} - {getDayLabel(selectedDate)}
            </h2>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-100 border-b border-slate-200">
                  <th className="w-20 px-3 py-2 text-left text-xs uppercase tracking-wide text-slate-600">Time</th>
                  <th className="px-3 py-2 text-left text-xs uppercase tracking-wide text-slate-600">Activities</th>
                </tr>
              </thead>
              <tbody>
                {timeSlots.map((slot) => {
                  const slotEvents = eventsByTimeSlot[slot] || [];
                  const isHourMark = slot.endsWith(':00');
                  
                  return (
                    <tr 
                      key={slot} 
                      className={`border-b border-slate-100 ${isHourMark ? 'bg-slate-50/50' : ''} ${canEdit() ? 'hover:bg-blue-50/30 cursor-pointer' : ''}`}
                      onClick={() => slotEvents.length === 0 && handleTimeSlotClick(slot)}
                    >
                      <td className={`px-3 py-1 font-mono text-sm ${isHourMark ? 'font-bold text-[#00205B]' : 'text-slate-400'}`}>
                        {slot}
                      </td>
                      <td className="px-3 py-1">
                        <div className="flex flex-wrap gap-2">
                          {slotEvents.map(event => (
                            <div
                              key={event.id}
                              className={`${getEventTypeColor(event.event_type)} text-white px-2 py-1 rounded text-xs flex items-center gap-2`}
                              onClick={(e) => e.stopPropagation()}
                              data-testid={`event-${event.id}`}
                            >
                              <span className="font-medium">{event.title}</span>
                              {event.location && <span className="opacity-75">@ {event.location}</span>}
                              {event.uniform && event.uniform !== 'default' && (
                                <span className="bg-white/30 px-1 rounded text-[10px] flex items-center gap-0.5">
                                  <Shirt className="w-2.5 h-2.5" />
                                  {event.uniform}
                                </span>
                              )}
                              {getTargetGroupsLabel(event.target_groups) && (
                                <span className="bg-white/20 px-1 rounded text-[10px]">
                                  {getTargetGroupsLabel(event.target_groups)}
                                </span>
                              )}
                              {canEdit() && (
                                <div className="flex gap-1 ml-1">
                                  <button onClick={() => handleEdit(event)} className="hover:bg-white/20 p-0.5 rounded">
                                    <Edit2 className="w-3 h-3" />
                                  </button>
                                  <button onClick={() => handleDelete(event.id)} className="hover:bg-white/20 p-0.5 rounded">
                                    <Trash2 className="w-3 h-3" />
                                  </button>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Desktop List View */}
      {!isMobile && viewMode === 'list' && (
        <div className="bg-white border border-slate-200 rounded-sm">
          <div className="bg-[#00205B] text-white p-3 text-center">
            <h2 className="font-bold uppercase tracking-wide">
              {format(selectedDate, 'EEEE, MMMM d, yyyy')} - {getDayLabel(selectedDate)}
            </h2>
          </div>
          
          <div className="divide-y divide-slate-100">
            {eventsForDate.length === 0 ? (
              <div className="p-8 text-center text-slate-400">
                No events scheduled for this day.
                {canEdit() && (
                  <div className="mt-2">
                    <Button onClick={() => {
                      setFormData({ ...formData, date: format(selectedDate, 'yyyy-MM-dd') });
                      setIsModalOpen(true);
                    }} variant="outline" size="sm">
                      <Plus className="w-4 h-4 mr-1" />
                      Add First Event
                    </Button>
                  </div>
                )}
              </div>
            ) : (
              eventsForDate.map(event => (
                <div key={event.id} className="p-4 flex items-center justify-between hover:bg-slate-50" data-testid={`list-event-${event.id}`}>
                  <div className="flex items-center gap-4">
                    <div className={`w-1 h-12 rounded-full ${getEventTypeColor(event.event_type)}`}></div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-semibold text-slate-900">{event.title}</p>
                        {getTargetGroupsLabel(event.target_groups) && (
                          <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded text-xs">
                            {getTargetGroupsLabel(event.target_groups)}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 mt-1 text-sm text-slate-500">
                        <span className="flex items-center gap-1 font-mono">
                          <Clock className="w-4 h-4" />
                          {event.start_time} - {event.end_time}
                        </span>
                        {event.location && (
                          <span className="flex items-center gap-1">
                            <MapPin className="w-4 h-4" />
                            {event.location}
                          </span>
                        )}
                        {event.uniform && event.uniform !== 'default' && (
                          <span className="flex items-center gap-1 text-indigo-600 font-medium">
                            <Shirt className="w-4 h-4" />
                            {event.uniform}
                          </span>
                        )}
                      </div>
                      {event.description && (
                        <p className="text-sm text-slate-500 mt-1">{event.description}</p>
                      )}
                    </div>
                  </div>
                  {canEdit() && (
                    <div className="flex items-center gap-2">
                      <Button variant="ghost" size="sm" onClick={() => handleEdit(event)} className="h-8 w-8 p-0">
                        <Edit2 className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(event.id)}
                        className="h-8 w-8 p-0 text-[#BF0D3E] hover:text-[#BF0D3E] hover:bg-red-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Daily Summary */}
      <div className={`mt-4 bg-white border border-slate-200 rounded-lg p-3 ${isMobile ? '' : 'p-4'}`}>
        <h3 className={`font-bold text-[#00205B] uppercase tracking-tight mb-2 ${isMobile ? 'text-xs' : 'text-sm'}`} style={{ fontFamily: 'Chivo, sans-serif' }}>
          Day Summary
        </h3>
        <div className={`grid gap-2 ${isMobile ? 'grid-cols-4' : 'grid-cols-2 sm:grid-cols-4 gap-4'}`}>
          <div className={`text-center bg-slate-50 rounded ${isMobile ? 'p-2' : 'p-3'}`}>
            <div className={`font-bold text-[#00205B] ${isMobile ? 'text-lg' : 'text-2xl'}`}>{eventsForDate.length}</div>
            <div className={`uppercase tracking-wide text-slate-500 ${isMobile ? 'text-[8px]' : 'text-xs'}`}>Events</div>
          </div>
          <div className={`text-center bg-blue-50 rounded ${isMobile ? 'p-2' : 'p-3'}`}>
            <div className={`font-bold text-blue-600 ${isMobile ? 'text-lg' : 'text-2xl'}`}>
              {eventsForDate.filter(e => e.event_type === 'training').length}
            </div>
            <div className={`uppercase tracking-wide text-slate-500 ${isMobile ? 'text-[8px]' : 'text-xs'}`}>Training</div>
          </div>
          <div className={`text-center bg-red-50 rounded ${isMobile ? 'p-2' : 'p-3'}`}>
            <div className={`font-bold text-red-600 ${isMobile ? 'text-lg' : 'text-2xl'}`}>
              {eventsForDate.filter(e => e.event_type === 'pt').length}
            </div>
            <div className={`uppercase tracking-wide text-slate-500 ${isMobile ? 'text-[8px]' : 'text-xs'}`}>PT</div>
          </div>
          <div className={`text-center bg-amber-50 rounded ${isMobile ? 'p-2' : 'p-3'}`}>
            <div className={`font-bold text-amber-600 ${isMobile ? 'text-lg' : 'text-2xl'}`}>
              {eventsForDate.filter(e => e.event_type === 'meal').length}
            </div>
            <div className={`uppercase tracking-wide text-slate-500 ${isMobile ? 'text-[8px]' : 'text-xs'}`}>Meals</div>
          </div>
        </div>
      </div>

      {/* Mobile Navigation Hint */}
      {isMobile && (
        <div className="mt-4 text-center text-[10px] text-slate-400">
          Day {currentDayIndex + 1} of {encampmentDates.length}
        </div>
      )}

      {/* ===== SUBMIT CHANGE REQUEST MODAL ===== */}
      <Dialog open={changeRequestOpen} onOpenChange={setChangeRequestOpen}>
        <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-[#00205B] uppercase font-bold text-sm">Request Schedule Change</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 mt-2">
            <div>
              <Label className="text-xs">Change Type</Label>
              <Select value={changeForm.change_type} onValueChange={(v) => setChangeForm(p => ({ ...p, change_type: v }))}>
                <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="modify">Modify Existing Event</SelectItem>
                  <SelectItem value="add">Add New Event</SelectItem>
                  <SelectItem value="remove">Remove Event</SelectItem>
                  <SelectItem value="reschedule">Reschedule Event</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Event / Activity Name *</Label>
              <Input value={changeForm.event_title} onChange={(e) => setChangeForm(p => ({ ...p, event_title: e.target.value }))}
                className="h-8 text-sm rounded-sm" placeholder="e.g., Morning PT" data-testid="change-event-title" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Date</Label>
                <Input type="date" value={changeForm.event_date} onChange={(e) => setChangeForm(p => ({ ...p, event_date: e.target.value }))}
                  className="h-8 text-sm rounded-sm" />
              </div>
              <div>
                <Label className="text-xs">Current Time</Label>
                <Input value={changeForm.current_time} onChange={(e) => setChangeForm(p => ({ ...p, current_time: e.target.value }))}
                  className="h-8 text-sm rounded-sm" placeholder="e.g., 0600-0700" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Requested Time</Label>
                <Input value={changeForm.requested_time} onChange={(e) => setChangeForm(p => ({ ...p, requested_time: e.target.value }))}
                  className="h-8 text-sm rounded-sm" placeholder="e.g., 0700-0800" />
              </div>
              <div>
                <Label className="text-xs">Requested Location</Label>
                <Input value={changeForm.requested_location} onChange={(e) => setChangeForm(p => ({ ...p, requested_location: e.target.value }))}
                  className="h-8 text-sm rounded-sm" placeholder="e.g., Field House" />
              </div>
            </div>
            <div>
              <Label className="text-xs">Reason for Change *</Label>
              <Textarea value={changeForm.reason} onChange={(e) => setChangeForm(p => ({ ...p, reason: e.target.value }))}
                rows={2} className="text-sm rounded-sm" placeholder="Why is this change needed?" data-testid="change-reason" />
            </div>
            <div>
              <Label className="text-xs">Additional Details</Label>
              <Textarea value={changeForm.details} onChange={(e) => setChangeForm(p => ({ ...p, details: e.target.value }))}
                rows={2} className="text-sm rounded-sm" placeholder="Any other info..." />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={() => setChangeRequestOpen(false)} className="rounded-sm">Cancel</Button>
              <Button onClick={handleSubmitChangeRequest} className="bg-[#00205B] rounded-sm" data-testid="submit-change-btn">Submit Request</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* ===== REVIEW CHANGE REQUESTS MODAL (Editors) ===== */}
      <Dialog open={changeReviewOpen} onOpenChange={setChangeReviewOpen}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-[#00205B] uppercase font-bold text-sm">Schedule Change Requests</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 mt-2">
            {changeRequests.length === 0 ? (
              <p className="text-center text-sm text-slate-400 py-6">No change requests</p>
            ) : (
              changeRequests.map(req => (
                <div key={req.id} className={`border rounded-sm p-3 ${
                  req.status === 'pending' ? 'border-amber-300 bg-amber-50' :
                  req.status === 'approved' ? 'border-emerald-200 bg-emerald-50' :
                  'border-slate-200 bg-slate-50'
                }`} data-testid={`change-request-${req.id}`}>
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] px-2 py-0.5 rounded uppercase font-medium ${
                          req.change_type === 'add' ? 'bg-blue-100 text-blue-700' :
                          req.change_type === 'remove' ? 'bg-red-100 text-red-700' :
                          req.change_type === 'reschedule' ? 'bg-purple-100 text-purple-700' :
                          'bg-slate-100 text-slate-600'
                        }`}>{req.change_type}</span>
                        <span className={`text-[10px] px-2 py-0.5 rounded uppercase font-medium ${
                          req.status === 'pending' ? 'bg-amber-100 text-amber-700' :
                          req.status === 'approved' ? 'bg-emerald-100 text-emerald-700' :
                          'bg-red-100 text-red-700'
                        }`}>{req.status}</span>
                      </div>
                      <p className="font-medium text-sm mt-1">{req.event_title}</p>
                      <p className="text-xs text-slate-500">
                        {req.submitted_by_name} ({req.submitted_by_role}) &middot; {new Date(req.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  {req.event_date && <p className="text-xs text-slate-600">Date: {req.event_date}</p>}
                  {req.current_time && <p className="text-xs text-slate-600">Current: {req.current_time}</p>}
                  {req.requested_time && <p className="text-xs text-slate-600">Requested time: {req.requested_time}</p>}
                  {req.requested_location && <p className="text-xs text-slate-600">Requested location: {req.requested_location}</p>}
                  <p className="text-xs text-slate-700 mt-1"><span className="font-medium">Reason:</span> {req.reason}</p>
                  {req.details && <p className="text-xs text-slate-500 mt-0.5">{req.details}</p>}
                  {req.review_notes && <p className="text-xs text-slate-600 mt-1 italic">Review note: {req.review_notes}</p>}
                  {req.reviewed_by_name && <p className="text-xs text-slate-400">Reviewed by {req.reviewed_by_name} &middot; {new Date(req.reviewed_at).toLocaleString()}</p>}
                  {canEdit() && req.status === 'pending' && (
                    <div className="flex gap-2 mt-2">
                      <Button size="sm" className="h-7 text-xs bg-emerald-600 rounded-sm" onClick={() => handleReviewChange(req.id, 'approved')} data-testid={`approve-${req.id}`}>
                        <CheckCircle className="w-3 h-3 mr-1" /> Approve
                      </Button>
                      <Button size="sm" variant="outline" className="h-7 text-xs text-red-600 border-red-200 rounded-sm" onClick={() => {
                        const notes = prompt('Denial reason (optional):');
                        handleReviewChange(req.id, 'denied', notes || '');
                      }} data-testid={`deny-${req.id}`}>
                        <XCircle className="w-3 h-3 mr-1" /> Deny
                      </Button>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SchedulePage;
