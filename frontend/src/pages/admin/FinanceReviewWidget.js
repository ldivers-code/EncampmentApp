import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import { Link } from 'react-router-dom';
import { DollarSign, AlertTriangle, Send, RefreshCw, ExternalLink, CheckCircle } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { getFinanceNeedsReview, notifyFinanceReview } from '../../services/api';

/**
 * Phase 10 widget — surfaces paid roster rows whose SubEvent is blank or a
 * Parent event (so we couldn't auto-bucket them in the budget). Lets the
 * admin re-send the finance-review email manually when SendGrid is finally
 * configured on production.
 */
const FinanceReviewWidget = () => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState({ count: 0, rows: [], notify_to: [], notify_cc: [] });
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getFinanceNeedsReview();
      setData(result);
    } catch (err) {
      // 403 just means the caller isn't a finance/admin role; quietly hide.
      if (err?.response?.status !== 403) {
        toast.error(err.response?.data?.detail || 'Could not load finance review list');
      }
      setData({ count: 0, rows: [], notify_to: [], notify_cc: [] });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleNotify = async () => {
    setSending(true);
    try {
      const result = await notifyFinanceReview();
      if (result.sent) {
        toast.success(result.message);
      } else {
        toast.warning(result.message);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not send notification');
    } finally {
      setSending(false);
    }
  };

  // Hide the widget entirely if the API returned forbidden (we won't have
  // permission anyway) or the load completed with no data structure.
  if (loading) {
    return (
      <div className="bg-white border border-slate-200 rounded-sm p-4 flex items-center gap-3" data-testid="finance-review-widget-loading">
        <RefreshCw className="w-4 h-4 text-slate-400 animate-spin" />
        <span className="text-sm text-slate-400">Loading finance review status…</span>
      </div>
    );
  }

  // All-clear card
  if (data.count === 0) {
    return (
      <div
        className="bg-white border border-emerald-200 rounded-sm p-4 flex items-center justify-between gap-4"
        data-testid="finance-review-widget-empty"
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-sm bg-emerald-50 flex items-center justify-center">
            <CheckCircle className="w-5 h-5 text-emerald-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900">Finance Review: All Clear</p>
            <p className="text-xs text-slate-500">No paid rows are waiting for manual classification.</p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={load}
          className="rounded-sm text-slate-500"
          data-testid="finance-review-refresh"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </Button>
      </div>
    );
  }

  const totalAmount = data.rows.reduce((sum, r) => sum + (Number(r.amount_paid) || 0), 0);
  const visible = data.rows.slice(0, 5);

  return (
    <div
      className="bg-white border border-orange-300 rounded-sm overflow-hidden"
      data-testid="finance-review-widget"
    >
      <div className="bg-orange-50 px-4 py-3 border-b border-orange-200 flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-sm bg-white border border-orange-300 flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-orange-600" />
          </div>
          <div>
            <p className="text-sm font-bold text-orange-900 flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              Pending Finance Review
              <span
                className="text-[11px] uppercase tracking-wider bg-orange-600 text-white px-1.5 py-0.5 rounded-sm"
                data-testid="finance-review-count"
              >
                {data.count}
              </span>
            </p>
            <p className="text-xs text-orange-800">
              {data.count} paid {data.count === 1 ? 'row' : 'rows'} totaling{' '}
              <span className="font-mono font-semibold">${totalAmount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>{' '}
              need manual classification (blank or Parent SubEvent).
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="rounded-sm border-orange-300 text-orange-700 hover:bg-orange-100"
            onClick={load}
            data-testid="finance-review-refresh"
            title="Refresh list"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Button
            size="sm"
            className="rounded-sm bg-[#00205B] hover:bg-[#001640]"
            disabled={sending || (data.notify_to.length === 0 && data.notify_cc.length === 0)}
            onClick={handleNotify}
            data-testid="finance-review-notify-btn"
          >
            <Send className="w-3.5 h-3.5 mr-1.5" />
            {sending ? 'Sending…' : 'Notify Finance Officer'}
          </Button>
        </div>
      </div>

      {/* Recipient summary */}
      {(data.notify_to.length > 0 || data.notify_cc.length > 0) && (
        <div className="px-4 py-2 text-[11px] text-slate-500 bg-slate-50 border-b border-slate-100 break-words">
          <span className="font-semibold">Will notify:</span>{' '}
          {data.notify_to.join(', ') || '—'}
          {data.notify_cc.length > 0 && (
            <>
              {' '}<span className="text-slate-400">·</span>{' '}
              <span className="font-semibold">cc:</span>{' '}
              {data.notify_cc.join(', ')}
            </>
          )}
        </div>
      )}
      {data.notify_to.length === 0 && data.notify_cc.length === 0 && (
        <div className="px-4 py-2 text-[11px] text-rose-600 bg-rose-50 border-b border-rose-100">
          No finance / admin recipients found. Assign at least one user the
          "Finance" role before notifying.
        </div>
      )}

      {/* Sample rows */}
      <ul className="divide-y divide-slate-100 text-sm">
        {visible.map((r) => (
          <li
            key={r.id}
            className="px-4 py-2 flex items-center justify-between gap-3"
            data-testid={`finance-review-row-${r.capid}`}
          >
            <div className="min-w-0 flex-1">
              <p className="font-medium text-slate-900 truncate">
                {r.name}{' '}
                <span className="text-slate-400 font-mono text-xs">CAPID {r.capid}</span>
              </p>
              <p className="text-xs text-slate-500 truncate">
                SubEvent: <span className="font-mono">{r.event_name || <em>blank</em>}</span>
                {r.member_type && (
                  <>
                    <span className="mx-1.5 text-slate-300">·</span>
                    <span className="uppercase text-[10px] tracking-wider">{r.member_type}</span>
                  </>
                )}
              </p>
            </div>
            <span className="font-mono text-sm text-slate-900 whitespace-nowrap">
              ${Number(r.amount_paid || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </span>
          </li>
        ))}
      </ul>

      <div className="px-4 py-2 flex items-center justify-between bg-slate-50 border-t border-slate-100">
        {data.count > visible.length ? (
          <span className="text-xs text-slate-500">
            + {data.count - visible.length} more not shown
          </span>
        ) : <span />}
        <Link
          to="/roster?category=needs_review"
          className="text-xs text-[#00205B] hover:underline flex items-center gap-1"
          data-testid="finance-review-open-roster"
        >
          Open Roster → Needs Review <ExternalLink className="w-3 h-3" />
        </Link>
      </div>
    </div>
  );
};

export default FinanceReviewWidget;
