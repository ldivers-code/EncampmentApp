import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  getOrgChartRoles,
  getOrgChartRole,
  updateOrgChartRole,
  seedOrgChart,
} from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '../components/ui/sheet';
import { toast } from 'sonner';
import {
  Network, User, Users, Search, X, Edit2,
  ChevronDown, ChevronRight, RefreshCw, Maximize2, Minimize2,
} from 'lucide-react';

/* ── Category palette ─────────────────────────── */
const CAT = {
  staff:          { bg: '#008651', text: '#fff', border: '#006b41', label: 'Staff / Executive' },
  '6th_cts':      { bg: '#00205B', text: '#fff', border: '#001540', label: '6th CTS' },
  '21st_cts':     { bg: '#D4A017', text: '#fff', border: '#b08812', label: '21st CTS' },
  '22nd_cts':     { bg: '#9B2335', text: '#fff', border: '#7a1c2a', label: '22nd CTS' },
  cadet_support:  { bg: '#8C9298', text: '#fff', border: '#6e767c', label: 'Cadet Support' },
};
const catStyle = (c) => CAT[c] || { bg: '#64748b', text: '#fff', border: '#475569', label: c || '' };

/* ── Layout constants ─────────────────────────── */
const NODE_W = 172;
const NODE_H = 54;
const H_GAP = 14;
const V_GAP = 56;

/* ── Recursive layout engine ──────────────────── */
function measureTree(id, childMap, collapsed) {
  const kids = collapsed.has(id) ? [] : (childMap[id] || []);
  if (kids.length === 0) return { id, w: NODE_W, kids: [] };
  const mKids = kids.map(k => measureTree(k.role_id, childMap, collapsed));
  const totalW = mKids.reduce((s, k) => s + k.w, 0) + (mKids.length - 1) * H_GAP;
  return { id, w: Math.max(NODE_W, totalW), kids: mKids };
}

function positionTree(m, cx, cy, out) {
  out[m.id] = { x: cx, y: cy };
  if (m.kids.length === 0) return;
  const totalW = m.kids.reduce((s, k) => s + k.w, 0) + (m.kids.length - 1) * H_GAP;
  let startX = cx - totalW / 2;
  const childY = cy + NODE_H + V_GAP;
  m.kids.forEach(k => {
    const kcx = startX + k.w / 2;
    positionTree(k, kcx, childY, out);
    startX += k.w + H_GAP;
  });
}

/* ── SVG Connector drawing ────────────────────── */
function Connectors({ positions, roles, childMap, collapsed }) {
  const paths = [];
  const dashed = [];

  roles.forEach(r => {
    if (!r.reports_to || !positions[r.role_id] || !positions[r.reports_to]) return;
    if (collapsed.has(r.reports_to)) return;
    const p = positions[r.reports_to];
    const c = positions[r.role_id];
    const midY = p.y + NODE_H + V_GAP * 0.4;
    paths.push(
      `M${p.x},${p.y + NODE_H} L${p.x},${midY} L${c.x},${midY} L${c.x},${c.y}`
    );
  });

  // Secondary (dashed) reporting lines
  roles.forEach(r => {
    if (!r.secondary_reports_to || !positions[r.role_id] || !positions[r.secondary_reports_to]) return;
    const s = positions[r.secondary_reports_to];
    const c = positions[r.role_id];
    // Same level (siblings) — draw a curved arc below the nodes
    if (Math.abs(s.y - c.y) < 10) {
      const arcY = s.y + NODE_H + 18;
      dashed.push(
        `M${s.x},${s.y + NODE_H} Q${s.x},${arcY} ${(s.x + c.x) / 2},${arcY} Q${c.x},${arcY} ${c.x},${c.y + NODE_H}`
      );
    } else {
      const midY = Math.min(s.y + NODE_H, c.y) + (V_GAP * 0.25);
      dashed.push(
        `M${s.x},${s.y + NODE_H} L${s.x},${midY} L${c.x},${midY} L${c.x},${c.y}`
      );
    }
  });

  return (
    <>
      {paths.map((d, i) => (
        <path key={`p${i}`} d={d} fill="none" stroke="#94a3b8" strokeWidth="1.5" />
      ))}
      {dashed.map((d, i) => (
        <path key={`d${i}`} d={d} fill="none" stroke="#9B2335" strokeWidth="1.5"
              strokeDasharray="6 4" opacity={0.7} />
      ))}
    </>
  );
}

