import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { toast } from 'sonner';
import axios from 'axios';
import {
  ClipboardList, Plus, Send, CheckCircle, Clock, AlertTriangle,
  FileUp, MessageSquare, Award, Trash2, Edit2, Bell, Download,
  ChevronDown, ChevronUp, Users, User, X
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Input } from '../components/ui/input';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const CREATOR_ROLES = ['exec_cadre', 'executive_staff', 'training_officer', 'commander', 'dcp'];
const GRADER_ROLES = ['exec_cadre', 'executive_staff', 'commander', 'dcp'];

export default function AssignmentsPage() {
  const { user } = useAuth();
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showGrade, setShowGrade] = useState(null);
  const [showSubmit, setShowSubmit] = useState(null);
  const [flights, setFlights] = useState([]);
  const [cadreUsers, setCadreUsers] = useState([]);

  const isCreator = CREATOR_ROLES.includes(user?.role);
  const isGrader = GRADER_ROLES.includes(user?.role);

  const fetchAssignments = useCallback(async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API}/assignments`);
      setAssignments(res.data);
    } catch (e) {
      toast.error('Failed to load assignments');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAssignments();
    // Fetch flights & users for assignment creation
    if (isCreator) {
      axios.get(`${API}/participants/stats`).then(r => {
        const flightNames = Object.keys(r.data?.flight_distribution || {}).filter(f => f && f !== 'Unassigned');
        setFlights(flightNames);
      }).catch(() => {});
      axios.get(`${API}/users`).then(r => {
        setCadreUsers(r.data.filter(u => ['cadre', 'exec_cadre'].includes(u.role)));
      }).catch(() => {});
    }
  }, [fetchAssignments, isCreator]);

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this assignment?')) return;
    try {
      await axios.delete(`${API}/assignments/${id}`);
      toast.success('Assignment deleted');
      fetchAssignments();
    } catch (e) {
      toast.error('Delete failed');
    }
  };

  const handleRemind = async (id) => {
    try {
      const res = await axios.post(`${API}/assignments/${id}/remind`);
      toast.success(res.data.message);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to send reminders');
    }
  };

  const getStatusBadge = (a) => {
    const now = new Date().toISOString().split('T')[0];
    const isOverdue = a.due_date < now;
    const mySub = a.my_submission;

    if (mySub?.graded) return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700" data-testid="status-graded"><CheckCircle className="w-3 h-3" />Graded</span>;
    if (mySub) return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700" data-testid="status-submitted"><Send className="w-3 h-3" />Submitted</span>;
    if (isOverdue) return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700" data-testid="status-overdue"><AlertTriangle className="w-3 h-3" />Overdue</span>;
    return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700" data-testid="status-pending"><Clock className="w-3 h-3" />Pending</span>;
  };

  if (loading) {
    return <div className="p-8 text-center text-slate-400">Loading assignments...</div>;
  }

  return (
    <div className="p-6 lg:p-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <ClipboardList className="w-6 h-6 text-indigo-600" />
            Assignments
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            {assignments.length} assignment{assignments.length !== 1 ? 's' : ''}
          </p>
        </div>
        {isCreator && (
          <Button onClick={() => setShowCreate(true)} data-testid="create-assignment-btn">
            <Plus className="w-4 h-4 mr-2" />
            Create Assignment
          </Button>
        )}
      </div>

      {/* Assignment cards */}
      {assignments.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-lg p-12 text-center">
          <ClipboardList className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500">{isCreator ? 'No assignments created yet.' : 'No assignments assigned to you.'}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {assignments.map(a => (
            <div key={a.id} className="bg-white border border-slate-200 rounded-lg p-5 hover:shadow-sm transition-shadow" data-testid={`assignment-card-${a.id}`}>
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-lg font-semibold text-slate-900 cursor-pointer hover:text-indigo-600"
                        onClick={() => setSelectedAssignment(a)} data-testid={`assignment-title-${a.id}`}>
                      {a.title}
                    </h3>
                    {!isCreator && getStatusBadge(a)}
                  </div>
                  <p className="text-sm text-slate-500 mt-1 line-clamp-2">{a.description}</p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-slate-400">
                    <span>Due: <span className="font-medium text-slate-600">{new Date(a.due_date + 'T00:00:00').toLocaleDateString()}</span></span>
                    <span>By: {a.created_by_name}</span>
                    <span className="capitalize">
                      {a.target_type === 'flight' ? `Flights: ${a.target_flights?.join(', ')}` :
                       a.target_type === 'individual' ? 'Individual' : 'All Cadre'}
                    </span>
                    {a.rubric?.length > 0 && <span>{a.rubric.length} rubric criteria</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {isCreator && (
                    <>
                      <span className="text-xs text-slate-500 bg-slate-100 rounded px-2 py-1" data-testid={`submission-count-${a.id}`}>
                        {a.submission_count || 0} submitted / {a.graded_count || 0} graded
                      </span>
                      <Button variant="outline" size="sm" onClick={() => handleRemind(a.id)} title="Send reminders to those who haven't submitted" data-testid={`remind-btn-${a.id}`}>
                        <Bell className="w-4 h-4" />
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => { setSelectedAssignment(a); }} data-testid={`view-btn-${a.id}`}>
                        <Award className="w-4 h-4" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(a.id)} className="text-red-500 hover:text-red-700" data-testid={`delete-btn-${a.id}`}>
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </>
                  )}
                  {!isCreator && !a.my_submission && (
                    <Button size="sm" onClick={() => setShowSubmit(a)} data-testid={`submit-btn-${a.id}`}>
                      <FileUp className="w-4 h-4 mr-1" /> Submit
                    </Button>
                  )}
                  {!isCreator && a.my_submission && !a.my_submission.graded && (
                    <Button variant="outline" size="sm" onClick={() => setShowSubmit(a)} data-testid={`resubmit-btn-${a.id}`}>
                      <Edit2 className="w-4 h-4 mr-1" /> Edit
                    </Button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Assignment Dialog */}
      {showCreate && <CreateAssignmentDialog flights={flights} cadreUsers={cadreUsers} onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); fetchAssignments(); }} />}

      {/* Submit Dialog */}
      {showSubmit && <SubmitDialog assignment={showSubmit} onClose={() => setShowSubmit(null)} onSubmitted={() => { setShowSubmit(null); fetchAssignments(); }} />}

      {/* Assignment Detail / Grading Dialog */}
      {selectedAssignment && (
        <AssignmentDetailDialog
          assignmentId={selectedAssignment.id}
          isGrader={isGrader}
          isCreator={isCreator}
          onClose={() => setSelectedAssignment(null)}
          onGraded={fetchAssignments}
        />
      )}
    </div>
  );
}


// ── Create Assignment Dialog ────────────────────────────────────────────

function CreateAssignmentDialog({ flights, cadreUsers, onClose, onCreated }) {
  const [form, setForm] = useState({
    title: '', description: '', due_date: '',
    target_type: 'all', target_flights: [], target_users: [],
    allow_file_upload: true, allow_text_response: true,
    rubric: [{ criterion: '', max_points: 10, description: '' }],
  });
  const [submitting, setSubmitting] = useState(false);

  const addRubricItem = () => {
    setForm(f => ({ ...f, rubric: [...f.rubric, { criterion: '', max_points: 10, description: '' }] }));
  };
  const removeRubricItem = (idx) => {
    setForm(f => ({ ...f, rubric: f.rubric.filter((_, i) => i !== idx) }));
  };
  const updateRubric = (idx, field, value) => {
    setForm(f => {
      const rubric = [...f.rubric];
      rubric[idx] = { ...rubric[idx], [field]: value };
      return { ...f, rubric };
    });
  };

  const handleSubmit = async () => {
    if (!form.title || !form.due_date) {
      toast.error('Title and due date are required');
      return;
    }
    if (form.rubric.some(r => !r.criterion)) {
      toast.error('All rubric criteria need a name');
      return;
    }
    setSubmitting(true);
    try {
      await axios.post(`${API}/assignments`, form);
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
          <DialogTitle>Create Assignment</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-slate-700">Title *</label>
            <Input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} placeholder="Assignment title" data-testid="assignment-title-input" />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">Description</label>
            <textarea className="w-full border border-slate-200 rounded-md p-2 text-sm min-h-[80px]"
              value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="Instructions and details..." data-testid="assignment-description-input" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-slate-700">Due Date *</label>
              <Input type="date" value={form.due_date} onChange={e => setForm(f => ({ ...f, due_date: e.target.value }))} data-testid="assignment-due-date" />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700">Assign To</label>
              <select className="w-full border border-slate-200 rounded-md p-2 text-sm"
                value={form.target_type} onChange={e => setForm(f => ({ ...f, target_type: e.target.value }))} data-testid="assignment-target-type">
                <option value="all">All Cadre</option>
                <option value="flight">Specific Flights</option>
                <option value="individual">Individual</option>
              </select>
            </div>
          </div>

          {form.target_type === 'flight' && (
            <div>
              <label className="text-sm font-medium text-slate-700">Select Flights</label>
              <div className="flex flex-wrap gap-2 mt-1">
                {flights.map(f => (
                  <label key={f} className="flex items-center gap-1 text-sm">
                    <input type="checkbox" checked={form.target_flights.includes(f)}
                      onChange={e => {
                        setForm(prev => ({
                          ...prev,
                          target_flights: e.target.checked
                            ? [...prev.target_flights, f]
                            : prev.target_flights.filter(x => x !== f)
                        }));
                      }} />
                    {f}
                  </label>
                ))}
              </div>
            </div>
          )}

          {form.target_type === 'individual' && (
            <div>
              <label className="text-sm font-medium text-slate-700">Select Cadre Members</label>
              <div className="max-h-40 overflow-y-auto border border-slate-200 rounded-md p-2 mt-1 space-y-1">
                {cadreUsers.map(u => (
                  <label key={u.id} className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={form.target_users.includes(u.id)}
                      onChange={e => {
                        setForm(prev => ({
                          ...prev,
                          target_users: e.target.checked
                            ? [...prev.target_users, u.id]
                            : prev.target_users.filter(x => x !== u.id)
                        }));
                      }} />
                    {u.name} <span className="text-xs text-slate-400">({u.flight || 'No flight'})</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.allow_text_response}
                onChange={e => setForm(f => ({ ...f, allow_text_response: e.target.checked }))} />
              Allow text response
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.allow_file_upload}
                onChange={e => setForm(f => ({ ...f, allow_file_upload: e.target.checked }))} />
              Allow file upload
            </label>
          </div>

          {/* Rubric Builder */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-slate-700">Rubric ({totalPoints} pts total)</label>
              <Button variant="outline" size="sm" onClick={addRubricItem} data-testid="add-rubric-item">
                <Plus className="w-3 h-3 mr-1" /> Add Criterion
              </Button>
            </div>
            <div className="space-y-3">
              {form.rubric.map((r, idx) => (
                <div key={idx} className="flex items-start gap-2 bg-slate-50 p-3 rounded-md">
                  <div className="flex-1 space-y-1">
                    <Input placeholder="Criterion name" value={r.criterion}
                      onChange={e => updateRubric(idx, 'criterion', e.target.value)} className="text-sm" data-testid={`rubric-name-${idx}`} />
                    <Input placeholder="Description (optional)" value={r.description}
                      onChange={e => updateRubric(idx, 'description', e.target.value)} className="text-xs" />
                  </div>
                  <div className="w-20">
                    <Input type="number" min="1" max="100" value={r.max_points}
                      onChange={e => updateRubric(idx, 'max_points', Number(e.target.value))} className="text-sm text-center" data-testid={`rubric-points-${idx}`} />
                    <span className="text-xs text-slate-400 text-center block">pts</span>
                  </div>
                  {form.rubric.length > 1 && (
                    <Button variant="ghost" size="sm" onClick={() => removeRubricItem(idx)} className="text-red-400 mt-0.5">
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
          <Button onClick={handleSubmit} disabled={submitting} data-testid="save-assignment-btn">
            {submitting ? 'Creating...' : 'Create Assignment'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


// ── Submit Assignment Dialog ────────────────────────────────────────────

function SubmitDialog({ assignment, onClose, onSubmitted }) {
  const [textResponse, setTextResponse] = useState('');
  const [file, setFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!textResponse && !file) {
      toast.error('Please provide a text response or upload a file');
      return;
    }
    setSubmitting(true);
    try {
      const formData = new FormData();
      if (textResponse) formData.append('text_response', textResponse);
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
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Submit: {assignment.title}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {assignment.description && (
            <div className="bg-slate-50 p-3 rounded-md text-sm text-slate-600">{assignment.description}</div>
          )}
          {assignment.rubric?.length > 0 && (
            <div className="text-xs text-slate-500">
              <span className="font-medium">Grading criteria:</span>{' '}
              {assignment.rubric.map(r => `${r.criterion} (${r.max_points}pts)`).join(', ')}
            </div>
          )}
          {assignment.allow_text_response && (
            <div>
              <label className="text-sm font-medium text-slate-700">Your Response</label>
              <textarea className="w-full border border-slate-200 rounded-md p-2 text-sm min-h-[120px]"
                value={textResponse} onChange={e => setTextResponse(e.target.value)}
                placeholder="Write your response here..." data-testid="submit-text-response" />
            </div>
          )}
          {assignment.allow_file_upload && (
            <div>
              <label className="text-sm font-medium text-slate-700">Upload File</label>
              <input type="file" className="block w-full text-sm text-slate-500 mt-1
                file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0
                file:text-sm file:font-medium file:bg-indigo-50 file:text-indigo-700
                hover:file:bg-indigo-100"
                onChange={e => setFile(e.target.files[0])} data-testid="submit-file-input" />
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={submitting} data-testid="confirm-submit-btn">
            {submitting ? 'Submitting...' : 'Submit Assignment'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


// ── Assignment Detail / Grading Dialog ──────────────────────────────────

function AssignmentDetailDialog({ assignmentId, isGrader, isCreator, onClose, onGraded }) {
  const [assignment, setAssignment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [gradingSub, setGradingSub] = useState(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await axios.get(`${API}/assignments/${assignmentId}`);
        setAssignment(res.data);
      } catch (e) {
        toast.error('Failed to load assignment');
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [assignmentId]);

  if (loading || !assignment) {
    return <Dialog open onOpenChange={onClose}><DialogContent><div className="text-center py-8 text-slate-400">Loading...</div></DialogContent></Dialog>;
  }

  const submissions = assignment.submissions || [];
  const assignees = assignment.assignees || [];
  const submittedUserIds = new Set(submissions.map(s => s.user_id));
  const missing = assignees.filter(a => !submittedUserIds.has(a.id));

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ClipboardList className="w-5 h-5 text-indigo-600" />
            {assignment.title}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Assignment info */}
          <div className="bg-slate-50 p-3 rounded-md text-sm space-y-1">
            <p>{assignment.description}</p>
            <div className="flex gap-4 text-xs text-slate-500 mt-2">
              <span>Due: {new Date(assignment.due_date + 'T00:00:00').toLocaleDateString()}</span>
              <span>Max Score: {assignment.max_score}</span>
              <span>Submissions: {submissions.length} / {assignees.length}</span>
            </div>
          </div>

          {/* Rubric */}
          {assignment.rubric?.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-2">Rubric</h4>
              <div className="grid gap-2">
                {assignment.rubric.map((r, i) => (
                  <div key={i} className="flex items-center justify-between bg-indigo-50 px-3 py-2 rounded-md text-sm">
                    <div>
                      <span className="font-medium">{r.criterion}</span>
                      {r.description && <span className="text-xs text-slate-500 ml-2">{r.description}</span>}
                    </div>
                    <span className="font-medium text-indigo-600">{r.max_points} pts</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* For my own submission (non-creator view) */}
          {!isCreator && assignment.my_submission && (
            <div className="border border-slate-200 rounded-md p-4">
              <h4 className="text-sm font-medium text-slate-700 mb-2">Your Submission</h4>
              {assignment.my_submission.text_response && (
                <p className="text-sm bg-slate-50 p-2 rounded">{assignment.my_submission.text_response}</p>
              )}
              {assignment.my_submission.file_name && (
                <p className="text-sm text-indigo-600 mt-1">File: {assignment.my_submission.file_name}</p>
              )}
              {assignment.my_submission.graded && (
                <div className="mt-3 bg-emerald-50 p-3 rounded-md">
                  <div className="flex items-center gap-2 mb-1">
                    <CheckCircle className="w-4 h-4 text-emerald-600" />
                    <span className="font-medium text-emerald-700">
                      Score: {assignment.my_submission.total_score} / {assignment.max_score}
                    </span>
                  </div>
                  {assignment.my_submission.feedback && (
                    <p className="text-sm text-slate-600">Feedback: {assignment.my_submission.feedback}</p>
                  )}
                  {assignment.my_submission.rubric_scores?.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {assignment.my_submission.rubric_scores.map((rs, i) => (
                        <div key={i} className="flex justify-between text-xs">
                          <span>{rs.criterion}</span>
                          <span className="font-medium">{rs.score}/{rs.max_points}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Creator / Grader view: all submissions */}
          {isCreator && (
            <>
              <h4 className="text-sm font-medium text-slate-700">Submissions ({submissions.length})</h4>
              {submissions.length === 0 ? (
                <p className="text-sm text-slate-400">No submissions yet.</p>
              ) : (
                <div className="space-y-3">
                  {submissions.map(sub => (
                    <div key={sub.id} className={`border rounded-md p-3 ${sub.graded ? 'border-emerald-200 bg-emerald-50/30' : 'border-slate-200'}`} data-testid={`submission-${sub.id}`}>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <User className="w-4 h-4 text-slate-400" />
                          <span className="font-medium text-sm">{sub.user_name}</span>
                          {sub.user_flight && <span className="text-xs text-slate-400">({sub.user_flight})</span>}
                        </div>
                        <div className="flex items-center gap-2">
                          {sub.graded ? (
                            <span className="text-xs font-medium text-emerald-600 bg-emerald-100 px-2 py-0.5 rounded-full">
                              {sub.total_score}/{assignment.max_score}
                            </span>
                          ) : (
                            isGrader && (
                              <Button size="sm" variant="outline" onClick={() => setGradingSub(sub)} data-testid={`grade-btn-${sub.id}`}>
                                <Award className="w-3 h-3 mr-1" /> Grade
                              </Button>
                            )
                          )}
                        </div>
                      </div>
                      {sub.text_response && <p className="text-sm text-slate-600 bg-white p-2 rounded border">{sub.text_response}</p>}
                      {sub.file_name && (
                        <a href={`${API}/assignments/${assignmentId}/submissions/${sub.id}/file`}
                           className="inline-flex items-center gap-1 text-sm text-indigo-600 hover:underline mt-1">
                          <Download className="w-3 h-3" /> {sub.file_name}
                        </a>
                      )}
                      {sub.graded && sub.feedback && (
                        <p className="text-xs text-slate-500 mt-2 italic">Feedback: {sub.feedback}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Missing submissions */}
              {missing.length > 0 && (
                <div>
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
            </>
          )}
        </div>

        {/* Grading sub-dialog */}
        {gradingSub && (
          <GradeDialog
            assignment={assignment}
            submission={gradingSub}
            onClose={() => setGradingSub(null)}
            onGraded={() => {
              setGradingSub(null);
              // Refresh assignment data
              axios.get(`${API}/assignments/${assignmentId}`).then(r => setAssignment(r.data));
              onGraded();
            }}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}


// ── Grade Dialog ────────────────────────────────────────────────────────

function GradeDialog({ assignment, submission, onClose, onGraded }) {
  const [scores, setScores] = useState(
    assignment.rubric.map(r => ({ criterion: r.criterion, max_points: r.max_points, score: 0 }))
  );
  const [feedback, setFeedback] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const totalScore = scores.reduce((sum, s) => sum + Number(s.score || 0), 0);

  const handleGrade = async () => {
    setSubmitting(true);
    try {
      await axios.post(`${API}/assignments/${assignment.id}/grade/${submission.id}`, {
        rubric_scores: scores,
        feedback,
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
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Grade: {submission.user_name}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          {/* Show submission content */}
          {submission.text_response && (
            <div className="bg-slate-50 p-2 rounded text-sm max-h-32 overflow-y-auto">{submission.text_response}</div>
          )}

          {/* Rubric scoring */}
          <div className="space-y-2">
            {scores.map((s, idx) => (
              <div key={idx} className="flex items-center gap-3 bg-indigo-50/50 p-2 rounded-md">
                <div className="flex-1">
                  <span className="text-sm font-medium">{s.criterion}</span>
                </div>
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

          <div className="text-right font-semibold text-indigo-700">
            Total: {totalScore} / {assignment.max_score}
          </div>

          <div>
            <label className="text-sm font-medium text-slate-700">Feedback (optional)</label>
            <textarea className="w-full border border-slate-200 rounded-md p-2 text-sm min-h-[60px]"
              value={feedback} onChange={e => setFeedback(e.target.value)}
              placeholder="Additional feedback..." data-testid="grade-feedback" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleGrade} disabled={submitting} data-testid="confirm-grade-btn">
            {submitting ? 'Saving...' : `Submit Grade (${totalScore}/${assignment.max_score})`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
