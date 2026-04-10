import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { toast } from 'sonner';
import axios from 'axios';
import {
  ClipboardList, Plus, Send, CheckCircle, Clock, AlertTriangle,
  FileUp, Award, Trash2, Bell, Download, Users, User, X, ArrowLeft,
  BookOpen, Paperclip, MessageSquare, ChevronRight, GraduationCap,
  Eye, FileText, Upload, Shield
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Input } from '../components/ui/input';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const CREATOR_ROLES = ['exec_cadre', 'executive_staff', 'training_officer', 'commander', 'dcp'];

const SQUADRON_LABELS = {
  '6th_cts': '6th CTS',
  '21st_cts': '21st CTS',
  '22nd_cts': '22nd CTS',
};

const FLIGHT_LABELS = {
  alpha: 'Alpha', bravo: 'Bravo', charlie: 'Charlie',
  delta: 'Delta', echo: 'Echo', foxtrot: 'Foxtrot',
};

export default function AssignmentsPage() {
  const { user } = useAuth();
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openId, setOpenId] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [flights, setFlights] = useState([]);
  const [squadrons, setSquadrons] = useState([]);
  const [allUsers, setAllUsers] = useState([]);

  const isCreator = CREATOR_ROLES.includes(user?.role);

  const fetchAssignments = useCallback(async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API}/assignments`);
      setAssignments(res.data);
    } catch {
      toast.error('Failed to load assignments');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAssignments();
    axios.get(`${API}/flights`).then(r => setFlights(r.data)).catch(() => {});
    axios.get(`${API}/squadrons`).then(r => setSquadrons(r.data)).catch(() => {});
    if (isCreator) {
      axios.get(`${API}/users`).then(r => {
        const users = r.data.filter(u => u.role !== 'parent');
        users.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
        setAllUsers(users);
      }).catch(() => {});
    }
  }, [fetchAssignments, isCreator]);

  if (openId) {
    return (
      <AssignmentDetailView
        assignmentId={openId}
        user={user}
        onBack={() => { setOpenId(null); fetchAssignments(); }}
      />
    );
  }

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="animate-pulse text-slate-400">Loading assignments...</div>
      </div>
    );
  }

  return (
    <div className="p-4 lg:p-8 animate-fade-in" data-testid="assignments-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2" data-testid="assignments-header">
            <BookOpen className="w-6 h-6 text-blue-600" />
            Classwork
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            {assignments.length} assignment{assignments.length !== 1 ? 's' : ''}
          </p>
        </div>
        {isCreator && (
          <Button onClick={() => setShowCreate(true)} className="bg-blue-600 hover:bg-blue-700" data-testid="create-assignment-btn">
            <Plus className="w-4 h-4 mr-2" />
            Create
          </Button>
        )}
      </div>

      {/* Stream */}
      {assignments.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center">
          <BookOpen className="w-14 h-14 text-slate-200 mx-auto mb-4" />
          <p className="text-slate-500 text-lg font-medium">No assignments yet</p>
          <p className="text-slate-400 text-sm mt-1">{isCreator ? 'Create your first assignment to get started.' : 'Check back later for new assignments.'}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {assignments.map(a => (
            <AssignmentCard key={a.id} assignment={a} user={user} isCreator={isCreator}
              onOpen={() => setOpenId(a.id)}
              onDelete={async () => {
                if (!window.confirm('Delete this assignment?')) return;
                try { await axios.delete(`${API}/assignments/${a.id}`); toast.success('Deleted'); fetchAssignments(); }
                catch { toast.error('Delete failed'); }
              }}
              onRemind={async () => {
                try { const r = await axios.post(`${API}/assignments/${a.id}/remind`); toast.success(r.data.message); }
                catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
              }}
            />
          ))}
        </div>
      )}

      {showCreate && (
        <CreateAssignmentDialog
          flights={flights} squadrons={squadrons} allUsers={allUsers}
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); fetchAssignments(); }}
        />
      )}
    </div>
  );
}


/* ── Assignment Card ─────────────────────────────────────────────────── */

function AssignmentCard({ assignment: a, user, isCreator, onOpen, onDelete, onRemind }) {
  const myRole = a.my_role || 'student';
  const now = new Date().toISOString().split('T')[0];
  const isOverdue = a.due_date < now;

  const getStatusBadge = () => {
    if (a.my_submission?.graded) return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700" data-testid="status-graded"><CheckCircle className="w-3 h-3" />Graded</span>;
    if (a.my_submission) return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700" data-testid="status-submitted"><Send className="w-3 h-3" />Submitted</span>;
    if (isOverdue) return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700" data-testid="status-overdue"><AlertTriangle className="w-3 h-3" />Overdue</span>;
    return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700" data-testid="status-pending"><Clock className="w-3 h-3" />Pending</span>;
  };

  const targetLabel = () => {
    if (a.target_type === 'all') return 'All Cadre';
    const parts = [];
    if (a.target_squadrons?.length) parts.push(a.target_squadrons.map(s => SQUADRON_LABELS[s] || s).join(', '));
    if (a.target_flights?.length) parts.push(a.target_flights.map(f => FLIGHT_LABELS[f] || f).join(', '));
    if (a.target_type === 'individual') parts.push('Individual');
    return parts.join(' + ') || 'All Cadre';
  };

  const roleColor = myRole === 'instructor' ? 'text-purple-600 bg-purple-50 border-purple-200'
    : myRole === 'mentor' ? 'text-teal-600 bg-teal-50 border-teal-200'
    : myRole === 'creator' ? 'text-blue-600 bg-blue-50 border-blue-200' : '';

  return (
    <div
      className="bg-white border border-slate-200 rounded-xl hover:shadow-md transition-all cursor-pointer group"
      onClick={onOpen}
      data-testid={`assignment-card-${a.id}`}
    >
      <div className="p-4 sm:p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center shrink-0 mt-0.5">
              <ClipboardList className="w-5 h-5 text-white" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-base font-semibold text-slate-900 group-hover:text-blue-600 transition-colors truncate" data-testid={`assignment-title-${a.id}`}>
                  {a.title}
                </h3>
                {myRole !== 'student' && myRole !== 'creator' && (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded border font-medium uppercase ${roleColor}`}>{myRole}</span>
                )}
                {myRole === 'student' && getStatusBadge()}
              </div>
              <p className="text-sm text-slate-500 mt-0.5 line-clamp-1">{a.description || 'No description'}</p>
              <div className="flex items-center gap-3 mt-2 text-xs text-slate-400 flex-wrap">
                <span>Due <span className="text-slate-600 font-medium">{new Date(a.due_date + 'T00:00:00').toLocaleDateString()}</span></span>
                <span className="hidden sm:inline">{a.created_by_name}</span>
                <span className="flex items-center gap-1"><Users className="w-3 h-3" />{targetLabel()}</span>
                {a.questions?.length > 0 && <span className="flex items-center gap-1"><MessageSquare className="w-3 h-3" />{a.questions.length} Q</span>}
                {a.materials?.length > 0 && <span className="flex items-center gap-1"><Paperclip className="w-3 h-3" />{a.materials.length}</span>}
              </div>
              {/* Instructor / Mentor names */}
              {(a.instructor_names?.length > 0 || a.mentor_names?.length > 0) && (
                <div className="flex items-center gap-3 mt-1.5 text-xs flex-wrap">
                  {a.instructor_names?.length > 0 && (
                    <span className="text-purple-600"><GraduationCap className="w-3 h-3 inline mr-0.5" />{a.instructor_names.join(', ')}</span>
                  )}
                  {a.mentor_names?.length > 0 && (
                    <span className="text-teal-600"><Shield className="w-3 h-3 inline mr-0.5" />{a.mentor_names.join(', ')}</span>
                  )}
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center gap-1 shrink-0" onClick={e => e.stopPropagation()}>
            {(isCreator || myRole === 'instructor') && (
              <>
                <span className="text-[11px] text-slate-500 bg-slate-100 rounded-full px-2.5 py-1 whitespace-nowrap" data-testid={`submission-count-${a.id}`}>
                  {a.submission_count || 0}/{(a.submission_count || 0) + (a.graded_count ? 0 : 0)} sub
                </span>
                <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-blue-600" onClick={onRemind} title="Send reminders" data-testid={`remind-btn-${a.id}`}>
                  <Bell className="w-4 h-4" />
                </Button>
              </>
            )}
            {isCreator && (
              <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-red-600" onClick={onDelete} data-testid={`delete-btn-${a.id}`}>
                <Trash2 className="w-4 h-4" />
              </Button>
            )}
            <ChevronRight className="w-4 h-4 text-slate-300 ml-1" />
          </div>
        </div>
      </div>
    </div>
  );
}