/* ── Single Node card ─────────────────────────── */
function NodeCard({ role, pos, isSelected, onClick, hasChildren, isCollapsed, onToggle }) {
  const st = catStyle(role.role_category);
  const vacant = !role.assigned_name;
  const x = pos.x - NODE_W / 2;
  const y = pos.y;

  return (
    <div
      className="absolute select-none"
      style={{ left: x, top: y, width: NODE_W, height: NODE_H }}
      data-testid={`org-node-${role.role_id}`}
    >
      <div
        onClick={() => onClick(role)}
        className={`
          w-full h-full rounded-lg border-2 cursor-pointer
          flex flex-col items-center justify-center px-2 text-center
          transition-all duration-150 hover:shadow-lg hover:scale-[1.04]
          ${isSelected ? 'ring-2 ring-offset-2 ring-yellow-400' : ''}
        `}
        style={{ backgroundColor: st.bg, color: st.text, borderColor: st.border }}
      >
        <div className="flex items-center gap-1 w-full justify-center">
          {role.display_label && (
            <span className="text-[9px] font-mono bg-white/20 px-1 rounded">{role.display_label}</span>
          )}
          <span className="text-[11px] font-bold leading-tight truncate max-w-[140px]">
            {role.position_title}
          </span>
        </div>
        <span className={`text-[10px] leading-tight truncate max-w-[150px] ${vacant ? 'italic opacity-60' : 'opacity-90'}`}>
          {role.assigned_name || 'Vacant'}
        </span>
      </div>
      {hasChildren && (
        <button
          onClick={(e) => { e.stopPropagation(); onToggle(role.role_id); }}
          className="absolute -bottom-3 left-1/2 -translate-x-1/2 w-5 h-5 rounded-full
                     bg-white border border-slate-300 shadow-sm flex items-center justify-center
                     hover:bg-slate-100 z-10 transition-colors"
          data-testid={`toggle-${role.role_id}`}
        >
          {isCollapsed
            ? <ChevronRight className="w-3 h-3 text-slate-600" />
            : <ChevronDown className="w-3 h-3 text-slate-600" />
          }
        </button>
      )}
    </div>
  );
}

/* ── Legend ────────────────────────────────────── */
function Legend() {
  return (
    <div className="flex flex-wrap gap-3 items-center">
      {Object.entries(CAT).map(([k, v]) => (
        <div key={k} className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: v.bg }} />
          <span className="text-[11px] text-slate-600 font-medium">{v.label}</span>
        </div>
      ))}
      <div className="flex items-center gap-1.5 ml-2">
        <svg width="24" height="8"><line x1="0" y1="4" x2="24" y2="4" stroke="#9B2335" strokeWidth="1.5" strokeDasharray="4 3" /></svg>
        <span className="text-[11px] text-slate-600 font-medium">Secondary Report</span>
      </div>
    </div>
  );
}

