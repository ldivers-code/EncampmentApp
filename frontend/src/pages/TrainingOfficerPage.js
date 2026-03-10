import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import {
  getTrainingSummary, getBisterChecks, createBlisterCheck, updateBlisterCheck,
  getCounselingLogs, createCounselingLog, updateCounselingLog,
  getCadreIssues, createCadreIssue, updateCadreIssue
} from '../services/api';
import {
  Footprints, MessageSquare, AlertTriangle, Plus, RefreshCw,
  CheckCircle, Clock, Eye, Filter, ChevronDown
} from 'lucide-react';

const SEVERITY_COLORS = {
  none: 'bg-slate-100 text-slate-600',
  mild: 'bg-yellow-100 text-yellow-700',
  moderate: 'bg-orange-100 text-orange-700',
  severe: 'bg-red-100 text-red-700'
};

const STATUS_COLORS = {
  checked: 'bg-emerald-100 text-emerald-700',
  monitoring: 'bg-amber-100 text-amber-700',
  resolved: 'bg-slate-100 text-slate-500',
  open: 'bg-red-100 text-red-700',
  in_progress: 'bg-amber-100 text-amber-700',
  escalated: 'bg-purple-100 text-purple-700'
};

const ISSUE_SEVERITY = {
  low: 'bg-slate-100 text-slate-600',
  medium: 'bg-yellow-100 text-yellow-700',
  high: 'bg-orange-100 text-orange-700',
  critical: 'bg-red-200 text-red-800 font-bold'
};

const COUNSELING_CATEGORIES = [
  { value: 'general', label: 'General' },
  { value: 'behavioral', label: 'Behavioral' },
  { value: 'performance', label: 'Performance' },
  { value: 'homesickness', label: 'Homesickness' },
  { value: 'conflict', label: 'Conflict' },
  { value: 'other', label: 'Other' }
];

const CADRE_ISSUE_CATEGORIES = [
  { value: 'behavioral', label: 'Behavioral' },
  { value: 'performance', label: 'Performance' },
  { value: 'safety', label: 'Safety' },
  { value: 'protocol', label: 'Protocol' },
  { value: 'leadership', label: 'Leadership' },
  { value: 'other', label: 'Other' }
];

const BLISTER_LOCATIONS = [
  'Left Heel', 'Right Heel', 'Left Toes', 'Right Toes',
  'Left Arch', 'Right Arch', 'Left Ankle', 'Right Ankle',
  'Left Ball', 'Right Ball', 'Other'
];

const FLIGHTS = ['alpha', 'bravo', 'charlie', 'delta', 'echo', 'foxtrot'];

const today = () => new Date().toISOString().split('T')[0];

