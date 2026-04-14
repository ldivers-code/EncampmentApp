import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  getCheckInRoster, getCheckInSummary, checkInStep, undoCheckInStep,
  checkInAll, undoAllCheckIn,
  getParticipantContraband, addContraband, returnContraband, deleteContraband
} from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '../components/ui/sheet';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import {
  UserCheck, Search, RefreshCw, CheckCircle, Circle, Users,
  ChevronRight, Undo2, CheckCheck, ClipboardList, Clock,
  Filter, Plane, FileText, Home, Package, MessageSquare, X,
  AlertTriangle, Plus, Trash2, RotateCcw
} from 'lucide-react';

const STEPS = [
  { key: 'arrival', label: 'Arrival', icon: Plane, color: 'emerald' },
  { key: 'paperwork', label: 'Paperwork', icon: FileText, color: 'blue' },
  { key: 'bunk_assignment', label: 'Bunk Assign', icon: Home, color: 'amber' },
  { key: 'gear_issue', label: 'Gear Issue', icon: Package, color: 'purple' },
];

const STEP_COLORS = {
  emerald: { bg: 'bg-emerald-500', light: 'bg-emerald-50 border-emerald-200 text-emerald-700', ring: 'ring-emerald-500' },
  blue: { bg: 'bg-blue-500', light: 'bg-blue-50 border-blue-200 text-blue-700', ring: 'ring-blue-500' },
  amber: { bg: 'bg-amber-500', light: 'bg-amber-50 border-amber-200 text-amber-700', ring: 'ring-amber-500' },
  purple: { bg: 'bg-purple-500', light: 'bg-purple-50 border-purple-200 text-purple-700', ring: 'ring-purple-500' },
};

