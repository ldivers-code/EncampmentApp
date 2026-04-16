import React, { useState, useEffect, useCallback } from 'react';
import {
  getSBFlights, createSBFlight, updateSBFlight, deleteSBFlight,
  getSBIssues, createSBIssue, updateSBIssue,
  getSBAnnouncements, createSBAnnouncement, updateSBAnnouncement, deleteSBAnnouncement,
  getSBSchedule, createSBScheduleEvent, updateSBScheduleEvent, deleteSBScheduleEvent,
  getSBResources, createSBResource, updateSBResource,
  getSBSettings, updateSBSettings, updateSBEmergency,
  getSBAudit, seedSBData
} from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import {
  Shield, MapPin, Activity, AlertTriangle, Megaphone, Calendar, Radio, Truck,
  Thermometer, Plus, Edit2, Trash2, Monitor, Settings, FileText, ExternalLink,
  RefreshCw, Clock, ChevronRight
} from 'lucide-react';

const TABS = [
  { key: 'flights', label: 'Flights', icon: Shield },
  { key: 'schedule', label: 'Schedule', icon: Calendar },
  { key: 'issues', label: 'Issues', icon: AlertTriangle },
  { key: 'announcements', label: 'Announcements', icon: Megaphone },
  { key: 'resources', label: 'Resources', icon: Radio },
  { key: 'settings', label: 'Settings', icon: Settings },
  { key: 'audit', label: 'Audit Log', icon: FileText },
];

const STATUS_LEVELS = ['green', 'yellow', 'red', 'blue', 'gray'];
const SEVERITIES = ['low', 'medium', 'high', 'critical'];
const HEAT_CATS = ['green', 'yellow', 'red', 'black'];
const RESOURCE_TYPES = ['radio', 'vehicle', 'equipment', 'supply'];
const RESOURCE_STATUSES = ['available', 'checked_out', 'in_use', 'maintenance', 'out_of_service'];

const SB_DOT = { green: 'bg-emerald-500', yellow: 'bg-amber-400', red: 'bg-red-500', blue: 'bg-sky-500', gray: 'bg-slate-400' };
const SEV_BADGE = { critical: 'bg-red-100 text-red-700', high: 'bg-amber-100 text-amber-700', medium: 'bg-yellow-100 text-yellow-700', low: 'bg-slate-100 text-slate-600' };

