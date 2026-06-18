import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import {
  MessageSquare, AlertTriangle, Send, CheckCircle2, Clock, ChevronDown, ChevronUp,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Textarea } from '../../components/ui/textarea';
import {
  listAllParentMessages, execReplyToParentMessage, updateParentMessageStatus,
} from '../../services/api';

/** Exec Staff inbox of parent messages.
 *
 * Sits at the top of the Admin tab alongside `ReviewQueueWidget` and
 * `FinanceReviewWidget`. Hides itself when there are no open threads
 * (so the admin dashboard stays clean for low-volume days).
 */
const URGENCY_STYLE = {
  emergency: { bg: 'bg-red-100', text: 'text-red-700', label: '🚨 EMERGENCY' },
  urgent:    { bg: 'bg-amber-100', text: 'text-amber-700', label: '⚠️ URGENT' },
  question:  { bg: 'bg-slate-100', text: 'text-slate-600', label: '📋 Question' },
};
const STATUS_LABEL = { open: 'Awaiting reply', in_progress: 'In progress', resolved: 'Resolved' };
const STATUS_STYLE = {
  open: 'bg-amber-100 text-amber-700',
  in_progress: 'bg-blue-100 text-blue-700',
  resolved: 'bg-emerald-100 text-emerald-700',
};