// Step indicator pill
const StepPill = ({ step, stepInfo, onClick, onUndo, disabled }) => {
  const completed = stepInfo?.completed;
  const colors = STEP_COLORS[step.color];
  const Icon = step.icon;

  return (
    <div className="relative group">
      <button
        onClick={() => !completed ? onClick(step.key) : null}
        disabled={disabled}
        className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-sm text-xs font-medium border transition-all ${
          completed
            ? `${colors.light} border`
            : 'bg-slate-50 border-slate-200 text-slate-400 hover:bg-slate-100 hover:text-slate-600'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        data-testid={`step-${step.key}`}
        title={completed ? `Completed by ${stepInfo.completed_by_name || 'unknown'}` : `Click to check-in: ${step.label}`}
      >
        {completed ? (
          <CheckCircle className="w-3.5 h-3.5" />
        ) : (
          <Circle className="w-3.5 h-3.5" />
        )}
        <Icon className="w-3 h-3" />
        <span className="hidden sm:inline">{step.label}</span>
      </button>
      {completed && !disabled && (
        <button
          onClick={(e) => { e.stopPropagation(); onUndo(step.key); }}
          className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-red-500 text-white rounded-full items-center justify-center text-[8px] hidden group-hover:flex"
          title="Undo"
          data-testid={`undo-step-${step.key}`}
        >
          <X className="w-2.5 h-2.5" />
        </button>
      )}
    </div>
  );
};

// Individual participant detail sheet
// Contraband section inside check-in detail
const ContrabandsSection = ({ participantId, canEdit }) => {
  const [items, setItems] = useState([]);
  const [showAdd, setShowAdd] = useState(false);
  const [newItem, setNewItem] = useState({ item_name: '', description: '', category: 'electronics', storage_location: '', notes: '' });

  useEffect(() => { if (participantId) loadItems(); }, [participantId]);

  const loadItems = async () => {
    try { const data = await getParticipantContraband(participantId); setItems(data); }
    catch { setItems([]); }
  };

  const handleAdd = async () => {
    if (!newItem.item_name) return;
    try {
      await addContraband(participantId, newItem);
      toast.success('Contraband logged');
      setShowAdd(false);
      setNewItem({ item_name: '', description: '', category: 'electronics', storage_location: '', notes: '' });
      loadItems();
    } catch { toast.error('Failed'); }
  };

  const handleReturn = async (itemId) => {
    try { await returnContraband(itemId, { returned_to: 'Cadet' }); toast.success('Marked returned'); loadItems(); }
    catch { toast.error('Failed'); }
  };

  const CATEGORIES = ['electronics', 'weapon', 'tobacco', 'alcohol', 'food', 'other'];

  return (
    <div className="pt-3 border-t border-slate-200" data-testid="contraband-section">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-bold text-[#00205B] flex items-center gap-1.5">
          <AlertTriangle className="w-4 h-4" /> Contraband
          {items.length > 0 && <span className="bg-red-100 text-red-700 text-xs px-1.5 py-0.5 rounded-full ml-1">{items.length}</span>}
        </h4>
        {canEdit && (
          <Button size="sm" variant="outline" className="h-6 text-xs rounded-sm" onClick={() => setShowAdd(!showAdd)} data-testid="add-contraband-btn">
            <Plus className="w-3 h-3 mr-1" /> Log Item
          </Button>
        )}
      </div>

      {showAdd && (
        <div className="bg-red-50 border border-red-200 rounded-sm p-3 mb-2 space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <input value={newItem.item_name} onChange={e => setNewItem({...newItem, item_name: e.target.value})}
              placeholder="Item name *" className="h-8 text-xs border rounded-sm px-2" data-testid="contraband-item-name" />
            <select value={newItem.category} onChange={e => setNewItem({...newItem, category: e.target.value})}
              className="h-8 text-xs border rounded-sm px-2">
              {CATEGORIES.map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
            </select>
            <input value={newItem.description} onChange={e => setNewItem({...newItem, description: e.target.value})}
              placeholder="Description" className="h-8 text-xs border rounded-sm px-2" />
            <input value={newItem.storage_location} onChange={e => setNewItem({...newItem, storage_location: e.target.value})}
              placeholder="Storage location" className="h-8 text-xs border rounded-sm px-2" />
          </div>
          <div className="flex gap-2">
            <Button size="sm" className="bg-red-600 hover:bg-red-700 text-white h-7 text-xs rounded-sm" onClick={handleAdd} disabled={!newItem.item_name}>Save</Button>
            <Button size="sm" variant="outline" className="h-7 text-xs rounded-sm" onClick={() => setShowAdd(false)}>Cancel</Button>
          </div>
        </div>
      )}

      {items.length > 0 && (
        <div className="space-y-1.5">
          {items.map(item => (
            <div key={item.id} className={`flex items-center justify-between p-2 rounded-sm border text-xs ${item.returned ? 'bg-slate-50 border-slate-200 opacity-60' : 'bg-red-50 border-red-200'}`}
                 data-testid={`contraband-${item.id}`}>
              <div>
                <span className="font-medium">{item.item_name}</span>
                {item.description && <span className="text-slate-500 ml-1">({item.description})</span>}
                <span className="ml-2 px-1.5 py-0.5 bg-slate-200 rounded text-[10px]">{item.category}</span>
                {item.storage_location && <span className="ml-1 text-slate-400">@ {item.storage_location}</span>}
                {item.returned && <span className="ml-2 text-green-600 font-bold">RETURNED</span>}
              </div>
              {canEdit && !item.returned && (
                <Button size="sm" variant="ghost" className="h-6 text-xs text-green-600 hover:bg-green-50" onClick={() => handleReturn(item.id)}>
                  <RotateCcw className="w-3 h-3 mr-1" /> Return
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const ParticipantDetailSheet = ({ participant, isOpen, onClose, onStepAction, canEdit }) => {
  const [noteText, setNoteText] = useState('');
  const [activeNoteStep, setActiveNoteStep] = useState(null);
  const [processing, setProcessing] = useState(false);

  if (!isOpen || !participant) return null;

  const handleStepWithNote = async (step) => {
    setProcessing(true);
    await onStepAction('check', participant.participant_id, step, noteText);
    setNoteText('');
    setActiveNoteStep(null);
    setProcessing(false);
  };

  const handleUndo = async (step) => {
    setProcessing(true);
    await onStepAction('undo', participant.participant_id, step);
    setProcessing(false);
  };

  const handleCheckAll = async () => {
    setProcessing(true);
    await onStepAction('checkAll', participant.participant_id);
    setProcessing(false);
  };

  const handleUndoAll = async () => {
    setProcessing(true);
    await onStepAction('undoAll', participant.participant_id);
    setProcessing(false);
  };

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto" data-testid="check-in-detail-sheet">
        <SheetHeader>
          <SheetTitle className="text-[#00205B] uppercase font-bold flex items-center gap-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
            <UserCheck className="w-5 h-5" />
            In-Processing Check-In
          </SheetTitle>
        </SheetHeader>

        <div className="mt-4 space-y-5">
          {/* Participant Header */}
          <div className="bg-[#00205B] text-white rounded-sm p-4">
            <h3 className="text-lg font-bold">{participant.name}</h3>
            <p className="text-blue-200 text-sm">
              {participant.capid && `CAPID: ${participant.capid} | `}
              {participant.rank && `${participant.rank} | `}
              <span className="capitalize">{participant.category}</span>
            </p>
            <p className="text-blue-200 text-xs mt-1">
              {participant.flight && `Flight: ${participant.flight} | `}
              {participant.squadron && `Sqdn: ${participant.squadron}`}
              {participant.wing && ` | Wing: ${participant.wing}`}
            </p>
            <div className="mt-2 flex items-center gap-2">
              <div className="flex-1 bg-blue-900 rounded-full h-2">
                <div
                  className="bg-emerald-400 h-2 rounded-full transition-all"
                  style={{ width: `${(participant.completed_steps / participant.total_steps) * 100}%` }}
                />
              </div>
              <span className="text-xs text-blue-200">
                {participant.completed_steps}/{participant.total_steps}
              </span>
            </div>
          </div>

          {/* Steps List */}
          <div className="space-y-3">
            {STEPS.map((step) => {
              const stepData = participant.steps?.[step.key] || {};
              const completed = stepData.completed;
              const colors = STEP_COLORS[step.color];
              const Icon = step.icon;

              return (
                <div
                  key={step.key}
                  className={`p-3 border rounded-sm transition-all ${
                    completed ? `${colors.light}` : 'border-slate-200 bg-white'
                  }`}
                  data-testid={`detail-step-${step.key}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {completed ? (
                        <CheckCircle className="w-5 h-5" />
                      ) : (
                        <Circle className="w-5 h-5 text-slate-300" />
                      )}
                      <Icon className="w-4 h-4" />
                      <span className="font-bold text-sm">{step.label}</span>
                    </div>
                    {canEdit && (
                      <div className="flex gap-1">
                        {!completed ? (
                          <>
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-xs h-7"
                              onClick={() => setActiveNoteStep(activeNoteStep === step.key ? null : step.key)}
                            >
                              <MessageSquare className="w-3 h-3 mr-1" /> Note
                            </Button>
                            <Button
                              size="sm"
                              className={`text-xs h-7 ${colors.bg} text-white hover:opacity-90`}
                              onClick={() => handleStepWithNote(step.key)}
                              disabled={processing}
                            >
                              Check In
                            </Button>
                          </>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-xs h-7 text-red-600 hover:bg-red-50"
                            onClick={() => handleUndo(step.key)}
                            disabled={processing}
                          >
                            <Undo2 className="w-3 h-3 mr-1" /> Undo
                          </Button>
                        )}
                      </div>
                    )}
                  </div>
                  {completed && (
                    <div className="mt-2 ml-7 text-xs">
                      <p>
                        <Clock className="w-3 h-3 inline mr-1" />
                        {new Date(stepData.completed_at).toLocaleString()}
                      </p>
                      {stepData.completed_by_name && (
                        <p className="mt-0.5">By: {stepData.completed_by_name}</p>
                      )}
                      {stepData.notes && (
                        <p className="mt-1 italic bg-white/50 px-2 py-1 rounded">{stepData.notes}</p>
                      )}
                    </div>
                  )}
                  {activeNoteStep === step.key && !completed && (
                    <div className="mt-2 ml-7">
                      <Input
                        placeholder="Add a note (optional)..."
                        value={noteText}
                        onChange={(e) => setNoteText(e.target.value)}
                        className="text-xs"
                        data-testid={`note-input-${step.key}`}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Bulk Actions */}
          {canEdit && (
            <div className="flex gap-2 pt-2 border-t border-slate-200">
              {!participant.fully_checked_in ? (
                <Button
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                  onClick={handleCheckAll}
                  disabled={processing}
                  data-testid="check-all-btn"
                >
                  <CheckCheck className="w-4 h-4 mr-2" /> Check-In All Steps
                </Button>
              ) : (
                <Button
                  variant="outline"
                  className="flex-1 text-red-600 hover:bg-red-50"
                  onClick={handleUndoAll}
                  disabled={processing}
                  data-testid="undo-all-btn"
                >
                  <Undo2 className="w-4 h-4 mr-2" /> Undo All Check-Ins
                </Button>
              )}
            </div>
          )}

          {/* Contraband Section */}
          <ContrabandsSection participantId={participant.participant_id} canEdit={canEdit} />
        </div>
      </SheetContent>
    </Sheet>
  );
};

// Main Check-In Page
const CheckInPage = () => {
  const { user } = useAuth();
  const [roster, setRoster] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [filterFlight, setFilterFlight] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [selectedParticipant, setSelectedParticipant] = useState(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const canEdit = ['dcp', 'commander', 'executive_staff', 'plans_programs', 'logistics', 'support_logistics'].includes(user?.role);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [rosterData, summaryData] = await Promise.all([
        getCheckInRoster(activeCategory),
        getCheckInSummary()
      ]);
      setRoster(rosterData);
      setSummary(summaryData);
    } catch (error) {
      toast.error('Failed to load check-in data');
    } finally {
      setLoading(false);
    }
  }, [activeCategory]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleStepAction = async (action, participantId, step, notes) => {
    try {
      if (action === 'check') {
        await checkInStep(participantId, step, notes || '');
        toast.success(`Step checked in`);
      } else if (action === 'undo') {
        await undoCheckInStep(participantId, step);
        toast.success(`Step undone`);
      } else if (action === 'checkAll') {
        await checkInAll(participantId);
        toast.success('All steps checked in');
      } else if (action === 'undoAll') {
        await undoAllCheckIn(participantId);
        toast.success('All check-ins undone');
      }
      // Reload data
      const [rosterData, summaryData] = await Promise.all([
        getCheckInRoster(activeCategory),
        getCheckInSummary()
      ]);
      setRoster(rosterData);
      setSummary(summaryData);
      // Update selected participant
      if (selectedParticipant) {
        const updated = rosterData.find(r => r.participant_id === selectedParticipant.participant_id);
        if (updated) setSelectedParticipant(updated);
      }
    } catch (error) {
      toast.error(`Action failed: ${error.response?.data?.detail || error.message}`);
    }
  };

  const quickCheckStep = async (e, participantId, step) => {
    e.stopPropagation();
    await handleStepAction('check', participantId, step);
  };

  const quickUndoStep = async (step, participantId) => {
    await handleStepAction('undo', participantId, step);
  };

  const openDetail = (participant) => {
    setSelectedParticipant(participant);
    setDetailOpen(true);
  };

  // Compute filters
  const flights = [...new Set(roster.map(r => r.flight).filter(Boolean))].sort();

  const filtered = roster.filter(r => {
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      if (!r.name.toLowerCase().includes(q) && !r.capid?.toLowerCase().includes(q)) return false;
    }
    if (filterFlight !== 'all' && r.flight !== filterFlight) return false;
    if (filterStatus === 'complete' && !r.fully_checked_in) return false;
    if (filterStatus === 'partial' && (r.completed_steps === 0 || r.fully_checked_in)) return false;
    if (filterStatus === 'none' && r.completed_steps > 0) return false;
    return true;
  });

  const categories = [
    { key: 'all', label: 'All', count: summary?.total_participants || 0 },
    { key: 'student', label: 'Students', count: summary?.total_students || 0 },
    { key: 'staff', label: 'Staff', count: summary?.total_staff || 0 },
    { key: 'cadre', label: 'Cadre', count: summary?.total_cadre || 0 },
  ];

  return (
    <div className="p-4 sm:p-6 max-w-full" data-testid="check-in-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-3">
        <div>
          <h1 className="text-2xl font-black text-[#00205B] uppercase tracking-tight" style={{ fontFamily: 'Chivo, sans-serif' }}>
            In-Processing Check-In
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">Track arrival and processing status for all participants</p>
        </div>
        <Button variant="outline" size="sm" onClick={loadData} className="rounded-sm" data-testid="refresh-btn">
          <RefreshCw className="w-4 h-4 mr-1" /> Refresh
        </Button>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 mb-6">
          <div className="bg-white border border-slate-200 rounded-sm p-3 text-center">
            <p className="text-2xl font-bold text-[#00205B]">{summary.total_participants}</p>
            <p className="text-[10px] uppercase tracking-wide text-slate-500">Total Expected</p>
          </div>
          <div className="bg-emerald-50 border border-emerald-200 rounded-sm p-3 text-center">
            <p className="text-2xl font-bold text-emerald-700">{summary.fully_checked_in}</p>
            <p className="text-[10px] uppercase tracking-wide text-emerald-600">Fully Checked In</p>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-sm p-3 text-center">
            <p className="text-2xl font-bold text-red-700">{summary.not_checked_in}</p>
            <p className="text-[10px] uppercase tracking-wide text-red-600">Not Complete</p>
          </div>
          {/* Per-step counts */}
          {STEPS.map(step => (
            <div key={step.key} className="bg-white border border-slate-200 rounded-sm p-3 text-center">
              <p className="text-2xl font-bold text-slate-700">{summary.step_counts?.[step.key] || 0}</p>
              <p className="text-[10px] uppercase tracking-wide text-slate-500">{step.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Category Tabs */}
      <div className="flex border-b border-slate-200 mb-4" data-testid="category-tabs">
        {categories.map(cat => (
          <button
            key={cat.key}
            onClick={() => setActiveCategory(cat.key)}
            className={`px-4 py-2.5 text-sm font-bold uppercase tracking-wide transition-colors border-b-2 -mb-px ${
              activeCategory === cat.key
                ? 'text-[#00205B] border-[#00205B]'
                : 'text-slate-500 border-transparent hover:text-slate-700 hover:border-slate-300'
            }`}
            data-testid={`tab-${cat.key}`}
          >
            {cat.label}
            <span className="ml-1.5 text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded-full">{cat.count}</span>
          </button>
        ))}
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col sm:flex-row gap-2 mb-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            placeholder="Search by name or CAPID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 rounded-sm"
            data-testid="check-in-search"
          />
        </div>
        <Select value={filterFlight} onValueChange={setFilterFlight}>
          <SelectTrigger className="w-36 rounded-sm" data-testid="flight-filter">
            <SelectValue placeholder="All Flights" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Flights</SelectItem>
            {flights.map(f => <SelectItem key={f} value={f}>{f}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-36 rounded-sm" data-testid="status-filter">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="complete">Fully Checked In</SelectItem>
            <SelectItem value="partial">Partial</SelectItem>
            <SelectItem value="none">Not Started</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Results */}
      <p className="text-xs text-slate-500 mb-2">{filtered.length} participants shown</p>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <RefreshCw className="w-5 h-5 animate-spin text-slate-400 mr-2" />
          <span className="text-slate-500">Loading...</span>
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-sm p-12 text-center">
          <Users className="w-12 h-12 mx-auto mb-3 text-slate-300" />
          <p className="text-slate-500">No participants match your filters</p>
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="check-in-table">
              <thead>
                <tr className="bg-[#00205B] text-white text-xs uppercase tracking-wide">
                  <th className="text-left p-3">Participant</th>
                  <th className="text-left p-3 hidden sm:table-cell">Flight</th>
                  <th className="text-center p-3">Progress</th>
                  <th className="text-center p-3">Steps</th>
                  <th className="text-center p-3 w-10"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((p) => (
                  <tr
                    key={p.participant_id}
                    className={`hover:bg-blue-50 cursor-pointer transition-colors ${
                      p.fully_checked_in ? 'bg-emerald-50/30' : ''
                    }`}
                    onClick={() => openDetail(p)}
                    data-testid={`checkin-row-${p.capid || p.participant_id}`}
                  >
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        {p.fully_checked_in ? (
                          <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                        ) : p.completed_steps > 0 ? (
                          <div className="w-4 h-4 rounded-full border-2 border-amber-400 flex-shrink-0 flex items-center justify-center">
                            <div className="w-1.5 h-1.5 bg-amber-400 rounded-full" />
                          </div>
                        ) : (
                          <Circle className="w-4 h-4 text-slate-300 flex-shrink-0" />
                        )}
                        <div>
                          <p className="font-medium text-[#00205B]">{p.name}</p>
                          <p className="text-[10px] text-slate-500">
                            {p.capid && `CAPID: ${p.capid}`}
                            {p.rank && ` | ${p.rank}`}
                            <span className="capitalize"> | {p.category}</span>
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="p-3 hidden sm:table-cell">
                      <span className="text-xs capitalize">{p.flight || '-'}</span>
                    </td>
                    <td className="p-3 text-center">
                      <div className="flex items-center gap-2 justify-center">
                        <div className="w-20 bg-slate-200 rounded-full h-1.5">
                          <div
                            className={`h-1.5 rounded-full transition-all ${
                              p.fully_checked_in ? 'bg-emerald-500' :
                              p.completed_steps > 0 ? 'bg-amber-400' : 'bg-slate-200'
                            }`}
                            style={{ width: `${(p.completed_steps / p.total_steps) * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-slate-500">{p.completed_steps}/{p.total_steps}</span>
                      </div>
                    </td>
                    <td className="p-3">
                      <div className="flex gap-1 justify-center flex-wrap" onClick={e => e.stopPropagation()}>
                        {STEPS.map(step => (
                          <StepPill
                            key={step.key}
                            step={step}
                            stepInfo={p.steps?.[step.key]}
                            onClick={(s) => canEdit && quickCheckStep({ stopPropagation: () => {} }, p.participant_id, s)}
                            onUndo={(s) => canEdit && quickUndoStep(s, p.participant_id)}
                            disabled={!canEdit}
                          />
                        ))}
                      </div>
                    </td>
                    <td className="p-3 text-center">
                      <ChevronRight className="w-4 h-4 text-slate-400" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Participant Detail Sheet */}
      <ParticipantDetailSheet
        participant={selectedParticipant}
        isOpen={detailOpen}
        onClose={() => setDetailOpen(false)}
        onStepAction={handleStepAction}
        canEdit={canEdit}
      />
    </div>
  );
};

export default CheckInPage;
