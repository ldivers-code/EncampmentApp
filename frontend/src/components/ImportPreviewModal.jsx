import React, { useState, useEffect, useMemo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { previewImportParticipants, applyImportParticipants } from '../services/api';
import { toast } from 'sonner';
import { AlertCircle, CheckCircle, FileSpreadsheet, RefreshCw, Plus, Edit3, X, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';

const FIELD_LABELS = {
  rank: 'Rank',
  first_name: 'First',
  last_name: 'Last',
  middle_name: 'Middle',
  email: 'Email',
  phone: 'Phone',
  cell_phone: 'Cell',
  unit: 'Unit',
  wing: 'Wing',
  region: 'Region',
  gender: 'Gender',
  age: 'Age',
  age_at_event: 'Age (Event)',
  shirt_size: 'Shirt',
  participant_type: 'Type',
  member_type: 'Member',
  paid_in_full: 'Paid',
  amount_paid: 'Amount Paid',
  registration_status: 'Reg Status',
  unit_approved: 'Unit Appr.',
  wing_approved: 'Wing Appr.',
  slotted: 'Slotted',
};

const fmtVal = (v) => {
  if (v === null || v === undefined || v === '') return '—';
  if (typeof v === 'boolean') return v ? 'Yes' : 'No';
  return String(v);
};

const ROW_FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'conflict', label: 'Conflicts' },
  { id: 'update', label: 'Updates' },
  { id: 'create', label: 'New' },
];

