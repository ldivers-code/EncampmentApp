import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { useAuth } from '../context/AuthContext';
import {
  User, Calendar, Heart, Award, Utensils, CheckCircle2, AlertTriangle,
  Clock, MapPin, Shield, Pill, Camera, Eye, EyeOff, Maximize2, Minimize2,
  Save, Settings, ChevronUp, ChevronDown, Search, Loader2
} from 'lucide-react';
import { toast } from 'sonner';
import { uploadCadetPhoto, getCadetPhotoUrl, deleteCadetPhoto } from '../services/api';

const API = process.env.REACT_APP_BACKEND_URL;
const fetchOpts = { credentials: 'include' };

const STAFF_ROLES = ['dcp', 'commander', 'executive_staff'];

const DEFAULT_WIDGETS = {
  overview: { visible: true, size: 'full', order: 0, label: 'Cadet Overview' },
  schedule: { visible: true, size: 'full', order: 1, label: 'Schedule' },
  health: { visible: true, size: 'half', order: 2, label: 'Health Incidents' },
  med_diary: { visible: true, size: 'half', order: 3, label: 'Medication Diary' },
  points: { visible: true, size: 'half', order: 4, label: 'Points & Awards' },
  meals: { visible: true, size: 'full', order: 5, label: 'Meal Plans' },
  otc_form: { visible: true, size: 'full', order: 6, label: 'OTC Permission Form' }
};

const SIZE_OPTIONS = [
  { value: 'third', label: '1/3 Width' },
  { value: 'half', label: '1/2 Width' },
  { value: 'full', label: 'Full Width' }
];

const SIZE_CLASSES = {
  third: 'lg:col-span-1',
  half: 'lg:col-span-2',
  full: 'lg:col-span-4'
};