const StatusBoardControl = () => {
  const { user } = useAuth();
  const [tab, setTab] = useState('flights');
  const [flights, setFlights] = useState([]);
  const [issues, setIssues] = useState([]);
  const [announcements, setAnnouncements] = useState([]);
  const [schedule, setSchedule] = useState([]);
  const [resources, setResources] = useState([]);
  const [settings, setSettings] = useState({});
  const [audit, setAudit] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState({});

  const canEdit = ['dcp', 'commander', 'executive_staff', 'staff', 'plans_programs', 'logistics', 'health_services', 'training_officer', 'dining_facility'].includes(user?.role);
  const canEmergency = ['dcp', 'commander', 'executive_staff'].includes(user?.role);

  const load = useCallback(async () => {
    try {
      const [f, i, a, s, r, st] = await Promise.all([
        getSBFlights(), getSBIssues(), getSBAnnouncements(), getSBSchedule(), getSBResources(), getSBSettings()
      ]);
      setFlights(f); setIssues(i); setAnnouncements(a); setSchedule(s); setResources(r); setSettings(st);
    } catch (e) { toast.error('Failed to load data'); }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const loadAudit = async () => { try { setAudit(await getSBAudit()); } catch (error) { console.error('Failed to load audit:', error); } };

  const openModal = (type, data = null) => {
    setModal(type);
    if (type === 'flight') setForm(data || { name: '', current_location: '', current_status: 'Standing By', status_level: 'green', short_note: '' });
    else if (type === 'issue') setForm(data || { title: '', description: '', severity: 'medium', assigned_section: '', status: 'open' });
    else if (type === 'announcement') setForm(data || { message: '', priority: 'normal', active: true });
    else if (type === 'event') setForm(data || { title: '', start_time: '', end_time: '', location: '', section: '', status: 'scheduled', display_priority: 'normal' });
    else if (type === 'resource') setForm(data || { type: 'radio', name: '', status: 'available', assigned_to: '', location: '', notes: '' });
  };

  const saveItem = async () => {
    try {
      if (modal === 'flight') {
        if (form.id) await updateSBFlight(form.id, form); else await createSBFlight(form);
      } else if (modal === 'issue') {
        if (form.id) await updateSBIssue(form.id, form); else await createSBIssue(form);
      } else if (modal === 'announcement') {
        if (form.id) await updateSBAnnouncement(form.id, form); else await createSBAnnouncement(form);
      } else if (modal === 'event') {
        if (form.id) await updateSBScheduleEvent(form.id, form); else await createSBScheduleEvent(form);
      } else if (modal === 'resource') {
        if (form.id) await updateSBResource(form.id, form); else await createSBResource(form);
      }
      toast.success('Saved');
      setModal(null);
      load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Save failed'); }
  };

  const handleSeed = async () => {
    try { await seedSBData(); toast.success('Sample data seeded'); load(); } catch { toast.error('Seed failed'); }
  };

  const F = (key, val) => setForm(p => ({ ...p, [key]: val }));

  if (loading) return <div className="p-8 text-center text-slate-400">Loading...</div>;

  return (
    <div className="p-2 sm:p-4 md:p-6 lg:p-8 animate-fade-in" data-testid="sb-control">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Status Board Control
          </h1>
          <p className="text-slate-500 text-sm mt-0.5">Manage the projected status board display</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={load} className="rounded-sm" data-testid="refresh-btn">
            <RefreshCw className="w-3 h-3 mr-1" /> Refresh
          </Button>
          {canEdit && (
            <Button variant="outline" size="sm" onClick={handleSeed} className="rounded-sm" data-testid="seed-btn">
              Seed Sample Data
            </Button>
          )}
          <a href="/status-display" target="_blank" rel="noopener noreferrer">
            <Button size="sm" className="bg-[#00205B] rounded-sm" data-testid="open-display-btn">
              <Monitor className="w-3 h-3 mr-1" /> Open Display
              <ExternalLink className="w-3 h-3 ml-1" />
            </Button>
          </a>
        </div>
      </div>

      {/* Emergency Banner Control */}
      {canEmergency && (
        <div className={`mb-4 p-4 rounded-sm border ${settings.emergency_banner_active ? 'bg-red-50 border-red-300' : 'bg-slate-50 border-slate-200'}`} data-testid="emergency-control">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertTriangle className={`w-5 h-5 ${settings.emergency_banner_active ? 'text-red-600' : 'text-slate-400'}`} />
              <div>
                <div className="font-bold text-sm">Emergency Banner</div>
                <div className="text-xs text-slate-500">{settings.emergency_banner_active ? 'ACTIVE — Displaying on projector' : 'Inactive'}</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Input
                value={settings.emergency_banner_message || ''}
                onChange={(e) => setSettings(p => ({ ...p, emergency_banner_message: e.target.value }))}
                placeholder="Emergency message..."
                className="w-64 h-8 text-sm rounded-sm"
                data-testid="emergency-message-input"
              />
              <Button size="sm"
                className={`rounded-sm ${settings.emergency_banner_active ? 'bg-slate-600' : 'bg-red-600 hover:bg-red-700'}`}
                onClick={async () => {
                  const next = !settings.emergency_banner_active;
                  await updateSBEmergency({ active: next, message: settings.emergency_banner_message || '' });
                  setSettings(p => ({ ...p, emergency_banner_active: next }));
                  toast.success(next ? 'Emergency banner activated' : 'Emergency banner deactivated');
                }}
                data-testid="emergency-toggle-btn"
              >
                {settings.emergency_banner_active ? 'Deactivate' : 'Activate'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-4 overflow-x-auto pb-1">
        {TABS.map(t => (
          <button key={t.key} onClick={() => { setTab(t.key); if (t.key === 'audit') loadAudit(); }}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-sm text-xs font-medium whitespace-nowrap transition-colors ${
              tab === t.key ? 'bg-[#00205B] text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
            data-testid={`tab-${t.key}`}
          >
            <t.icon className="w-3.5 h-3.5" /> {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="bg-white border border-slate-200 rounded-sm">
        {/* FLIGHTS */}
        {tab === 'flights' && (
          <div className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-sm uppercase text-slate-700">Flight Status ({flights.length})</h2>
              {canEdit && <Button size="sm" className="bg-[#00205B] rounded-sm" onClick={() => openModal('flight')} data-testid="add-flight-btn"><Plus className="w-3 h-3 mr-1" />Add Flight</Button>}
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {flights.map(f => (
                <div key={f.id} className="border border-slate-200 rounded-sm p-3 flex gap-3" data-testid={`ctrl-flight-${f.id}`}>
                  <div className={`w-1.5 rounded-full shrink-0 ${SB_DOT[f.status_level] || 'bg-slate-400'}`} />
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-sm">{f.name}</div>
                    <div className="text-xs text-slate-500 flex items-center gap-1"><MapPin className="w-3 h-3" />{f.current_location || '—'}</div>
                    <div className="text-xs text-slate-500 flex items-center gap-1"><Activity className="w-3 h-3" />{f.current_status}</div>
                    {f.short_note && <div className="text-[10px] text-amber-600 mt-0.5">{f.short_note}</div>}
                    <div className="text-[10px] text-slate-400 mt-1">Updated by {f.updated_by}</div>
                  </div>
                  {canEdit && (
                    <div className="flex flex-col gap-1">
                      <button onClick={() => openModal('flight', f)} className="p-1 hover:bg-slate-100 rounded"><Edit2 className="w-3 h-3 text-slate-400" /></button>
                      <button onClick={async () => { await deleteSBFlight(f.id); load(); }} className="p-1 hover:bg-red-50 rounded"><Trash2 className="w-3 h-3 text-red-400" /></button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* SCHEDULE */}
        {tab === 'schedule' && (
          <div className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-sm uppercase text-slate-700">Schedule Events ({schedule.length})</h2>
              {canEdit && <Button size="sm" className="bg-[#00205B] rounded-sm" onClick={() => openModal('event')}><Plus className="w-3 h-3 mr-1" />Add Event</Button>}
            </div>
            <div className="space-y-2">
              {schedule.map(e => (
                <div key={e.id} className="flex items-center gap-4 border border-slate-200 rounded-sm p-3">
                  <div className="text-sm font-mono font-bold text-[#00205B] w-20">{e.start_time}{e.end_time ? `–${e.end_time}` : ''}</div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm truncate">{e.title}</div>
                    <div className="text-xs text-slate-500">{e.location}{e.section ? ` — ${e.section}` : ''}</div>
                  </div>
                  <span className={`text-[10px] px-2 py-0.5 rounded font-medium ${e.display_priority === 'high' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-500'}`}>{e.status}</span>
                  {canEdit && (
                    <div className="flex gap-1">
                      <button onClick={() => openModal('event', e)} className="p-1 hover:bg-slate-100 rounded"><Edit2 className="w-3 h-3 text-slate-400" /></button>
                      <button onClick={async () => { await deleteSBScheduleEvent(e.id); load(); }} className="p-1 hover:bg-red-50 rounded"><Trash2 className="w-3 h-3 text-red-400" /></button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ISSUES */}
        {tab === 'issues' && (
          <div className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-sm uppercase text-slate-700">Issues ({issues.length})</h2>
              {canEdit && <Button size="sm" className="bg-[#00205B] rounded-sm" onClick={() => openModal('issue')}><Plus className="w-3 h-3 mr-1" />Create Issue</Button>}
            </div>
            <div className="space-y-2">
              {issues.map(i => (
                <div key={i.id} className="flex items-center gap-3 border border-slate-200 rounded-sm p-3">
                  <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${SEV_BADGE[i.severity] || SEV_BADGE.medium}`}>{i.severity}</span>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm truncate">{i.title}</div>
                    <div className="text-xs text-slate-500">{i.assigned_section || 'Unassigned'} — {i.status}</div>
                  </div>
                  {canEdit && <button onClick={() => openModal('issue', i)} className="p-1 hover:bg-slate-100 rounded"><Edit2 className="w-3 h-3 text-slate-400" /></button>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ANNOUNCEMENTS */}
        {tab === 'announcements' && (
          <div className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-sm uppercase text-slate-700">Announcements ({announcements.length})</h2>
              {canEdit && <Button size="sm" className="bg-[#00205B] rounded-sm" onClick={() => openModal('announcement')}><Plus className="w-3 h-3 mr-1" />New Announcement</Button>}
            </div>
            <div className="space-y-2">
              {announcements.map(a => (
                <div key={a.id} className={`flex items-center gap-3 border rounded-sm p-3 ${a.active ? 'border-slate-200 bg-white' : 'border-slate-100 bg-slate-50 opacity-60'}`}>
                  <Megaphone className={`w-4 h-4 shrink-0 ${a.active ? 'text-amber-500' : 'text-slate-400'}`} />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm">{a.message}</div>
                    <div className="text-[10px] text-slate-400">{a.priority} — {a.active ? 'Active' : 'Inactive'} — by {a.created_by}</div>
                  </div>
                  {canEdit && (
                    <div className="flex gap-1">
                      <button onClick={() => openModal('announcement', a)} className="p-1 hover:bg-slate-100 rounded"><Edit2 className="w-3 h-3 text-slate-400" /></button>
                      <button onClick={async () => { await deleteSBAnnouncement(a.id); load(); }} className="p-1 hover:bg-red-50 rounded"><Trash2 className="w-3 h-3 text-red-400" /></button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* RESOURCES */}
        {tab === 'resources' && (
          <div className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-sm uppercase text-slate-700">Resources ({resources.length})</h2>
              {canEdit && <Button size="sm" className="bg-[#00205B] rounded-sm" onClick={() => openModal('resource')}><Plus className="w-3 h-3 mr-1" />Add Resource</Button>}
            </div>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {resources.map(r => (
                <div key={r.id} className="border border-slate-200 rounded-sm p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-500 font-medium uppercase">{r.type}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${r.status === 'available' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>{r.status}</span>
                  </div>
                  <div className="font-medium text-sm">{r.name}</div>
                  {r.assigned_to && <div className="text-xs text-slate-500">Assigned: {r.assigned_to}</div>}
                  {r.location && <div className="text-xs text-slate-500">Location: {r.location}</div>}
                  {canEdit && <button onClick={() => openModal('resource', r)} className="mt-1 p-1 hover:bg-slate-100 rounded"><Edit2 className="w-3 h-3 text-slate-400" /></button>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* SETTINGS */}
        {tab === 'settings' && (
          <div className="p-4 max-w-xl space-y-4">
            <h2 className="font-bold text-sm uppercase text-slate-700 mb-3">Display Settings</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs">Heat Category</Label>
                <Select value={settings.heat_category || 'green'} onValueChange={v => setSettings(p => ({ ...p, heat_category: v }))}>
                  <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue /></SelectTrigger>
                  <SelectContent>{HEAT_CATS.map(h => <SelectItem key={h} value={h}>{h.toUpperCase()}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Weather Condition</Label>
                <Input value={settings.weather_condition || ''} onChange={e => setSettings(p => ({ ...p, weather_condition: e.target.value }))} className="h-8 text-sm rounded-sm" />
              </div>
              <div>
                <Label className="text-xs">Encampment Day</Label>
                <Input value={settings.encampment_day || ''} onChange={e => setSettings(p => ({ ...p, encampment_day: e.target.value }))} className="h-8 text-sm rounded-sm" />
              </div>
              <div>
                <Label className="text-xs">Phase</Label>
                <Input value={settings.encampment_phase || ''} onChange={e => setSettings(p => ({ ...p, encampment_phase: e.target.value }))} className="h-8 text-sm rounded-sm" />
              </div>
              <div>
                <Label className="text-xs">Auto-Rotate Seconds</Label>
                <Input type="number" value={settings.auto_rotate_seconds || 25} onChange={e => setSettings(p => ({ ...p, auto_rotate_seconds: parseInt(e.target.value) || 25 }))} className="h-8 text-sm rounded-sm" />
              </div>
              <div className="flex items-end gap-3">
                <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={settings.auto_rotate_enabled ?? true} onChange={e => setSettings(p => ({ ...p, auto_rotate_enabled: e.target.checked }))} /> Auto-Rotate</label>
              </div>
            </div>
            <Button className="bg-[#00205B] rounded-sm" onClick={async () => {
              await updateSBSettings(settings); toast.success('Settings saved');
            }} data-testid="save-settings-btn">Save Settings</Button>
          </div>
        )}

        {/* AUDIT */}
        {tab === 'audit' && (
          <div className="p-4">
            <h2 className="font-bold text-sm uppercase text-slate-700 mb-3">Audit Log</h2>
            <div className="space-y-1 max-h-[500px] overflow-y-auto">
              {audit.map((a, i) => (
                <div key={a.id || `audit-${a.timestamp}-${i}`} className="flex items-center gap-3 text-xs border-b border-slate-100 py-2">
                  <span className="text-slate-400 font-mono w-36 shrink-0">{new Date(a.timestamp).toLocaleString()}</span>
                  <span className="font-medium text-slate-600 w-24 shrink-0">{a.action}</span>
                  <span className="text-slate-500 truncate flex-1">{a.details}</span>
                  <span className="text-slate-400">{a.user_name}</span>
                </div>
              ))}
              {audit.length === 0 && <div className="text-slate-400 text-sm text-center py-8">No audit entries yet</div>}
            </div>
          </div>
        )}
      </div>

      {/* ===== EDIT MODAL ===== */}
      <Dialog open={!!modal} onOpenChange={(o) => { if (!o) setModal(null); }}>
        <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-[#00205B] uppercase font-bold text-sm">
              {form.id ? 'Edit' : 'New'} {modal === 'event' ? 'Schedule Event' : modal}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 mt-2">
            {/* Flight fields */}
            {modal === 'flight' && (<>
              <div><Label className="text-xs">Flight Name *</Label><Input value={form.name||''} onChange={e=>F('name',e.target.value)} className="h-8 text-sm rounded-sm" data-testid="flight-name" /></div>
              <div><Label className="text-xs">Current Location</Label><Input value={form.current_location||''} onChange={e=>F('current_location',e.target.value)} className="h-8 text-sm rounded-sm" /></div>
              <div><Label className="text-xs">Current Status</Label><Input value={form.current_status||''} onChange={e=>F('current_status',e.target.value)} className="h-8 text-sm rounded-sm" /></div>
              <div><Label className="text-xs">Status Level</Label>
                <Select value={form.status_level||'green'} onValueChange={v=>F('status_level',v)}>
                  <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue /></SelectTrigger>
                  <SelectContent>{STATUS_LEVELS.map(l=><SelectItem key={l} value={l}><div className="flex items-center gap-2"><span className={`w-2 h-2 rounded-full ${SB_DOT[l]}`}/>{l.toUpperCase()}</div></SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label className="text-xs">Short Note</Label><Input value={form.short_note||''} onChange={e=>F('short_note',e.target.value)} className="h-8 text-sm rounded-sm" /></div>
            </>)}
            {/* Issue fields */}
            {modal === 'issue' && (<>
              <div><Label className="text-xs">Title *</Label><Input value={form.title||''} onChange={e=>F('title',e.target.value)} className="h-8 text-sm rounded-sm" /></div>
              <div><Label className="text-xs">Description</Label><Textarea value={form.description||''} onChange={e=>F('description',e.target.value)} rows={2} className="text-sm rounded-sm" /></div>
              <div><Label className="text-xs">Severity</Label>
                <Select value={form.severity||'medium'} onValueChange={v=>F('severity',v)}>
                  <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue /></SelectTrigger>
                  <SelectContent>{SEVERITIES.map(s=><SelectItem key={s} value={s}>{s.toUpperCase()}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label className="text-xs">Assigned Section</Label><Input value={form.assigned_section||''} onChange={e=>F('assigned_section',e.target.value)} className="h-8 text-sm rounded-sm" /></div>
              {form.id && <div><Label className="text-xs">Status</Label>
                <Select value={form.status||'open'} onValueChange={v=>F('status',v)}>
                  <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue /></SelectTrigger>
                  <SelectContent>{['open','in_progress','resolved','closed'].map(s=><SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                </Select>
              </div>}
            </>)}
            {/* Announcement fields */}
            {modal === 'announcement' && (<>
              <div><Label className="text-xs">Message *</Label><Textarea value={form.message||''} onChange={e=>F('message',e.target.value)} rows={2} className="text-sm rounded-sm" /></div>
              <div><Label className="text-xs">Priority</Label>
                <Select value={form.priority||'normal'} onValueChange={v=>F('priority',v)}>
                  <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue /></SelectTrigger>
                  <SelectContent>{['normal','high','urgent'].map(p=><SelectItem key={p} value={p}>{p.toUpperCase()}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.active ?? true} onChange={e=>F('active',e.target.checked)} /> Active</label></div>
            </>)}
            {/* Event fields */}
            {modal === 'event' && (<>
              <div><Label className="text-xs">Title *</Label><Input value={form.title||''} onChange={e=>F('title',e.target.value)} className="h-8 text-sm rounded-sm" /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><Label className="text-xs">Start Time</Label><Input value={form.start_time||''} onChange={e=>F('start_time',e.target.value)} className="h-8 text-sm rounded-sm" placeholder="e.g. 0800" /></div>
                <div><Label className="text-xs">End Time</Label><Input value={form.end_time||''} onChange={e=>F('end_time',e.target.value)} className="h-8 text-sm rounded-sm" placeholder="e.g. 0900" /></div>
              </div>
              <div><Label className="text-xs">Location</Label><Input value={form.location||''} onChange={e=>F('location',e.target.value)} className="h-8 text-sm rounded-sm" /></div>
              <div><Label className="text-xs">Section</Label><Input value={form.section||''} onChange={e=>F('section',e.target.value)} className="h-8 text-sm rounded-sm" /></div>
              <div><Label className="text-xs">Display Priority</Label>
                <Select value={form.display_priority||'normal'} onValueChange={v=>F('display_priority',v)}>
                  <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue /></SelectTrigger>
                  <SelectContent>{['normal','high'].map(p=><SelectItem key={p} value={p}>{p.toUpperCase()}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </>)}
            {/* Resource fields */}
            {modal === 'resource' && (<>
              <div><Label className="text-xs">Type</Label>
                <Select value={form.type||'radio'} onValueChange={v=>F('type',v)}>
                  <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue /></SelectTrigger>
                  <SelectContent>{RESOURCE_TYPES.map(t=><SelectItem key={t} value={t}>{t.toUpperCase()}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label className="text-xs">Name *</Label><Input value={form.name||''} onChange={e=>F('name',e.target.value)} className="h-8 text-sm rounded-sm" /></div>
              <div><Label className="text-xs">Status</Label>
                <Select value={form.status||'available'} onValueChange={v=>F('status',v)}>
                  <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue /></SelectTrigger>
                  <SelectContent>{RESOURCE_STATUSES.map(s=><SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label className="text-xs">Assigned To</Label><Input value={form.assigned_to||''} onChange={e=>F('assigned_to',e.target.value)} className="h-8 text-sm rounded-sm" /></div>
              <div><Label className="text-xs">Location</Label><Input value={form.location||''} onChange={e=>F('location',e.target.value)} className="h-8 text-sm rounded-sm" /></div>
              <div><Label className="text-xs">Notes</Label><Input value={form.notes||''} onChange={e=>F('notes',e.target.value)} className="h-8 text-sm rounded-sm" /></div>
            </>)}

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={() => setModal(null)} className="rounded-sm">Cancel</Button>
              <Button onClick={saveItem} className="bg-[#00205B] rounded-sm" data-testid="modal-save-btn">Save</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default StatusBoardControl;
