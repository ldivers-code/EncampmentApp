import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import { Link } from 'react-router-dom';
import {
  AlertCircle, CheckCircle, X, GitMerge, RefreshCw, ExternalLink, UserCheck, UserX,
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../../components/ui/select';
import {
  getReviewQueue, getReviewQueueStats, resolveReviewQueueRow, getParticipants,
} from '../../services/api';

/**
 * Surfaces every participant flagged for human review:
 *  - Blank SubEvents on upload → participant_type='needs_review'
 *  - Existed in app but missing from latest spreadsheet → review_status='needs_review'
 *
 * One-click actions: approve as student / cadre / senior_staff, mark cancelled,
 * or merge into an existing participant.
 */
const ReviewQueueWidget = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ total: 0, blank_subevents: 0, missing_from_upload: 0, legacy: 0 });
  const [rows, setRows] = useState([]);
  const [expanded, setExpanded] = useState(false);
  const [busyId, setBusyId] = useState(null);

  // Per-row merge target selector
  const [mergeOpenFor, setMergeOpenFor] = useState(null);
  const [allParticipants, setAllParticipants] = useState([]);
  const [mergeTargetId, setMergeTargetId] = useState('');
  const [mergeFilter, setMergeFilter] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, r] = await Promise.all([getReviewQueueStats(), getReviewQueue()]);
      setStats(s);
      setRows(r);
    } catch (err) {
      if (err?.response?.status !== 403) {
        toast.error(err?.response?.data?.detail || 'Could not load review queue');
      }
      setStats({ total: 0, blank_subevents: 0, missing_from_upload: 0, legacy: 0 });
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openMerge = async (row) => {
    setMergeOpenFor(row.id);
    setMergeTargetId('');
    setMergeFilter('');
    if (allParticipants.length === 0) {
      try {
        const all = await getParticipants();
        setAllParticipants(all);
      } catch {
        toast.error('Could not load participant list for merge');
      }
    }
  };

  const doAction = async (row, action) => {
    setBusyId(row.id);
    try {
      const res = await resolveReviewQueueRow(row.id, action);
      toast.success(res.message || 'Resolved');
      setMergeOpenFor(null);
      await load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Action failed');
    } finally {
      setBusyId(null);
    }
  };

  const doMerge = async (row) => {
    if (!mergeTargetId) {
      toast.error('Pick a participant to merge into');
      return;
    }
    setBusyId(row.id);
    try {
      const res = await resolveReviewQueueRow(row.id, 'merge_into', mergeTargetId);
      toast.success(`Merged — carried ${res.fields_carried?.length || 0} field(s)`);
      setMergeOpenFor(null);
      await load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Merge failed');
    } finally {
      setBusyId(null);
    }
  };

  // Hide entirely if no rows AND not still loading
  if (!loading && stats.total === 0) {
    return null;
  }

  const filteredMergeCandidates = allParticipants
    .filter(p => !p.is_removed && p.review_status !== 'needs_review' && p.participant_type !== 'needs_review')
    .filter(p => {
      const q = mergeFilter.trim().toLowerCase();
      if (!q) return true;
      return (
        `${p.first_name} ${p.last_name}`.toLowerCase().includes(q)
        || (p.capid || '').toLowerCase().includes(q)
        || (p.email || '').toLowerCase().includes(q)
      );
    })
    .slice(0, 40);

  return (
    <div className="bg-white border border-amber-200 rounded-sm shadow-sm" data-testid="review-queue-widget">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-amber-200 bg-amber-50">
        <div className="flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600" />
          <div>
            <h3 className="font-bold text-[#00205B] text-sm flex items-center gap-2">
              Review Queue
              {stats.total > 0 && (
                <span className="bg-amber-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-sm">
                  {stats.total}
                </span>
              )}
            </h3>
            <p className="text-[11px] text-slate-500">
              {stats.blank_subevents} blank SubEvents · {stats.missing_from_upload} missing from upload
              {stats.legacy > 0 && ` · ${stats.legacy} other`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button" variant="ghost" size="sm"
            onClick={load}
            className="rounded-sm text-slate-500"
            data-testid="review-queue-refresh"
            disabled={loading}
            aria-label="Refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          {stats.total > 0 && (
            <Button
              type="button" variant="outline" size="sm"
              onClick={() => setExpanded(!expanded)}
              className="rounded-sm"
              data-testid="review-queue-toggle"
            >
              {expanded ? 'Hide' : 'Review now'}
            </Button>
          )}
        </div>
      </div>

      {/* Rows */}
      {expanded && (
        <div className="max-h-96 overflow-y-auto divide-y divide-slate-200">
          {loading && (
            <div className="px-4 py-6 text-center text-xs text-slate-400">Loading…</div>
          )}
          {!loading && rows.length === 0 && (
            <div className="px-4 py-6 text-center text-xs text-slate-400">
              Nothing to review.
            </div>
          )}
          {rows.map((row) => {
            const isMerging = mergeOpenFor === row.id;
            const isBusy = busyId === row.id;
            return (
              <div key={row.id} className="px-4 py-3 hover:bg-slate-50" data-testid={`review-row-${row.id}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Link
                        to={`/roster?capid=${row.capid || ''}`}
                        className="font-bold text-sm text-[#00205B] hover:underline flex items-center gap-1"
                      >
                        {row.first_name} {row.last_name}
                        <ExternalLink className="w-3 h-3 text-slate-400" />
                      </Link>
                      {row.capid && (
                        <span className="text-[10px] font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">
                          CAPID {row.capid}
                        </span>
                      )}
                      {row.rank && (
                        <span className="text-[10px] bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">
                          {row.rank}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-amber-800 mt-1 italic">
                      {row.review_reason || 'Flagged for review'}
                    </p>
                    {row.review_flagged_at && (
                      <p className="text-[10px] text-slate-400 mt-0.5">
                        Flagged: {new Date(row.review_flagged_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>

                {/* Actions */}
                {!isMerging && (
                  <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                    <Button
                      type="button" size="sm" variant="outline"
                      className="rounded-sm text-xs h-7 border-blue-300 text-blue-700 hover:bg-blue-50"
                      disabled={isBusy}
                      onClick={() => doAction(row, 'approve_as_student')}
                      data-testid={`review-approve-student-${row.id}`}
                    >
                      <UserCheck className="w-3 h-3 mr-1" /> Approve as Student
                    </Button>
                    <Button
                      type="button" size="sm" variant="outline"
                      className="rounded-sm text-xs h-7 border-emerald-300 text-emerald-700 hover:bg-emerald-50"
                      disabled={isBusy}
                      onClick={() => doAction(row, 'approve_as_cadre')}
                      data-testid={`review-approve-cadre-${row.id}`}
                    >
                      <UserCheck className="w-3 h-3 mr-1" /> Cadre
                    </Button>
                    <Button
                      type="button" size="sm" variant="outline"
                      className="rounded-sm text-xs h-7 border-amber-300 text-amber-700 hover:bg-amber-50"
                      disabled={isBusy}
                      onClick={() => doAction(row, 'approve_as_senior_staff')}
                      data-testid={`review-approve-staff-${row.id}`}
                    >
                      <UserCheck className="w-3 h-3 mr-1" /> Sr Staff
                    </Button>
                    <Button
                      type="button" size="sm" variant="outline"
                      className="rounded-sm text-xs h-7 border-violet-300 text-violet-700 hover:bg-violet-50"
                      disabled={isBusy}
                      onClick={() => openMerge(row)}
                      data-testid={`review-merge-${row.id}`}
                    >
                      <GitMerge className="w-3 h-3 mr-1" /> Merge
                    </Button>
                    <Button
                      type="button" size="sm" variant="outline"
                      className="rounded-sm text-xs h-7 border-rose-300 text-rose-700 hover:bg-rose-50"
                      disabled={isBusy}
                      onClick={() => doAction(row, 'mark_cancelled')}
                      data-testid={`review-cancel-${row.id}`}
                    >
                      <UserX className="w-3 h-3 mr-1" /> Cancel
                    </Button>
                  </div>
                )}

                {/* Merge picker */}
                {isMerging && (
                  <div className="mt-2 p-2 bg-violet-50 border border-violet-200 rounded-sm">
                    <p className="text-[11px] text-violet-900 mb-1.5">
                      Pick the existing participant to merge <strong>{row.first_name} {row.last_name}</strong> into.
                      Their non-empty fields will fill any blanks on the target row.
                    </p>
                    <input
                      type="text"
                      placeholder="Search by name, CAPID, or email…"
                      value={mergeFilter}
                      onChange={(e) => setMergeFilter(e.target.value)}
                      className="w-full text-xs px-2 py-1 border border-violet-300 rounded-sm mb-1.5"
                      data-testid={`merge-search-${row.id}`}
                    />
                    <Select value={mergeTargetId} onValueChange={setMergeTargetId}>
                      <SelectTrigger className="h-8 text-xs rounded-sm" data-testid={`merge-target-${row.id}`}>
                        <SelectValue placeholder="Select target participant" />
                      </SelectTrigger>
                      <SelectContent>
                        {filteredMergeCandidates.map(p => (
                          <SelectItem key={p.id} value={p.id}>
                            {p.last_name}, {p.first_name} {p.capid ? `· ${p.capid}` : ''} {p.participant_type ? `· ${p.participant_type}` : ''}
                          </SelectItem>
                        ))}
                        {filteredMergeCandidates.length === 0 && (
                          <SelectItem value="__none__" disabled>No matches</SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                    <div className="flex items-center gap-1.5 mt-2">
                      <Button
                        type="button" size="sm"
                        className="rounded-sm text-xs h-7 bg-violet-600 hover:bg-violet-700 text-white"
                        disabled={isBusy || !mergeTargetId}
                        onClick={() => doMerge(row)}
                        data-testid={`merge-confirm-${row.id}`}
                      >
                        <CheckCircle className="w-3 h-3 mr-1" /> Confirm Merge
                      </Button>
                      <Button
                        type="button" size="sm" variant="ghost"
                        className="rounded-sm text-xs h-7"
                        onClick={() => setMergeOpenFor(null)}
                      >
                        <X className="w-3 h-3 mr-1" /> Cancel
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ReviewQueueWidget;
