import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { toast } from 'sonner';
import {
  ClipboardList, Settings as SettingsIcon, BarChart3, Pencil, Calendar,
  Users as UsersIcon, TrendingUp, Save, RotateCcw, AlertTriangle,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import {
  getInspectionTypes, getInspectionSettings, updateInspectionSettings,
  getInspectionDashboard, getInspectionScores, upsertInspectionScores,
  setFlightMeritPoints, getParticipants,
} from '../services/api';
import { useAuth } from '../context/AuthContext';

/* ── Constants ────────────────────────────────── */
const ALLOWED_ROLES = ['exec_cadre', 'executive_staff', 'plans_programs', 'commander', 'dcp'];

const TYPE_LABEL = {
  dorm_uniform:        'Dorm & Uniform',
  dorm_uniform_repeat: 'Dorm & Uniform (Repeat)',
  drill:               'Drill',
  daily_sports:        'Daily Sports',
  knowledge:           'Knowledge',
  app:                 'App',
};
const FIELD_LABEL = {
  // Dorm & Uniform
  personal_appearance: 'Personal Appearance', garments: 'Garments',
  accoutrements: 'Accoutrements', footwear: 'Footwear',
  shirt_fold: 'Shirt Fold', socks_fold: 'Socks Fold',
  bunks: 'Bunks', barrack_cleanliness: 'Barrack Cleanliness',
  // Drill
  fall_in: 'FALL IN', dress_right_dress: 'Dress Right, DRESS',
  ready_front: 'Ready, FRONT', at_ease: 'AT EASE',
  flight_attention: 'Flight, ATTENTION', present_arms: 'Present, ARMS',
  order_arms: 'Order, ARMS', left_face: 'Left, FACE',
  right_face: 'Right, FACE', about_face: 'About, FACE',
  parade_rest: 'Parade, REST', hand_salute: 'Hand, SALUTE',
  forward_march: 'Forward, MARCH', incline_to_the_left: 'INCLINE TO THE LEFT',
  incline_to_the_right: 'INCLINE TO THE RIGHT', flight_halt: 'Flight, HALT',
  column_of_files: 'Column of Files (R), Column right MARCH', fall_out: 'FALL OUT',
  // Sports
  sports_score: 'Sports Score (0–20)',
};
for (let i = 1; i <= 9; i++) FIELD_LABEL[`q${i}`] = `Question #${i}`;

const FLIGHTS = ['alpha', 'bravo', 'charlie', 'delta', 'echo', 'foxtrot'];
const FLIGHT_TO_SQ = { alpha: '6th_cts', bravo: '6th_cts', charlie: '21st_cts',
  delta: '21st_cts', echo: '22nd_cts', foxtrot: '22nd_cts' };
const SQ_FLIGHTS = { '6th_cts': ['alpha', 'bravo'], '21st_cts': ['charlie', 'delta'], '22nd_cts': ['echo', 'foxtrot'] };
const SQ_LABEL = { '6th_cts': '6th CTS', '21st_cts': '21st CTS', '22nd_cts': '22nd CTS' };
const DAYS = [1, 2, 3, 4, 5, 6];
const fmtPct = (v) => (v == null ? '—' : `${(v * 100).toFixed(1)}%`);
const fmtPts = (v) => (v == null ? '—' : v.toFixed(1));
const sign = (v) => (v > 0 ? `+${v.toFixed(1)}` : v.toFixed(1));

/* ── Page ─────────────────────────────────────── */
const InspectionsPage = () => {
  const { user } = useAuth();
  const allowed = ALLOWED_ROLES.includes(user?.role);

  const [tab, setTab] = useState('dashboard');
  const [typesMeta, setTypesMeta] = useState(null);
  const [settings, setSettings] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadAll = useCallback(async () => {
    if (!allowed) { setLoading(false); return; }
    try {
      const [m, s, d, ps] = await Promise.all([
        getInspectionTypes(), getInspectionSettings(),
        getInspectionDashboard(), getParticipants(),
      ]);
      setTypesMeta(m); setSettings(s); setDashboard(d); setParticipants(ps || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to load Inspections');
    } finally { setLoading(false); }
  }, [allowed]);

  useEffect(() => { loadAll(); }, [loadAll]);

  if (!allowed) {
    return (
      <div className="p-8 max-w-xl mx-auto text-center" data-testid="inspections-denied">
        <AlertTriangle className="w-10 h-10 text-amber-500 mx-auto mb-3" />
        <h2 className="text-lg font-bold text-slate-800 mb-1">Access restricted</h2>
        <p className="text-sm text-slate-500">
          Inspections & Points is available only to Exec Cadre, Exec Staff,
          and Plans &amp; Programs (cadre or staff).
        </p>
      </div>
    );
  }

  if (loading || !settings || !typesMeta || !dashboard) {
    return <div className="p-6 text-sm text-slate-400">Loading inspections…</div>;
  }

  const tabs = [
    { id: 'dashboard',   label: 'Dashboard',     Icon: BarChart3 },
    { id: 'enter',       label: 'Enter Scores',  Icon: Pencil },
    { id: 'weekly',      label: 'Weekly Totals', Icon: TrendingUp },
    { id: 'students',    label: 'Student Points', Icon: UsersIcon },
    { id: 'settings',    label: 'Settings',      Icon: SettingsIcon },
  ];

  return (
    <div className="p-3 lg:p-6" data-testid="inspections-page">
      <div className="flex items-center gap-3 mb-4">
        <ClipboardList className="w-6 h-6 text-[#00205B]" />
        <h1 className="text-lg lg:text-xl font-black uppercase tracking-tight text-[#00205B]"
            style={{ fontFamily: 'Chivo, sans-serif' }}>
          Inspections &amp; Points
        </h1>
      </div>
      <div className="flex flex-wrap gap-1 mb-4 border-b border-slate-200">
        {tabs.map(({ id, label, Icon }) => (
          <button key={id} onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-semibold uppercase
              border-b-2 transition-colors -mb-px ${
              tab === id ? 'border-[#00205B] text-[#00205B]'
                         : 'border-transparent text-slate-500 hover:text-slate-800'}`}
            data-testid={`tab-${id}`}>
            <Icon className="w-3.5 h-3.5" />{label}
          </button>
        ))}
      </div>

      {tab === 'dashboard' && <DashboardTab dashboard={dashboard} settings={settings} reload={loadAll} />}
      {tab === 'enter'     && <EnterScoresTab typesMeta={typesMeta} settings={settings} participants={participants} reload={loadAll} />}
      {tab === 'weekly'    && <WeeklyTotalsTab dashboard={dashboard} reload={loadAll} />}
      {tab === 'students'  && <StudentPointsTab participants={participants} />}
      {tab === 'settings'  && <SettingsTab settings={settings} typesMeta={typesMeta} reload={loadAll} />}
    </div>
  );
};

/* ── Dashboard ────────────────────────────────── */
const DashboardTab = ({ dashboard, settings }) => {
  const enabledDays = DAYS.filter(d => (settings.day_inspections[String(d)] || []).length > 0);
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <StatCard label="Days Active"     value={enabledDays.length} />
        <StatCard label="Merit Points"    value={dashboard.include_merit_points ? 'Included' : 'Excluded'} />
        <StatCard label="Leading Flight"  value={leader(dashboard.weekly_totals)} />
      </div>
      {enabledDays.map(day => (
        <DayTotalsCard key={day} day={day} dashboard={dashboard} />
      ))}
    </div>
  );
};

const leader = (totals) => {
  const entries = Object.entries(totals).sort((a, b) => b[1] - a[1]);
  if (!entries[0] || entries[0][1] === 0) return '—';
  return `${entries[0][0].charAt(0).toUpperCase() + entries[0][0].slice(1)} (${entries[0][1].toFixed(1)})`;
};

const StatCard = ({ label, value }) => (
  <div className="bg-white border border-slate-200 rounded-lg p-3" data-testid={`stat-${label}`}>
    <div className="text-[10px] uppercase tracking-widest text-slate-400">{label}</div>
    <div className="text-lg font-bold text-[#00205B] mt-1">{value}</div>
  </div>
);

const DayTotalsCard = ({ day, dashboard }) => {
  const dayData = dashboard.by_day[String(day)] || dashboard.by_day[day];
  if (!dayData) return null;
  return (
    <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
      <div className="px-4 py-2 bg-slate-50 border-b border-slate-200 flex items-center gap-2">
        <Calendar className="w-4 h-4 text-[#00205B]" />
        <span className="font-bold text-[#00205B] text-sm">Day {day} TOTALS</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-slate-50 text-slate-500 uppercase text-[10px]">
            <tr>
              <th className="px-2 py-1.5 text-left">CTS</th>
              <th className="px-2 py-1.5 text-left">Flight</th>
              {Object.keys(dayData.flights[0]?.per_inspection || {}).map(t => (
                <th key={t} className="px-2 py-1.5 text-center">{TYPE_LABEL[t] || t}</th>
              ))}
              <th className="px-2 py-1.5 text-center">CTF Avg</th>
              <th className="px-2 py-1.5 text-center">CTF Pts</th>
              <th className="px-2 py-1.5 text-center">CTS Avg</th>
              <th className="px-2 py-1.5 text-center">CTS Pts</th>
            </tr>
          </thead>
          <tbody>
            {dayData.flights.map((r, i) => {
              const sq = FLIGHT_TO_SQ[r.flight];
              const isFirstInSq = SQ_FLIGHTS[sq][0] === r.flight;
              const cts = dayData.squadrons.find(c => c.squadron === sq);
              return (
                <tr key={r.flight} className={i % 2 ? 'bg-slate-50/40' : ''}>
                  <td className="px-2 py-1.5 font-semibold text-slate-700">
                    {isFirstInSq ? SQ_LABEL[sq] : ''}
                  </td>
                  <td className="px-2 py-1.5 capitalize">{r.flight}</td>
                  {Object.entries(r.per_inspection).map(([t, info]) => (
                    <td key={t} className="px-2 py-1.5 text-center">
                      <div>{fmtPct(info.percent)}</div>
                      <div className="text-[10px] text-slate-400">+{fmtPts(info.points)}</div>
                    </td>
                  ))}
                  <td className="px-2 py-1.5 text-center font-medium">{fmtPct(r.ctf_average)}</td>
                  <td className="px-2 py-1.5 text-center font-bold text-[#00205B]">{fmtPts(r.ctf_points)}</td>
                  {isFirstInSq ? (
                    <>
                      <td rowSpan={2} className="px-2 py-1.5 text-center bg-emerald-50/40 font-medium">{fmtPct(cts?.cts_average)}</td>
                      <td rowSpan={2} className="px-2 py-1.5 text-center bg-emerald-50/40 font-bold text-emerald-700">{fmtPts(cts?.cts_points)}</td>
                    </>
                  ) : null}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

/* ── Enter Scores ─────────────────────────────── */
const EnterScoresTab = ({ typesMeta, settings, participants, reload }) => {
  const [day, setDay] = useState(2);
  const [flight, setFlight] = useState('alpha');
  const [type, setType] = useState('knowledge');
  const [rows, setRows] = useState([]);
  const [fieldScores, setFieldScores] = useState({});
  const [saving, setSaving] = useState(false);

  const enabledTypes = settings.day_inspections[String(day)] || [];
  const isPerCadet = typesMeta.per_cadet_types.includes(type);
  const fields = typesMeta.fields[type] || [];

  // Reset type if it's not enabled for the selected day
  useEffect(() => {
    if (!enabledTypes.includes(type) && enabledTypes.length > 0) setType(enabledTypes[0]);
  }, [day, enabledTypes, type]);

  const flightCadets = useMemo(() =>
    participants.filter(p =>
      (p.flight || '').toLowerCase() === flight
      && ['student', 'basic_student', 'advanced_student'].includes((p.participant_type || '').toLowerCase())
      && !p.is_removed
    ).sort((a, b) => {
      const al = (a.last_name || '').toLowerCase();
      const bl = (b.last_name || '').toLowerCase();
      if (al !== bl) return al < bl ? -1 : 1;
      return (a.first_name || '').toLowerCase().localeCompare((b.first_name || '').toLowerCase());
    }),
  [participants, flight]);

  const loadExisting = useCallback(async () => {
    if (!day || !flight || !type) return;
    try {
      const scores = await getInspectionScores({ day, flight, inspectionType: type });
      if (isPerCadet) {
        // Map existing scores → flightCadets list
        const byId = Object.fromEntries(scores.map(s => [s.cadet_participant_id, s]));
        setRows(flightCadets.map(c => {
          const ex = byId[c.id];
          return {
            cadet_participant_id: c.id,
            cadet_name: `${c.last_name}, ${c.first_name?.[0] || ''}`,
            field_scores: ex?.field_scores || {},
            absent: !!ex?.absent,
          };
        }));
      } else {
        const r = scores[0];
        setFieldScores(r?.field_scores || {});
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Load failed');
    }
  }, [day, flight, type, isPerCadet, flightCadets]);

  useEffect(() => { loadExisting(); }, [loadExisting]);

  const updateRowField = (idx, field, value) => {
    setRows(prev => {
      const next = [...prev];
      next[idx] = { ...next[idx], field_scores: { ...(next[idx].field_scores || {}), [field]: value === '' ? '' : Number(value) } };
      return next;
    });
  };
  const toggleAbsent = (idx) => {
    setRows(prev => {
      const next = [...prev];
      next[idx] = { ...next[idx], absent: !next[idx].absent };
      return next;
    });
  };

  const save = async () => {
    setSaving(true);
    try {
      let payload;
      if (isPerCadet) {
        // Strip empty rows + clean field values
        const clean = rows.map(r => ({
          cadet_participant_id: r.cadet_participant_id,
          cadet_name: r.cadet_name,
          absent: r.absent,
          field_scores: Object.fromEntries(
            Object.entries(r.field_scores || {})
              .filter(([, v]) => v !== '' && v !== null && !Number.isNaN(Number(v)))
              .map(([k, v]) => [k, Number(v)]),
          ),
        }));
        payload = { day, flight, inspection_type: type, cadet_scores: clean };
      } else {
        const clean = Object.fromEntries(
          Object.entries(fieldScores)
            .filter(([, v]) => v !== '' && v !== null && !Number.isNaN(Number(v)))
            .map(([k, v]) => [k, Number(v)]),
        );
        payload = { day, flight, inspection_type: type, field_scores: clean };
      }
      const res = await upsertInspectionScores(payload);
      toast.success(`Saved ${res.inserted} record(s)`);
      reload();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Save failed');
    } finally { setSaving(false); }
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-white border border-slate-200 rounded-lg p-3">
        <div>
          <Label className="text-[10px] uppercase tracking-widest text-slate-400">Day</Label>
          <select value={day} onChange={e => setDay(Number(e.target.value))}
            className="mt-1 w-full h-9 border border-slate-200 rounded-sm px-2 text-sm" data-testid="day-select">
            {DAYS.map(d => <option key={d} value={d}>Day {d}</option>)}
          </select>
        </div>
        <div>
          <Label className="text-[10px] uppercase tracking-widest text-slate-400">Flight</Label>
          <select value={flight} onChange={e => setFlight(e.target.value)}
            className="mt-1 w-full h-9 border border-slate-200 rounded-sm px-2 text-sm capitalize" data-testid="flight-select">
            {FLIGHTS.map(f => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
        <div>
          <Label className="text-[10px] uppercase tracking-widest text-slate-400">Inspection</Label>
          <select value={type} onChange={e => setType(e.target.value)}
            disabled={enabledTypes.length === 0}
            className="mt-1 w-full h-9 border border-slate-200 rounded-sm px-2 text-sm" data-testid="type-select">
            {enabledTypes.length === 0
              ? <option>(none enabled for Day {day})</option>
              : enabledTypes.map(t => <option key={t} value={t}>{TYPE_LABEL[t] || t}</option>)}
          </select>
        </div>
        <div className="flex items-end">
          <Button onClick={save} disabled={saving || enabledTypes.length === 0}
                  className="w-full bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="save-scores-btn">
            <Save className="w-3.5 h-3.5 mr-1.5" /> {saving ? 'Saving…' : 'Save'}
          </Button>
        </div>
      </div>

      {enabledTypes.length === 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-sm p-3 text-xs text-amber-700">
          No inspections enabled for Day {day}. Add them in Settings.
        </div>
      )}

      {enabledTypes.length > 0 && isPerCadet && (
        <div className="bg-white border border-slate-200 rounded-lg overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-slate-50 text-slate-500 uppercase text-[10px]">
              <tr>
                <th className="px-2 py-1.5 text-left">Cadet</th>
                <th className="px-2 py-1.5 text-center">Absent</th>
                {fields.map(f => (
                  <th key={f} className="px-2 py-1.5 text-center">{FIELD_LABEL[f] || f}</th>
                ))}
                <th className="px-2 py-1.5 text-center">Total</th>
                <th className="px-2 py-1.5 text-center">% Correct</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr><td colSpan={fields.length + 4} className="px-2 py-4 text-center text-slate-400 italic">
                  No cadets assigned to {flight}.
                </td></tr>
              )}
              {rows.map((r, idx) => {
                const total = fields.reduce((s, f) => {
                  const v = r.field_scores?.[f];
                  return s + (typeof v === 'number' && !Number.isNaN(v) ? v : 0);
                }, 0);
                const maxTotal = typesMeta.max_total[type] || 1;
                const pct = r.absent ? null : total / maxTotal;
                return (
                  <tr key={r.cadet_participant_id} className={r.absent ? 'opacity-40' : (idx % 2 ? 'bg-slate-50/40' : '')}>
                    <td className="px-2 py-1.5 font-medium text-slate-700 whitespace-nowrap">{r.cadet_name}</td>
                    <td className="px-2 py-1.5 text-center">
                      <input type="checkbox" checked={r.absent} onChange={() => toggleAbsent(idx)}
                             data-testid={`absent-${r.cadet_participant_id}`} />
                    </td>
                    {fields.map(f => (
                      <td key={f} className="px-1 py-1">
                        <Input type="number" step="any" disabled={r.absent}
                          value={r.field_scores?.[f] ?? ''}
                          onChange={e => updateRowField(idx, f, e.target.value)}
                          className="h-7 text-xs text-center px-1 rounded-sm"
                          data-testid={`score-${r.cadet_participant_id}-${f}`} />
                      </td>
                    ))}
                    <td className="px-2 py-1.5 text-center font-bold">{r.absent ? '—' : total}</td>
                    <td className="px-2 py-1.5 text-center">{fmtPct(pct)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {enabledTypes.length > 0 && !isPerCadet && (
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="text-xs font-bold text-slate-700 mb-3 uppercase">
            {TYPE_LABEL[type]} — {flight}, Day {day} (flight-level)
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {fields.map(f => (
              <div key={f}>
                <Label className="text-[10px] text-slate-500">{FIELD_LABEL[f] || f}</Label>
                <Input type="number" step="any" value={fieldScores[f] ?? ''}
                  onChange={e => setFieldScores(prev => ({ ...prev, [f]: e.target.value === '' ? '' : Number(e.target.value) }))}
                  className="mt-1 h-8 text-sm rounded-sm" data-testid={`flight-score-${f}`} />
              </div>
            ))}
          </div>
          <div className="mt-3 text-xs text-slate-500">
            Total: <span className="font-bold">{fields.reduce((s, f) => s + (typeof fieldScores[f] === 'number' ? fieldScores[f] : 0), 0)}</span>
            {' '}of {typesMeta.max_total[type]} ({fmtPct(
              fields.reduce((s, f) => s + (typeof fieldScores[f] === 'number' ? fieldScores[f] : 0), 0) / (typesMeta.max_total[type] || 1)
            )})
          </div>
        </div>
      )}
    </div>
  );
};

/* ── Weekly Totals (with merit toggle + change matrix) ─── */
const WeeklyTotalsTab = ({ dashboard, reload }) => {
  const [meritOn, setMeritOn] = useState(dashboard.include_merit_points);
  const [working, setWorking] = useState(dashboard);
  const [busy, setBusy] = useState(false);

  const toggleMerit = async () => {
    setBusy(true);
    try {
      // Persist the toggle in settings + re-fetch dashboard with new setting
      await updateInspectionSettings({ include_merit_points: !meritOn });
      const d = await getInspectionDashboard();
      setWorking(d); setMeritOn(!meritOn);
      toast.success(`Merit points ${!meritOn ? 'INCLUDED' : 'EXCLUDED'}`);
      reload();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed');
    } finally { setBusy(false); }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between bg-white border border-slate-200 rounded-lg p-3">
        <div>
          <div className="font-bold text-[#00205B] text-sm">Weekly Point Totals</div>
          <div className="text-xs text-slate-500">
            Day-by-day CTF Points per flight. Merit points are currently{' '}
            <span className={`font-bold ${meritOn ? 'text-emerald-600' : 'text-slate-400'}`}>
              {meritOn ? 'INCLUDED' : 'EXCLUDED'}
            </span>.
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500">Include merit</span>
          <Switch checked={meritOn} onCheckedChange={toggleMerit} disabled={busy}
                  data-testid="merit-toggle" />
        </div>
      </div>

      <PointsMatrix label="Weekly Point Totals" matrix={working.per_day_points} totals={working.weekly_totals} />
      <PointsMatrix label="Weekly Point Change (vs previous day; Day 1 = baseline)"
                    matrix={working.weekly_change} signed />
    </div>
  );
};

const PointsMatrix = ({ label, matrix, totals, signed }) => (
  <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
    <div className="px-4 py-2 bg-slate-50 border-b border-slate-200 font-bold text-[#00205B] text-sm">{label}</div>
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead className="bg-slate-50 text-slate-500 uppercase text-[10px]">
          <tr>
            <th className="px-3 py-2 text-left">Day</th>
            {FLIGHTS.map(f => <th key={f} className="px-3 py-2 capitalize">{f}</th>)}
          </tr>
        </thead>
        <tbody>
          {DAYS.map(day => {
            const row = matrix[day] || matrix[String(day)] || {};
            return (
              <tr key={day} className={day % 2 ? '' : 'bg-slate-50/40'}>
                <td className="px-3 py-1.5 font-semibold text-slate-700">Day {day}</td>
                {FLIGHTS.map(f => {
                  const v = row[f] ?? 0;
                  const cls = signed ? (v > 0 ? 'text-emerald-600' : v < 0 ? 'text-red-600' : 'text-slate-400') : 'text-[#00205B]';
                  return (
                    <td key={f} className={`px-3 py-1.5 text-center font-medium ${cls}`}>
                      {signed ? sign(v) : (v ? v.toFixed(1) : '0.0')}
                    </td>
                  );
                })}
              </tr>
            );
          })}
          {totals && (
            <tr className="bg-emerald-50/40 font-bold border-t-2 border-slate-200">
              <td className="px-3 py-2 text-emerald-700">Total</td>
              {FLIGHTS.map(f => (
                <td key={f} className="px-3 py-2 text-center text-emerald-700">{(totals[f] || 0).toFixed(1)}</td>
              ))}
            </tr>
          )}
        </tbody>
      </table>
    </div>
  </div>
);

/* ── Student Points ───────────────────────────── */
const StudentPointsTab = ({ participants }) => {
  const [data, setData] = useState({});  // pid -> summary
  const [loading, setLoading] = useState(false);
  const [filterFlight, setFilterFlight] = useState('all');

  const eligible = useMemo(() =>
    participants.filter(p =>
      ['student', 'basic_student', 'advanced_student'].includes((p.participant_type || '').toLowerCase())
      && !p.is_removed
      && (filterFlight === 'all' || (p.flight || '').toLowerCase() === filterFlight)
    ).slice(0, 500),
  [participants, filterFlight]);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setLoading(true);
      const out = {};
      // Just fetch all rows once and aggregate client-side (avoids N round-trips)
      try {
        const scores = await getInspectionScores();
        scores.forEach(s => {
          if (!s.cadet_participant_id) return;
          if (!out[s.cadet_participant_id]) out[s.cadet_participant_id] = { rows: [], total: 0, percents: [] };
          out[s.cadet_participant_id].rows.push(s);
          if (!s.absent && typeof s.percent === 'number') {
            out[s.cadet_participant_id].total += (s.total || 0);
            out[s.cadet_participant_id].percents.push(s.percent);
          }
        });
        if (!cancelled) setData(out);
      } catch (e) {
        toast.error(e?.response?.data?.detail || 'Failed to load');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 bg-white border border-slate-200 rounded-lg p-3">
        <Label className="text-xs">Flight:</Label>
        <select value={filterFlight} onChange={e => setFilterFlight(e.target.value)}
                className="h-8 border border-slate-200 rounded-sm px-2 text-sm capitalize">
          <option value="all">All</option>
          {FLIGHTS.map(f => <option key={f} value={f}>{f}</option>)}
        </select>
        <span className="ml-auto text-xs text-slate-500">{eligible.length} cadet(s)</span>
      </div>
      <div className="bg-white border border-slate-200 rounded-lg overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-slate-50 text-slate-500 uppercase text-[10px]">
            <tr>
              <th className="px-3 py-2 text-left">Cadet</th>
              <th className="px-3 py-2 text-left">Flight</th>
              <th className="px-3 py-2 text-center">Inspections Taken</th>
              <th className="px-3 py-2 text-center">Total Score</th>
              <th className="px-3 py-2 text-center">Avg % Correct</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="px-3 py-4 text-center text-slate-400">Loading…</td></tr>
            ) : eligible.length === 0 ? (
              <tr><td colSpan={5} className="px-3 py-4 text-center text-slate-400 italic">No cadets match the filter.</td></tr>
            ) : eligible.map((p, idx) => {
              const summary = data[p.id];
              const count = summary?.percents.length || 0;
              const avg = count > 0 ? summary.percents.reduce((a, b) => a + b, 0) / count : null;
              return (
                <tr key={p.id} className={idx % 2 ? 'bg-slate-50/40' : ''}>
                  <td className="px-3 py-1.5 font-medium text-slate-700">{p.last_name}, {p.first_name}</td>
                  <td className="px-3 py-1.5 capitalize">{p.flight || '—'}</td>
                  <td className="px-3 py-1.5 text-center">{count}</td>
                  <td className="px-3 py-1.5 text-center font-bold">{summary?.total?.toFixed(1) || '—'}</td>
                  <td className="px-3 py-1.5 text-center font-medium text-[#00205B]">{fmtPct(avg)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

/* ── Settings ─────────────────────────────────── */
const SettingsTab = ({ settings, typesMeta, reload }) => {
  const [dayInsp, setDayInsp] = useState(settings.day_inspections);
  const [weights, setWeights] = useState(settings.weights);
  const [merit, setMerit] = useState(settings.include_merit_points);
  const [saving, setSaving] = useState(false);

  const toggleTypeForDay = (day, type) => {
    setDayInsp(prev => {
      const cur = prev[String(day)] || [];
      const next = cur.includes(type) ? cur.filter(t => t !== type) : [...cur, type];
      return { ...prev, [String(day)]: next };
    });
  };

  const save = async () => {
    setSaving(true);
    try {
      await updateInspectionSettings({
        day_inspections: dayInsp,
        weights: Object.fromEntries(Object.entries(weights).map(([k, v]) => [k, Number(v)])),
        include_merit_points: merit,
      });
      toast.success('Settings saved');
      reload();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Save failed');
    } finally { setSaving(false); }
  };

  const reset = () => {
    setDayInsp({
      '1': [],
      '2': ['dorm_uniform', 'dorm_uniform_repeat', 'drill', 'daily_sports', 'knowledge'],
      '3': ['drill', 'daily_sports', 'knowledge'],
      '4': ['dorm_uniform_repeat', 'daily_sports'],
      '5': ['drill', 'daily_sports', 'knowledge'],
      '6': ['dorm_uniform_repeat', 'knowledge'],
    });
    setWeights(typesMeta.default_weights);
    setMerit(true);
    toast.info('Reset to spreadsheet defaults (click Save to apply)');
  };

  return (
    <div className="space-y-4">
      <div className="bg-white border border-slate-200 rounded-lg p-4">
        <div className="font-bold text-[#00205B] mb-2 text-sm uppercase">Day → Inspections Mapping</div>
        <div className="text-xs text-slate-500 mb-3">
          Select which inspections happen each day. Selected types appear in <em>Enter Scores</em>.
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-slate-50 text-slate-500 uppercase text-[10px]">
              <tr>
                <th className="px-3 py-2 text-left">Day</th>
                {Object.keys(TYPE_LABEL).filter(t => t !== 'app').map(t => (
                  <th key={t} className="px-2 py-2 text-center">{TYPE_LABEL[t]}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {DAYS.map(day => (
                <tr key={day}>
                  <td className="px-3 py-1.5 font-semibold text-slate-700">Day {day}</td>
                  {Object.keys(TYPE_LABEL).filter(t => t !== 'app').map(t => (
                    <td key={t} className="px-2 py-1.5 text-center">
                      <input type="checkbox"
                        checked={(dayInsp[String(day)] || []).includes(t)}
                        onChange={() => toggleTypeForDay(day, t)}
                        data-testid={`day-${day}-${t}`} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-4">
        <div className="font-bold text-[#00205B] mb-2 text-sm uppercase">Category Weights — TOTALS U22:W26</div>
        <div className="text-xs text-slate-500 mb-3">
          Per the spreadsheet: <code>Point Conv. = flight average % × weight</code>.
          Sum of all point conversions for a flight on a day = <strong>CTF Points</strong>.
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {Object.keys(typesMeta.default_weights).map(k => (
            <div key={k}>
              <Label className="text-[10px] uppercase tracking-widest text-slate-500">{TYPE_LABEL[k] || k}</Label>
              <Input type="number" step="any" value={weights[k] ?? ''}
                onChange={e => setWeights(prev => ({ ...prev, [k]: e.target.value }))}
                className="mt-1 h-8 rounded-sm" data-testid={`weight-${k}`} />
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-4 flex items-center justify-between">
        <div>
          <div className="font-bold text-[#00205B] text-sm uppercase">Include Merit Points</div>
          <div className="text-xs text-slate-500">When ON, merit points add to each flight's CTF Points.</div>
        </div>
        <Switch checked={merit} onCheckedChange={setMerit} data-testid="settings-merit-toggle" />
      </div>

      <div className="flex gap-2">
        <Button onClick={save} disabled={saving} className="bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="save-settings-btn">
          <Save className="w-3.5 h-3.5 mr-1.5" /> {saving ? 'Saving…' : 'Save Settings'}
        </Button>
        <Button onClick={reset} variant="outline" className="rounded-sm" data-testid="reset-settings-btn">
          <RotateCcw className="w-3.5 h-3.5 mr-1.5" /> Reset to spreadsheet defaults
        </Button>
      </div>
    </div>
  );
};

export default InspectionsPage;