export default function MyCadetPage() {
  const { user } = useAuth();
  const isAdmin = STAFF_ROLES.includes(user?.role);

  const [cadet, setCadet] = useState(null);
  const [schedule, setSchedule] = useState(null);
  const [health, setHealth] = useState(null);
  const [medDiary, setMedDiary] = useState([]);
  const [points, setPoints] = useState(null);
  const [meals, setMeals] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Admin state
  const [participants, setParticipants] = useState([]);
  const [selectedParticipant, setSelectedParticipant] = useState('');
  const [participantSearch, setParticipantSearch] = useState('');
  const [widgets, setWidgets] = useState(DEFAULT_WIDGETS);
  const [configDirty, setConfigDirty] = useState(false);
  const [editMode, setEditMode] = useState(false);

  // OTC form state
  const [otcData, setOtcData] = useState(null);
  const [otcLoading, setOtcLoading] = useState(false);
  const [otcSubmitting, setOtcSubmitting] = useState(false);
  const [photoUploading, setPhotoUploading] = useState(false);
  const [otcForm, setOtcForm] = useState({
    parent_name: '', parent_relationship: '', parent_phone: '', parent_email: '',
    medications: {},
    ack_otc_only: false, ack_staff_discretion: false,
    ack_prescription_separate: false, ack_accurate_info: false,
    notes_for_hso: '', signature: '',
  });

  // Load portal config
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API}/api/parent/portal-config`, fetchOpts);
        if (res.ok) {
          const data = await res.json();
          if (data.widgets) {
            setWidgets(prev => {
              const merged = { ...prev };
              Object.keys(data.widgets).forEach(k => {
                if (merged[k]) merged[k] = { ...merged[k], ...data.widgets[k] };
              });
              return merged;
            });
          }
        }
      } catch (err) { console.error('Failed to load widget settings:', err); }
    })();
  }, []);

  // Admin: load participants list
  useEffect(() => {
    if (!isAdmin) return;
    (async () => {
      try {
        const res = await fetch(`${API}/api/parent/admin-preview/participants`, fetchOpts);
        if (res.ok) setParticipants(await res.json());
      } catch (err) { console.error('Failed to load participants:', err); }
    })();
  }, [isAdmin]);

  // Parent: fetch own cadet data
  const fetchParentData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [cadetRes, schedRes, healthRes, pointsRes, mealsRes, medDiaryRes] = await Promise.all([
        fetch(`${API}/api/parent/my-cadet`, fetchOpts),
        fetch(`${API}/api/parent/my-cadet/schedule`, fetchOpts),
        fetch(`${API}/api/parent/my-cadet/health-incidents`, fetchOpts),
        fetch(`${API}/api/parent/my-cadet/points`, fetchOpts),
        fetch(`${API}/api/parent/my-cadet/meals`, fetchOpts),
        fetch(`${API}/api/parent/my-cadet/med-diary`, fetchOpts),
      ]);
      if (!cadetRes.ok) {
        const err = await cadetRes.json();
        throw new Error(err.detail || 'Failed to load cadet data');
      }
      setCadet(await cadetRes.json());
      setSchedule(await schedRes.json());
      setHealth(await healthRes.json());
      setPoints(await pointsRes.json());
      setMeals(await mealsRes.json());
      if (medDiaryRes.ok) setMedDiary(await medDiaryRes.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Admin: fetch preview data for selected participant
  const fetchAdminPreview = useCallback(async (pid) => {
    if (!pid) return;
    try {
      setLoading(true);
      setError(null);
      const [cadetRes, schedRes, healthRes, pointsRes, mealsRes] = await Promise.all([
        fetch(`${API}/api/parent/admin-preview/${pid}`, fetchOpts),
        fetch(`${API}/api/parent/admin-preview/${pid}/schedule`, fetchOpts),
        fetch(`${API}/api/parent/admin-preview/${pid}/health`, fetchOpts),
        fetch(`${API}/api/parent/admin-preview/${pid}/points`, fetchOpts),
        fetch(`${API}/api/parent/admin-preview/${pid}/meals`, fetchOpts),
      ]);
      if (!cadetRes.ok) {
        const err = await cadetRes.json();
        throw new Error(err.detail || 'Failed to load preview data');
      }
      setCadet(await cadetRes.json());
      setSchedule(await schedRes.json());
      setHealth(await healthRes.json());
      setPoints(await pointsRes.json());
      setMeals(await mealsRes.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isAdmin) fetchParentData();
  }, [isAdmin, fetchParentData]);

  useEffect(() => {
    if (isAdmin && selectedParticipant) fetchAdminPreview(selectedParticipant);
  }, [isAdmin, selectedParticipant, fetchAdminPreview]);

  // OTC form loader
  const loadOtcForm = useCallback(async () => {
    if (!user || isAdmin) return;
    setOtcLoading(true);
    try {
      const res = await fetch(`${API}/api/parent/my-cadet/otc-permission`, fetchOpts);
      if (res.ok) {
        const data = await res.json();
        setOtcData(data);
        if (data.form) {
          setOtcForm({
            parent_name: data.form.parent_name || '', parent_relationship: data.form.parent_relationship || '',
            parent_phone: data.form.parent_phone || '', parent_email: data.form.parent_email || '',
            medications: data.form.medications || {},
            ack_otc_only: data.form.ack_otc_only || false, ack_staff_discretion: data.form.ack_staff_discretion || false,
            ack_prescription_separate: data.form.ack_prescription_separate || false,
            ack_accurate_info: data.form.ack_accurate_info || false,
            notes_for_hso: data.form.notes_for_hso || '', signature: data.form.signature || '',
          });
        }
      }
    } catch (err) { console.error('Failed to load OTC form:', err); } finally { setOtcLoading(false); }
  }, [user, isAdmin]);

  const submitOtcForm = async () => {
    if (!otcForm.parent_name || !otcForm.parent_relationship || !otcForm.parent_phone || !otcForm.parent_email) {
      toast.error('Please fill in all parent/guardian information'); return;
    }
    if (!otcForm.signature || otcForm.signature.trim().length < 2) {
      toast.error('Typed signature is required'); return;
    }
    setOtcSubmitting(true);
    try {
      const res = await fetch(`${API}/api/parent/my-cadet/otc-permission`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        credentials: 'include', body: JSON.stringify(otcForm),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Submission failed');
      toast.success('OTC Permission Form submitted successfully');
      loadOtcForm();
    } catch (e) { toast.error(e.message); } finally { setOtcSubmitting(false); }
  };

  const handlePhotoUpload = async (file) => {
    if (!cadet || !file) return;
    setPhotoUploading(true);
    try {
      await uploadCadetPhoto(cadet.id, file);
      toast.success('Photo uploaded');
      isAdmin ? fetchAdminPreview(selectedParticipant) : fetchParentData();
    } catch { toast.error('Failed to upload photo'); } finally { setPhotoUploading(false); }
  };

  // Widget config helpers
  const updateWidget = (key, field, value) => {
    setWidgets(prev => ({ ...prev, [key]: { ...prev[key], [field]: value } }));
    setConfigDirty(true);
  };

  const moveWidget = (key, direction) => {
    setWidgets(prev => {
      const sorted = Object.entries(prev).sort((a, b) => a[1].order - b[1].order);
      const idx = sorted.findIndex(([k]) => k === key);
      const swapIdx = direction === 'up' ? idx - 1 : idx + 1;
      if (swapIdx < 0 || swapIdx >= sorted.length) return prev;
      const newWidgets = { ...prev };
      const myOrder = newWidgets[key].order;
      newWidgets[key] = { ...newWidgets[key], order: newWidgets[sorted[swapIdx][0]].order };
      newWidgets[sorted[swapIdx][0]] = { ...newWidgets[sorted[swapIdx][0]], order: myOrder };
      return newWidgets;
    });
    setConfigDirty(true);
  };

  const saveConfig = async () => {
    try {
      const payload = {};
      Object.entries(widgets).forEach(([k, v]) => {
        payload[k] = { visible: v.visible, size: v.size, order: v.order };
      });
      const res = await fetch(`${API}/api/parent/portal-config`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        credentials: 'include', body: JSON.stringify({ widgets: payload }),
      });
      if (!res.ok) throw new Error('Save failed');
      toast.success('Portal layout saved');
      setConfigDirty(false);
    } catch (e) { toast.error(e.message); }
  };

  const sortedWidgets = Object.entries(widgets).sort((a, b) => a[1].order - b[1].order);

  const filteredParticipants = participants.filter(p => {
    if (!participantSearch) return true;
    const q = participantSearch.toLowerCase();
    return `${p.first_name} ${p.last_name}`.toLowerCase().includes(q) || (p.capid || '').toLowerCase().includes(q);
  });

  // =================== WIDGET RENDERERS ===================
  const renderOverview = () => (
    <div className="space-y-3">
      {cadet && (
        <div className="flex items-start gap-4">
          <div className="relative w-20 h-20 rounded-sm bg-slate-100 border border-slate-200 flex items-center justify-center overflow-hidden flex-shrink-0">
            {cadet.photo_url ? (
              <img src={getCadetPhotoUrl(cadet.id)} alt="" className="w-full h-full object-cover" />
            ) : (
              <User className="w-8 h-8 text-slate-300" />
            )}
            {!isAdmin && (
              <label className="absolute inset-0 cursor-pointer bg-black/0 hover:bg-black/30 flex items-center justify-center transition-colors group">
                <Camera className="w-5 h-5 text-white opacity-0 group-hover:opacity-100" />
                <input type="file" accept="image/*" className="hidden" onChange={e => e.target.files[0] && handlePhotoUpload(e.target.files[0])} />
              </label>
            )}
            {photoUploading && <div className="absolute inset-0 bg-white/80 flex items-center justify-center"><Loader2 className="w-4 h-4 animate-spin" /></div>}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-bold text-lg text-[#00205B]">{cadet.first_name} {cadet.last_name}</h3>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-1 text-sm text-slate-600">
              {cadet.capid && <div><span className="text-slate-400 text-xs">CAPID:</span> {cadet.capid}</div>}
              {cadet.flight && <div><span className="text-slate-400 text-xs">Flight:</span> {cadet.flight}</div>}
              {cadet.squadron && <div><span className="text-slate-400 text-xs">Squadron:</span> {cadet.squadron}</div>}
              {cadet.unit && <div><span className="text-slate-400 text-xs">Unit:</span> {cadet.unit}</div>}
              {cadet.check_in_status && <div><span className="text-slate-400 text-xs">Check-In:</span> <Badge variant={cadet.check_in_status === 'completed' ? 'default' : 'secondary'}>{cadet.check_in_status}</Badge></div>}
              {cadet.bunk_assignment && <div><span className="text-slate-400 text-xs">Bunk:</span> {cadet.building} - #{cadet.bunk_assignment}</div>}
            </div>
            {cadet.dietary_restrictions?.length > 0 && (
              <div className="mt-2 flex items-center gap-1 flex-wrap">
                <AlertTriangle className="w-3 h-3 text-amber-500" />
                <span className="text-xs text-amber-700 font-medium">Dietary:</span>
                {cadet.dietary_restrictions.map((d, i) => (
                  <Badge key={`diet-${d}-${i}`} variant="outline" className="text-[10px] border-amber-200 text-amber-700">{d}</Badge>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );

  const renderSchedule = () => (
    <div className="space-y-2 max-h-[400px] overflow-y-auto">
      {(!schedule || schedule.length === 0) ? (
        <p className="text-sm text-slate-400 text-center py-4">No schedule events</p>
      ) : schedule.slice(0, 20).map((evt, i) => (
        <div key={evt.id || `sched-${i}`} className="flex items-start gap-2 p-2 bg-slate-50 rounded-sm border border-slate-100">
          <Clock className="w-3.5 h-3.5 text-[#00205B] mt-0.5 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="font-medium text-sm">{evt.title}</div>
            <div className="text-xs text-slate-500">{evt.date} {evt.start_time && `${evt.start_time} - ${evt.end_time}`}</div>
            {evt.location && <div className="text-xs text-slate-400 flex items-center gap-1"><MapPin className="w-2.5 h-2.5" />{evt.location}</div>}
          </div>
        </div>
      ))}
    </div>
  );

  const renderHealth = () => (
    <div className="space-y-2 max-h-[300px] overflow-y-auto">
      {(!health || health.length === 0) ? (
        <div className="text-center py-4">
          <CheckCircle2 className="w-6 h-6 mx-auto text-emerald-400 mb-1" />
          <p className="text-sm text-slate-400">No health incidents reported</p>
        </div>
      ) : health.map((inc, i) => (
        <div key={inc.id || `health-${i}`} className="p-2 bg-rose-50 rounded-sm border border-rose-100">
          <div className="flex items-center gap-1.5">
            <Heart className="w-3 h-3 text-rose-500" />
            <span className="font-medium text-sm text-rose-800">{inc.type || inc.incident_type || 'Incident'}</span>
            <span className="text-xs text-rose-400 ml-auto">{inc.created_at?.substring(0, 10)}</span>
          </div>
          {inc.notes && <p className="text-xs text-rose-600 mt-1">{inc.notes}</p>}
        </div>
      ))}
    </div>
  );

  const renderMedDiary = () => (
    <div className="space-y-2 max-h-[300px] overflow-y-auto">
      {(!medDiary || medDiary.length === 0) ? (
        <div className="text-center py-4">
          <Pill className="w-6 h-6 mx-auto text-slate-300 mb-1" />
          <p className="text-sm text-slate-400">No medication diary entries</p>
        </div>
      ) : medDiary.map((entry, i) => (
        <div key={entry.id || `med-${i}`} className="p-2 bg-blue-50 rounded-sm border border-blue-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Pill className="w-3 h-3 text-blue-500" />
              <span className="font-medium text-sm text-blue-800">{entry.medication_name}</span>
              {entry.dosage && <span className="text-xs text-blue-500">({entry.dosage})</span>}
              {entry.refused && <span className="text-xs text-red-600 font-bold ml-1">REFUSED</span>}
            </div>
            <span className="text-xs text-blue-400">
              {entry.administered_at ? new Date(entry.administered_at).toLocaleString([], {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'}) : entry.date}
            </span>
          </div>
          <p className="text-xs text-blue-600 mt-0.5">Administered by: {entry.administered_by}</p>
          {entry.notes && <p className="text-xs text-blue-500 mt-0.5">{entry.notes}</p>}
        </div>
      ))}
    </div>
  );

  const renderPoints = () => (
    <div className="space-y-2 max-h-[300px] overflow-y-auto">
      {(!points || points.length === 0) ? (
        <div className="text-center py-4">
          <Award className="w-6 h-6 mx-auto text-slate-300 mb-1" />
          <p className="text-sm text-slate-400">No points or awards yet</p>
        </div>
      ) : points.map((pt, i) => (
        <div key={pt.id || `pt-${i}`} className="flex items-center gap-2 p-2 bg-amber-50 rounded-sm border border-amber-100">
          <Award className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <span className="text-sm font-medium">{pt.reason || pt.description || 'Points'}</span>
            {pt.category && <span className="text-xs text-slate-400 ml-2">{pt.category}</span>}
          </div>
          <Badge className="bg-amber-600">{pt.points > 0 ? `+${pt.points}` : pt.points}</Badge>
        </div>
      ))}
    </div>
  );

  const renderMeals = () => (
    <div className="space-y-2 max-h-[400px] overflow-y-auto">
      {(!meals || meals.length === 0) ? (
        <p className="text-sm text-slate-400 text-center py-4">No meal plans available</p>
      ) : meals.map((meal, i) => (
        <div key={meal.id || `meal-${i}`} className="flex items-start gap-2 p-2 bg-orange-50 rounded-sm border border-orange-100">
          <Utensils className="w-3.5 h-3.5 text-orange-600 mt-0.5 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium capitalize">{meal.meal_type} — {meal.date}</div>
            <div className="text-xs text-slate-600">{meal.menu_items}</div>
            {meal.dietary_notes && <div className="text-xs text-amber-600 mt-0.5"><AlertTriangle className="w-2.5 h-2.5 inline mr-0.5" />{meal.dietary_notes}</div>}
          </div>
        </div>
      ))}
    </div>
  );

  const renderOtcForm = () => {
    if (isAdmin) {
      return (
        <div className="text-center py-4">
          <Pill className="w-6 h-6 mx-auto text-slate-300 mb-2" />
          <p className="text-sm text-slate-400">OTC Permission Form is only fillable by parents</p>
          <p className="text-xs text-slate-300 mt-1">Parents will see the full form here</p>
        </div>
      );
    }
    if (otcLoading) return <div className="text-center py-4"><Loader2 className="w-5 h-5 animate-spin mx-auto" /></div>;
    if (!otcData) {
      return (
        <div className="text-center py-4">
          <Button onClick={loadOtcForm} variant="outline" size="sm">Load OTC Form</Button>
        </div>
      );
    }
    return (
      <div className="space-y-3 text-sm">
        <p className="text-xs text-slate-500">{otcData.form ? 'Form previously submitted. You can update below.' : 'Please fill out and submit.'}</p>
        <div className="grid grid-cols-2 gap-2">
          <Input placeholder="Parent Name" value={otcForm.parent_name} onChange={e => setOtcForm(p => ({ ...p, parent_name: e.target.value }))} className="text-sm rounded-sm" />
          <Input placeholder="Relationship" value={otcForm.parent_relationship} onChange={e => setOtcForm(p => ({ ...p, parent_relationship: e.target.value }))} className="text-sm rounded-sm" />
          <Input placeholder="Phone" value={otcForm.parent_phone} onChange={e => setOtcForm(p => ({ ...p, parent_phone: e.target.value }))} className="text-sm rounded-sm" />
          <Input placeholder="Email" value={otcForm.parent_email} onChange={e => setOtcForm(p => ({ ...p, parent_email: e.target.value }))} className="text-sm rounded-sm" />
        </div>
        {otcData.medications_list?.map(med => (
          <label key={med} className="flex items-center gap-2">
            <input type="checkbox" checked={otcForm.medications[med] === true} onChange={e => setOtcForm(p => ({ ...p, medications: { ...p.medications, [med]: e.target.checked } }))} />
            <span className="text-xs">{otcData.medication_labels?.[med] || med}</span>
          </label>
        ))}
        <Textarea placeholder="Notes for HSO" value={otcForm.notes_for_hso} onChange={e => setOtcForm(p => ({ ...p, notes_for_hso: e.target.value }))} className="text-sm rounded-sm" rows={2} />
        <Input placeholder="Type your full name as signature" value={otcForm.signature} onChange={e => setOtcForm(p => ({ ...p, signature: e.target.value }))} className="text-sm rounded-sm" style={{ fontFamily: 'cursive' }} />
        <Button onClick={submitOtcForm} disabled={otcSubmitting} className="w-full bg-[#00205B] rounded-sm" size="sm">
          {otcSubmitting ? 'Submitting...' : 'Submit OTC Form'}
        </Button>
      </div>
    );
  };

  const WIDGET_RENDERERS = {
    overview: renderOverview,
    schedule: renderSchedule,
    health: renderHealth,
    med_diary: renderMedDiary,
    points: renderPoints,
    meals: renderMeals,
    otc_form: renderOtcForm
  };

  const WIDGET_ICONS = {
    overview: User,
    schedule: Calendar,
    health: Heart,
    points: Award,
    meals: Utensils,
    otc_form: Pill
  };

  // =================== RENDER ===================
  if (!isAdmin && loading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-[#00205B]" />
      </div>
    );
  }

  return (
    <div className="p-3 sm:p-6 lg:p-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl sm:text-2xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
            {isAdmin ? 'Parent Portal Admin' : 'My Cadet'}
          </h1>
          <p className="text-slate-500 text-sm mt-0.5">
            {isAdmin ? 'Preview and configure the parent portal layout' : 'View your cadet\'s encampment information'}
          </p>
        </div>
        {isAdmin && (
          <div className="flex items-center gap-2">
            <Button
              variant={editMode ? 'default' : 'outline'}
              size="sm"
              onClick={() => setEditMode(!editMode)}
              className={`rounded-sm ${editMode ? 'bg-amber-600 hover:bg-amber-700' : ''}`}
              data-testid="toggle-edit-mode"
            >
              <Settings className="w-4 h-4 mr-1" />
              {editMode ? 'Editing Layout' : 'Edit Layout'}
            </Button>
            {configDirty && (
              <Button size="sm" onClick={saveConfig} className="bg-emerald-600 hover:bg-emerald-700 rounded-sm" data-testid="save-portal-config">
                <Save className="w-4 h-4 mr-1" /> Save Layout
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Admin: Cadet Selector */}
      {isAdmin && (
        <div className="bg-white border border-slate-200 rounded-sm p-4 mb-6" data-testid="cadet-selector">
          <div className="flex items-center gap-3">
            <Search className="w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search cadets by name or CAPID..."
              value={participantSearch}
              onChange={e => setParticipantSearch(e.target.value)}
              className="max-w-xs rounded-sm text-sm"
              data-testid="cadet-search-input"
            />
            <Select value={selectedParticipant} onValueChange={setSelectedParticipant}>
              <SelectTrigger className="w-64 rounded-sm text-sm" data-testid="cadet-selector-dropdown">
                <SelectValue placeholder="Select a cadet to preview..." />
              </SelectTrigger>
              <SelectContent>
                {filteredParticipants.map(p => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.last_name}, {p.first_name} {p.flight ? `(${p.flight})` : ''}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {!selectedParticipant && (
            <p className="text-xs text-amber-600 mt-2 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              Select a cadet to preview their parent portal view
            </p>
          )}
        </div>
      )}

      {/* Error state */}
      {error && !isAdmin && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="py-6 text-center">
            <AlertTriangle className="w-8 h-8 mx-auto text-red-400 mb-2" />
            <p className="text-red-700 font-medium">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Loading state for admin preview */}
      {isAdmin && selectedParticipant && loading && (
        <div className="flex items-center justify-center h-32">
          <Loader2 className="w-6 h-6 animate-spin text-[#00205B]" />
        </div>
      )}

      {/* Widget Grid */}
      {((!isAdmin && cadet) || (isAdmin && cadet)) && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4" data-testid="widget-grid">
          {sortedWidgets.map(([key, config]) => {
            if (!config.visible && !editMode) return null;
            const Icon = WIDGET_ICONS[key];
            const renderer = WIDGET_RENDERERS[key];
            const sizeClass = SIZE_CLASSES[config.size] || SIZE_CLASSES.full;

            return (
              <div
                key={key}
                className={`${sizeClass} ${!config.visible && editMode ? 'opacity-50' : ''}`}
                data-testid={`widget-${key}`}
              >
                <Card className="border-slate-200 rounded-sm h-full relative group">
                  <CardHeader className="pb-2 flex flex-row items-center justify-between">
                    <CardTitle className="text-sm font-bold uppercase tracking-tight text-[#00205B] flex items-center gap-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
                      {Icon && <Icon className="w-4 h-4" />}
                      {config.label}
                    </CardTitle>
                    {/* Admin edit controls */}
                    {isAdmin && editMode && (
                      <div className="flex items-center gap-1" data-testid={`widget-controls-${key}`}>
                        <button onClick={() => moveWidget(key, 'up')} className="p-1 hover:bg-slate-100 rounded" title="Move up">
                          <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
                        </button>
                        <button onClick={() => moveWidget(key, 'down')} className="p-1 hover:bg-slate-100 rounded" title="Move down">
                          <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                        </button>
                        <button
                          onClick={() => updateWidget(key, 'visible', !config.visible)}
                          className={`p-1 rounded ${config.visible ? 'hover:bg-slate-100' : 'hover:bg-red-50'}`}
                          title={config.visible ? 'Hide widget' : 'Show widget'}
                          data-testid={`toggle-visibility-${key}`}
                        >
                          {config.visible ? <Eye className="w-3.5 h-3.5 text-emerald-500" /> : <EyeOff className="w-3.5 h-3.5 text-red-400" />}
                        </button>
                        <Select value={config.size} onValueChange={v => updateWidget(key, 'size', v)}>
                          <SelectTrigger className="w-24 h-7 rounded-sm text-[10px]" data-testid={`size-select-${key}`}>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {SIZE_OPTIONS.map(s => (
                              <SelectItem key={s.value} value={s.value} className="text-xs">{s.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                  </CardHeader>
                  <CardContent>
                    {renderer ? renderer() : null}
                  </CardContent>
                </Card>
              </div>
            );
          })}
        </div>
      )}

      {/* Admin: no cadet selected placeholder */}
      {isAdmin && !selectedParticipant && !loading && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4" data-testid="widget-grid-empty">
          {sortedWidgets.map(([key, config]) => {
            if (!config.visible && !editMode) return null;
            const Icon = WIDGET_ICONS[key];
            const sizeClass = SIZE_CLASSES[config.size] || SIZE_CLASSES.full;

            return (
              <div key={key} className={`${sizeClass} ${!config.visible && editMode ? 'opacity-50' : ''}`} data-testid={`widget-${key}`}>
                <Card className="border-slate-200 rounded-sm border-dashed h-full">
                  <CardHeader className="pb-2 flex flex-row items-center justify-between">
                    <CardTitle className="text-sm font-bold uppercase tracking-tight text-slate-400 flex items-center gap-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
                      {Icon && <Icon className="w-4 h-4" />}
                      {config.label}
                    </CardTitle>
                    {isAdmin && editMode && (
                      <div className="flex items-center gap-1">
                        <button onClick={() => moveWidget(key, 'up')} className="p-1 hover:bg-slate-100 rounded"><ChevronUp className="w-3.5 h-3.5 text-slate-400" /></button>
                        <button onClick={() => moveWidget(key, 'down')} className="p-1 hover:bg-slate-100 rounded"><ChevronDown className="w-3.5 h-3.5 text-slate-400" /></button>
                        <button onClick={() => updateWidget(key, 'visible', !config.visible)} className="p-1 rounded hover:bg-slate-100" data-testid={`toggle-visibility-${key}`}>
                          {config.visible ? <Eye className="w-3.5 h-3.5 text-emerald-500" /> : <EyeOff className="w-3.5 h-3.5 text-red-400" />}
                        </button>
                        <Select value={config.size} onValueChange={v => updateWidget(key, 'size', v)}>
                          <SelectTrigger className="w-24 h-7 rounded-sm text-[10px]"><SelectValue /></SelectTrigger>
                          <SelectContent>{SIZE_OPTIONS.map(s => <SelectItem key={s.value} value={s.value} className="text-xs">{s.label}</SelectItem>)}</SelectContent>
                        </Select>
                      </div>
                    )}
                  </CardHeader>
                  <CardContent>
                    <div className="text-center py-6 text-slate-300 text-sm">Select a cadet to preview</div>
                  </CardContent>
                </Card>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