const fmtDate = (iso) => {
  if (!iso) return '';
  return new Date(iso).toLocaleString(undefined,
    { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
};

export default function ExecParentMessagesWidget() {
  const [data, setData] = useState({ messages: [], open_count: 0, emergency_open: 0, total: 0 });
  const [showResolved, setShowResolved] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [replyDrafts, setReplyDrafts] = useState({});
  const [working, setWorking] = useState(false);

  const reload = useCallback(async () => {
    try {
      const d = await listAllParentMessages();
      setData(d);
    } catch (e) {
      // Silently fail — widget hides on error
      console.warn('Parent messages widget load failed', e);
    }
  }, []);

  useEffect(() => {
    reload();
    const t = setInterval(reload, 30000);  // refresh every 30s
    return () => clearInterval(t);
  }, [reload]);

  const sendReply = async (id) => {
    const text = (replyDrafts[id] || '').trim();
    if (!text) return;
    setWorking(true);
    try {
      await execReplyToParentMessage(id, text);
      toast.success('Reply sent to parent (and emailed)');
      setReplyDrafts(prev => ({ ...prev, [id]: '' }));
      reload();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Reply failed');
    } finally { setWorking(false); }
  };

  const setStatus = async (id, status) => {
    setWorking(true);
    try {
      await updateParentMessageStatus(id, status);
      toast.success(`Marked ${STATUS_LABEL[status] || status}`);
      reload();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Status update failed');
    } finally { setWorking(false); }
  };

  // Hide widget entirely when there's nothing to act on
  if (data.total === 0) return null;

  const visible = showResolved
    ? data.messages
    : data.messages.filter(m => m.status !== 'resolved');

  return (
    <Card data-testid="exec-parent-messages-widget" className="rounded-sm border-l-4 border-l-blue-500">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle className="flex items-center gap-2 text-base font-bold uppercase tracking-tight text-[#00205B]">
            <MessageSquare className="w-4 h-4" /> Parent Messages
            {data.emergency_open > 0 && (
              <span className="ml-2 inline-flex items-center gap-1 text-[10px] uppercase font-bold bg-red-600 text-white px-2 py-0.5 rounded-sm animate-pulse">
                <AlertTriangle className="w-3 h-3" /> {data.emergency_open} emergency
              </span>
            )}
            <span className="ml-1 inline-block text-[10px] uppercase font-bold bg-amber-100 text-amber-700 px-2 py-0.5 rounded-sm">
              {data.open_count} open
            </span>
          </CardTitle>
          <button
            onClick={() => setShowResolved(s => !s)}
            className="text-[10px] uppercase tracking-widest text-slate-500 hover:text-slate-800"
            data-testid="toggle-resolved-parent-messages">
            {showResolved ? 'Hide resolved' : `Show resolved (${data.total - data.open_count})`}
          </button>
        </div>
      </CardHeader>

      <CardContent className="space-y-1.5">
        {visible.map(m => {
          const urgency = URGENCY_STYLE[m.urgency] || URGENCY_STYLE.question;
          const isOpen = expandedId === m.id;
          const lastReply = m.thread?.[m.thread.length - 1];
          const lastIsParent = lastReply?.from_role === 'parent';
          return (
            <div key={m.id}
                 className="border border-slate-200 rounded-sm bg-white"
                 data-testid={`exec-thread-${m.id}`}>
              <button onClick={() => setExpandedId(isOpen ? null : m.id)}
                      className="w-full text-left p-2.5 flex items-center gap-2 hover:bg-slate-50">
                <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded-sm ${urgency.bg} ${urgency.text}`}>
                  {urgency.label}
                </span>
                <span className="flex-1 min-w-0">
                  <span className="block text-sm font-medium text-slate-800 truncate">{m.subject}</span>
                  <span className="block text-[10px] text-slate-500">
                    From <strong>{m.parent_name}</strong>
                    {m.cadet_name && ` — parent of ${m.cadet_name}`}
                    · {m.thread?.length || 0} msg · {fmtDate(m.updated_at)}
                    {lastIsParent && m.status !== 'resolved' && (
                      <span className="ml-1 text-red-600 font-bold">· needs reply</span>
                    )}
                  </span>
                </span>
                <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded-sm ${STATUS_STYLE[m.status] || ''}`}>
                  {STATUS_LABEL[m.status] || m.status}
                </span>
                {isOpen ? <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
                        : <ChevronDown className="w-3.5 h-3.5 text-slate-400" />}
              </button>

              {isOpen && (
                <div className="border-t border-slate-100 p-3 space-y-2 bg-slate-50/40">
                  {(m.thread || []).map(r => (
                    <div key={r.id}
                         className={`text-xs ${r.from_role === 'exec' ? 'ml-4 bg-blue-50 border border-blue-200' : 'mr-4 bg-white border border-slate-200'} rounded-sm p-2`}>
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="font-bold text-slate-800">
                          {r.from_role === 'exec' ? '🛡️ ' : '👤 '}{r.from_name}
                        </span>
                        <span className="text-[10px] text-slate-400 flex items-center gap-1">
                          <Clock className="w-3 h-3" /> {fmtDate(r.created_at)}
                        </span>
                      </div>
                      <div className="text-slate-700 whitespace-pre-wrap leading-relaxed">{r.body}</div>
                    </div>
                  ))}

                  {m.status !== 'resolved' ? (
                    <>
                      <div className="flex gap-2 items-end mt-2">
                        <Textarea
                          value={replyDrafts[m.id] || ''}
                          onChange={e => setReplyDrafts(prev => ({ ...prev, [m.id]: e.target.value }))}
                          placeholder="Reply to the parent…"
                          rows={2}
                          className="rounded-sm text-xs flex-1"
                          data-testid={`exec-reply-input-${m.id}`}
                          maxLength={5000}
                        />
                        <Button onClick={() => sendReply(m.id)}
                                disabled={working || !(replyDrafts[m.id] || '').trim()}
                                data-testid={`exec-reply-btn-${m.id}`}
                                className="bg-[#00205B] hover:bg-[#001540] rounded-sm h-9">
                          <Send className="w-3 h-3 mr-1" /> Reply
                        </Button>
                      </div>
                      <div className="flex gap-2 justify-end">
                        {m.status === 'open' && (
                          <Button size="sm" variant="outline" className="text-xs rounded-sm"
                                  onClick={() => setStatus(m.id, 'in_progress')}
                                  data-testid={`exec-mark-progress-${m.id}`}>
                            Mark In-Progress
                          </Button>
                        )}
                        <Button size="sm" variant="outline" className="text-xs rounded-sm text-emerald-700 border-emerald-200"
                                onClick={() => setStatus(m.id, 'resolved')}
                                data-testid={`exec-mark-resolved-${m.id}`}>
                          <CheckCircle2 className="w-3 h-3 mr-1" /> Resolve
                        </Button>
                      </div>
                    </>
                  ) : (
                    <div className="flex items-center justify-between text-[10px] mt-1">
                      <span className="text-emerald-700 font-bold flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Resolved
                      </span>
                      <Button size="sm" variant="ghost" className="text-xs"
                              onClick={() => setStatus(m.id, 'open')}
                              data-testid={`exec-reopen-${m.id}`}>
                        Re-open
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