/* ── Assignment Detail View (full page) ──────────────────────────────── */

function AssignmentDetailView({ assignmentId, user, onBack }) {
  const [assignment, setAssignment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('instructions');
  const [showSubmit, setShowSubmit] = useState(false);
  const [gradingSub, setGradingSub] = useState(null);

  const fetchDetail = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/assignments/${assignmentId}`);
      setAssignment(res.data);
    } catch {
      toast.error('Failed to load assignment');
    } finally {
      setLoading(false);
    }
  }, [assignmentId]);

  useEffect(() => { fetchDetail(); }, [fetchDetail]);

  if (loading || !assignment) {
    return <div className="p-8 text-center text-slate-400">Loading...</div>;
  }

  const a = assignment;
  const myRole = a.my_role || 'student';
  const canGrade = myRole === 'creator' || myRole === 'instructor' || CREATOR_ROLES.includes(user?.role);
  const canViewSubs = canGrade || myRole === 'mentor';
  const submissions = a.submissions || [];
  const assignees = a.assignees || [];
  const submittedIds = new Set(submissions.map(s => s.user_id));
  const missing = assignees.filter(x => !submittedIds.has(x.id));

  const tabs = [
    { id: 'instructions', label: 'Instructions', icon: FileText },
    ...(canViewSubs ? [{ id: 'submissions', label: `Submissions (${submissions.length})`, icon: FileUp }] : []),
    ...(canViewSubs ? [{ id: 'people', label: 'People', icon: Users }] : []),
  ];

  return (
    <div className="p-4 lg:p-8 animate-fade-in" data-testid="assignment-detail-view">
      {/* Back button + header */}
      <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-500 hover:text-blue-600 mb-4 transition-colors" data-testid="back-to-assignments">
        <ArrowLeft className="w-4 h-4" /> Back to Classwork
      </button>

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        {/* Header bar */}
        <div className="bg-blue-600 text-white px-6 py-4">
          <h1 className="text-xl font-bold" data-testid="detail-title">{a.title}</h1>
          <div className="flex items-center gap-4 mt-1 text-blue-100 text-sm flex-wrap">
            <span>Due {new Date(a.due_date + 'T00:00:00').toLocaleDateString()}</span>
            <span>{a.max_score} pts</span>
            <span>{a.created_by_name}</span>
            {myRole !== 'student' && (
              <span className="bg-white/20 px-2 py-0.5 rounded text-xs font-medium uppercase">{myRole}</span>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-slate-200 px-6 flex gap-1 overflow-x-auto">
          {tabs.map(t => (
            <button key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                tab === t.id ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
              data-testid={`tab-${t.id}`}
            >
              <t.icon className="w-4 h-4" /> {t.label}
            </button>
          ))}
        </div>

        <div className="p-6">
          {/* Instructions tab */}
          {tab === 'instructions' && (
            <div className="space-y-6">
              {a.description && (
                <div className="prose prose-sm max-w-none text-slate-700" data-testid="assignment-description">
                  <p className="whitespace-pre-wrap">{a.description}</p>
                </div>
              )}

              {/* Target info */}
              <TargetInfo assignment={a} />

              {/* Materials */}
              {a.materials?.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-1"><Paperclip className="w-4 h-4" /> Materials</h3>
                  <div className="space-y-2">
                    {a.materials.map(m => (
                      <a key={m.id} href={`${API}/assignments/${a.id}/materials/${m.id}`}
                        className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 bg-blue-50 px-3 py-2 rounded-lg border border-blue-100"
                        data-testid={`material-${m.id}`}
                      >
                        <Download className="w-4 h-4" /> {m.file_name}
                        {m.file_size && <span className="text-slate-400 text-xs">({(m.file_size / 1024).toFixed(1)} KB)</span>}
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Questions */}
              {a.questions?.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-1"><MessageSquare className="w-4 h-4" /> Questions</h3>
                  <div className="space-y-2">
                    {a.questions.map((q, i) => (
                      <div key={q.id} className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                        <span className="text-xs text-slate-400 font-medium">Q{i + 1}</span>
                        <p className="text-sm text-slate-700 mt-0.5">{q.question_text}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Rubric */}
              {a.rubric?.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-1"><Award className="w-4 h-4" /> Rubric ({a.max_score} pts)</h3>
                  <div className="grid gap-2">
                    {a.rubric.map((r, i) => (
                      <div key={i} className="flex items-center justify-between bg-indigo-50 px-3 py-2 rounded-lg text-sm border border-indigo-100">
                        <div>
                          <span className="font-medium text-slate-800">{r.criterion}</span>
                          {r.description && <span className="text-xs text-slate-500 ml-2">{r.description}</span>}
                        </div>
                        <span className="font-semibold text-indigo-600">{r.max_points} pts</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Student: My submission / Submit */}
              {myRole === 'student' && (
                <div className="border-t border-slate-200 pt-6">
                  {a.my_submission ? (
                    <MySubmissionCard sub={a.my_submission} assignment={a} onResubmit={() => setShowSubmit(true)} />
                  ) : (
                    <div className="text-center py-6">
                      <p className="text-slate-500 mb-3">You haven't submitted yet.</p>
                      <Button onClick={() => setShowSubmit(true)} className="bg-blue-600 hover:bg-blue-700" data-testid="submit-work-btn">
                        <Upload className="w-4 h-4 mr-2" /> Submit Your Work
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Submissions tab */}
          {tab === 'submissions' && canViewSubs && (
            <div className="space-y-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-slate-500">{submissions.length} of {assignees.length} submitted</span>
              </div>

              {submissions.length === 0 ? (
                <p className="text-sm text-slate-400 text-center py-8">No submissions yet.</p>
              ) : (
                <div className="space-y-3">
                  {submissions.map(sub => (
                    <SubmissionCard key={sub.id} sub={sub} assignment={a} canGrade={canGrade}
                      onGrade={() => setGradingSub(sub)} />
                  ))}
                </div>
              )}

              {missing.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-amber-700 flex items-center gap-1 mb-2">
                    <AlertTriangle className="w-4 h-4" /> Not Submitted ({missing.length})
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {missing.map(m => (
                      <span key={m.id} className="text-xs bg-amber-50 text-amber-700 px-2 py-1 rounded-full border border-amber-200">
                        {m.name} {m.flight ? `(${m.flight})` : ''}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* People tab */}
          {tab === 'people' && canViewSubs && (
            <PeopleTab assignment={a} assignees={assignees} />
          )}
        </div>
      </div>

      {showSubmit && (
        <SubmitDialog assignment={a} onClose={() => setShowSubmit(false)}
          onSubmitted={() => { setShowSubmit(false); fetchDetail(); }} />
      )}

      {gradingSub && (
        <GradeDialog assignment={a} submission={gradingSub}
          onClose={() => setGradingSub(null)}
          onGraded={() => { setGradingSub(null); fetchDetail(); }} />
      )}
    </div>
  );
}


/* ── Target Info ─────────────────────────────────────────────────────── */

function TargetInfo({ assignment: a }) {
  const parts = [];
  if (a.target_type === 'all') {
    parts.push('All Cadre');
  } else {
    if (a.target_squadrons?.length) {
      parts.push('Squadrons: ' + a.target_squadrons.map(s => SQUADRON_LABELS[s] || s).join(', '));
    }
    if (a.target_flights?.length) {
      parts.push('Flights: ' + a.target_flights.map(f => FLIGHT_LABELS[f] || f).join(', '));
    }
    if (a.target_type === 'individual') {
      parts.push('Individual assignment');
    }
  }
  if (!parts.length) return null;

  return (
    <div className="flex items-center gap-2 text-xs text-slate-500 bg-slate-50 px-3 py-2 rounded-lg border border-slate-100" data-testid="assignment-target-info">
      <Users className="w-3.5 h-3.5" />
      <span>Assigned to: <span className="font-medium text-slate-700">{parts.join(' + ')}</span></span>
    </div>
  );
}


/* ── My Submission (student view) ────────────────────────────────────── */

function MySubmissionCard({ sub, assignment, onResubmit }) {
  return (
    <div className="border border-slate-200 rounded-xl p-4" data-testid="my-submission-card">
      <h4 className="text-sm font-semibold text-slate-700 mb-3">Your Submission</h4>
      {sub.text_response && <p className="text-sm bg-slate-50 p-3 rounded-lg border">{sub.text_response}</p>}
      {sub.answers?.length > 0 && (
        <div className="mt-2 space-y-2">
          {sub.answers.map((ans, i) => {
            const q = assignment.questions?.find(q => q.id === ans.question_id);
            return (
              <div key={i} className="bg-slate-50 p-2 rounded-lg border text-sm">
                <span className="text-xs text-slate-400 font-medium">{q ? q.question_text : `Q${i+1}`}</span>
                <p className="text-slate-700 mt-0.5">{ans.answer_text}</p>
              </div>
            );
          })}
        </div>
      )}
      {sub.file_name && (
        <p className="text-sm text-blue-600 mt-2 flex items-center gap-1"><Paperclip className="w-3 h-3" />{sub.file_name}</p>
      )}
      {sub.graded ? (
        <div className="mt-3 bg-emerald-50 p-3 rounded-lg border border-emerald-200">
          <div className="flex items-center gap-2 mb-1">
            <CheckCircle className="w-4 h-4 text-emerald-600" />
            <span className="font-semibold text-emerald-700">Score: {sub.total_score} / {assignment.max_score}</span>
          </div>
          {sub.feedback && <p className="text-sm text-slate-600 mt-1">Feedback: {sub.feedback}</p>}
          {sub.rubric_scores?.length > 0 && (
            <div className="mt-2 space-y-1">
              {sub.rubric_scores.map((rs, i) => (
                <div key={i} className="flex justify-between text-xs"><span>{rs.criterion}</span><span className="font-medium">{rs.score}/{rs.max_points}</span></div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="mt-3 flex items-center justify-between">
          <span className="text-xs text-blue-600 font-medium flex items-center gap-1"><Clock className="w-3 h-3" /> Awaiting grade</span>
          <Button variant="outline" size="sm" onClick={onResubmit} data-testid="resubmit-btn">Edit Submission</Button>
        </div>
      )}
    </div>
  );
}


/* ── Submission Card (grader view) ───────────────────────────────────── */

function SubmissionCard({ sub, assignment, canGrade, onGrade }) {
  return (
    <div className={`border rounded-xl p-4 ${sub.graded ? 'border-emerald-200 bg-emerald-50/30' : 'border-slate-200 bg-white'}`} data-testid={`submission-${sub.id}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center">
            <User className="w-4 h-4 text-slate-500" />
          </div>
          <div>
            <span className="font-medium text-sm text-slate-900">{sub.user_name}</span>
            {sub.user_flight && <span className="text-xs text-slate-400 ml-1">({sub.user_flight})</span>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {sub.graded ? (
            <span className="text-xs font-semibold text-emerald-700 bg-emerald-100 px-2.5 py-1 rounded-full">{sub.total_score}/{assignment.max_score}</span>
          ) : (
            canGrade && <Button size="sm" variant="outline" onClick={onGrade} data-testid={`grade-btn-${sub.id}`}><Award className="w-3 h-3 mr-1" />Grade</Button>
          )}
        </div>
      </div>
      {sub.text_response && <p className="text-sm text-slate-600 bg-slate-50 p-2 rounded-lg border mt-1">{sub.text_response}</p>}
      {sub.answers?.length > 0 && (
        <div className="mt-2 space-y-1">
          {sub.answers.map((ans, i) => {
            const q = assignment.questions?.find(q => q.id === ans.question_id);
            return (
              <div key={i} className="text-sm bg-slate-50 p-2 rounded border">
                <span className="text-xs font-medium text-slate-400">{q ? q.question_text : `Q${i+1}`}</span>
                <p className="text-slate-700">{ans.answer_text}</p>
              </div>
            );
          })}
        </div>
      )}
      {sub.file_name && (
        <a href={`${API}/assignments/${assignment.id}/submissions/${sub.id}/file`}
          className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline mt-2">
          <Download className="w-3 h-3" /> {sub.file_name}
        </a>
      )}
      {sub.graded && sub.feedback && <p className="text-xs text-slate-500 mt-2 italic">Feedback: {sub.feedback}</p>}
    </div>
  );
}


/* ── People Tab ──────────────────────────────────────────────────────── */

function PeopleTab({ assignment, assignees }) {
  const sections = [
    { title: 'Instructors', ids: assignment.instructors || [], icon: GraduationCap, color: 'purple' },
    { title: 'Mentors', ids: assignment.mentors || [], icon: Shield, color: 'teal' },
  ];

  return (
    <div className="space-y-6">
      {sections.map(sec => sec.ids.length > 0 && (
        <div key={sec.title}>
          <h4 className={`text-sm font-semibold text-${sec.color}-700 mb-2 flex items-center gap-1`}>
            <sec.icon className="w-4 h-4" /> {sec.title} ({sec.ids.length})
          </h4>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {(assignment[sec.title.toLowerCase() + '_names'] || []).map((name, i) => (
              <div key={i} className={`flex items-center gap-2 text-sm bg-${sec.color}-50 px-3 py-2 rounded-lg border border-${sec.color}-100`}>
                <sec.icon className={`w-3.5 h-3.5 text-${sec.color}-500`} /> {name}
              </div>
            ))}
          </div>
        </div>
      ))}

      <div>
        <h4 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-1">
          <Users className="w-4 h-4" /> Students ({assignees.length})
        </h4>
        {assignees.length === 0 ? (
          <p className="text-sm text-slate-400">No students assigned.</p>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {assignees.map(a => (
              <div key={a.id} className="flex items-center gap-2 text-sm bg-slate-50 px-3 py-2 rounded-lg border border-slate-100">
                <User className="w-3.5 h-3.5 text-slate-400" /> {a.name}
                {a.flight && <span className="text-xs text-slate-400">({a.flight})</span>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}


/* ── Create Assignment Dialog ────────────────────────────────────────── */

function CreateAssignmentDialog({ flights, squadrons, allUsers, onClose, onCreated }) {
  const [form, setForm] = useState({
    title: '', description: '', due_date: '', category: '',
    target_type: 'all',
    target_flights: [], target_squadrons: [], target_users: [],
    instructors: [], mentors: [],
    allow_file_upload: true, allow_text_response: true,
    rubric: [{ criterion: '', max_points: 10, description: '' }],
    questions: [],
  });
  const [submitting, setSubmitting] = useState(false);
  const [materialFiles, setMaterialFiles] = useState([]);

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }));
  const toggle = (key, val) => setForm(f => ({
    ...f, [key]: f[key].includes(val) ? f[key].filter(x => x !== val) : [...f[key], val]
  }));

  const addRubric = () => set('rubric', [...form.rubric, { criterion: '', max_points: 10, description: '' }]);
  const removeRubric = (i) => set('rubric', form.rubric.filter((_, idx) => idx !== i));
  const updateRubric = (i, field, val) => {
    const r = [...form.rubric]; r[i] = { ...r[i], [field]: val }; set('rubric', r);
  };

  const addQuestion = () => set('questions', [...form.questions, { question_text: '' }]);
  const removeQuestion = (i) => set('questions', form.questions.filter((_, idx) => idx !== i));
  const updateQuestion = (i, val) => {
    const q = [...form.questions]; q[i] = { ...q[i], question_text: val }; set('questions', q);
  };

  const handleSubmit = async () => {
    if (!form.title || !form.due_date) { toast.error('Title and due date are required'); return; }
    if (form.rubric.some(r => !r.criterion)) { toast.error('All rubric criteria need a name'); return; }
    if (form.questions.some(q => !q.question_text.trim())) { toast.error('All questions need text'); return; }
    setSubmitting(true);
    try {
      const res = await axios.post(`${API}/assignments`, form);
      const assignmentId = res.data.id;
      // Upload materials
      for (const file of materialFiles) {
        const fd = new FormData();
        fd.append('file', file);
        await axios.post(`${API}/assignments/${assignmentId}/materials`, fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      }
      toast.success('Assignment created!');
      onCreated();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to create assignment');
    } finally {
      setSubmitting(false);
    }
  };

  const totalPoints = form.rubric.reduce((sum, r) => sum + (Number(r.max_points) || 0), 0);

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Plus className="w-5 h-5 text-blue-600" /> Create Assignment</DialogTitle>
        </DialogHeader>
        <div className="space-y-5">
          {/* Title & Description */}
          <div>
            <label className="text-sm font-medium text-slate-700">Title *</label>
            <Input value={form.title} onChange={e => set('title', e.target.value)} placeholder="Assignment title" data-testid="assignment-title-input" />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">Instructions</label>
            <textarea className="w-full border border-slate-200 rounded-md p-2 text-sm min-h-[80px] focus:ring-2 focus:ring-blue-200 focus:border-blue-400 outline-none"
              value={form.description} onChange={e => set('description', e.target.value)}
              placeholder="Detailed instructions..." data-testid="assignment-description-input" />
          </div>

          {/* Due Date & Category */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-slate-700">Due Date *</label>
              <Input type="date" value={form.due_date} onChange={e => set('due_date', e.target.value)} data-testid="assignment-due-date" />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700">Category</label>
              <Input value={form.category} onChange={e => set('category', e.target.value)} placeholder="e.g., Training, Admin" data-testid="assignment-category" />
            </div>
          </div>

          {/* Assign To */}
          <div className="border border-slate-200 rounded-lg p-4 space-y-3">
            <label className="text-sm font-semibold text-slate-700">Assign To</label>
            <select className="w-full border border-slate-200 rounded-md p-2 text-sm"
              value={form.target_type} onChange={e => set('target_type', e.target.value)} data-testid="assignment-target-type">
              <option value="all">All Cadre</option>
              <option value="squadron">Squadrons</option>
              <option value="flight">Flights</option>
              <option value="individual">Individual</option>
            </select>

            {(form.target_type === 'squadron' || form.target_type === 'flight') && (
              <>
                {/* Squadron selection */}
                <div>
                  <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Squadrons</label>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {squadrons.map(s => (
                      <label key={s.value} className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-full border cursor-pointer transition-colors ${
                        form.target_squadrons.includes(s.value) ? 'bg-blue-50 border-blue-300 text-blue-700' : 'border-slate-200 hover:bg-slate-50'
                      }`}>
                        <input type="checkbox" className="sr-only" checked={form.target_squadrons.includes(s.value)}
                          onChange={() => toggle('target_squadrons', s.value)} />
                        {s.label}
                      </label>
                    ))}
                  </div>
                </div>
                {/* Flight selection */}
                <div>
                  <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Flights</label>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {flights.map(f => (
                      <label key={f.value} className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-full border cursor-pointer transition-colors ${
                        form.target_flights.includes(f.value) ? 'bg-blue-50 border-blue-300 text-blue-700' : 'border-slate-200 hover:bg-slate-50'
                      }`}>
                        <input type="checkbox" className="sr-only" checked={form.target_flights.includes(f.value)}
                          onChange={() => toggle('target_flights', f.value)} />
                        {f.label}
                      </label>
                    ))}
                  </div>
                </div>
              </>
            )}

            {form.target_type === 'individual' && (
              <div>
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Select Members</label>
                <div className="max-h-48 overflow-y-auto border border-slate-200 rounded-md p-2 mt-1">
                  {allUsers.map(u => (
                    <label key={u.id} className="flex items-center gap-2 text-sm py-0.5 px-1 hover:bg-slate-50 rounded cursor-pointer">
                      <input type="checkbox" checked={form.target_users.includes(u.id)}
                        onChange={() => toggle('target_users', u.id)} />
                      {u.name} <span className="text-xs text-slate-400">({u.role?.replace(/_/g, ' ')})</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Instructors & Mentors */}
          <div className="border border-slate-200 rounded-lg p-4 space-y-3">
            <label className="text-sm font-semibold text-slate-700">Assign Roles (optional)</label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-purple-600 uppercase tracking-wider flex items-center gap-1">
                  <GraduationCap className="w-3 h-3" /> Instructors
                </label>
                <div className="max-h-32 overflow-y-auto border border-slate-200 rounded-md p-2 mt-1">
                  {allUsers.map(u => (
                    <label key={u.id} className="flex items-center gap-2 text-sm py-0.5 px-1 hover:bg-purple-50 rounded cursor-pointer">
                      <input type="checkbox" checked={form.instructors.includes(u.id)}
                        onChange={() => toggle('instructors', u.id)} />
                      {u.name}
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-teal-600 uppercase tracking-wider flex items-center gap-1">
                  <Shield className="w-3 h-3" /> Mentors
                </label>
                <div className="max-h-32 overflow-y-auto border border-slate-200 rounded-md p-2 mt-1">
                  {allUsers.map(u => (
                    <label key={u.id} className="flex items-center gap-2 text-sm py-0.5 px-1 hover:bg-teal-50 rounded cursor-pointer">
                      <input type="checkbox" checked={form.mentors.includes(u.id)}
                        onChange={() => toggle('mentors', u.id)} />
                      {u.name}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Response types */}
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.allow_text_response} onChange={e => set('allow_text_response', e.target.checked)} />
              Text response
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.allow_file_upload} onChange={e => set('allow_file_upload', e.target.checked)} />
              File upload
            </label>
          </div>

          {/* Questions */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-semibold text-slate-700 flex items-center gap-1"><MessageSquare className="w-4 h-4" /> Questions ({form.questions.length})</label>
              <Button variant="outline" size="sm" onClick={addQuestion} data-testid="add-question-btn">
                <Plus className="w-3 h-3 mr-1" /> Add Question
              </Button>
            </div>
            {form.questions.map((q, i) => (
              <div key={i} className="flex items-start gap-2 bg-slate-50 p-3 rounded-md mb-2">
                <span className="text-xs text-slate-400 font-medium mt-2">Q{i + 1}</span>
                <textarea className="flex-1 border border-slate-200 rounded-md p-2 text-sm min-h-[40px]"
                  value={q.question_text} onChange={e => updateQuestion(i, e.target.value)}
                  placeholder="Enter your question..." data-testid={`question-input-${i}`} />
                <Button variant="ghost" size="sm" onClick={() => removeQuestion(i)} className="text-red-400 mt-0.5">
                  <X className="w-4 h-4" />
                </Button>
              </div>
            ))}
          </div>

          {/* Materials */}
          <div>
            <label className="text-sm font-semibold text-slate-700 flex items-center gap-1 mb-2"><Paperclip className="w-4 h-4" /> Attach Materials</label>
            <input type="file" multiple className="block w-full text-sm text-slate-500
              file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0
              file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700
              hover:file:bg-blue-100"
              onChange={e => setMaterialFiles(Array.from(e.target.files))} data-testid="material-file-input" />
            {materialFiles.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {materialFiles.map((f, i) => (
                  <span key={i} className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded-full">{f.name}</span>
                ))}
              </div>
            )}
          </div>

          {/* Rubric */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-semibold text-slate-700">Rubric ({totalPoints} pts)</label>
              <Button variant="outline" size="sm" onClick={addRubric} data-testid="add-rubric-item">
                <Plus className="w-3 h-3 mr-1" /> Criterion
              </Button>
            </div>
            <div className="space-y-2">
              {form.rubric.map((r, i) => (
                <div key={i} className="flex items-start gap-2 bg-slate-50 p-3 rounded-md">
                  <div className="flex-1 space-y-1">
                    <Input placeholder="Criterion name" value={r.criterion}
                      onChange={e => updateRubric(i, 'criterion', e.target.value)} className="text-sm" data-testid={`rubric-name-${i}`} />
                    <Input placeholder="Description (optional)" value={r.description}
                      onChange={e => updateRubric(i, 'description', e.target.value)} className="text-xs" />
                  </div>
                  <div className="w-20">
                    <Input type="number" min="1" max="100" value={r.max_points}
                      onChange={e => updateRubric(i, 'max_points', Number(e.target.value))} className="text-sm text-center" data-testid={`rubric-points-${i}`} />
                    <span className="text-xs text-slate-400 text-center block">pts</span>
                  </div>
                  {form.rubric.length > 1 && (
                    <Button variant="ghost" size="sm" onClick={() => removeRubric(i)} className="text-red-400 mt-0.5">
                      <X className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={submitting} className="bg-blue-600 hover:bg-blue-700" data-testid="save-assignment-btn">
            {submitting ? 'Creating...' : 'Create Assignment'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


/* ── Submit Dialog ───────────────────────────────────────────────────── */

function SubmitDialog({ assignment, onClose, onSubmitted }) {
  const [textResponse, setTextResponse] = useState('');
  const [answers, setAnswers] = useState(
    (assignment.questions || []).map(q => ({ question_id: q.id, answer_text: '' }))
  );
  const [file, setFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const updateAnswer = (idx, val) => {
    setAnswers(prev => prev.map((a, i) => i === idx ? { ...a, answer_text: val } : a));
  };

  const handleSubmit = async () => {
    const hasText = textResponse.trim();
    const hasAnswers = answers.some(a => a.answer_text.trim());
    if (!hasText && !hasAnswers && !file) {
      toast.error('Please provide a response, answer questions, or upload a file');
      return;
    }
    setSubmitting(true);
    try {
      const formData = new FormData();
      if (textResponse) formData.append('text_response', textResponse);
      if (answers.length) formData.append('answers', JSON.stringify(answers));
      if (file) formData.append('file', file);
      await axios.post(`${API}/assignments/${assignment.id}/submit`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      toast.success('Assignment submitted!');
      onSubmitted();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Upload className="w-5 h-5 text-blue-600" /> Submit: {assignment.title}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {assignment.description && (
            <div className="bg-slate-50 p-3 rounded-lg text-sm text-slate-600 border">{assignment.description}</div>
          )}

          {/* Questions */}
          {assignment.questions?.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-semibold text-slate-700 flex items-center gap-1"><MessageSquare className="w-4 h-4" /> Questions</h4>
              {assignment.questions.map((q, i) => (
                <div key={q.id} className="bg-slate-50 p-3 rounded-lg border">
                  <label className="text-sm font-medium text-slate-700">Q{i + 1}: {q.question_text}</label>
                  <textarea className="w-full border border-slate-200 rounded-md p-2 text-sm min-h-[60px] mt-1"
                    value={answers[i]?.answer_text || ''}
                    onChange={e => updateAnswer(i, e.target.value)}
                    placeholder="Your answer..." data-testid={`answer-input-${i}`} />
                </div>
              ))}
            </div>
          )}

          {assignment.allow_text_response && (
            <div>
              <label className="text-sm font-medium text-slate-700">Your Response</label>
              <textarea className="w-full border border-slate-200 rounded-md p-2 text-sm min-h-[100px]"
                value={textResponse} onChange={e => setTextResponse(e.target.value)}
                placeholder="Write your response here..." data-testid="submit-text-response" />
            </div>
          )}

          {assignment.allow_file_upload && (
            <div>
              <label className="text-sm font-medium text-slate-700">Upload File</label>
              <input type="file" className="block w-full text-sm text-slate-500 mt-1
                file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0
                file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700
                hover:file:bg-blue-100"
                onChange={e => setFile(e.target.files[0])} data-testid="submit-file-input" />
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={submitting} className="bg-blue-600 hover:bg-blue-700" data-testid="confirm-submit-btn">
            {submitting ? 'Submitting...' : 'Submit'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


/* ── Grade Dialog ────────────────────────────────────────────────────── */

function GradeDialog({ assignment, submission, onClose, onGraded }) {
  const [scores, setScores] = useState(
    (assignment.rubric || []).map(r => ({ criterion: r.criterion, max_points: r.max_points, score: 0 }))
  );
  const [feedback, setFeedback] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const totalScore = scores.reduce((sum, s) => sum + Number(s.score || 0), 0);

  const handleGrade = async () => {
    setSubmitting(true);
    try {
      await axios.post(`${API}/assignments/${assignment.id}/grade/${submission.id}`, {
        rubric_scores: scores, feedback,
      });
      toast.success(`Graded ${submission.user_name}: ${totalScore}/${assignment.max_score}`);
      onGraded();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Grading failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-md max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Award className="w-5 h-5 text-blue-600" /> Grade: {submission.user_name}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          {submission.text_response && (
            <div className="bg-slate-50 p-2 rounded-lg text-sm max-h-32 overflow-y-auto border">{submission.text_response}</div>
          )}
          {submission.answers?.length > 0 && (
            <div className="space-y-1">
              {submission.answers.map((ans, i) => {
                const q = assignment.questions?.find(q => q.id === ans.question_id);
                return (
                  <div key={i} className="bg-slate-50 p-2 rounded border text-sm">
                    <span className="text-xs font-medium text-slate-400">{q ? q.question_text : `Q${i+1}`}</span>
                    <p className="text-slate-700">{ans.answer_text}</p>
                  </div>
                );
              })}
            </div>
          )}

          <div className="space-y-2">
            {scores.map((s, idx) => (
              <div key={idx} className="flex items-center gap-3 bg-indigo-50/50 p-2 rounded-md border border-indigo-100">
                <div className="flex-1"><span className="text-sm font-medium">{s.criterion}</span></div>
                <div className="flex items-center gap-1">
                  <Input type="number" min="0" max={s.max_points}
                    value={s.score} className="w-16 text-center text-sm"
                    onChange={e => {
                      const v = Math.min(Number(e.target.value) || 0, s.max_points);
                      setScores(prev => prev.map((p, i) => i === idx ? { ...p, score: v } : p));
                    }}
                    data-testid={`grade-score-${idx}`} />
                  <span className="text-xs text-slate-500">/ {s.max_points}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="text-right font-semibold text-blue-700">Total: {totalScore} / {assignment.max_score}</div>

          <div>
            <label className="text-sm font-medium text-slate-700">Feedback</label>
            <textarea className="w-full border border-slate-200 rounded-md p-2 text-sm min-h-[60px]"
              value={feedback} onChange={e => setFeedback(e.target.value)}
              placeholder="Additional feedback..." data-testid="grade-feedback" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleGrade} disabled={submitting} className="bg-blue-600 hover:bg-blue-700" data-testid="confirm-grade-btn">
            {submitting ? 'Saving...' : `Submit Grade (${totalScore}/${assignment.max_score})`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
