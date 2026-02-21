import React, { useState, useEffect, useMemo, useRef } from 'react';
import { 
  getSchedule, 
  getScheduleSettings,
  createScheduleEvent, 
  updateScheduleEvent, 
  deleteScheduleEvent,
  importSchedule,
  publishSchedule,
  unpublishSchedule
} from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
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
  AlertCircle
} from 'lucide-react';

const SchedulePage = () => {
  const { canEdit } = useAuth();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(new Date('2026-07-17'));
  const [viewMode, setViewMode] = useState('day');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingEvent, setEditingEvent] = useState(null);
  const [isPublished, setIsPublished] = useState(false);
  const [scheduleSettings, setScheduleSettings] = useState(null);
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef(null);

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    date: '',
    start_time: '',
    end_time: '',
    location: '',
    event_type: 'training',
    squadron: ''
  });

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
    { value: 'general', label: 'General', color: 'bg-slate-500' },
    { value: 'training', label: 'Training', color: 'bg-blue-600' },
    { value: 'ceremony', label: 'Ceremony', color: 'bg-purple-600' },
    { value: 'meal', label: 'Meal', color: 'bg-amber-500' },
    { value: 'recreation', label: 'Recreation', color: 'bg-emerald-500' },
    { value: 'pt', label: 'Physical Training', color: 'bg-red-600' },
    { value: 'admin', label: 'Admin/Logistics', color: 'bg-slate-600' },
    { value: 'leadership', label: 'Leadership', color: 'bg-indigo-600' },
    { value: 'academics', label: 'Academics', color: 'bg-teal-600' }
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

  useEffect(() => {
    loadEvents();
    loadSettings();
  }, []);

  const loadEvents = async () => {
    try {
      const data = await getSchedule();
      setEvents(data);
    } catch (error) {
      toast.error('Failed to load schedule');
    } finally {
      setLoading(false);
    }
  };

  const loadSettings = async () => {
    try {
      const settings = await getScheduleSettings();
      setScheduleSettings(settings);
      setIsPublished(settings.is_published);
    } catch (error) {
      console.error('Failed to load schedule settings');
    }
  };

  // Get events for selected date
  const eventsForDate = useMemo(() => {
    return events
      .filter(e => isSameDay(parseISO(e.date), selectedDate))
      .sort((a, b) => a.start_time.localeCompare(b.start_time));
  }, [events, selectedDate]);

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
      squadron: event.squadron || ''
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
      })
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
      toast.success('Schedule published! All users can now view it.');
      loadSettings();
    } catch (error) {
      toast.error('Failed to publish schedule');
    }
  };

  const handleUnpublish = async () => {
    try {
      await unpublishSchedule();
      setIsPublished(false);
      toast.success('Schedule unpublished. Only editors can view it now.');
      loadSettings();
    } catch (error) {
      toast.error('Failed to unpublish schedule');
    }
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
      squadron: ''
    });
  };

  const getEventTypeColor = (type) => {
    return eventTypes.find(t => t.value === type)?.color || 'bg-slate-500';
  };

  const getDayLabel = (date) => {
    const dayIndex = encampmentDates.findIndex(d => isSameDay(d, date));
    if (dayIndex === 0) return 'Staff Arrival';
    if (dayIndex === 1) return 'In-Processing';
    if (dayIndex === 7) return 'Graduation';
    return `Day ${dayIndex - 1}`;
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-400">Loading schedule...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl lg:text-3xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Training Schedule
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            TNWG Summer Encampment • July 17-24, 2026
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Draft/Published Badge */}
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

          {/* View Toggle */}
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
              {/* Import Button */}
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

              {/* Publish/Unpublish Button */}
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

              {/* Add Event Button */}
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
                <DialogContent className="max-w-md">
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
                        <Label className="text-xs uppercase tracking-wide text-slate-600">Squadron</Label>
                        <Select
                          value={formData.squadron || 'all'}
                          onValueChange={(value) => setFormData({ ...formData, squadron: value === 'all' ? '' : value })}
                        >
                          <SelectTrigger className="mt-1 rounded-sm">
                            <SelectValue placeholder="All" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="all">All Squadrons</SelectItem>
                            <SelectItem value="sq1">Squadron 1</SelectItem>
                            <SelectItem value="sq2">Squadron 2</SelectItem>
                            <SelectItem value="sq3">Squadron 3</SelectItem>
                            <SelectItem value="staff">Staff/Cadre</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
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
        </div>
      </div>

      {/* Draft Warning for non-editors */}
      {!canEdit() && !isPublished && (
        <div className="bg-amber-50 border border-amber-200 rounded-sm p-4 mb-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600" />
          <p className="text-amber-800 text-sm">
            The schedule is currently being updated. Check back later for the published version.
          </p>
        </div>
      )}

      {/* Date Selector Tabs */}
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

      {/* Event Type Legend */}
      <div className="bg-white border border-slate-200 rounded-sm p-3 mb-4">
        <div className="flex flex-wrap gap-3">
          {eventTypes.map(type => (
            <div key={type.value} className="flex items-center gap-2">
              <span className={`w-3 h-3 rounded-sm ${type.color}`}></span>
              <span className="text-xs text-slate-600">{type.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Day View */}
      {viewMode === 'day' && (
        <div className="bg-white border border-slate-200 rounded-sm overflow-hidden">
          <div className="bg-[#00205B] text-white p-3 text-center">
            <h2 className="font-bold uppercase tracking-wide">
              {format(selectedDate, 'EEEE, MMMM d, yyyy')} - {getDayLabel(selectedDate)}
            </h2>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px]">
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
                              {event.squadron && (
                                <span className="bg-white/20 px-1 rounded text-[10px]">{event.squadron.toUpperCase()}</span>
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

      {/* List View */}
      {viewMode === 'list' && (
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
                        {event.squadron && (
                          <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded text-xs uppercase">
                            {event.squadron}
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
      <div className="mt-4 bg-white border border-slate-200 rounded-sm p-4">
        <h3 className="font-bold text-[#00205B] uppercase tracking-tight mb-3" style={{ fontFamily: 'Chivo, sans-serif' }}>
          Day Summary
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-slate-50 rounded-sm">
            <div className="text-2xl font-bold text-[#00205B]">{eventsForDate.length}</div>
            <div className="text-xs uppercase tracking-wide text-slate-500">Total Events</div>
          </div>
          <div className="text-center p-3 bg-blue-50 rounded-sm">
            <div className="text-2xl font-bold text-blue-600">
              {eventsForDate.filter(e => e.event_type === 'training').length}
            </div>
            <div className="text-xs uppercase tracking-wide text-slate-500">Training</div>
          </div>
          <div className="text-center p-3 bg-red-50 rounded-sm">
            <div className="text-2xl font-bold text-red-600">
              {eventsForDate.filter(e => e.event_type === 'pt').length}
            </div>
            <div className="text-xs uppercase tracking-wide text-slate-500">PT Sessions</div>
          </div>
          <div className="text-center p-3 bg-amber-50 rounded-sm">
            <div className="text-2xl font-bold text-amber-600">
              {eventsForDate.filter(e => e.event_type === 'meal').length}
            </div>
            <div className="text-xs uppercase tracking-wide text-slate-500">Meals</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SchedulePage;