/* ── Main component ───────────────────────────── */
const OrgChartPage = () => {
  const { canEdit } = useAuth();
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [collapsed, setCollapsed] = useState(new Set());
  const [search, setSearch] = useState('');
  const [catFilter, setCatFilter] = useState('all');
  const containerRef = useRef(null);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const data = await getOrgChartRoles();
      setRoles(data);
      // Start with deeper levels collapsed for minimal scroll
      const root = data.find(r => !r.reports_to);
      if (root) {
        const l1 = data.filter(r => r.reports_to === root.role_id).map(r => r.role_id);
        const l2 = data.filter(r => l1.includes(r.reports_to)).map(r => r.role_id);
        const l3 = data.filter(r => l2.includes(r.reports_to)).map(r => r.role_id);
        // Collapse everything below level 3
        const collapseSet = new Set();
        data.forEach(r => {
          const kids = data.filter(k => k.reports_to === r.role_id);
          if (kids.length > 0 && !l1.includes(r.role_id) && !l2.includes(r.role_id) && ![root.role_id, ...l1].includes(r.role_id)) {
            if (l3.includes(r.role_id)) collapseSet.add(r.role_id);
          }
        });
        setCollapsed(collapseSet);
      }
    } catch (err) {
      console.error('Failed to load org chart:', err);
    } finally {
      setLoading(false);
    }
  };

  /* Build maps */
  const { nodeMap, childMap, rootId } = useMemo(() => {
    const nm = {};
    const cm = {};
    let rid = null;
    roles.forEach(r => {
      nm[r.role_id] = r;
      const p = r.reports_to || '__root__';
      if (!cm[p]) cm[p] = [];
      cm[p].push(r);
      if (!r.reports_to) rid = r.role_id;
    });
    Object.values(cm).forEach(arr => arr.sort((a, b) => (a.order || 0) - (b.order || 0)));
    return { nodeMap: nm, childMap: cm, rootId: rid };
  }, [roles]);

  /* Compute positions */
  const positions = useMemo(() => {
    if (!rootId) return {};
    const measure = measureTree(rootId, childMap, collapsed);
    const pos = {};
    positionTree(measure, measure.w / 2, 20, pos);
    return pos;
  }, [rootId, childMap, collapsed]);

  /* Canvas size */
  const canvasSize = useMemo(() => {
    let maxX = 0, maxY = 0;
    Object.values(positions).forEach(p => {
      if (p.x + NODE_W / 2 > maxX) maxX = p.x + NODE_W / 2;
      if (p.y + NODE_H > maxY) maxY = p.y + NODE_H;
    });
    return { w: maxX + 40, h: maxY + 60 };
  }, [positions]);

  /* Search highlight */
  const matchIds = useMemo(() => {
    if (!search) return null;
    const term = search.toLowerCase();
    return new Set(
      roles
        .filter(r =>
          (r.position_title || '').toLowerCase().includes(term) ||
          (r.assigned_name || '').toLowerCase().includes(term) ||
          (r.display_label || '').toLowerCase().includes(term)
        )
        .map(r => r.role_id)
    );
  }, [search, roles]);

  /* Filter by category */
  const visibleRoles = useMemo(() => {
    if (catFilter === 'all') return roles;
    return roles.filter(r => r.role_category === catFilter);
  }, [roles, catFilter]);

  const toggle = useCallback((id) => {
    setCollapsed(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const expandAll = () => setCollapsed(new Set());
  const collapseBelow2 = () => {
    if (!rootId) return;
    const l1 = (childMap[rootId] || []).map(r => r.role_id);
    const l2 = roles.filter(r => l1.includes(r.reports_to)).map(r => r.role_id);
    const newC = new Set();
    roles.forEach(r => {
      const kids = childMap[r.role_id] || [];
      if (kids.length > 0 && ![rootId, ...l1, ...l2].includes(r.role_id)) {
        newC.add(r.role_id);
      }
    });
    setCollapsed(newC);
  };

  const handleSelect = useCallback(async (role) => {
    try {
      const full = await getOrgChartRole(role.role_id);
      setSelected(full);
      setEditForm({
        position_title: full.position_title || '',
        assigned_name: full.assigned_name || '',
        job_description: full.job_description || '',
        responsible_for: full.responsible_for || '',
        supervises: full.supervises || '',
        display_label: full.display_label || '',
      });
      setSheetOpen(true);
      setEditing(false);
    } catch {
      toast.error('Failed to load details');
    }
  }, []);

  const handleSave = async () => {
    if (!selected) return;
    try {
      await updateOrgChartRole(selected.role_id, editForm);
      toast.success('Saved');
      setEditing(false);
      loadData();
      const updated = await getOrgChartRole(selected.role_id);
      setSelected(updated);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Save failed');
    }
  };

  const handleReseed = async () => {
    if (!window.confirm('Wipe and reseed the entire org chart?')) return;
    try {
      await seedOrgChart();
      toast.success('Reseeded');
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Reseed failed');
    }
  };

  /* Center scroll on mount */
  useEffect(() => {
    if (!loading && containerRef.current && canvasSize.w > 0) {
      const el = containerRef.current;
      const scrollX = (canvasSize.w - el.clientWidth) / 2;
      if (scrollX > 0) el.scrollLeft = scrollX;
    }
  }, [loading, canvasSize]);

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <div className="text-slate-400">Loading org chart...</div>
      </div>
    );
  }

  const parentTitle = (pid) => nodeMap[pid]?.position_title || pid;

  return (
    <div className="p-3 lg:p-6 animate-fade-in" data-testid="org-chart-page">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 mb-4">
        <div className="flex items-center gap-3">
          <Network className="w-6 h-6 text-[#00205B]" />
          <h1 className="text-lg lg:text-xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Encampment 2026 Command Map
          </h1>
          <span className="text-xs text-slate-400">{roles.length} positions</span>
        </div>
        {canEdit() && (
          <Button variant="outline" size="sm" className="rounded-sm border-slate-300 text-slate-600 w-fit"
                  onClick={handleReseed} data-testid="reseed-orgchart-btn">
            <RefreshCw className="w-3.5 h-3.5 mr-1.5" /> Reseed
          </Button>
        )}
      </div>

      {/* Toolbar */}
      <div className="bg-white border border-slate-200 rounded-t-lg px-4 py-2.5 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[180px] max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <Input
            value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search positions..."
            className="pl-8 h-8 text-sm rounded-md"
            data-testid="org-chart-search"
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Category filters */}
        <div className="flex gap-1">
          <button onClick={() => setCatFilter('all')}
            className={`text-[11px] px-2.5 py-1 rounded-full font-medium transition-colors
              ${catFilter === 'all' ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
            data-testid="filter-all"
          >All</button>
          {Object.entries(CAT).map(([k, v]) => (
            <button key={k} onClick={() => setCatFilter(k)}
              className={`text-[11px] px-2.5 py-1 rounded-full font-medium transition-colors
                ${catFilter === k ? 'text-white' : 'text-slate-600 hover:opacity-80'}`}
              style={catFilter === k ? { backgroundColor: v.bg, color: v.text } : { backgroundColor: v.bg + '18', color: v.bg }}
              data-testid={`filter-${k}`}
            >{v.label}</button>
          ))}
        </div>

        <div className="ml-auto flex gap-1">
          <Button variant="ghost" size="sm" onClick={expandAll} className="text-xs h-7 px-2" data-testid="expand-all-btn">
            <Maximize2 className="w-3 h-3 mr-1" />Expand
          </Button>
          <Button variant="ghost" size="sm" onClick={collapseBelow2} className="text-xs h-7 px-2" data-testid="collapse-btn">
            <Minimize2 className="w-3 h-3 mr-1" />Collapse
          </Button>
        </div>
      </div>

      {/* Legend + Diagram */}
      <div className="bg-white border-x border-b border-slate-200 rounded-b-lg overflow-hidden">
        <div className="px-4 py-2 border-b border-slate-100 bg-slate-50/50">
          <Legend />
        </div>

        {/* Node-link diagram canvas */}
        <div
          ref={containerRef}
          className="overflow-auto relative"
          style={{ maxHeight: 'calc(100vh - 260px)' }}
          data-testid="org-chart-canvas"
        >
          <div className="relative" style={{ width: canvasSize.w, height: canvasSize.h, minWidth: '100%' }}>
            {/* SVG connector layer */}
            <svg
              className="absolute inset-0 pointer-events-none"
              width={canvasSize.w}
              height={canvasSize.h}
            >
              <Connectors positions={positions} roles={roles} childMap={childMap} collapsed={collapsed} />
            </svg>

            {/* Node layer */}
            {roles.map(r => {
              const pos = positions[r.role_id];
              if (!pos) return null;
              // search dimming
              const dimmed = matchIds && !matchIds.has(r.role_id);
              // category filter hiding
              if (catFilter !== 'all' && r.role_category !== catFilter) return null;
              const hasKids = (childMap[r.role_id] || []).length > 0;
              return (
                <div key={r.role_id} style={{ opacity: dimmed ? 0.25 : 1, transition: 'opacity 0.2s' }}>
                  <NodeCard
                    role={r}
                    pos={pos}
                    isSelected={selected?.role_id === r.role_id}
                    onClick={handleSelect}
                    hasChildren={hasKids}
                    isCollapsed={collapsed.has(r.role_id)}
                    onToggle={toggle}
                  />
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Detail Panel */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent className="w-full sm:max-w-md overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-[#00205B] uppercase font-bold flex items-center gap-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
              <User className="w-5 h-5" /> Position Details
            </SheetTitle>
          </SheetHeader>

          {selected && (
            <div className="mt-5 space-y-4">
              {/* Category + label */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border"
                  style={{ backgroundColor: catStyle(selected.role_category).bg, color: catStyle(selected.role_category).text, borderColor: catStyle(selected.role_category).border }}>
                  {catStyle(selected.role_category).label}
                </span>
                {selected.display_label && (
                  <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">{selected.display_label}</span>
                )}
              </div>

              {/* Title */}
              <div>
                <Label className="text-[10px] uppercase tracking-widest text-slate-400">Position Title</Label>
                {editing ? (
                  <Input value={editForm.position_title} onChange={e => setEditForm({ ...editForm, position_title: e.target.value })} className="mt-1 rounded-sm" />
                ) : (
                  <p className="text-lg font-bold text-[#00205B]" data-testid="detail-title">{selected.position_title}</p>
                )}
              </div>

              {/* Name */}
              <div>
                <Label className="text-[10px] uppercase tracking-widest text-slate-400">Assigned Name</Label>
                {editing ? (
                  <Input value={editForm.assigned_name} onChange={e => setEditForm({ ...editForm, assigned_name: e.target.value })} className="mt-1 rounded-sm" />
                ) : (
                  <div className={`mt-1 p-2.5 rounded-sm border ${selected.assigned_name ? 'bg-slate-50 border-slate-200' : 'bg-amber-50 border-amber-200'}`}>
                    <div className="flex items-center gap-2">
                      <User className={`w-4 h-4 ${selected.assigned_name ? 'text-[#00205B]' : 'text-amber-600'}`} />
                      <span className={selected.assigned_name ? 'font-medium text-sm' : 'text-amber-600 italic text-sm'} data-testid="detail-name">
                        {selected.assigned_name || 'Vacant'}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Reports To */}
              <div>
                <Label className="text-[10px] uppercase tracking-widest text-slate-400">Reports To</Label>
                <div className="mt-1 p-2.5 bg-slate-50 rounded-sm border border-slate-200">
                  {selected.reports_to ? (
                    <div className="flex items-center gap-2">
                      <Users className="w-4 h-4 text-[#00205B]" />
                      <span className="font-medium text-sm">{parentTitle(selected.reports_to)}</span>
                    </div>
                  ) : <span className="text-slate-500 text-sm">Top Level</span>}
                </div>
                {selected.secondary_reports_to && (
                  <div className="mt-1 p-2 bg-red-50 rounded-sm border border-red-200 flex items-center gap-2">
                    <svg width="20" height="8"><line x1="0" y1="4" x2="20" y2="4" stroke="#9B2335" strokeWidth="1.5" strokeDasharray="4 3" /></svg>
                    <span className="text-xs text-red-800">Secondary: {parentTitle(selected.secondary_reports_to)}</span>
                  </div>
                )}
              </div>

              {/* Supervises / Children */}
              {selected.children && selected.children.length > 0 && (
                <div>
                  <Label className="text-[10px] uppercase tracking-widest text-slate-400">Supervises ({selected.children.length})</Label>
                  <div className="mt-1 space-y-1 max-h-40 overflow-y-auto">
                    {selected.children.map(cid => {
                      const child = nodeMap[cid];
                      if (!child) return null;
                      return (
                        <div key={cid} className="p-1.5 bg-slate-50 rounded border border-slate-200 flex items-center gap-2 cursor-pointer hover:bg-slate-100"
                             onClick={() => handleSelect(child)}>
                          <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: catStyle(child.role_category).bg }} />
                          <span className="text-xs font-medium truncate">{child.position_title}</span>
                          {child.assigned_name && <span className="text-[10px] text-slate-500 truncate">- {child.assigned_name}</span>}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Responsibilities */}
              <div>
                <Label className="text-[10px] uppercase tracking-widest text-slate-400">Responsibilities</Label>
                {editing ? (
                  <Textarea value={editForm.responsible_for} onChange={e => setEditForm({ ...editForm, responsible_for: e.target.value })} className="mt-1 rounded-sm" rows={3} />
                ) : (
                  <p className="mt-1 text-sm text-slate-700">{selected.responsible_for || <span className="text-slate-400 italic">Not defined</span>}</p>
                )}
              </div>

              {/* Job Description */}
              <div>
                <Label className="text-[10px] uppercase tracking-widest text-slate-400">Job Description</Label>
                {editing ? (
                  <Textarea value={editForm.job_description} onChange={e => setEditForm({ ...editForm, job_description: e.target.value })} className="mt-1 rounded-sm" rows={3} />
                ) : (
                  <p className="mt-1 text-sm text-slate-700">{selected.job_description || <span className="text-slate-400 italic">Not defined</span>}</p>
                )}
              </div>

              {/* Actions */}
              {canEdit() && (
                <div className="pt-3 border-t border-slate-200 flex items-center gap-2">
                  {editing ? (
                    <>
                      <Button variant="outline" size="sm" onClick={() => setEditing(false)} className="rounded-sm">Cancel</Button>
                      <Button size="sm" onClick={handleSave} className="bg-[#00205B] hover:bg-[#001540] rounded-sm">Save</Button>
                    </>
                  ) : (
                    <Button size="sm" onClick={() => setEditing(true)} className="bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="edit-btn">
                      <Edit2 className="w-3.5 h-3.5 mr-1.5" /> Edit
                    </Button>
                  )}
                </div>
              )}
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
};

export default OrgChartPage;
