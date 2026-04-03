import React, { useState, useEffect, useCallback, useRef } from 'react';
import { getSBDisplay } from '../services/api';
import { AlertTriangle, Radio, Truck, Shield, Clock, MapPin, Megaphone, Calendar, Thermometer, Cloud, Activity, ChevronRight } from 'lucide-react';

const MODES = ['command', 'schedule', 'logistics', 'safety'];
const MODE_LABELS = { command: 'COMMAND DASHBOARD', schedule: 'SCHEDULE', logistics: 'LOGISTICS', safety: 'SAFETY OVERVIEW' };

const STATUS_COLORS = {
  green: 'bg-emerald-500', yellow: 'bg-amber-400', red: 'bg-red-500',
  blue: 'bg-sky-500', gray: 'bg-slate-500',
};
const SEVERITY_COLORS = { critical: 'text-red-400 bg-red-500/20', high: 'text-amber-400 bg-amber-500/20', medium: 'text-yellow-300 bg-yellow-500/15', low: 'text-slate-300 bg-slate-500/20' };
const HEAT_COLORS = { green: '#22c55e', yellow: '#eab308', red: '#ef4444', black: '#1e293b', white: '#f8fafc' };

const StatusBoardDisplay = () => {
  const [data, setData] = useState(null);
  const [currentMode, setCurrentMode] = useState(0);
  const [currentTime, setCurrentTime] = useState(new Date());
  const timerRef = useRef(null);
  const rotateRef = useRef(null);

  const fetchData = useCallback(async () => {
    try {
      const d = await getSBDisplay();
      setData(d);
    } catch (error) { console.error('Failed to load status board data:', error); }
  }, []);

  // Data refresh every 15s
  useEffect(() => {
    fetchData();
    const i = setInterval(fetchData, 15000);
    return () => clearInterval(i);
  }, [fetchData]);

  // Clock
  useEffect(() => {
    timerRef.current = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timerRef.current);
  }, []);

  // Auto-rotate
  useEffect(() => {
    if (!data?.settings?.auto_rotate_enabled) return;
    const sec = (data?.settings?.auto_rotate_seconds || 25) * 1000;
    rotateRef.current = setInterval(() => setCurrentMode(p => (p + 1) % MODES.length), sec);
    return () => clearInterval(rotateRef.current);
  }, [data?.settings?.auto_rotate_enabled, data?.settings?.auto_rotate_seconds]);

  // Keyboard nav
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'ArrowRight' || e.key === ' ') setCurrentMode(p => (p + 1) % MODES.length);
      if (e.key === 'ArrowLeft') setCurrentMode(p => (p - 1 + MODES.length) % MODES.length);
      if (e.key === 'f' || e.key === 'F') document.documentElement.requestFullscreen?.();
      if (e.key === 'Escape') document.exitFullscreen?.();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  if (!data) return (
    <div className="fixed inset-0 bg-slate-950 flex items-center justify-center">
      <div className="text-slate-400 text-2xl animate-pulse">Loading Status Board...</div>
    </div>
  );

  const s = data.settings;
  const mode = MODES[currentMode];
  const emergency = s.emergency_banner_active;

  return (
    <div className="fixed inset-0 bg-slate-950 text-white overflow-hidden flex flex-col" data-testid="sb-display">
      {/* EMERGENCY BANNER */}
      {emergency && (
        <div className="bg-red-600 animate-pulse px-6 py-4 text-center" data-testid="emergency-banner">
          <div className="flex items-center justify-center gap-4">
            <AlertTriangle className="w-10 h-10" />
            <span className="text-3xl font-black uppercase tracking-wider">{s.emergency_banner_message || 'EMERGENCY'}</span>
            <AlertTriangle className="w-10 h-10" />
          </div>
        </div>
      )}

      {/* TOP BAR */}
      <div className="bg-slate-900 border-b border-slate-700/50 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3">
            <Shield className="w-7 h-7 text-sky-400" />
            <div>
              <div className="text-lg font-black uppercase tracking-wider text-sky-400">TNWG Encampment</div>
              <div className="text-xs text-slate-400 uppercase tracking-wide">{s.encampment_day} &mdash; {s.encampment_phase}</div>
            </div>
          </div>
          <div className="h-8 w-px bg-slate-700" />
          <div className="flex items-center gap-2">
            <Thermometer className="w-5 h-5" style={{ color: HEAT_COLORS[s.heat_category] || '#22c55e' }} />
            <span className="text-sm font-bold uppercase" style={{ color: HEAT_COLORS[s.heat_category] || '#22c55e' }}>
              Heat Cat: {s.heat_category?.toUpperCase()}
            </span>
          </div>
          <div className="flex items-center gap-2 text-slate-300">
            <Cloud className="w-5 h-5" />
            <span className="text-sm">{s.weather_condition}</span>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex gap-1">
            {MODES.map((m, i) => (
              <button key={m} onClick={() => setCurrentMode(i)}
                className={`px-3 py-1 rounded text-xs font-bold uppercase tracking-wide transition-colors ${i === currentMode ? 'bg-sky-600 text-white' : 'bg-slate-800 text-slate-500 hover:text-slate-300'}`}>
                {m}
              </button>
            ))}
          </div>
          <div className="text-right">
            <div className="text-3xl font-mono font-bold tabular-nums text-white">
              {currentTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
            </div>
            <div className="text-xs text-slate-400">{currentTime.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}</div>
          </div>
        </div>
      </div>

      {/* MODE TITLE */}
      <div className="bg-slate-900/50 px-6 py-1.5 border-b border-slate-800 flex items-center justify-between">
        <div className="text-xs font-bold uppercase tracking-[0.2em] text-sky-400/70">{MODE_LABELS[mode]}</div>
        <div className="text-[10px] text-slate-600">Updated {new Date(data.last_updated).toLocaleTimeString()} &bull; Auto-refresh 15s{s.auto_rotate_enabled ? ` &bull; Rotating ${s.auto_rotate_seconds}s` : ''}</div>
      </div>

      {/* MAIN CONTENT */}
      <div className="flex-1 overflow-hidden p-4">
        {mode === 'command' && <CommandMode data={data} />}
        {mode === 'schedule' && <ScheduleMode data={data} />}
        {mode === 'logistics' && <LogisticsMode data={data} />}
        {mode === 'safety' && <SafetyMode data={data} />}
      </div>

      {/* FOOTER - Announcements ticker */}
      {s.show_footer && data.announcements.length > 0 && (
        <div className="bg-slate-900 border-t border-slate-700/50 px-6 py-2.5 shrink-0">
          <div className="flex items-center gap-4">
            <Megaphone className="w-5 h-5 text-amber-400 shrink-0" />
            <div className="overflow-hidden flex-1">
              <div className="animate-marquee whitespace-nowrap text-sm text-slate-300">
                {data.announcements.map((a, i) => (
                  <span key={a.id}>{a.message}{i < data.announcements.length - 1 ? '  ///  ' : ''}</span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

/* ===================== COMMAND DASHBOARD MODE ===================== */
const CommandMode = ({ data }) => (
  <div className="h-full grid grid-cols-[1fr_340px] gap-4">
    {/* Left: Flight Status Cards */}
    <div className="space-y-3 overflow-y-auto pr-2">
      <div className="grid grid-cols-2 xl:grid-cols-3 gap-3">
        {data.flights.map(f => (
          <div key={f.id} className="bg-slate-800/80 rounded-lg border border-slate-700/50 p-4 flex gap-3" data-testid={`flight-card-${f.id}`}>
            <div className={`w-2 rounded-full shrink-0 ${STATUS_COLORS[f.status_level] || 'bg-slate-500'}`} />
            <div className="flex-1 min-w-0">
              <div className="text-xl font-black uppercase tracking-wide text-white">{f.name}</div>
              <div className="flex items-center gap-1.5 mt-1 text-slate-300">
                <MapPin className="w-4 h-4 text-sky-400 shrink-0" />
                <span className="text-base font-medium truncate">{f.current_location || '—'}</span>
              </div>
              <div className="flex items-center gap-1.5 mt-0.5 text-slate-400">
                <Activity className="w-4 h-4 shrink-0" />
                <span className="text-sm truncate">{f.current_status || '—'}</span>
              </div>
              {f.short_note && <div className="mt-1 text-xs text-amber-400/80 truncate">{f.short_note}</div>}
            </div>
          </div>
        ))}
      </div>
      {/* Upcoming schedule below flights */}
      <div className="bg-slate-800/50 rounded-lg border border-slate-700/30 p-4">
        <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
          <Calendar className="w-4 h-4" /> Upcoming Events
        </div>
        <div className="space-y-2">
          {data.schedule.slice(0, 4).map(e => (
            <div key={e.id} className="flex items-center gap-4">
              <div className="text-lg font-mono font-bold text-sky-400 w-20 shrink-0">{e.start_time}</div>
              <div className="flex-1 min-w-0">
                <div className="text-base font-semibold text-white truncate">{e.title}</div>
                <div className="text-xs text-slate-400">{e.location}{e.section ? ` — ${e.section}` : ''}</div>
              </div>
              <ChevronRight className="w-4 h-4 text-slate-600" />
            </div>
          ))}
        </div>
      </div>
    </div>
    {/* Right: Issues */}
    <div className="bg-slate-800/50 rounded-lg border border-slate-700/30 p-4 overflow-y-auto">
      <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
        <AlertTriangle className="w-4 h-4" /> Active Issues ({data.issues.length})
      </div>
      {data.issues.length === 0 ? (
        <div className="text-center text-slate-600 py-8 text-sm">No active issues</div>
      ) : (
        <div className="space-y-3">
          {data.issues.map(issue => (
            <div key={issue.id} className="bg-slate-900/60 rounded-lg p-3 border border-slate-700/30">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${SEVERITY_COLORS[issue.severity] || SEVERITY_COLORS.medium}`}>
                  {issue.severity}
                </span>
                <span className="text-[10px] uppercase text-slate-500">{issue.status}</span>
              </div>
              <div className="text-sm font-semibold text-white">{issue.title}</div>
              {issue.assigned_section && <div className="text-xs text-slate-400 mt-0.5">Assigned: {issue.assigned_section}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  </div>
);

/* ===================== SCHEDULE MODE ===================== */
const ScheduleMode = ({ data }) => (
  <div className="h-full overflow-y-auto">
    <div className="max-w-4xl mx-auto space-y-2">
      {data.schedule.length === 0 ? (
        <div className="text-center text-slate-500 text-xl py-20">No scheduled events</div>
      ) : (
        data.schedule.map((e, i) => (
          <div key={e.id} className={`flex items-center gap-6 p-5 rounded-lg border ${i === 0 ? 'bg-sky-900/30 border-sky-700/50' : 'bg-slate-800/50 border-slate-700/30'}`}>
            <div className="text-center w-24 shrink-0">
              <div className={`text-3xl font-mono font-black ${i === 0 ? 'text-sky-400' : 'text-white'}`}>{e.start_time}</div>
              {e.end_time && <div className="text-sm text-slate-500">{e.end_time}</div>}
            </div>
            <div className="h-12 w-px bg-slate-700" />
            <div className="flex-1 min-w-0">
              <div className={`text-2xl font-bold truncate ${i === 0 ? 'text-sky-300' : 'text-white'}`}>{e.title}</div>
              <div className="flex items-center gap-4 mt-1">
                {e.location && <span className="flex items-center gap-1 text-sm text-slate-400"><MapPin className="w-4 h-4" />{e.location}</span>}
                {e.section && <span className="text-sm text-slate-500">{e.section}</span>}
              </div>
            </div>
            {e.display_priority === 'high' && <div className="text-amber-400 text-xs font-bold uppercase px-2 py-1 bg-amber-500/15 rounded">Priority</div>}
          </div>
        ))
      )}
    </div>
  </div>
);

/* ===================== LOGISTICS MODE ===================== */
const LogisticsMode = ({ data }) => {
  const radios = data.resources.filter(r => r.type === 'radio');
  const vehicles = data.resources.filter(r => r.type === 'vehicle');
  const equipment = data.resources.filter(r => r.type === 'equipment');
  const checkedOut = radios.filter(r => r.status === 'checked_out');
  const vehiclesInUse = vehicles.filter(r => r.status === 'in_use');

  return (
    <div className="h-full grid grid-cols-3 gap-4">
      {/* Radios */}
      <div className="bg-slate-800/50 rounded-lg border border-slate-700/30 p-4 overflow-y-auto">
        <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
          <Radio className="w-4 h-4" /> Radios ({checkedOut.length} / {radios.length} out)
        </div>
        <div className="space-y-2">
          {radios.map(r => (
            <div key={r.id} className="flex items-center justify-between bg-slate-900/50 rounded p-3">
              <div>
                <div className="text-base font-semibold text-white">{r.name}</div>
                {r.assigned_to && <div className="text-xs text-slate-400">{r.assigned_to}</div>}
              </div>
              <span className={`text-xs font-bold uppercase px-2 py-1 rounded ${r.status === 'available' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}`}>
                {r.status === 'checked_out' ? 'OUT' : r.status === 'available' ? 'AVAIL' : r.status?.toUpperCase()}
              </span>
            </div>
          ))}
          {radios.length === 0 && <div className="text-slate-600 text-sm text-center py-4">No radios tracked</div>}
        </div>
      </div>
      {/* Vehicles */}
      <div className="bg-slate-800/50 rounded-lg border border-slate-700/30 p-4 overflow-y-auto">
        <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
          <Truck className="w-4 h-4" /> Vehicles ({vehiclesInUse.length} / {vehicles.length} in use)
        </div>
        <div className="space-y-2">
          {vehicles.map(r => (
            <div key={r.id} className="flex items-center justify-between bg-slate-900/50 rounded p-3">
              <div>
                <div className="text-base font-semibold text-white">{r.name}</div>
                <div className="text-xs text-slate-400">{r.assigned_to || '—'} {r.notes ? `• ${r.notes}` : ''}</div>
              </div>
              <span className={`text-xs font-bold uppercase px-2 py-1 rounded ${r.status === 'available' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-sky-500/20 text-sky-400'}`}>
                {r.status === 'in_use' ? 'IN USE' : r.status?.toUpperCase()}
              </span>
            </div>
          ))}
          {vehicles.length === 0 && <div className="text-slate-600 text-sm text-center py-4">No vehicles tracked</div>}
        </div>
      </div>
      {/* Equipment & Open Requests */}
      <div className="bg-slate-800/50 rounded-lg border border-slate-700/30 p-4 overflow-y-auto">
        <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
          <Activity className="w-4 h-4" /> Equipment & Issues
        </div>
        <div className="space-y-2">
          {equipment.map(r => (
            <div key={r.id} className="flex items-center justify-between bg-slate-900/50 rounded p-3">
              <div>
                <div className="text-sm font-semibold text-white">{r.name}</div>
                <div className="text-xs text-slate-400">{r.location}</div>
              </div>
              <span className={`text-xs font-bold uppercase px-2 py-1 rounded ${r.status === 'available' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-sky-500/20 text-sky-400'}`}>
                {r.status?.toUpperCase()}
              </span>
            </div>
          ))}
          {data.issues.filter(i => i.assigned_section === 'Logistics').map(issue => (
            <div key={issue.id} className="bg-red-900/20 border border-red-800/30 rounded p-3">
              <div className="text-xs text-red-400 font-bold uppercase">{issue.severity} ISSUE</div>
              <div className="text-sm text-white mt-0.5">{issue.title}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

/* ===================== SAFETY MODE ===================== */
const SafetyMode = ({ data }) => {
  const s = data.settings;
  const safetyIssues = data.issues.filter(i => ['Safety', 'Health Services'].includes(i.assigned_section));

  return (
    <div className="h-full flex gap-6 items-stretch">
      {/* Heat Category - big display */}
      <div className="flex-1 flex flex-col items-center justify-center bg-slate-800/50 rounded-lg border border-slate-700/30">
        <div className="text-sm font-bold uppercase tracking-[0.3em] text-slate-500 mb-4">HEAT CATEGORY</div>
        <div className="w-48 h-48 rounded-full flex items-center justify-center border-4"
          style={{ backgroundColor: `${HEAT_COLORS[s.heat_category]}20`, borderColor: HEAT_COLORS[s.heat_category] }}>
          <span className="text-6xl font-black uppercase" style={{ color: HEAT_COLORS[s.heat_category] }}>
            {s.heat_category?.toUpperCase()}
          </span>
        </div>
        <div className="mt-6 text-lg text-slate-300 flex items-center gap-2">
          <Cloud className="w-5 h-5" /> {s.weather_condition}
        </div>
        <div className="mt-8 bg-sky-900/30 border border-sky-700/30 rounded-lg px-8 py-4 text-center max-w-md">
          <div className="text-sky-400 font-bold uppercase text-sm mb-1">Hydration Reminder</div>
          <div className="text-slate-300 text-base">Drink water regularly. Monitor for heat-related symptoms.</div>
        </div>
      </div>
      {/* Safety notices and incident summary */}
      <div className="w-96 flex flex-col gap-4">
        <div className="bg-slate-800/50 rounded-lg border border-slate-700/30 p-5 flex-1 overflow-y-auto">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">Safety Notices</div>
          {data.announcements.filter(a => a.priority === 'urgent' || a.priority === 'high').length === 0 && safetyIssues.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-slate-600">
              <Shield className="w-12 h-12 mb-2" />
              <div className="text-sm">No active safety notices</div>
            </div>
          ) : (
            <div className="space-y-2">
              {data.announcements.filter(a => a.priority === 'urgent' || a.priority === 'high').map(a => (
                <div key={a.id} className="bg-amber-900/20 border border-amber-800/30 rounded p-3 text-sm text-amber-300">{a.message}</div>
              ))}
              {safetyIssues.map(i => (
                <div key={i.id} className="bg-red-900/20 border border-red-800/30 rounded p-3">
                  <div className="text-xs text-red-400 font-bold uppercase">{i.severity}</div>
                  <div className="text-sm text-white">{i.title}</div>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="bg-slate-800/50 rounded-lg border border-slate-700/30 p-5">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Incident Summary</div>
          <div className="grid grid-cols-2 gap-4 text-center">
            <div>
              <div className="text-4xl font-black text-white">{data.issues.filter(i => i.status === 'open').length}</div>
              <div className="text-xs text-slate-500 uppercase">Open Issues</div>
            </div>
            <div>
              <div className="text-4xl font-black text-emerald-400">{data.issues.filter(i => i.status === 'resolved').length}</div>
              <div className="text-xs text-slate-500 uppercase">Resolved</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Add marquee animation via style
const style = document.createElement('style');
style.textContent = `
  @keyframes marquee { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
  .animate-marquee { animation: marquee 30s linear infinite; }
`;
if (!document.querySelector('[data-sb-style]')) { style.setAttribute('data-sb-style', ''); document.head.appendChild(style); }

export default StatusBoardDisplay;
