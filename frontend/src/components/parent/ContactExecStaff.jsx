import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import {
  Mail, Phone, Send, AlertTriangle, Clock, CheckCircle2, MessageCircle, ChevronDown, ChevronUp,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Label } from '../ui/label';
import {
  getExecStaffContacts, createParentMessage, listParentMessages, parentReplyToMessage,
} from '../../services/api';

/** Contact Exec Staff — used inside the Parent Portal (`MyCadetPage`).
 *
 * Three sections:
 *   1. **Contact card list** — names + email + phone of every approved
 *      `role=executive_staff` user, pulled from `GET /api/parent/exec-contacts`.
 *   2. **New-message form** — subject / urgency / body. Submits to
 *      `POST /api/parent/messages`; backend emails Exec Staff via SendGrid.
 *   3. **Inbox** — the parent's own threads. Tap to expand → see replies and
 *      add a follow-up via `POST /api/parent/messages/{id}/reply`.
 */
const URGENCY = [
  { value: 'question',  label: 'Question',   color: 'text-slate-600', bg: 'bg-slate-100' },
  { value: 'urgent',    label: 'Urgent',     color: 'text-amber-700', bg: 'bg-amber-100' },
  { value: 'emergency', label: 'EMERGENCY',  color: 'text-red-700',   bg: 'bg-red-100' },
];
const STATUS_LABEL = { open: 'Awaiting response', in_progress: 'In progress', resolved: 'Resolved' };
const STATUS_STYLE = {
  open: 'bg-amber-100 text-amber-700',
  in_progress: 'bg-blue-100 text-blue-700',
  resolved: 'bg-emerald-100 text-emerald-700',
};

const fmtDate = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
};

