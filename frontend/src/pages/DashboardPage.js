import React, { useState, useEffect } from 'react';
import { getDashboardStats, getDailySettings, updateUniformOfDay, updateWeatherFlag, getSchedule } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { 
  Users, 
  DollarSign, 
  Calendar, 
  TrendingUp, 
  TrendingDown,
  UserCheck,
  UserX,
  Radio,
  Shirt,
  Thermometer,
  Flag,
  Edit,
  AlertTriangle,
  Droplets,
  Clock,
  Info,
  ChevronRight,
  MapPin
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const ROLE_LABELS = {
  commander: 'Commander',
  finance: 'Finance',
  plans_programs: 'Plans & Programs',
  exec_cadre: 'Executive Cadre',
  staff: 'Staff',
  cadre: 'Cadre'
};

const DashboardPage = () => {
  const { user, activeUsers } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dailySettings, setDailySettings] = useState(null);
  const [todayEvents, setTodayEvents] = useState([]);
  
  // Admin edit dialogs
  const [uniformDialogOpen, setUniformDialogOpen] = useState(false);
  const [weatherDialogOpen, setWeatherDialogOpen] = useState(false);
  const [uniformForm, setUniformForm] = useState({ uniform_code: '', description: '', special_instructions: '' });
  const [weatherForm, setWeatherForm] = useState({ flag_color: 'green', heat_index: '', notes: '' });
  const [saving, setSaving] = useState(false);

  // Check if user can edit daily settings
  const canEditSettings = ['commander', 'plans_programs', 'staff', 'executive_cadre'].includes(user?.role);

  // Event type colors
  const eventTypeColors = {
    general: { bg: 'bg-slate-500', light: 'bg-slate-100', text: 'text-slate-700', border: 'border-l-slate-500' },
    training: { bg: 'bg-blue-600', light: 'bg-blue-50', text: 'text-blue-700', border: 'border-l-blue-600' },
    ceremony: { bg: 'bg-purple-600', light: 'bg-purple-50', text: 'text-purple-700', border: 'border-l-purple-600' },
    meal: { bg: 'bg-amber-500', light: 'bg-amber-50', text: 'text-amber-700', border: 'border-l-amber-500' },
    recreation: { bg: 'bg-emerald-500', light: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-l-emerald-500' },
    pt: { bg: 'bg-red-600', light: 'bg-red-50', text: 'text-red-700', border: 'border-l-red-600' },
    admin: { bg: 'bg-slate-600', light: 'bg-slate-100', text: 'text-slate-700', border: 'border-l-slate-600' },
    leadership: { bg: 'bg-indigo-600', light: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-l-indigo-600' },
    academics: { bg: 'bg-teal-600', light: 'bg-teal-50', text: 'text-teal-700', border: 'border-l-teal-600' }
  };

  useEffect(() => {
    loadStats();
    loadDailySettings();
    loadTodaySchedule();
  }, []);

  const loadStats = async () => {
    try {
      const data = await getDashboardStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadDailySettings = async () => {
    try {
      const data = await getDailySettings();
      setDailySettings(data);
      if (data.uniform) {
        setUniformForm({
          uniform_code: data.uniform.uniform_code || '',
          description: data.uniform.description || '',
          special_instructions: data.uniform.special_instructions || ''
        });
      }
      if (data.weather_flag) {
        setWeatherForm({
          flag_color: data.weather_flag.flag_color || 'green',
          heat_index: data.weather_flag.heat_index || '',
          notes: data.weather_flag.notes || ''
        });
      }
    } catch (error) {
      console.error('Failed to load daily settings:', error);
    }
  };

  const loadTodaySchedule = async () => {
    try {
      const allEvents = await getSchedule();
      // Get today's date (using encampment date range: July 17-24, 2026)
      // For demo purposes, we'll show day 1 events if current date is outside encampment
      const today = new Date();
      const encampmentStart = new Date('2026-07-17');
      const encampmentEnd = new Date('2026-07-24');
      
      let targetDate;
      if (today >= encampmentStart && today <= encampmentEnd) {
        targetDate = today.toISOString().split('T')[0];
      } else {
        // Show first day of encampment for demo
        targetDate = '2026-07-17';
      }
      
      // Filter events for today and sort by start time
      const todaysEvents = allEvents
        .filter(event => {
          const eventDate = event.date?.split('T')[0];
          return eventDate === targetDate && event.is_published !== false;
        })
        .sort((a, b) => {
          const timeA = a.start_time || '00:00';
          const timeB = b.start_time || '00:00';
          return timeA.localeCompare(timeB);
        });
      
      setTodayEvents(todaysEvents);
    } catch (error) {
      console.error('Failed to load today\'s schedule:', error);
    }
  };

  const formatTime = (time) => {
    if (!time) return '';
    const [hours, minutes] = time.split(':');
    const hour = parseInt(hours);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const hour12 = hour % 12 || 12;
    return `${hour12}:${minutes} ${ampm}`;
  };

  const getCurrentEvent = () => {
    if (todayEvents.length === 0) return null;
    const now = new Date();
    const currentTime = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
    
    return todayEvents.find(event => {
      const start = event.start_time || '00:00';
      const end = event.end_time || '23:59';
      return currentTime >= start && currentTime <= end;
    });
  };

  const getUpcomingEvents = () => {
    const now = new Date();
    const currentTime = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
    
    return todayEvents.filter(event => {
      const start = event.start_time || '00:00';
      return start > currentTime;
    }).slice(0, 5);
  };

  const handleSaveUniform = async () => {
    setSaving(true);
    try {
      await updateUniformOfDay(uniformForm);
      toast.success('Uniform of the Day updated');
      setUniformDialogOpen(false);
      loadDailySettings();
    } catch (error) {
      toast.error('Failed to update uniform');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveWeather = async () => {
    setSaving(true);
    try {
      await updateWeatherFlag({
        ...weatherForm,
        heat_index: weatherForm.heat_index ? parseFloat(weatherForm.heat_index) : null
      });
      toast.success('Weather flag updated');
      setWeatherDialogOpen(false);
      loadDailySettings();
    } catch (error) {
      toast.error('Failed to update weather flag');
    } finally {
      setSaving(false);
    }
  };

  // Weather flag colors
  const flagColors = {
    green: { bg: 'bg-green-500', text: 'text-green-700', bgLight: 'bg-green-50', border: 'border-green-200' },
    yellow: { bg: 'bg-yellow-400', text: 'text-yellow-700', bgLight: 'bg-yellow-50', border: 'border-yellow-200' },
    red: { bg: 'bg-red-500', text: 'text-red-700', bgLight: 'bg-red-50', border: 'border-red-200' },
    black: { bg: 'bg-gray-900', text: 'text-gray-900', bgLight: 'bg-gray-100', border: 'border-gray-400' }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const participantTypeData = stats?.participants?.by_type 
    ? Object.entries(stats.participants.by_type).map(([name, value]) => ({
        name: name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        value
      }))
    : [];

  const genderData = stats?.participants?.by_gender
    ? Object.entries(stats.participants.by_gender).map(([name, value]) => ({
        name: name === 'M' ? 'Male' : name === 'F' ? 'Female' : 'Other',
        value
      }))
    : [];

  const COLORS = ['#00205B', '#BF0D3E', '#475569', '#94A3B8'];

  if (loading) {
    return (
      <div className="p-6 lg:p-8 animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-400">Loading dashboard...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 lg:p-8 animate-fade-in">
      {/* Encampment Banner */}
      <div className="mb-6 rounded-lg overflow-hidden shadow-lg">
        <img 
          src="/encampment-banner.png" 
          alt="2026 Tennessee Wing Encampment" 
          className="w-full h-auto object-cover"
        />
      </div>

      {/* Welcome Message */}
      <div className="mb-8">
        <h1 className="text-xl md:text-2xl lg:text-3xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
          Welcome back, {user?.name?.split(' ')[0]}
        </h1>
        <p className="text-slate-500 text-sm mt-1">
          July 17-24, 2026 • VTS Catoosa, GA
        </p>
      </div>

      {/* Daily Info Cards - Uniform & Weather */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        {/* Uniform of the Day */}
        <div className="bg-white border border-slate-200 rounded-sm overflow-hidden" data-testid="uniform-of-day">
          <div className="bg-[#00205B] px-4 py-2 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shirt className="w-4 h-4 text-white" />
              <h2 className="text-white font-bold text-sm uppercase tracking-wide">Uniform of the Day</h2>
            </div>
            {canEditSettings && (
              <Dialog open={uniformDialogOpen} onOpenChange={setUniformDialogOpen}>
                <DialogTrigger asChild>
                  <Button variant="ghost" size="sm" className="text-white hover:bg-white/20 h-7 px-2">
                    <Edit className="w-3 h-3" />
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Update Uniform of the Day</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 pt-4">
                    <div>
                      <Label>Uniform</Label>
                      <Select value={uniformForm.uniform_code} onValueChange={(v) => setUniformForm(prev => ({ ...prev, uniform_code: v }))}>
                        <SelectTrigger><SelectValue placeholder="Select uniform" /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="ABU">ABU (Airman Battle Uniform)</SelectItem>
                          <SelectItem value="Blues">Service Dress Blues</SelectItem>
                          <SelectItem value="PT">PT Gear</SelectItem>
                          <SelectItem value="Flight Suit">Flight Suit</SelectItem>
                          <SelectItem value="Civilian">Civilian Attire</SelectItem>
                          <SelectItem value="Class A">Class A</SelectItem>
                          <SelectItem value="Class B">Class B</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label>Description (optional)</Label>
                      <Input
                        value={uniformForm.description}
                        onChange={(e) => setUniformForm(prev => ({ ...prev, description: e.target.value }))}
                        placeholder="e.g., With boots"
                      />
                    </div>
                    <div>
                      <Label>Special Instructions (optional)</Label>
                      <Input
                        value={uniformForm.special_instructions}
                        onChange={(e) => setUniformForm(prev => ({ ...prev, special_instructions: e.target.value }))}
                        placeholder="e.g., Bring rain gear"
                      />
                    </div>
                    <Button onClick={handleSaveUniform} disabled={saving} className="w-full bg-[#00205B]">
                      {saving ? 'Saving...' : 'Save Uniform'}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            )}
          </div>
          <div className="p-4">
            <div className="text-3xl font-black text-[#00205B] mb-1">
              {dailySettings?.uniform?.uniform_code || 'ABU'}
            </div>
            <p className="text-slate-600 text-sm">
              {dailySettings?.uniform?.description || 'Airman Battle Uniform'}
            </p>
            {dailySettings?.uniform?.special_instructions && (
              <p className="text-amber-600 text-sm mt-2 flex items-center gap-1">
                <Info className="w-3 h-3" />
                {dailySettings.uniform.special_instructions}
              </p>
            )}
            {dailySettings?.uniform?.updated_at && (
              <p className="text-xs text-slate-400 mt-2">
                Updated {new Date(dailySettings.uniform.updated_at).toLocaleString()}
              </p>
            )}
          </div>
        </div>

        {/* Weather Flag */}
        <div className={`bg-white border rounded-sm overflow-hidden ${flagColors[dailySettings?.weather_flag?.flag_color || 'green']?.border}`} data-testid="weather-flag">
          <div className={`${flagColors[dailySettings?.weather_flag?.flag_color || 'green']?.bg} px-4 py-2 flex items-center justify-between`}>
            <div className="flex items-center gap-2">
              <Flag className="w-4 h-4 text-white" />
              <h2 className="text-white font-bold text-sm uppercase tracking-wide">Heat Condition Flag</h2>
            </div>
            {canEditSettings && (
              <Dialog open={weatherDialogOpen} onOpenChange={setWeatherDialogOpen}>
                <DialogTrigger asChild>
                  <Button variant="ghost" size="sm" className="text-white hover:bg-white/20 h-7 px-2">
                    <Edit className="w-3 h-3" />
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-lg">
                  <DialogHeader>
                    <DialogTitle>Update Weather Flag</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 pt-4">
                    <div>
                      <Label>Flag Color</Label>
                      <div className="grid grid-cols-4 gap-2 mt-2">
                        {['green', 'yellow', 'red', 'black'].map((color) => (
                          <button
                            key={color}
                            onClick={() => setWeatherForm(prev => ({ ...prev, flag_color: color }))}
                            className={`p-3 rounded-sm border-2 transition-all ${
                              weatherForm.flag_color === color 
                                ? 'ring-2 ring-[#00205B] ring-offset-2' 
                                : 'border-transparent'
                            }`}
                          >
                            <div className={`h-8 rounded ${flagColors[color].bg}`} />
                            <p className="text-xs mt-1 capitalize font-medium">{color}</p>
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <Label>Heat Index (°F)</Label>
                      <Input
                        type="number"
                        value={weatherForm.heat_index}
                        onChange={(e) => setWeatherForm(prev => ({ ...prev, heat_index: e.target.value }))}
                        placeholder="e.g., 95"
                      />
                      <p className="text-xs text-slate-400 mt-1">
                        Green: &lt;85° | Yellow: 85-90° | Red: 91-102° | Black: &gt;103°
                      </p>
                    </div>
                    <div>
                      <Label>Notes (optional)</Label>
                      <Input
                        value={weatherForm.notes}
                        onChange={(e) => setWeatherForm(prev => ({ ...prev, notes: e.target.value }))}
                        placeholder="e.g., Expected to cool down after 1600"
                      />
                    </div>
                    <Button onClick={handleSaveWeather} disabled={saving} className="w-full bg-[#00205B]">
                      {saving ? 'Saving...' : 'Update Flag Status'}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            )}
          </div>
          <div className={`p-4 ${flagColors[dailySettings?.weather_flag?.flag_color || 'green']?.bgLight}`}>
            <div className="flex items-center gap-4">
              <div className={`w-16 h-20 ${flagColors[dailySettings?.weather_flag?.flag_color || 'green']?.bg} rounded shadow-lg flex items-center justify-center`}>
                <Flag className="w-8 h-8 text-white" />
              </div>
              <div className="flex-1">
                <div className={`text-2xl font-black uppercase ${flagColors[dailySettings?.weather_flag?.flag_color || 'green']?.text}`}>
                  {dailySettings?.weather_flag?.flag_color || 'Green'} Flag
                </div>
                {dailySettings?.weather_flag?.heat_index && (
                  <div className="flex items-center gap-1 text-slate-600 text-sm">
                    <Thermometer className="w-4 h-4" />
                    Heat Index: {dailySettings.weather_flag.heat_index}°F
                  </div>
                )}
                <p className="text-sm text-slate-600 mt-1">
                  {dailySettings?.weather_flag?.guidelines?.water_intake && (
                    <span className="flex items-center gap-1">
                      <Droplets className="w-3 h-3" />
                      Water: {dailySettings.weather_flag.guidelines.water_intake}
                    </span>
                  )}
                </p>
              </div>
            </div>
            
            {/* Guidelines */}
            {dailySettings?.weather_flag?.guidelines && (
              <div className="mt-4 pt-4 border-t border-slate-200">
                <p className="text-xs font-bold uppercase text-slate-500 mb-2">Activity Guidelines</p>
                <div className="grid grid-cols-3 gap-2 text-center mb-3">
                  <div className="bg-white p-2 rounded text-xs">
                    <p className="text-slate-500">Low</p>
                    <p className="font-bold">{dailySettings.weather_flag.guidelines.rest_schedule?.low}</p>
                  </div>
                  <div className="bg-white p-2 rounded text-xs">
                    <p className="text-slate-500">Medium</p>
                    <p className="font-bold">{dailySettings.weather_flag.guidelines.rest_schedule?.medium}</p>
                  </div>
                  <div className="bg-white p-2 rounded text-xs">
                    <p className="text-slate-500">High</p>
                    <p className={`font-bold ${dailySettings.weather_flag.guidelines.rest_schedule?.high === 'PROHIBITED' ? 'text-red-600' : ''}`}>
                      {dailySettings.weather_flag.guidelines.rest_schedule?.high}
                    </p>
                  </div>
                </div>
                <ul className="text-xs text-slate-600 space-y-1">
                  {dailySettings.weather_flag.guidelines.instructions?.slice(0, 3).map((instruction, idx) => (
                    <li key={idx} className="flex items-start gap-1">
                      <span className="text-slate-400">•</span>
                      {instruction}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {dailySettings?.weather_flag?.notes && (
              <p className="text-amber-700 text-sm mt-3 flex items-center gap-1 bg-amber-50 p-2 rounded">
                <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                {dailySettings.weather_flag.notes}
              </p>
            )}
            {dailySettings?.weather_flag?.updated_at && (
              <p className="text-xs text-slate-400 mt-2">
                Updated {new Date(dailySettings.weather_flag.updated_at).toLocaleString()}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {/* Total Participants */}
        <div className="bg-white border border-slate-200 rounded-sm p-4" data-testid="stat-total-participants">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">Total Participants</p>
              <p className="text-3xl font-bold text-[#00205B] font-mono">{stats?.participants?.total || 0}</p>
            </div>
            <div className="p-2 bg-[#00205B]/10 rounded-sm">
              <Users className="w-5 h-5 text-[#00205B]" />
            </div>
          </div>
        </div>

        {/* Paid Status */}
        <div className="bg-white border border-slate-200 rounded-sm p-4" data-testid="stat-paid-status">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">Payment Status</p>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold text-emerald-600 font-mono">{stats?.participants?.paid || 0}</span>
                <span className="text-sm text-slate-400">/</span>
                <span className="text-lg text-[#BF0D3E] font-mono">{stats?.participants?.unpaid || 0}</span>
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-1 text-xs text-emerald-600">
                <UserCheck className="w-4 h-4" /> Paid
              </div>
              <div className="flex items-center gap-1 text-xs text-[#BF0D3E]">
                <UserX className="w-4 h-4" /> Unpaid
              </div>
            </div>
          </div>
        </div>

        {/* Budget Estimated */}
        <div className="bg-white border border-slate-200 rounded-sm p-4" data-testid="stat-budget-estimated">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">Budget Estimated</p>
              <p className="text-3xl font-bold text-[#00205B] font-mono">{formatCurrency(stats?.budget?.total_estimated || 0)}</p>
            </div>
            <div className="p-2 bg-[#00205B]/10 rounded-sm">
              <DollarSign className="w-5 h-5 text-[#00205B]" />
            </div>
          </div>
        </div>

        {/* Budget Variance */}
        <div className="bg-white border border-slate-200 rounded-sm p-4" data-testid="stat-budget-variance">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">Budget Variance</p>
              <p className={`text-3xl font-bold font-mono ${(stats?.budget?.variance || 0) >= 0 ? 'text-emerald-600' : 'text-[#BF0D3E]'}`}>
                {formatCurrency(stats?.budget?.variance || 0)}
              </p>
            </div>
            <div className={`p-2 rounded-sm ${(stats?.budget?.variance || 0) >= 0 ? 'bg-emerald-100' : 'bg-red-100'}`}>
              {(stats?.budget?.variance || 0) >= 0 
                ? <TrendingUp className="w-5 h-5 text-emerald-600" />
                : <TrendingDown className="w-5 h-5 text-[#BF0D3E]" />
              }
            </div>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Participant Types */}
        <div className="bg-white border border-slate-200 rounded-sm">
          <div className="border-b border-slate-100 p-4">
            <h2 className="font-bold uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Participants by Type
            </h2>
          </div>
          <div className="p-4">
            {participantTypeData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={participantTypeData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis 
                    dataKey="name" 
                    tick={{ fontSize: 10, fill: '#64748B' }}
                    axisLine={{ stroke: '#E2E8F0' }}
                  />
                  <YAxis 
                    tick={{ fontSize: 10, fill: '#64748B' }}
                    axisLine={{ stroke: '#E2E8F0' }}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#fff', 
                      border: '1px solid #E2E8F0',
                      borderRadius: '2px'
                    }}
                  />
                  <Bar dataKey="value" fill="#00205B" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[250px] flex items-center justify-center text-slate-400">
                No participant data available
              </div>
            )}
          </div>
        </div>

        {/* Gender Distribution */}
        <div className="bg-white border border-slate-200 rounded-sm">
          <div className="border-b border-slate-100 p-4">
            <h2 className="font-bold uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Gender Distribution
            </h2>
          </div>
          <div className="p-4">
            {genderData.some(d => d.value > 0) ? (
              <div className="flex items-center justify-center gap-8">
                <ResponsiveContainer width={200} height={200}>
                  <PieChart>
                    <Pie
                      data={genderData}
                      cx="50%"
                      cy="50%"
                      innerRadius={40}
                      outerRadius={80}
                      dataKey="value"
                      paddingAngle={2}
                    >
                      {genderData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                {/* Legend beside the chart */}
                <div className="space-y-3">
                  {genderData.map((entry, index) => (
                    <div key={entry.name} className="flex items-center gap-3">
                      <div 
                        className="w-4 h-4 rounded-sm" 
                        style={{ backgroundColor: COLORS[index % COLORS.length] }}
                      />
                      <div>
                        <p className="font-medium text-slate-700">{entry.name}</p>
                        <p className="text-sm text-slate-500">
                          {entry.value} ({((entry.value / genderData.reduce((a, b) => a + b.value, 0)) * 100).toFixed(0) || 0}%)
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="h-[200px] flex items-center justify-center text-slate-400">
                No gender data available
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Active Users & Schedule Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Users Widget */}
        <div className="bg-white border border-slate-200 rounded-sm" data-testid="active-users-widget">
          <div className="border-b border-slate-100 p-4 flex items-center justify-between">
            <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Who's Online
            </h2>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
              <span className="text-sm font-bold text-emerald-600">{activeUsers.count}</span>
            </div>
          </div>
          <div className="p-4 max-h-[280px] overflow-y-auto">
            {activeUsers.users.length === 0 ? (
              <div className="text-center text-slate-400 py-4">
                <Radio className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No other users online</p>
              </div>
            ) : (
              <div className="space-y-2">
                {activeUsers.users.map((u) => (
                  <div 
                    key={u.id} 
                    className="flex items-center gap-3 p-2 rounded-sm hover:bg-slate-50 transition-colors"
                  >
                    <div className="relative">
                      <div className="w-8 h-8 rounded-full bg-[#00205B] text-white flex items-center justify-center text-sm font-bold">
                        {u.name?.charAt(0)?.toUpperCase() || '?'}
                      </div>
                      <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-500 border-2 border-white rounded-full" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-900 truncate">{u.name}</p>
                      <p className="text-xs text-slate-500 capitalize">{ROLE_LABELS[u.role] || u.role}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Schedule Info */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-sm" data-testid="todays-schedule">
          <div className="border-b border-slate-100 p-4 flex items-center justify-between">
            <h2 className="font-bold uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Today's Schedule
            </h2>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => navigate('/schedule')}
              className="text-[#00205B] hover:bg-[#00205B]/10"
            >
              View Full Schedule <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
          <div className="p-4">
            {todayEvents.length === 0 ? (
              <div className="text-center py-8 text-slate-400">
                <Calendar className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="text-sm">No events scheduled for today</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[320px] overflow-y-auto">
                {/* Current Event Highlight */}
                {getCurrentEvent() && (
                  <div className="mb-4 p-3 bg-[#00205B]/5 border border-[#00205B]/20 rounded-sm">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-2 h-2 bg-[#BF0D3E] rounded-full animate-pulse" />
                      <span className="text-xs font-bold uppercase text-[#BF0D3E]">Happening Now</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className={`w-1 self-stretch rounded ${eventTypeColors[getCurrentEvent().event_type]?.bg || 'bg-slate-500'}`} />
                      <div className="flex-1">
                        <p className="font-bold text-[#00205B]">{getCurrentEvent().title}</p>
                        <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {formatTime(getCurrentEvent().start_time)} - {formatTime(getCurrentEvent().end_time)}
                          </span>
                          {getCurrentEvent().location && (
                            <span className="flex items-center gap-1">
                              <MapPin className="w-3 h-3" />
                              {getCurrentEvent().location}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Event List */}
                {todayEvents.map((event, idx) => (
                  <div 
                    key={event.id || idx}
                    className={`flex items-start gap-3 p-2 rounded-sm hover:bg-slate-50 transition-colors border-l-4 ${eventTypeColors[event.event_type]?.border || 'border-l-slate-500'}`}
                  >
                    <div className="text-center min-w-[60px]">
                      <p className="text-sm font-bold text-[#00205B]">{formatTime(event.start_time)}</p>
                      <p className="text-xs text-slate-400">{formatTime(event.end_time)}</p>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-slate-900 text-sm truncate">{event.title}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        {event.location && (
                          <span className="text-xs text-slate-500 flex items-center gap-1">
                            <MapPin className="w-3 h-3" />
                            {event.location}
                          </span>
                        )}
                        {event.uniform && event.uniform !== 'default' && (
                          <span className="text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                            {event.uniform}
                          </span>
                        )}
                      </div>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded capitalize ${eventTypeColors[event.event_type]?.light || 'bg-slate-100'} ${eventTypeColors[event.event_type]?.text || 'text-slate-600'}`}>
                      {event.event_type}
                    </span>
                  </div>
                ))}
              </div>
            )}
            
            {/* Quick Stats Footer */}
            <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between text-sm">
              <div className="flex items-center gap-4 text-slate-500">
                <span className="flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  <strong className="text-[#00205B]">{todayEvents.length}</strong> events today
                </span>
              </div>
              <span className="text-xs text-slate-400">
                {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