export const ImportPreviewModal = ({ open, file, onClose, onApplied }) => {
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [preview, setPreview] = useState(null);
  // resolutions: { [row_idx]: { action: 'update'|'create'|'skip', participant_id?: string } }
  const [resolutions, setResolutions] = useState({});
  const [filter, setFilter] = useState('all');
  const [expandedRows, setExpandedRows] = useState({});

  // Load preview when modal opens with a file
  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      if (!open || !file) return;
      setLoading(true);
      setPreview(null);
      setResolutions({});
      setExpandedRows({});
      try {
        const data = await previewImportParticipants(file);
        if (cancelled) return;
        setPreview(data);
        // Pre-populate default resolutions for non-conflict rows.
        // Conflict rows are intentionally left unresolved so the user MUST pick.
        const defaults = {};
        data.rows.forEach((r) => {
          if (r.default_action === 'update') {
            defaults[r.row_idx] = { action: 'update', participant_id: r.default_target_id };
          } else if (r.default_action === 'create') {
            defaults[r.row_idx] = { action: 'create' };
          }
          // Conflict rows: leave undefined → unresolvedConflicts counter blocks Apply
        });
        setResolutions(defaults);
        // Auto-filter to conflicts if any exist
        if (data.summary.conflict > 0) setFilter('conflict');
      } catch (err) {
        if (!cancelled) {
          toast.error(err.response?.data?.detail || 'Failed to parse upload');
          onClose();
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => { cancelled = true; };
  }, [open, file]);

  const filteredRows = useMemo(() => {
    if (!preview) return [];
    if (filter === 'all') return preview.rows;
    return preview.rows.filter((r) => r.default_action === filter);
  }, [preview, filter]);

  const unresolvedConflicts = useMemo(() => {
    if (!preview) return 0;
    return preview.rows.filter((r) => {
      if (r.default_action !== 'conflict') return false;
      const res = resolutions[r.row_idx];
      // A conflict is "resolved" when user picks update+participant_id, create, or skip
      if (!res) return true;
      if (res.action === 'update' && !res.participant_id) return true;
      return false;
    }).length;
  }, [preview, resolutions]);

  const setRowResolution = (rowIdx, patch) => {
    setResolutions((prev) => {
      const current = prev[rowIdx] || {};
      return { ...prev, [rowIdx]: { ...current, ...patch } };
    });
  };

  const setRowAction = (rowIdx, action, candidateId = null) => {
    if (action === 'update') {
      setRowResolution(rowIdx, { action: 'update', participant_id: candidateId });
    } else if (action === 'create') {
      setRowResolution(rowIdx, { action: 'create', participant_id: null });
    } else {
      setRowResolution(rowIdx, { action: 'skip', participant_id: null });
    }
  };

  const toggleExpanded = (rowIdx) => setExpandedRows((p) => ({ ...p, [rowIdx]: !p[rowIdx] }));

  const handleApply = async () => {
    if (!preview) return;
    if (unresolvedConflicts > 0) {
      toast.warning(`Resolve ${unresolvedConflicts} conflict(s) before applying`);
      return;
    }
    setApplying(true);
    try {
      // Convert keys to strings for the API
      const payload = {};
      Object.entries(resolutions).forEach(([k, v]) => { payload[String(k)] = v; });
      const result = await applyImportParticipants(preview.staging_id, payload);
      toast.success(result.message || 'Import applied');
      onApplied(result);
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to apply import');
    } finally {
      setApplying(false);
    }
  };

  const renderActionBadge = (row) => {
    const res = resolutions[row.row_idx];
    const action = res?.action || row.default_action;
    if (action === 'create') {
      return <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] uppercase font-bold bg-emerald-100 text-emerald-800 rounded-sm" data-testid={`row-action-${row.row_idx}`}><Plus className="w-3 h-3" /> Create</span>;
    }
    if (action === 'update') {
      return <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] uppercase font-bold bg-blue-100 text-blue-800 rounded-sm" data-testid={`row-action-${row.row_idx}`}><Edit3 className="w-3 h-3" /> Update</span>;
    }
    if (action === 'skip') {
      return <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] uppercase font-bold bg-slate-200 text-slate-700 rounded-sm" data-testid={`row-action-${row.row_idx}`}><X className="w-3 h-3" /> Skip</span>;
    }
    // unresolved conflict (no res yet, default_action='conflict')
    return <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] uppercase font-bold bg-amber-200 text-amber-900 rounded-sm animate-pulse" data-testid={`row-action-${row.row_idx}`}><AlertTriangle className="w-3 h-3" /> Needs Pick</span>;
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="rounded-sm max-w-5xl max-h-[90vh] overflow-hidden flex flex-col" data-testid="import-preview-modal">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-[#00205B]" />
            Import Preview {file && <span className="text-xs font-normal text-slate-500">— {file.name}</span>}
          </DialogTitle>
        </DialogHeader>

        {loading && (
          <div className="flex items-center justify-center py-12 text-slate-500" data-testid="import-preview-loading">
            <RefreshCw className="w-5 h-5 mr-2 animate-spin" />
            Analyzing spreadsheet…
          </div>
        )}

        {!loading && preview && (
          <>
            {/* Summary bar */}
            <div className="grid grid-cols-4 gap-3 mb-3" data-testid="import-preview-summary">
              <div className="bg-emerald-50 border border-emerald-200 rounded-sm px-3 py-2">
                <div className="text-[10px] uppercase tracking-wide text-emerald-700">New</div>
                <div className="text-2xl font-bold text-emerald-900" data-testid="summary-new">{preview.summary.new}</div>
              </div>
              <div className="bg-blue-50 border border-blue-200 rounded-sm px-3 py-2">
                <div className="text-[10px] uppercase tracking-wide text-blue-700">Updates</div>
                <div className="text-2xl font-bold text-blue-900" data-testid="summary-update">{preview.summary.update}</div>
              </div>
              <div className="bg-amber-50 border border-amber-300 rounded-sm px-3 py-2">
                <div className="text-[10px] uppercase tracking-wide text-amber-800">Conflicts</div>
                <div className="text-2xl font-bold text-amber-900" data-testid="summary-conflict">{preview.summary.conflict}</div>
              </div>
              <div className="bg-slate-100 border border-slate-300 rounded-sm px-3 py-2">
                <div className="text-[10px] uppercase tracking-wide text-slate-600">Total Rows</div>
                <div className="text-2xl font-bold text-slate-900" data-testid="summary-total">{preview.rows.length}</div>
              </div>
            </div>

            {preview.summary.conflict > 0 && unresolvedConflicts > 0 && (
              <div className="mb-3 flex items-start gap-2 bg-amber-50 border border-amber-300 rounded-sm px-3 py-2 text-sm text-amber-900">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="font-semibold">{unresolvedConflicts} conflict(s) need your attention.</span> Multiple existing participants share the same first and last name with no CAPID. Pick the correct one (or choose Create New / Skip) for each row before applying.
                </div>
              </div>
            )}

            {/* Filter tabs */}
            <div className="flex gap-1 mb-2 border-b border-slate-200 pb-2" data-testid="import-preview-filters">
              {ROW_FILTERS.map((f) => {
                const count = f.id === 'all'
                  ? preview.rows.length
                  : preview.rows.filter((r) => r.default_action === f.id).length;
                return (
                  <button
                    key={f.id}
                    onClick={() => setFilter(f.id)}
                    className={`px-3 py-1 text-xs uppercase tracking-wide rounded-sm transition-colors ${filter === f.id ? 'bg-[#00205B] text-white' : 'text-slate-600 hover:bg-slate-100'}`}
                    data-testid={`filter-${f.id}`}
                  >
                    {f.label} ({count})
                  </button>
                );
              })}
            </div>

            {/* Rows */}
            <div className="flex-1 overflow-y-auto border border-slate-200 rounded-sm">
              {filteredRows.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-sm">No rows in this view</div>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-left text-[10px] uppercase tracking-wide text-slate-600 sticky top-0 z-10">
                    <tr>
                      <th className="px-3 py-2 w-10"></th>
                      <th className="px-3 py-2">#</th>
                      <th className="px-3 py-2">Action</th>
                      <th className="px-3 py-2">Name</th>
                      <th className="px-3 py-2">CAPID</th>
                      <th className="px-3 py-2">Unit / Wing</th>
                      <th className="px-3 py-2">Incoming Type</th>
                      <th className="px-3 py-2">Resolution</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRows.map((row) => {
                      const expanded = !!expandedRows[row.row_idx];
                      const res = resolutions[row.row_idx] || {};
                      const isConflict = row.default_action === 'conflict';
                      const hasChanges = Object.keys(row.changes || {}).length > 0;

                      return (
                        <React.Fragment key={row.row_idx}>
                          <tr
                            className={`border-t border-slate-100 hover:bg-slate-50 ${isConflict ? 'bg-amber-50/40' : ''}`}
                            data-testid={`preview-row-${row.row_idx}`}
                          >
                            <td className="px-2 py-2">
                              {(hasChanges || row.candidates.length > 0) && (
                                <button
                                  type="button"
                                  onClick={() => toggleExpanded(row.row_idx)}
                                  className="text-slate-400 hover:text-slate-700"
                                  data-testid={`expand-row-${row.row_idx}`}
                                >
                                  {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                </button>
                              )}
                            </td>
                            <td className="px-3 py-2 text-xs text-slate-500">{row.row_idx + 1}</td>
                            <td className="px-3 py-2">{renderActionBadge(row)}</td>
                            <td className="px-3 py-2 font-medium">
                              {row.last_name}, {row.first_name}
                            </td>
                            <td className="px-3 py-2 font-mono text-xs">{row.capid}</td>
                            <td className="px-3 py-2 text-xs text-slate-600">
                              {row.unit || '—'} / {row.wing || '—'}
                            </td>
                            <td className="px-3 py-2 text-xs">
                              {row.incoming_type || <span className="text-slate-400 italic">unchanged</span>}
                            </td>
                            <td className="px-3 py-2">
                              {isConflict ? (
                                <Select
                                  value={
                                    res.action === 'update' && res.participant_id
                                      ? `update:${res.participant_id}`
                                      : res.action === 'create'
                                        ? 'create'
                                        : res.action === 'skip'
                                          ? 'skip'
                                          : undefined
                                  }
                                  onValueChange={(v) => {
                                    if (v === 'create') setRowAction(row.row_idx, 'create');
                                    else if (v === 'skip') setRowAction(row.row_idx, 'skip');
                                    else if (v.startsWith('update:')) setRowAction(row.row_idx, 'update', v.slice('update:'.length));
                                  }}
                                >
                                  <SelectTrigger className="h-8 w-72 text-xs rounded-sm border-amber-400" data-testid={`resolve-${row.row_idx}`}>
                                    <SelectValue placeholder="⚠ Pick existing match…" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {row.candidates.map((c) => (
                                      <SelectItem key={c.id} value={`update:${c.id}`}>
                                        Update: {c.last_name}, {c.first_name} • CAPID {c.capid} • {c.unit || '—'} / {c.wing || '—'} ({c.participant_type || '—'})
                                      </SelectItem>
                                    ))}
                                    <SelectItem value="create">Create New (separate record)</SelectItem>
                                    <SelectItem value="skip">Skip this row</SelectItem>
                                  </SelectContent>
                                </Select>
                              ) : (
                                <Select
                                  value={res.action || row.default_action}
                                  onValueChange={(v) => {
                                    if (v === 'update') setRowResolution(row.row_idx, { action: 'update', participant_id: row.default_target_id });
                                    else setRowAction(row.row_idx, v);
                                  }}
                                >
                                  <SelectTrigger className="h-8 w-32 text-xs rounded-sm" data-testid={`resolve-${row.row_idx}`}>
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {row.default_action === 'update' && <SelectItem value="update">Update</SelectItem>}
                                    {row.default_action === 'create' && <SelectItem value="create">Create</SelectItem>}
                                    {row.default_action === 'update' && <SelectItem value="create">Create New Instead</SelectItem>}
                                    <SelectItem value="skip">Skip</SelectItem>
                                  </SelectContent>
                                </Select>
                              )}
                            </td>
                          </tr>
                          {expanded && (
                            <tr className="bg-slate-50/60">
                              <td colSpan={8} className="px-6 py-3">
                                {row.candidates.length > 0 && (
                                  <div className="mb-3">
                                    <div className="text-[10px] uppercase tracking-wide text-slate-500 mb-1">Existing match{row.candidates.length > 1 ? 'es' : ''}</div>
                                    <div className="space-y-1">
                                      {row.candidates.map((c) => (
                                        <div key={c.id} className="flex flex-wrap items-center gap-2 text-xs bg-white border border-slate-200 rounded-sm px-2 py-1.5" data-testid={`candidate-${row.row_idx}-${c.id}`}>
                                          <span className="font-mono text-[#00205B]">{c.capid}</span>
                                          <span className="font-medium">{c.last_name}, {c.first_name}</span>
                                          <span className="text-slate-500">{c.rank || '—'}</span>
                                          <span className="text-slate-500">{c.unit || '—'} / {c.wing || '—'}</span>
                                          <span className="text-slate-500">{c.email || '—'}</span>
                                          <span className="px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded-sm">{c.participant_type || '—'}</span>
                                          {c.flight && <span className="px-1.5 py-0.5 bg-blue-100 text-blue-800 rounded-sm">{c.flight}</span>}
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                                {hasChanges && (
                                  <div>
                                    <div className="text-[10px] uppercase tracking-wide text-slate-500 mb-1">Field changes (when updating)</div>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-1">
                                      {Object.entries(row.changes).map(([f, ch]) => (
                                        <div key={f} className="flex items-center gap-2 text-xs bg-white border border-slate-200 rounded-sm px-2 py-1">
                                          <span className="font-medium text-slate-700 w-24 truncate">{FIELD_LABELS[f] || f}</span>
                                          <span className="text-slate-500 line-through">{fmtVal(ch.old)}</span>
                                          <span className="text-slate-400">→</span>
                                          <span className="text-emerald-700 font-medium">{fmtVal(ch.new)}</span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                                {!hasChanges && row.candidates.length === 0 && (
                                  <div className="text-xs text-slate-500">No additional details.</div>
                                )}
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>

            {/* Footer */}
            <div className="mt-3 flex items-center justify-between gap-2">
              <div className="text-xs text-slate-500">
                Staging expires in 2 hours. Close to discard.
              </div>
              <div className="flex gap-2">
                <Button variant="outline" className="rounded-sm" onClick={onClose} disabled={applying} data-testid="import-cancel">
                  Cancel
                </Button>
                <Button
                  className="rounded-sm bg-[#00205B] hover:bg-[#001540] text-white"
                  onClick={handleApply}
                  disabled={applying || unresolvedConflicts > 0}
                  data-testid="import-apply"
                >
                  {applying ? (
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <CheckCircle className="w-4 h-4 mr-2" />
                  )}
                  Apply Import
                </Button>
              </div>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default ImportPreviewModal;