const TrainingOfficerPage = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('blisters');
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  // Blister state
  const [blisters, setBlisters] = useState([]);
  const [showBlisterForm, setShowBlisterForm] = useState(false);
  const [blisterForm, setBlisterForm] = useState({
    cadet_name: '', capid: '', flight: '', squadron: '',
    date: today(), severity: 'none', location: '',
    description: '', treatment_given: '', follow_up_needed: false, status: 'checked'
  });

  // Counseling state
  const [counselingLogs, setCounselingLogs] = useState([]);
  const [showCounselingForm, setShowCounselingForm] = useState(false);
  const [counselingForm, setCounselingForm] = useState({
    cadet_name: '', capid: '', flight: '', squadron: '',
    date: today(), category: 'general', reason: '',
    outcome: '', follow_up_needed: false, follow_up_date: ''
  });

  // Cadre issues state
  const [cadreIssues, setCadreIssues] = useState([]);
  const [showIssueForm, setShowIssueForm] = useState(false);
  const [issueForm, setIssueForm] = useState({
    cadre_name: '', cadre_capid: '', flight: '', squadron: '',
    date: today(), category: 'general', severity: 'low',
    description: '', action_taken: '', resolution_status: 'open'
  });

  // Filters
  const [dateFilter, setDateFilter] = useState('');
  const [flightFilter, setFlightFilter] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [sumData, bData, cData, iData] = await Promise.all([
        getTrainingSummary(),
        getBisterChecks(buildFilterParams()),
        getCounselingLogs(buildFilterParams()),
        getCadreIssues(buildFilterParams())
      ]);
      setSummary(sumData);
      setBlisters(bData);
      setCounselingLogs(cData);
      setCadreIssues(iData);
    } catch (error) {
      console.error('Failed to load training data:', error);
      toast.error('Failed to load training data');
    } finally {
      setLoading(false);
    }
  };

  const buildFilterParams = () => {
    const params = {};
    if (dateFilter) params.date = dateFilter;
    if (flightFilter) params.flight = flightFilter;
    return params;
  };

  const applyFilters = async () => {
    const params = buildFilterParams();
    try {
      const [bData, cData, iData] = await Promise.all([
        getBisterChecks(params), getCounselingLogs(params), getCadreIssues(params)
      ]);
      setBlisters(bData);
      setCounselingLogs(cData);
      setCadreIssues(iData);
    } catch (error) {
      toast.error('Failed to filter data');
    }
  };

  // ===== Blister Handlers =====
  const handleCreateBlister = async () => {
    if (!blisterForm.cadet_name) { toast.error('Cadet name is required'); return; }
    try {
      const result = await createBlisterCheck(blisterForm);
      setBlisters(prev => [result, ...prev]);
      setShowBlisterForm(false);
      resetBlisterForm();
      toast.success('Blister check logged');
      loadData();
    } catch (error) {
      toast.error('Failed to log blister check');
    }
  };

  const handleUpdateBlisterStatus = async (id, status) => {
    try {
      await updateBlisterCheck(id, { status });
      setBlisters(prev => prev.map(b => b.id === id ? { ...b, status } : b));
      toast.success('Status updated');
    } catch (error) {
      toast.error('Failed to update');
    }
  };

  const resetBlisterForm = () => {
    setBlisterForm({
      cadet_name: '', capid: '', flight: '', squadron: user?.squadron || '',
      date: today(), severity: 'none', location: '',
      description: '', treatment_given: '', follow_up_needed: false, status: 'checked'
    });
  };

  // ===== Counseling Handlers =====
  const handleCreateCounseling = async () => {
    if (!counselingForm.cadet_name) { toast.error('Cadet name is required'); return; }
    if (!counselingForm.reason) { toast.error('Reason is required'); return; }
    try {
      const result = await createCounselingLog(counselingForm);
      setCounselingLogs(prev => [result, ...prev]);
      setShowCounselingForm(false);
      resetCounselingForm();
      toast.success('Counseling session logged');
      loadData();
    } catch (error) {
      toast.error('Failed to log counseling session');
    }
  };

  const resetCounselingForm = () => {
    setCounselingForm({
      cadet_name: '', capid: '', flight: '', squadron: user?.squadron || '',
      date: today(), category: 'general', reason: '',
      outcome: '', follow_up_needed: false, follow_up_date: ''
    });
  };

  // ===== Cadre Issue Handlers =====
  const handleCreateIssue = async () => {
    if (!issueForm.cadre_name) { toast.error('Cadre name is required'); return; }
    if (!issueForm.description) { toast.error('Description is required'); return; }
    try {
      const result = await createCadreIssue(issueForm);
      setCadreIssues(prev => [result, ...prev]);
      setShowIssueForm(false);
      resetIssueForm();
      toast.success('Cadre issue logged');
      loadData();
    } catch (error) {
      toast.error('Failed to log cadre issue');
    }
  };

  const handleUpdateIssueStatus = async (id, resolution_status) => {
    try {
      await updateCadreIssue(id, { resolution_status });
      setCadreIssues(prev => prev.map(i => i.id === id ? { ...i, resolution_status } : i));
      toast.success('Status updated');
    } catch (error) {
      toast.error('Failed to update');
    }
  };

  const resetIssueForm = () => {
    setIssueForm({
      cadre_name: '', cadre_capid: '', flight: '', squadron: user?.squadron || '',
      date: today(), category: 'general', severity: 'low',
      description: '', action_taken: '', resolution_status: 'open'
    });
  };

  if (loading && !summary) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-6 h-6 animate-spin text-[#00205B]" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-black uppercase tracking-tight text-[#00205B]" data-testid="training-officer-title">
            Training Officer
          </h1>
          <p className="text-sm text-slate-500">
            {user?.squadron ? `${user.squadron.replace(/_/g, ' ').toUpperCase()} Squadron` : 'All Squadrons'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadData} className="rounded-sm">
            <RefreshCw className="w-4 h-4 mr-2" /> Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
          <SummaryCard icon={Footprints} label="Blister Checks Today" value={summary.blister_checks_today} color="text-blue-600" />
          <SummaryCard icon={Eye} label="Blisters Monitoring" value={summary.blisters_monitoring} color="text-amber-600" />
          <SummaryCard icon={MessageSquare} label="Counseling Today" value={summary.counseling_today} color="text-indigo-600" />
          <SummaryCard icon={Clock} label="Follow-ups Pending" value={summary.counseling_followup} color="text-orange-600" />
          <SummaryCard icon={AlertTriangle} label="Cadre Issues Open" value={summary.cadre_issues_open} color="text-red-600" />
          <SummaryCard icon={AlertTriangle} label="Critical Issues" value={summary.cadre_issues_critical} color="text-red-800" />
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4 bg-white p-3 border border-slate-200 rounded-sm">
        <Filter className="w-4 h-4 text-slate-400" />
        <Input
          type="date"
          value={dateFilter}
          onChange={(e) => setDateFilter(e.target.value)}
          className="w-40 h-8 text-sm rounded-sm"
          data-testid="date-filter"
        />
        <Select value={flightFilter || "all"} onValueChange={(v) => setFlightFilter(v === 'all' ? '' : v)}>
          <SelectTrigger className="w-36 h-8 text-sm rounded-sm" data-testid="flight-filter">
            <SelectValue placeholder="All Flights" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Flights</SelectItem>
            {FLIGHTS.map(f => (
              <SelectItem key={f} value={f}>{f.charAt(0).toUpperCase() + f.slice(1)}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button size="sm" variant="outline" onClick={applyFilters} className="h-8 rounded-sm">Apply</Button>
        <Button size="sm" variant="ghost" onClick={() => { setDateFilter(''); setFlightFilter(''); loadData(); }} className="h-8 text-xs">Clear</Button>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid grid-cols-3 w-full max-w-lg">
          <TabsTrigger value="blisters" className="text-xs" data-testid="tab-blisters">
            <Footprints className="w-3.5 h-3.5 mr-1.5" /> Blister Checks
          </TabsTrigger>
          <TabsTrigger value="counseling" className="text-xs" data-testid="tab-counseling">
            <MessageSquare className="w-3.5 h-3.5 mr-1.5" /> Counseling
          </TabsTrigger>
          <TabsTrigger value="cadre" className="text-xs" data-testid="tab-cadre-issues">
            <AlertTriangle className="w-3.5 h-3.5 mr-1.5" /> Cadre Issues
          </TabsTrigger>
        </TabsList>

        {/* ===== Blister Checks Tab ===== */}
        <TabsContent value="blisters" className="mt-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold uppercase text-[#00205B]">Daily Blister Checks</h3>
            <Button size="sm" onClick={() => { resetBlisterForm(); setShowBlisterForm(true); }} className="bg-[#00205B] rounded-sm" data-testid="add-blister-check-btn">
              <Plus className="w-4 h-4 mr-1" /> Log Check
            </Button>
          </div>
          {blisters.length === 0 ? (
            <EmptyState text="No blister checks recorded" />
          ) : (
            <div className="space-y-2">
              {blisters.map(check => (
                <div key={check.id} className="bg-white border border-slate-200 rounded-sm p-4" data-testid={`blister-${check.id}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-sm">{check.cadet_name} {check.capid && <span className="text-slate-400 text-xs">({check.capid})</span>}</p>
                      <p className="text-xs text-slate-500">{check.flight && `${check.flight.charAt(0).toUpperCase() + check.flight.slice(1)} Flight`} &middot; {check.date}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] px-2 py-0.5 rounded uppercase ${SEVERITY_COLORS[check.severity] || SEVERITY_COLORS.none}`}>
                        {check.severity}
                      </span>
                      <span className={`text-[10px] px-2 py-0.5 rounded uppercase ${STATUS_COLORS[check.status] || ''}`}>
                        {check.status}
                      </span>
                    </div>
                  </div>
                  {check.location && <p className="text-xs text-slate-600 mt-1">Location: {check.location}</p>}
                  {check.description && <p className="text-xs text-slate-600 mt-0.5">{check.description}</p>}
                  {check.treatment_given && <p className="text-xs text-emerald-700 mt-0.5">Treatment: {check.treatment_given}</p>}
                  {check.follow_up_needed && <p className="text-xs text-amber-600 mt-0.5 font-medium">Follow-up needed</p>}
                  <div className="flex items-center gap-1 mt-2">
                    {check.status !== 'resolved' && (
                      <>
                        <Button variant="ghost" size="sm" className="h-6 text-[10px]" onClick={() => handleUpdateBlisterStatus(check.id, 'monitoring')}>
                          <Eye className="w-3 h-3 mr-1" /> Monitor
                        </Button>
                        <Button variant="ghost" size="sm" className="h-6 text-[10px]" onClick={() => handleUpdateBlisterStatus(check.id, 'resolved')}>
                          <CheckCircle className="w-3 h-3 mr-1" /> Resolve
                        </Button>
                      </>
                    )}
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1">Logged by {check.created_by_name}</p>
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        {/* ===== Counseling Tab ===== */}
        <TabsContent value="counseling" className="mt-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold uppercase text-[#00205B]">Cadet Counseling Log</h3>
            <Button size="sm" onClick={() => { resetCounselingForm(); setShowCounselingForm(true); }} className="bg-[#00205B] rounded-sm" data-testid="add-counseling-btn">
              <Plus className="w-4 h-4 mr-1" /> Log Session
            </Button>
          </div>
          {counselingLogs.length === 0 ? (
            <EmptyState text="No counseling sessions recorded" />
          ) : (
            <div className="space-y-2">
              {counselingLogs.map(log => (
                <div key={log.id} className="bg-white border border-slate-200 rounded-sm p-4" data-testid={`counseling-${log.id}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-sm">{log.cadet_name} {log.capid && <span className="text-slate-400 text-xs">({log.capid})</span>}</p>
                      <p className="text-xs text-slate-500">{log.flight && `${log.flight.charAt(0).toUpperCase() + log.flight.slice(1)} Flight`} &middot; {log.date}</p>
                    </div>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-100 text-indigo-700 uppercase">{log.category}</span>
                  </div>
                  <p className="text-xs text-slate-700 mt-2"><span className="font-medium">Reason:</span> {log.reason}</p>
                  {log.outcome && <p className="text-xs text-slate-600 mt-1"><span className="font-medium">Outcome:</span> {log.outcome}</p>}
                  {log.follow_up_needed && (
                    <p className="text-xs text-amber-600 mt-1 font-medium">
                      Follow-up needed {log.follow_up_date && `by ${log.follow_up_date}`}
                    </p>
                  )}
                  <p className="text-[10px] text-slate-400 mt-2">Logged by {log.created_by_name}</p>
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        {/* ===== Cadre Issues Tab ===== */}
        <TabsContent value="cadre" className="mt-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold uppercase text-[#00205B]">Cadre Issues</h3>
            <Button size="sm" onClick={() => { resetIssueForm(); setShowIssueForm(true); }} className="bg-[#00205B] rounded-sm" data-testid="add-cadre-issue-btn">
              <Plus className="w-4 h-4 mr-1" /> Log Issue
            </Button>
          </div>
          {cadreIssues.length === 0 ? (
            <EmptyState text="No cadre issues recorded" />
          ) : (
            <div className="space-y-2">
              {cadreIssues.map(issue => (
                <div key={issue.id} className={`bg-white border rounded-sm p-4 ${issue.severity === 'critical' ? 'border-red-300' : 'border-slate-200'}`} data-testid={`issue-${issue.id}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-sm">{issue.cadre_name} {issue.cadre_capid && <span className="text-slate-400 text-xs">({issue.cadre_capid})</span>}</p>
                      <p className="text-xs text-slate-500">{issue.flight && `${issue.flight.charAt(0).toUpperCase() + issue.flight.slice(1)} Flight`} &middot; {issue.date}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] px-2 py-0.5 rounded uppercase ${ISSUE_SEVERITY[issue.severity] || ISSUE_SEVERITY.low}`}>
                        {issue.severity}
                      </span>
                      <span className={`text-[10px] px-2 py-0.5 rounded uppercase ${STATUS_COLORS[issue.resolution_status] || ''}`}>
                        {issue.resolution_status?.replace('_', ' ')}
                      </span>
                    </div>
                  </div>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 uppercase mt-1 inline-block">{issue.category}</span>
                  <p className="text-xs text-slate-700 mt-1">{issue.description}</p>
                  {issue.action_taken && <p className="text-xs text-emerald-700 mt-1"><span className="font-medium">Action taken:</span> {issue.action_taken}</p>}
                  {issue.resolution_status !== 'resolved' && (
                    <div className="flex items-center gap-1 mt-2">
                      <Button variant="ghost" size="sm" className="h-6 text-[10px]" onClick={() => handleUpdateIssueStatus(issue.id, 'in_progress')}>In Progress</Button>
                      <Button variant="ghost" size="sm" className="h-6 text-[10px]" onClick={() => handleUpdateIssueStatus(issue.id, 'resolved')}>
                        <CheckCircle className="w-3 h-3 mr-1" /> Resolve
                      </Button>
                      <Button variant="ghost" size="sm" className="h-6 text-[10px] text-purple-600" onClick={() => handleUpdateIssueStatus(issue.id, 'escalated')}>Escalate</Button>
                    </div>
                  )}
                  <p className="text-[10px] text-slate-400 mt-1">Logged by {issue.created_by_name}</p>
                </div>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* ===== Blister Check Form Modal ===== */}
      <Dialog open={showBlisterForm} onOpenChange={setShowBlisterForm}>
        <DialogContent className="max-w-lg" data-testid="blister-form-modal">
          <DialogHeader>
            <DialogTitle className="text-[#00205B] uppercase font-bold">Log Blister Check</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 mt-2">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Cadet Name *</Label>
                <Input value={blisterForm.cadet_name} onChange={(e) => setBlisterForm(p => ({...p, cadet_name: e.target.value}))} className="h-8 text-sm rounded-sm" data-testid="blister-cadet-name" />
              </div>
              <div>
                <Label className="text-xs">CAPID</Label>
                <Input value={blisterForm.capid} onChange={(e) => setBlisterForm(p => ({...p, capid: e.target.value}))} className="h-8 text-sm rounded-sm" />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label className="text-xs">Flight</Label>
                <Select value={blisterForm.flight || "none"} onValueChange={(v) => setBlisterForm(p => ({...p, flight: v === 'none' ? '' : v}))}>
                  <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Select</SelectItem>
                    {FLIGHTS.map(f => <SelectItem key={f} value={f}>{f.charAt(0).toUpperCase() + f.slice(1)}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Date</Label>
                <Input type="date" value={blisterForm.date} onChange={(e) => setBlisterForm(p => ({...p, date: e.target.value}))} className="h-8 text-sm rounded-sm" />
              </div>
              <div>
                <Label className="text-xs">Severity</Label>
                <Select value={blisterForm.severity} onValueChange={(v) => setBlisterForm(p => ({...p, severity: v}))}>
                  <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    <SelectItem value="mild">Mild</SelectItem>
                    <SelectItem value="moderate">Moderate</SelectItem>
                    <SelectItem value="severe">Severe</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label className="text-xs">Location</Label>
              <Select value={blisterForm.location || "none"} onValueChange={(v) => setBlisterForm(p => ({...p, location: v === 'none' ? '' : v}))}>
                <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Select Location</SelectItem>
                  {BLISTER_LOCATIONS.map(l => <SelectItem key={l} value={l}>{l}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Description</Label>
              <Textarea value={blisterForm.description} onChange={(e) => setBlisterForm(p => ({...p, description: e.target.value}))} rows={2} className="text-sm rounded-sm" />
            </div>
            <div>
              <Label className="text-xs">Treatment Given</Label>
              <Textarea value={blisterForm.treatment_given} onChange={(e) => setBlisterForm(p => ({...p, treatment_given: e.target.value}))} rows={2} className="text-sm rounded-sm" />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={blisterForm.follow_up_needed} onChange={(e) => setBlisterForm(p => ({...p, follow_up_needed: e.target.checked}))} className="rounded" />
              Follow-up needed
            </label>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={() => setShowBlisterForm(false)}>Cancel</Button>
              <Button onClick={handleCreateBlister} className="bg-[#00205B]" data-testid="submit-blister-check">Log Check</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* ===== Counseling Form Modal ===== */}
      <Dialog open={showCounselingForm} onOpenChange={setShowCounselingForm}>
        <DialogContent className="max-w-lg" data-testid="counseling-form-modal">
          <DialogHeader>
            <DialogTitle className="text-[#00205B] uppercase font-bold">Log Counseling Session</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 mt-2">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Cadet Name *</Label>
                <Input value={counselingForm.cadet_name} onChange={(e) => setCounselingForm(p => ({...p, cadet_name: e.target.value}))} className="h-8 text-sm rounded-sm" data-testid="counseling-cadet-name" />
              </div>
              <div>
                <Label className="text-xs">CAPID</Label>
                <Input value={counselingForm.capid} onChange={(e) => setCounselingForm(p => ({...p, capid: e.target.value}))} className="h-8 text-sm rounded-sm" />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label className="text-xs">Flight</Label>
                <Select value={counselingForm.flight || "none"} onValueChange={(v) => setCounselingForm(p => ({...p, flight: v === 'none' ? '' : v}))}>
                  <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Select</SelectItem>
                    {FLIGHTS.map(f => <SelectItem key={f} value={f}>{f.charAt(0).toUpperCase() + f.slice(1)}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Date</Label>
                <Input type="date" value={counselingForm.date} onChange={(e) => setCounselingForm(p => ({...p, date: e.target.value}))} className="h-8 text-sm rounded-sm" />
              </div>
              <div>
                <Label className="text-xs">Category *</Label>
                <Select value={counselingForm.category} onValueChange={(v) => setCounselingForm(p => ({...p, category: v}))}>
                  <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {COUNSELING_CATEGORIES.map(c => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label className="text-xs">Reason *</Label>
              <Textarea value={counselingForm.reason} onChange={(e) => setCounselingForm(p => ({...p, reason: e.target.value}))} rows={3} className="text-sm rounded-sm" data-testid="counseling-reason" />
            </div>
            <div>
              <Label className="text-xs">Outcome</Label>
              <Textarea value={counselingForm.outcome} onChange={(e) => setCounselingForm(p => ({...p, outcome: e.target.value}))} rows={2} className="text-sm rounded-sm" />
            </div>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={counselingForm.follow_up_needed} onChange={(e) => setCounselingForm(p => ({...p, follow_up_needed: e.target.checked}))} className="rounded" />
                Follow-up needed
              </label>
              {counselingForm.follow_up_needed && (
                <Input type="date" value={counselingForm.follow_up_date} onChange={(e) => setCounselingForm(p => ({...p, follow_up_date: e.target.value}))} className="w-40 h-8 text-sm rounded-sm" />
              )}
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={() => setShowCounselingForm(false)}>Cancel</Button>
              <Button onClick={handleCreateCounseling} className="bg-[#00205B]" data-testid="submit-counseling">Log Session</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* ===== Cadre Issue Form Modal ===== */}
      <Dialog open={showIssueForm} onOpenChange={setShowIssueForm}>
        <DialogContent className="max-w-lg" data-testid="cadre-issue-form-modal">
          <DialogHeader>
            <DialogTitle className="text-[#00205B] uppercase font-bold">Log Cadre Issue</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 mt-2">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Cadre Member Name *</Label>
                <Input value={issueForm.cadre_name} onChange={(e) => setIssueForm(p => ({...p, cadre_name: e.target.value}))} className="h-8 text-sm rounded-sm" data-testid="issue-cadre-name" />
              </div>
              <div>
                <Label className="text-xs">CAPID</Label>
                <Input value={issueForm.cadre_capid} onChange={(e) => setIssueForm(p => ({...p, cadre_capid: e.target.value}))} className="h-8 text-sm rounded-sm" />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label className="text-xs">Flight</Label>
                <Select value={issueForm.flight || "none"} onValueChange={(v) => setIssueForm(p => ({...p, flight: v === 'none' ? '' : v}))}>
                  <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Select</SelectItem>
                    {FLIGHTS.map(f => <SelectItem key={f} value={f}>{f.charAt(0).toUpperCase() + f.slice(1)}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Category</Label>
                <Select value={issueForm.category} onValueChange={(v) => setIssueForm(p => ({...p, category: v}))}>
                  <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CADRE_ISSUE_CATEGORIES.map(c => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Severity</Label>
                <Select value={issueForm.severity} onValueChange={(v) => setIssueForm(p => ({...p, severity: v}))}>
                  <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="critical">Critical</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label className="text-xs">Description *</Label>
              <Textarea value={issueForm.description} onChange={(e) => setIssueForm(p => ({...p, description: e.target.value}))} rows={3} className="text-sm rounded-sm" data-testid="issue-description" />
            </div>
            <div>
              <Label className="text-xs">Action Taken</Label>
              <Textarea value={issueForm.action_taken} onChange={(e) => setIssueForm(p => ({...p, action_taken: e.target.value}))} rows={2} className="text-sm rounded-sm" />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={() => setShowIssueForm(false)}>Cancel</Button>
              <Button onClick={handleCreateIssue} className="bg-[#00205B]" data-testid="submit-cadre-issue">Log Issue</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

const SummaryCard = ({ icon: Icon, label, value, color }) => (
  <div className="bg-white border border-slate-200 rounded-sm p-3">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-[10px] uppercase tracking-wide text-slate-400">{label}</p>
        <p className={`text-xl font-bold ${color}`}>{value}</p>
      </div>
      <Icon className={`w-5 h-5 ${color} opacity-50`} />
    </div>
  </div>
);

const EmptyState = ({ text }) => (
  <div className="text-center py-12 text-slate-400 bg-white border border-slate-200 rounded-sm">
    <p className="text-sm">{text}</p>
    <p className="text-xs mt-1">Click the button above to add a new entry</p>
  </div>
);

export default TrainingOfficerPage;
