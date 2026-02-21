import React, { useState, useEffect } from 'react';
import { getSchedule, createScheduleEvent, updateScheduleEvent, deleteScheduleEvent } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { format, parseISO, startOfWeek, addDays, isSameDay } from 'date-fns';
import { 
  Plus, 
  Calendar as CalendarIcon, 
  Clock, 
  MapPin, 
  Edit2, 
  Trash2,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

const SchedulePage = () => {
  const { canEdit } = useAuth();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentWeekStart, setCurrentWeekStart] = useState(startOfWeek(new Date(), { weekStartsOn: 0 }));
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingEvent, setEditingEvent] = useState(null);
  const [selectedDate, setSelectedDate] = useState(null);

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    date: '',
    start_time: '',
    end_time: '',
    location: '',
    event_type: 'general'
  });

  const eventTypes = [
    { value: 'general', label: 'General', color: 'bg-slate-100 border-slate-300 text-slate-700' },
    { value: 'training', label: 'Training', color: 'bg-blue-100 border-blue-300 text-blue-700' },
    { value: 'ceremony', label: 'Ceremony', color: 'bg-purple-100 border-purple-300 text-purple-700' },
    { value: 'meal', label: 'Meal', color: 'bg-amber-100 border-amber-300 text-amber-700' },
    { value: 'recreation', label: 'Recreation', color: 'bg-emerald-100 border-emerald-300 text-emerald-700' }
  ];

  useEffect(() => {
    loadEvents();
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
      event_type: event.event_type
    });
    setIsModalOpen(true);
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this event?')) {
      try {
        await deleteScheduleEvent(id);
        toast.success('Event deleted');
        loadEvents();
      } catch (error) {
        toast.error('Failed to delete event');
      }
    }
  };

  const handleDateClick = (date) => {
    if (!canEdit()) return;
    setSelectedDate(date);
    setFormData({ ...formData, date: format(date, 'yyyy-MM-dd') });
    setIsModalOpen(true);
  };

  const resetForm = () => {
    setEditingEvent(null);
    setSelectedDate(null);
    setFormData({
      title: '',
      description: '',
      date: '',
      start_time: '',
      end_time: '',
      location: '',
      event_type: 'general'
    });
  };

  const weekDays = Array.from({ length: 7 }, (_, i) => addDays(currentWeekStart, i));

  const getEventsForDay = (date) => {
    return events.filter(e => isSameDay(parseISO(e.date), date))
      .sort((a, b) => a.start_time.localeCompare(b.start_time));
  };

  const getEventTypeColor = (type) => {
    return eventTypes.find(t => t.value === type)?.color || eventTypes[0].color;
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
            Encampment Schedule
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            {events.length} events scheduled
          </p>
        </div>

        <div className="flex items-center gap-4">
          {/* Week Navigation */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentWeekStart(addDays(currentWeekStart, -7))}
              className="rounded-sm"
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <span className="text-sm font-medium text-slate-600 min-w-[180px] text-center">
              {format(currentWeekStart, 'MMM d')} - {format(addDays(currentWeekStart, 6), 'MMM d, yyyy')}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentWeekStart(addDays(currentWeekStart, 7))}
              className="rounded-sm"
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>

          {canEdit() && (
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
                  <div>
                    <Label className="text-xs uppercase tracking-wide text-slate-600">Event Type</Label>
                    <Select
                      value={formData.event_type}
                      onValueChange={(value) => setFormData({ ...formData, event_type: value })}
                    >
                      <SelectTrigger className="mt-1 rounded-sm" data-testid="event-type-select">
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
                      data-testid="event-date-input"
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
                        data-testid="event-start-time-input"
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
                        data-testid="event-end-time-input"
                      />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs uppercase tracking-wide text-slate-600">Location</Label>
                    <Input
                      value={formData.location}
                      onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                      className="mt-1 rounded-sm"
                      placeholder="Parade Ground"
                    />
                  </div>
                  <div>
                    <Label className="text-xs uppercase tracking-wide text-slate-600">Description</Label>
                    <Textarea
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      className="mt-1 rounded-sm"
                      rows={3}
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-4">
                    <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)} className="rounded-sm">
                      Cancel
                    </Button>
                    <Button type="submit" className="bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="save-event-btn">
                      {editingEvent ? 'Update' : 'Add'} Event
                    </Button>
                  </div>
                </form>
              </DialogContent>
            </Dialog>
          )}
        </div>
      </div>

      {/* Event Type Legend */}
      <div className="bg-white border border-slate-200 rounded-sm p-4 mb-6">
        <div className="flex flex-wrap gap-4">
          {eventTypes.map(type => (
            <div key={type.value} className="flex items-center gap-2">
              <span className={`w-3 h-3 rounded-sm border ${type.color}`}></span>
              <span className="text-xs uppercase tracking-wide text-slate-600">{type.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Calendar Grid */}
      <div className="bg-white border border-slate-200 rounded-sm overflow-hidden">
        {/* Day Headers */}
        <div className="grid grid-cols-7 border-b border-slate-200">
          {weekDays.map((day, i) => (
            <div 
              key={i}
              className={`p-3 text-center border-r border-slate-200 last:border-r-0 ${
                isSameDay(day, new Date()) ? 'bg-[#00205B]/5' : ''
              }`}
            >
              <p className="text-xs uppercase tracking-wide text-slate-500">{format(day, 'EEE')}</p>
              <p className={`text-lg font-bold ${isSameDay(day, new Date()) ? 'text-[#00205B]' : 'text-slate-700'}`}>
                {format(day, 'd')}
              </p>
            </div>
          ))}
        </div>

        {/* Events Grid */}
        <div className="grid grid-cols-7 min-h-[400px]">
          {weekDays.map((day, i) => {
            const dayEvents = getEventsForDay(day);
            return (
              <div 
                key={i}
                className={`border-r border-slate-200 last:border-r-0 p-2 ${
                  canEdit() ? 'cursor-pointer hover:bg-slate-50' : ''
                } ${isSameDay(day, new Date()) ? 'bg-[#00205B]/5' : ''}`}
                onClick={() => handleDateClick(day)}
                data-testid={`calendar-day-${format(day, 'yyyy-MM-dd')}`}
              >
                <div className="space-y-1">
                  {dayEvents.map(event => (
                    <div
                      key={event.id}
                      className={`p-2 rounded-sm border text-xs ${getEventTypeColor(event.event_type)}`}
                      onClick={(e) => e.stopPropagation()}
                      data-testid={`event-${event.id}`}
                    >
                      <div className="flex items-start justify-between gap-1">
                        <div className="flex-1 min-w-0">
                          <p className="font-semibold truncate">{event.title}</p>
                          <div className="flex items-center gap-1 mt-1 text-[10px] opacity-75">
                            <Clock className="w-3 h-3" />
                            <span>{event.start_time} - {event.end_time}</span>
                          </div>
                          {event.location && (
                            <div className="flex items-center gap-1 mt-0.5 text-[10px] opacity-75">
                              <MapPin className="w-3 h-3" />
                              <span className="truncate">{event.location}</span>
                            </div>
                          )}
                        </div>
                        {canEdit() && (
                          <div className="flex flex-col gap-1">
                            <button
                              onClick={() => handleEdit(event)}
                              className="p-1 hover:bg-black/10 rounded"
                              data-testid={`edit-event-${event.id}`}
                            >
                              <Edit2 className="w-3 h-3" />
                            </button>
                            <button
                              onClick={() => handleDelete(event.id)}
                              className="p-1 hover:bg-black/10 rounded text-red-600"
                              data-testid={`delete-event-${event.id}`}
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Upcoming Events List */}
      <div className="mt-6 bg-white border border-slate-200 rounded-sm">
        <div className="border-b border-slate-100 p-4">
          <h2 className="font-bold uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
            All Events
          </h2>
        </div>
        <div className="divide-y divide-slate-100">
          {events.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              No events scheduled yet.
            </div>
          ) : (
            events
              .sort((a, b) => `${a.date} ${a.start_time}`.localeCompare(`${b.date} ${b.start_time}`))
              .map(event => (
                <div key={event.id} className="p-4 flex items-center justify-between hover:bg-slate-50">
                  <div className="flex items-center gap-4">
                    <div className={`w-1 h-12 rounded-full ${getEventTypeColor(event.event_type).split(' ')[0]}`}></div>
                    <div>
                      <p className="font-semibold text-slate-900">{event.title}</p>
                      <div className="flex items-center gap-3 mt-1 text-sm text-slate-500">
                        <span className="flex items-center gap-1">
                          <CalendarIcon className="w-4 h-4" />
                          {format(parseISO(event.date), 'MMM d, yyyy')}
                        </span>
                        <span className="flex items-center gap-1">
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
                    </div>
                  </div>
                  {canEdit() && (
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEdit(event)}
                        className="h-8 w-8 p-0"
                      >
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
    </div>
  );
};

export default SchedulePage;