export default function ContactExecStaff() {
  const [contacts, setContacts] = useState([]);
  const [contactsNote, setContactsNote] = useState(null);
  const [threads, setThreads] = useState([]);
  const [expandedId, setExpandedId] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const [form, setForm] = useState({ subject: '', body: '', urgency: 'question' });
  const [replyDrafts, setReplyDrafts] = useState({});  // {messageId: text}

  const reload = useCallback(async () => {
    try {
      const [c, t] = await Promise.all([getExecStaffContacts(), listParentMessages()]);
      setContacts(c.contacts || []);
      setContactsNote(c.note || null);
      setThreads(t || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to load Exec Staff contacts');
    }
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const submit = async (e) => {
    e?.preventDefault();
    if (!form.subject.trim() || !form.body.trim()) {
      toast.error('Please add a subject and a message body.'); return;
    }
    setSubmitting(true);
    try {
      const res = await createParentMessage(form.subject.trim(), form.body.trim(), form.urgency);
      const label = URGENCY.find(u => u.value === form.urgency)?.label || form.urgency;
      const tail = res.email_sent
        ? ` — Exec Staff has been emailed (${res.recipients_count} recipient${res.recipients_count === 1 ? '' : 's'}).`
        : ' — saved. Exec Staff will see it on their next portal refresh.';
      toast.success(`${label === 'EMERGENCY' ? '🚨 ' : ''}Message sent${tail}`);
      setForm({ subject: '', body: '', urgency: 'question' });
      reload();
    } catch (e2) {
      toast.error(e2?.response?.data?.detail || 'Send failed');
    } finally { setSubmitting(false); }
  };

  const sendReply = async (messageId) => {
    const text = (replyDrafts[messageId] || '').trim();
    if (!text) return;
    try {
      await parentReplyToMessage(messageId, text);
      toast.success('Reply sent');
      setReplyDrafts(prev => ({ ...prev, [messageId]: '' }));
      reload();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Reply failed');
    }
  };

  return (
    <Card data-testid="contact-exec-staff-widget" className="rounded-sm">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base font-bold uppercase tracking-tight text-[#00205B]">
          <MessageCircle className="w-4 h-4" /> Contact Exec Staff
        </CardTitle>
        <p className="text-xs text-slate-500 mt-1">
          For questions, urgent issues, or emergencies — your message is delivered to
          Exec Staff by email <em>and</em> stored here so you can track replies.
        </p>
      </CardHeader>

      <CardContent className="space-y-5">
        {/* === Contact card list === */}
        <section>
          <div className="text-[10px] uppercase tracking-widest text-slate-400 font-semibold mb-2">
            Exec Staff
          </div>
          {contacts.length === 0 ? (
            <div className="text-xs text-slate-500 italic">
              {contactsNote || 'Exec Staff contacts not yet published. Send a message — it will still reach them.'}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {contacts.map(c => (
                <div key={c.id}
                     className="border border-slate-200 rounded-sm p-2.5 bg-white text-xs"
                     data-testid={`exec-contact-${c.id}`}>
                  <div className="font-bold text-slate-800">{c.name || 'Exec Staff member'}</div>
                  <div className="text-[10px] uppercase tracking-widest text-slate-400">{c.position_title}</div>
                  <div className="mt-1 flex flex-col gap-0.5">
                    {c.email && (
                      <a className="flex items-center gap-1 text-[#00205B] hover:underline"
                         href={`mailto:${c.email}`}>
                        <Mail className="w-3 h-3" /> {c.email}
                      </a>
                    )}
                    {c.phone && (
                      <a className="flex items-center gap-1 text-[#00205B] hover:underline"
                         href={`tel:${c.phone}`}>
                        <Phone className="w-3 h-3" /> {c.phone}
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* === New message form === */}
        <section>
          <div className="text-[10px] uppercase tracking-widest text-slate-400 font-semibold mb-2">
            Send a New Message
          </div>
          <form onSubmit={submit} className="space-y-2.5 bg-slate-50 border border-slate-200 rounded-sm p-3">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <div className="sm:col-span-2">
                <Label htmlFor="parent-msg-subject" className="text-xs">Subject</Label>
                <Input
                  id="parent-msg-subject"
                  data-testid="parent-msg-subject"
                  value={form.subject}
                  onChange={e => setForm(f => ({ ...f, subject: e.target.value }))}
                  placeholder="e.g. Question about meal pickup time"
                  className="rounded-sm h-9 text-sm"
                  maxLength={200}
                />
              </div>
              <div>
                <Label className="text-xs">Urgency</Label>
                <div className="flex gap-1 mt-1">
                  {URGENCY.map(u => (
                    <button
                      key={u.value} type="button"
                      onClick={() => setForm(f => ({ ...f, urgency: u.value }))}
                      data-testid={`parent-msg-urgency-${u.value}`}
                      className={`flex-1 text-[10px] uppercase tracking-widest font-bold rounded-sm py-1.5 transition
                        ${form.urgency === u.value ? `${u.bg} ${u.color} ring-2 ring-offset-1 ring-current` : 'bg-white text-slate-500 border border-slate-200'}`}>
                      {u.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div>
              <Label htmlFor="parent-msg-body" className="text-xs">Message</Label>
              <Textarea
                id="parent-msg-body"
                data-testid="parent-msg-body"
                value={form.body}
                onChange={e => setForm(f => ({ ...f, body: e.target.value }))}
                placeholder="Tell Exec Staff what you need…"
                className="rounded-sm text-sm"
                rows={4}
                maxLength={5000}
              />
            </div>
            {form.urgency === 'emergency' && (
              <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-sm p-2 text-xs text-red-700">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <div>
                  <strong>For life-threatening emergencies, also call 911 directly.</strong> This
                  channel is monitored by Exec Staff but is not a substitute for emergency services.
                </div>
              </div>
            )}
            <div className="flex justify-end">
              <Button type="submit" disabled={submitting}
                      data-testid="parent-msg-send-btn"
                      className="bg-[#00205B] hover:bg-[#001540] rounded-sm">
                <Send className="w-3.5 h-3.5 mr-1.5" />
                {submitting ? 'Sending…' : 'Send to Exec Staff'}
              </Button>
            </div>
          </form>
        </section>

        {/* === Inbox === */}
        <section>
          <div className="text-[10px] uppercase tracking-widest text-slate-400 font-semibold mb-2">
            My Messages ({threads.length})
          </div>
          {threads.length === 0 ? (
            <div className="text-xs text-slate-500 italic">No messages yet.</div>
          ) : (
            <div className="space-y-1.5">
              {threads.map(t => {
                const isOpen = expandedId === t.id;
                const urgency = URGENCY.find(u => u.value === t.urgency) || URGENCY[0];
                const lastReply = t.thread?.[t.thread.length - 1];
                const lastIsExec = lastReply?.from_role === 'exec';
                return (
                  <div key={t.id} className="border border-slate-200 rounded-sm bg-white"
                       data-testid={`parent-thread-${t.id}`}>
                    <button
                      onClick={() => setExpandedId(isOpen ? null : t.id)}
                      className="w-full text-left p-2.5 flex items-center gap-2 hover:bg-slate-50">
                      <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded-sm ${urgency.bg} ${urgency.color}`}>
                        {urgency.label}
                      </span>
                      <span className="flex-1 min-w-0">
                        <span className="block text-sm font-medium text-slate-800 truncate">{t.subject}</span>
                        <span className="block text-[10px] text-slate-500">
                          {t.thread?.length || 0} message{(t.thread?.length || 0) === 1 ? '' : 's'} · last updated {fmtDate(t.updated_at)}
                          {lastIsExec && <span className="ml-1 text-emerald-600 font-bold">· NEW REPLY</span>}
                        </span>
                      </span>
                      <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded-sm ${STATUS_STYLE[t.status] || ''}`}>
                        {STATUS_LABEL[t.status] || t.status}
                      </span>
                      {isOpen ? <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
                              : <ChevronDown className="w-3.5 h-3.5 text-slate-400" />}
                    </button>

                    {isOpen && (
                      <div className="border-t border-slate-100 p-3 space-y-2 bg-slate-50/40">
                        {(t.thread || []).map(r => (
                          <div key={r.id}
                               className={`text-xs ${r.from_role === 'exec' ? 'ml-4 bg-blue-50 border border-blue-200' : 'mr-4 bg-white border border-slate-200'} rounded-sm p-2`}>
                            <div className="flex items-center justify-between gap-2 mb-1">
                              <span className="font-bold text-slate-800">
                                {r.from_role === 'exec' ? '🛡️ ' : ''}{r.from_name}
                              </span>
                              <span className="text-[10px] text-slate-400 flex items-center gap-1">
                                <Clock className="w-3 h-3" /> {fmtDate(r.created_at)}
                              </span>
                            </div>
                            <div className="text-slate-700 whitespace-pre-wrap leading-relaxed">{r.body}</div>
                          </div>
                        ))}

                        {t.status !== 'resolved' ? (
                          <div className="flex gap-2 items-end mt-2">
                            <Textarea
                              value={replyDrafts[t.id] || ''}
                              onChange={e => setReplyDrafts(prev => ({ ...prev, [t.id]: e.target.value }))}
                              placeholder="Add a follow-up…"
                              rows={2}
                              className="rounded-sm text-xs flex-1"
                              data-testid={`parent-reply-input-${t.id}`}
                              maxLength={5000}
                            />
                            <Button onClick={() => sendReply(t.id)}
                                    disabled={!(replyDrafts[t.id] || '').trim()}
                                    data-testid={`parent-reply-btn-${t.id}`}
                                    className="bg-[#00205B] hover:bg-[#001540] rounded-sm h-9">
                              <Send className="w-3 h-3 mr-1" /> Reply
                            </Button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1.5 text-[10px] text-emerald-700 font-bold mt-1">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Thread marked resolved by Exec Staff.
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </CardContent>
    </Card>
  );
}
