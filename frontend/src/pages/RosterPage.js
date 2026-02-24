import React, { useState, useEffect, useMemo } from 'react';
import { getParticipants, createParticipant, updateParticipant, deleteParticipant, importParticipants, getParticipantStats, removeParticipantFromEncampment, reinstateParticipant } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { 
  Plus, 
  Search, 
  Upload, 
  Edit2, 
  Trash2, 
  Users,
  Filter,
  Download,
  ChevronLeft,
  ChevronRight,
  CheckCircle,
  AlertCircle,
  DollarSign,
  UserCheck,
  FileSpreadsheet,
  RefreshCw,
  X,
  Phone,
  Mail,
  MapPin,
  Calendar,
  Shield,
  UserX,
  RotateCcw,
  Eye
} from 'lucide-react';

const RosterPage = () => {
  const { canEdit } = useAuth();
  const [participants, setParticipants] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [paidFilter, setPaidFilter] = useState('all');
  const [showRemoved, setShowRemoved] = useState(false);
  const [editingParticipant, setEditingParticipant] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  // Participant detail view
  const [selectedParticipant, setSelectedParticipant] = useState(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  // Removal modal
  const [isRemovalModalOpen, setIsRemovalModalOpen] = useState(false);
  const [removalReason, setRemovalReason] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;

  const [formData, setFormData] = useState({
    capid: '',
    rank: '',
    last_name: '',
    first_name: '',
    unit: '',
    wing: '',
    region: '',
    gender: '',
    age: '',
    email: '',
    phone: '',
    shirt_size: '',
    participant_type: 'basic_student',
    squadron: '',
    flight: '',
    position: '',
    paid: false,
    first_encampment: true,
    religious_preference: '',
    emergency_contact: '',
    notes: ''
  });

  useEffect(() => {
    loadParticipants();
    loadStats();
  }, []);

  const loadParticipants = async () => {
    try {
      const data = await getParticipants();
      setParticipants(data);
    } catch (error) {
      toast.error('Failed to load participants');
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const data = await getParticipantStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats');
    }
  };

  const filteredParticipants = useMemo(() => {
    return participants.filter(p => {
      // Filter out removed participants unless showRemoved is true
      if (!showRemoved && p.is_removed) return false;
      if (showRemoved && !p.is_removed) return false;
      
      const matchesSearch = 
        `${p.first_name} ${p.last_name} ${p.capid} ${p.unit}`.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = typeFilter === 'all' || p.participant_type === typeFilter;
      const matchesPaid = paidFilter === 'all' || 
        (paidFilter === 'paid' && (p.paid || p.paid_in_full)) ||
        (paidFilter === 'unpaid' && !p.paid && !p.paid_in_full);
      return matchesSearch && matchesType && matchesPaid;
    });
  }, [participants, searchTerm, typeFilter, paidFilter, showRemoved]);

  const paginatedParticipants = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredParticipants.slice(start, start + itemsPerPage);
  }, [filteredParticipants, currentPage]);

  const totalPages = Math.ceil(filteredParticipants.length / itemsPerPage);

  // Count removed participants
  const removedCount = useMemo(() => {
    return participants.filter(p => p.is_removed).length;
  }, [participants]);

  const handleViewParticipant = (participant) => {
    setSelectedParticipant(participant);
    setIsDetailOpen(true);
  };

  const handleRemoveParticipant = async () => {
    if (!selectedParticipant || !removalReason.trim()) {
      toast.error('Please provide a reason for removal');
      return;
    }
    
    try {
      await removeParticipantFromEncampment(selectedParticipant.id, removalReason);
      toast.success(`${selectedParticipant.first_name} ${selectedParticipant.last_name} removed from encampment`);
      setIsRemovalModalOpen(false);
      setRemovalReason('');
      setIsDetailOpen(false);
      setSelectedParticipant(null);
      loadParticipants();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to remove participant');
    }
  };

  const handleReinstateParticipant = async (participant) => {
    try {
      await reinstateParticipant(participant.id);
      toast.success(`${participant.first_name} ${participant.last_name} reinstated`);
      loadParticipants();
      if (selectedParticipant?.id === participant.id) {
        setIsDetailOpen(false);
        setSelectedParticipant(null);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reinstate participant');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const dataToSubmit = {
        ...formData,
        age: formData.age ? parseInt(formData.age) : null
      };
      
      if (editingParticipant) {
        await updateParticipant(editingParticipant.id, dataToSubmit);
        toast.success('Participant updated');
      } else {
        await createParticipant(dataToSubmit);
        toast.success('Participant added');
      }
      setIsModalOpen(false);
      resetForm();
      loadParticipants();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Operation failed');
    }
  };

  const handleEdit = (participant) => {
    setEditingParticipant(participant);
    setFormData({
      ...participant,
      age: participant.age || ''
    });
    setIsModalOpen(true);
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to remove this participant?')) {
      try {
        await deleteParticipant(id);
        toast.success('Participant removed');
        loadParticipants();
      } catch (error) {
        toast.error('Failed to remove participant');
      }
    }
  };

  const handleImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setImporting(true);
    try {
      const result = await importParticipants(file);
      setImportResult(result);
      toast.success(`Import complete: ${result.imported} new, ${result.updated} updated`);
      loadParticipants();
      loadStats();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Import failed');
    } finally {
      setImporting(false);
    }
    e.target.value = '';
  };

  const resetForm = () => {
    setEditingParticipant(null);
    setFormData({
      capid: '',
      rank: '',
      last_name: '',
      first_name: '',
      unit: '',
      wing: '',
      region: '',
      gender: '',
      age: '',
      email: '',
      phone: '',
      shirt_size: '',
      participant_type: 'basic_student',
      squadron: '',
      flight: '',
      position: '',
      paid: false,
      first_encampment: true,
      religious_preference: '',
      emergency_contact: '',
      notes: ''
    });
  };

  const participantTypes = [
    { value: 'basic_student', label: 'Basic Student' },
    { value: 'advanced_student', label: 'Advanced Student' },
    { value: 'cadre', label: 'Cadre' },
    { value: 'staff', label: 'Staff' },
    { value: 'senior_member', label: 'Senior Member' }
  ];

  const getTypeBadgeColor = (type) => {
    const colors = {
      basic_student: 'bg-blue-100 text-blue-800 border-blue-200',
      advanced_student: 'bg-purple-100 text-purple-800 border-purple-200',
      cadre: 'bg-amber-100 text-amber-800 border-amber-200',
      staff: 'bg-emerald-100 text-emerald-800 border-emerald-200',
      senior_member: 'bg-slate-100 text-slate-800 border-slate-200'
    };
    return colors[type] || colors.basic_student;
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-400">Loading roster...</div>
        </div>
      </div>
    );
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(value || 0);
  };

  return (
    <div className="p-6 lg:p-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl lg:text-3xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Master Roster
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            {filteredParticipants.length} of {participants.length} participants
          </p>
        </div>
        
        {canEdit() && (
          <div className="flex items-center gap-2 flex-wrap">
            <label className="cursor-pointer">
              <input
                type="file"
                accept=".xlsx,.xls"
                onChange={handleImport}
                className="hidden"
                data-testid="import-roster-input"
              />
              <Button 
                variant="outline" 
                className="rounded-sm border-[#00205B] text-[#00205B] hover:bg-[#00205B]/10" 
                asChild
                disabled={importing}
              >
                <span>
                  {importing ? (
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <FileSpreadsheet className="w-4 h-4 mr-2" />
                  )}
                  {importing ? 'Importing...' : 'Import CAP Report'}
                </span>
              </Button>
            </label>
            
            <Dialog open={isModalOpen} onOpenChange={(open) => {
              setIsModalOpen(open);
              if (!open) resetForm();
            }}>
              <DialogTrigger asChild>
                <Button className="bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="add-participant-btn">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Participant
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle className="text-[#00205B] uppercase font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                    {editingParticipant ? 'Edit Participant' : 'Add Participant'}
                  </DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4 mt-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">CAP ID *</Label>
                      <Input
                        value={formData.capid}
                        onChange={(e) => setFormData({ ...formData, capid: e.target.value })}
                        required
                        className="mt-1 rounded-sm font-mono"
                        data-testid="participant-capid-input"
                      />
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Rank</Label>
                      <Input
                        value={formData.rank}
                        onChange={(e) => setFormData({ ...formData, rank: e.target.value })}
                        className="mt-1 rounded-sm"
                        placeholder="C/Amn"
                        data-testid="participant-rank-input"
                      />
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">First Name *</Label>
                      <Input
                        value={formData.first_name}
                        onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                        required
                        className="mt-1 rounded-sm"
                        data-testid="participant-firstname-input"
                      />
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Last Name *</Label>
                      <Input
                        value={formData.last_name}
                        onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                        required
                        className="mt-1 rounded-sm"
                        data-testid="participant-lastname-input"
                      />
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Unit *</Label>
                      <Input
                        value={formData.unit}
                        onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                        required
                        className="mt-1 rounded-sm font-mono"
                        placeholder="TN001"
                        data-testid="participant-unit-input"
                      />
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Participant Type</Label>
                      <Select
                        value={formData.participant_type}
                        onValueChange={(value) => setFormData({ ...formData, participant_type: value })}
                      >
                        <SelectTrigger className="mt-1 rounded-sm" data-testid="participant-type-select">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {participantTypes.map(type => (
                            <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Gender</Label>
                      <Select
                        value={formData.gender || ''}
                        onValueChange={(value) => setFormData({ ...formData, gender: value })}
                      >
                        <SelectTrigger className="mt-1 rounded-sm">
                          <SelectValue placeholder="Select" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="M">Male</SelectItem>
                          <SelectItem value="F">Female</SelectItem>
                          <SelectItem value="Other">Other</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Age</Label>
                      <Input
                        type="number"
                        value={formData.age}
                        onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                        className="mt-1 rounded-sm"
                        min="12"
                        max="99"
                      />
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Email</Label>
                      <Input
                        type="email"
                        value={formData.email || ''}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        className="mt-1 rounded-sm"
                      />
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Phone</Label>
                      <Input
                        value={formData.phone || ''}
                        onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                        className="mt-1 rounded-sm font-mono"
                      />
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Shirt Size</Label>
                      <Select
                        value={formData.shirt_size || ''}
                        onValueChange={(value) => setFormData({ ...formData, shirt_size: value })}
                      >
                        <SelectTrigger className="mt-1 rounded-sm">
                          <SelectValue placeholder="Select" />
                        </SelectTrigger>
                        <SelectContent>
                          {['XS', 'S', 'M', 'L', 'XL', '2XL', '3XL'].map(size => (
                            <SelectItem key={size} value={size}>{size}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Squadron</Label>
                      <Input
                        value={formData.squadron || ''}
                        onChange={(e) => setFormData({ ...formData, squadron: e.target.value })}
                        className="mt-1 rounded-sm"
                      />
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Flight</Label>
                      <Input
                        value={formData.flight || ''}
                        onChange={(e) => setFormData({ ...formData, flight: e.target.value })}
                        className="mt-1 rounded-sm"
                      />
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Position</Label>
                      <Input
                        value={formData.position || ''}
                        onChange={(e) => setFormData({ ...formData, position: e.target.value })}
                        className="mt-1 rounded-sm"
                      />
                    </div>
                    <div className="flex items-center gap-4 pt-6">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={formData.paid}
                          onChange={(e) => setFormData({ ...formData, paid: e.target.checked })}
                          className="rounded border-slate-300"
                        />
                        <span className="text-sm">Paid</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={formData.first_encampment}
                          onChange={(e) => setFormData({ ...formData, first_encampment: e.target.checked })}
                          className="rounded border-slate-300"
                        />
                        <span className="text-sm">First Encampment</span>
                      </label>
                    </div>
                  </div>
                  <div className="flex justify-end gap-2 pt-4">
                    <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)} className="rounded-sm">
                      Cancel
                    </Button>
                    <Button type="submit" className="bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="save-participant-btn">
                      {editingParticipant ? 'Update' : 'Add'} Participant
                    </Button>
                  </div>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        )}
      </div>

      {/* Import Results Banner */}
      {importResult && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-sm p-4 mb-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0" />
              <div>
                <p className="font-medium text-emerald-800">Import & Sync Complete</p>
                <p className="text-sm text-emerald-600">
                  {importResult.imported} new, {importResult.updated} updated ({importResult.total} total)
                </p>
              </div>
            </div>
            <div className="text-right text-sm flex-shrink-0">
              <div className="flex gap-4">
                <span className="text-emerald-700">Seniors: {importResult.stats?.seniors || 0}</span>
                <span className="text-emerald-700">Cadets: {importResult.stats?.cadets || 0}</span>
                <span className="text-emerald-700">Staff: {importResult.stats?.staff || 0}</span>
                <span className="text-emerald-700">Cadre: {importResult.stats?.cadre || 0}</span>
              </div>
              <div className="mt-1 flex gap-4 justify-end">
                <span className="text-emerald-600">Collected: {formatCurrency(importResult.stats?.total_collected || 0)}</span>
                {importResult.budget_sync && (
                  <span className="text-[#00205B] font-medium">Budget synced!</span>
                )}
              </div>
            </div>
            <button onClick={() => setImportResult(null)} className="text-emerald-400 hover:text-emerald-600 text-xl leading-none">
              ×
            </button>
          </div>
          
          {/* Budget Sync Details */}
          {importResult.budget_sync?.updates?.length > 0 && (
            <div className="mt-3 pt-3 border-t border-emerald-200">
              <p className="text-xs uppercase tracking-wide text-emerald-700 mb-2">Budget Income Updated:</p>
              <div className="flex gap-4 text-sm">
                {importResult.budget_sync.updates.map((u, i) => (
                  <span key={i} className="text-emerald-600">
                    {u.item}: {formatCurrency(u.actual)} ({u.count} participants)
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Stats Dashboard */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
          <div className="bg-white border border-slate-200 rounded-sm p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Total</p>
                <p className="text-2xl font-bold text-[#00205B]">{stats.total}</p>
              </div>
              <Users className="w-5 h-5 text-[#00205B]" />
            </div>
          </div>
          
          <div className="bg-white border border-slate-200 rounded-sm p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Seniors</p>
                <p className="text-2xl font-bold text-slate-700">{stats.seniors}</p>
                <p className="text-xs text-slate-400">{stats.staff} staff</p>
              </div>
              <UserCheck className="w-5 h-5 text-slate-500" />
            </div>
          </div>
          
          <div className="bg-white border border-slate-200 rounded-sm p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Cadets</p>
                <p className="text-2xl font-bold text-slate-700">{stats.cadets}</p>
                <p className="text-xs text-slate-400">{stats.cadre} cadre, {stats.students} students</p>
              </div>
              <Users className="w-5 h-5 text-slate-500" />
            </div>
          </div>
          
          <div className="bg-white border border-slate-200 rounded-sm p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Paid</p>
                <p className="text-2xl font-bold text-emerald-600">{stats.paid}</p>
                <p className="text-xs text-amber-600">{stats.unpaid} unpaid</p>
              </div>
              <DollarSign className="w-5 h-5 text-emerald-500" />
            </div>
          </div>
          
          <div className="bg-white border border-slate-200 rounded-sm p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Collected</p>
                <p className="text-xl font-bold text-emerald-600 font-mono">{formatCurrency(stats.total_collected)}</p>
              </div>
              <DollarSign className="w-5 h-5 text-emerald-500" />
            </div>
          </div>
          
          <div className="bg-white border border-slate-200 rounded-sm p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Approved</p>
                <p className="text-2xl font-bold text-[#00205B]">{stats.wing_approved}</p>
                <p className="text-xs text-slate-400">{stats.slotted} slotted</p>
              </div>
              <CheckCircle className="w-5 h-5 text-[#00205B]" />
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white border border-slate-200 rounded-sm p-4 mb-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search by name, CAPID, or unit..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              className="pl-10 rounded-sm"
              data-testid="roster-search-input"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <Select value={typeFilter} onValueChange={(value) => {
              setTypeFilter(value);
              setCurrentPage(1);
            }}>
              <SelectTrigger className="w-40 rounded-sm" data-testid="roster-type-filter">
                <SelectValue placeholder="Filter by type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                {participantTypes.map(type => (
                  <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={paidFilter} onValueChange={(value) => {
              setPaidFilter(value);
              setCurrentPage(1);
            }}>
              <SelectTrigger className="w-32 rounded-sm" data-testid="roster-paid-filter">
                <SelectValue placeholder="Payment" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="paid">Paid</SelectItem>
                <SelectItem value="unpaid">Unpaid</SelectItem>
              </SelectContent>
            </Select>
            {/* Show Removed Toggle */}
            <Button
              variant={showRemoved ? "default" : "outline"}
              size="sm"
              onClick={() => {
                setShowRemoved(!showRemoved);
                setCurrentPage(1);
              }}
              className={`rounded-sm text-xs ${showRemoved ? 'bg-red-600 hover:bg-red-700' : ''}`}
              data-testid="show-removed-toggle"
            >
              <UserX className="w-3 h-3 mr-1" />
              Removed ({removedCount})
            </Button>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-slate-200 rounded-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full cap-table" data-testid="roster-table">
            <thead>
              <tr>
                <th className="text-left">CAP ID</th>
                <th className="text-left">Rank</th>
                <th className="text-left">Name</th>
                <th className="text-left">Unit</th>
                <th className="text-left">Wing</th>
                <th className="text-left">Type</th>
                <th className="text-center">Paid</th>
                {!showRemoved && <th className="text-center">Approved</th>}
                {showRemoved && <th className="text-left">Removal Reason</th>}
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginatedParticipants.length === 0 ? (
                <tr>
                  <td colSpan={9} className="text-center py-8 text-slate-400">
                    {showRemoved 
                      ? 'No removed participants' 
                      : (searchTerm || typeFilter !== 'all' || paidFilter !== 'all' 
                        ? 'No matching participants found' 
                        : 'No participants yet. Import a CAP Event Admin Report to get started.')}
                  </td>
                </tr>
              ) : (
                paginatedParticipants.map((p) => (
                  <tr 
                    key={p.id} 
                    className={`hover:bg-slate-50 cursor-pointer transition-colors ${p.is_removed ? 'bg-red-50/50' : ''}`}
                    onClick={() => handleViewParticipant(p)}
                    data-testid={`roster-row-${p.capid}`}
                  >
                    <td className="font-mono text-[#00205B] font-medium">{p.capid}</td>
                    <td>{p.rank}</td>
                    <td className="font-medium">
                      {p.last_name}, {p.first_name}
                      {p.is_removed && <span className="ml-2 text-xs text-red-500">(Removed)</span>}
                    </td>
                    <td className="font-mono text-sm">{p.unit}</td>
                    <td className="text-sm text-slate-500">{p.wing || '-'}</td>
                    <td>
                      <span className={`inline-block px-2 py-0.5 text-[10px] uppercase tracking-wider font-bold rounded-sm border ${getTypeBadgeColor(p.participant_type)}`}>
                        {p.participant_type?.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="text-center">
                      {p.paid || p.paid_in_full ? (
                        <span className="inline-flex items-center gap-1 text-emerald-600 text-xs">
                          <CheckCircle className="w-3 h-3" />
                          {p.amount_paid > 0 && <span className="font-mono">${p.amount_paid}</span>}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-red-500 text-xs">
                          <AlertCircle className="w-3 h-3" />
                        </span>
                      )}
                    </td>
                    {!showRemoved && (
                      <td className="text-center">
                        <div className="flex items-center justify-center gap-1">
                          {p.unit_approved && <span className="text-[10px] px-1 bg-blue-100 text-blue-700 rounded">Unit</span>}
                          {p.wing_approved && <span className="text-[10px] px-1 bg-emerald-100 text-emerald-700 rounded">Wing</span>}
                          {!p.unit_approved && !p.wing_approved && <span className="text-slate-300">-</span>}
                        </div>
                      </td>
                    )}
                    {showRemoved && (
                      <td className="text-sm text-red-600 max-w-[200px] truncate">
                        {p.removal_reason || '-'}
                      </td>
                    )}
                    <td className="text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleViewParticipant(p);
                          }}
                          className="h-8 w-8 p-0 text-slate-500 hover:text-[#00205B]"
                          data-testid={`view-participant-${p.capid}`}
                        >
                          <Eye className="w-4 h-4" />
                        </Button>
                        {showRemoved ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleReinstateParticipant(p);
                            }}
                            className="h-8 w-8 p-0 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50"
                            data-testid={`reinstate-participant-${p.capid}`}
                          >
                            <RotateCcw className="w-4 h-4" />
                          </Button>
                        ) : canEdit() && (
                          <>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleEdit(p);
                              }}
                              className="h-8 w-8 p-0"
                              data-testid={`edit-participant-${p.capid}`}
                            >
                              <Edit2 className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDelete(p.id);
                              }}
                              className="h-8 w-8 p-0 text-[#BF0D3E] hover:text-[#BF0D3E] hover:bg-red-50"
                              data-testid={`delete-participant-${p.capid}`}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="border-t border-slate-200 px-4 py-3 flex items-center justify-between">
            <p className="text-sm text-slate-500">
              Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, filteredParticipants.length)} of {filteredParticipants.length}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="rounded-sm"
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <span className="text-sm text-slate-600">
                Page {currentPage} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="rounded-sm"
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Participant Detail Modal */}
      <Dialog open={isDetailOpen} onOpenChange={(open) => {
        setIsDetailOpen(open);
        if (!open) setSelectedParticipant(null);
      }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          {selectedParticipant && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-[#00205B] text-white flex items-center justify-center text-lg font-bold">
                    {selectedParticipant.first_name?.charAt(0)}{selectedParticipant.last_name?.charAt(0)}
                  </div>
                  <div>
                    <p className="text-xl font-bold text-[#00205B]">
                      {selectedParticipant.rank} {selectedParticipant.first_name} {selectedParticipant.last_name}
                    </p>
                    <p className="text-sm text-slate-500 font-mono">CAPID: {selectedParticipant.capid}</p>
                  </div>
                </DialogTitle>
              </DialogHeader>

              {/* Removal Warning */}
              {selectedParticipant.is_removed && (
                <div className="bg-red-50 border border-red-200 rounded-sm p-3 mb-4 flex items-start gap-2">
                  <UserX className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-red-800">Removed from Encampment</p>
                    <p className="text-sm text-red-600">{selectedParticipant.removal_reason}</p>
                    <p className="text-xs text-red-500 mt-1">
                      Removed by {selectedParticipant.removed_by} on {new Date(selectedParticipant.removed_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-6">
                {/* Basic Info */}
                <div className="space-y-4">
                  <h4 className="font-bold text-[#00205B] uppercase text-xs tracking-wide border-b border-slate-200 pb-2">
                    Basic Information
                  </h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Type:</span>
                      <span className={`px-2 py-0.5 text-xs uppercase font-bold rounded-sm border ${getTypeBadgeColor(selectedParticipant.participant_type)}`}>
                        {selectedParticipant.participant_type?.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Member Type:</span>
                      <span className="font-medium">{selectedParticipant.member_type || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Age:</span>
                      <span className="font-medium">{selectedParticipant.age || selectedParticipant.age_at_event || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Gender:</span>
                      <span className="font-medium">{selectedParticipant.gender === 'M' ? 'Male' : selectedParticipant.gender === 'F' ? 'Female' : selectedParticipant.gender || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">First Encampment:</span>
                      <span className="font-medium">{selectedParticipant.first_encampment ? 'Yes' : 'No'}</span>
                    </div>
                  </div>
                </div>

                {/* Unit Info */}
                <div className="space-y-4">
                  <h4 className="font-bold text-[#00205B] uppercase text-xs tracking-wide border-b border-slate-200 pb-2 flex items-center gap-1">
                    <Shield className="w-3 h-3" /> CAP Unit
                  </h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Unit:</span>
                      <span className="font-mono font-medium">{selectedParticipant.unit || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Wing:</span>
                      <span className="font-medium">{selectedParticipant.wing || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Region:</span>
                      <span className="font-medium">{selectedParticipant.region || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Unit Approved:</span>
                      <span className={selectedParticipant.unit_approved ? 'text-emerald-600' : 'text-slate-400'}>{selectedParticipant.unit_approved ? 'Yes' : 'No'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Wing Approved:</span>
                      <span className={selectedParticipant.wing_approved ? 'text-emerald-600' : 'text-slate-400'}>{selectedParticipant.wing_approved ? 'Yes' : 'No'}</span>
                    </div>
                  </div>
                </div>

                {/* Contact Info */}
                <div className="space-y-4">
                  <h4 className="font-bold text-[#00205B] uppercase text-xs tracking-wide border-b border-slate-200 pb-2 flex items-center gap-1">
                    <Phone className="w-3 h-3" /> Contact Information
                  </h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2">
                      <Mail className="w-4 h-4 text-slate-400" />
                      <span>{selectedParticipant.email || '-'}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Phone className="w-4 h-4 text-slate-400" />
                      <span>{selectedParticipant.phone || selectedParticipant.cell_phone || '-'}</span>
                    </div>
                    {selectedParticipant.cadet_parent_email && (
                      <div className="pt-2 border-t border-slate-100">
                        <p className="text-xs text-slate-500 mb-1">Parent/Guardian:</p>
                        <div className="flex items-center gap-2">
                          <Mail className="w-4 h-4 text-slate-400" />
                          <span>{selectedParticipant.cadet_parent_email}</span>
                        </div>
                        {selectedParticipant.cadet_parent_phone && (
                          <div className="flex items-center gap-2 mt-1">
                            <Phone className="w-4 h-4 text-slate-400" />
                            <span>{selectedParticipant.cadet_parent_phone}</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Payment Info */}
                <div className="space-y-4">
                  <h4 className="font-bold text-[#00205B] uppercase text-xs tracking-wide border-b border-slate-200 pb-2 flex items-center gap-1">
                    <DollarSign className="w-3 h-3" /> Payment Status
                  </h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Paid:</span>
                      <span className={selectedParticipant.paid || selectedParticipant.paid_in_full ? 'text-emerald-600 font-medium' : 'text-red-500'}>
                        {selectedParticipant.paid || selectedParticipant.paid_in_full ? 'Yes' : 'No'}
                      </span>
                    </div>
                    {selectedParticipant.amount_paid > 0 && (
                      <div className="flex justify-between">
                        <span className="text-slate-500">Amount Paid:</span>
                        <span className="font-mono font-medium text-emerald-600">${selectedParticipant.amount_paid}</span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span className="text-slate-500">Registration Status:</span>
                      <span className="font-medium">{selectedParticipant.registration_status || '-'}</span>
                    </div>
                  </div>
                </div>

                {/* Address */}
                {(selectedParticipant.address || selectedParticipant.city) && (
                  <div className="col-span-2 space-y-4">
                    <h4 className="font-bold text-[#00205B] uppercase text-xs tracking-wide border-b border-slate-200 pb-2 flex items-center gap-1">
                      <MapPin className="w-3 h-3" /> Address
                    </h4>
                    <p className="text-sm">
                      {selectedParticipant.address && <span>{selectedParticipant.address}<br/></span>}
                      {selectedParticipant.city && <span>{selectedParticipant.city}, </span>}
                      {selectedParticipant.state && <span>{selectedParticipant.state} </span>}
                      {selectedParticipant.zip_code && <span>{selectedParticipant.zip_code}</span>}
                    </p>
                  </div>
                )}

                {/* Notes */}
                {(selectedParticipant.notes || selectedParticipant.comments) && (
                  <div className="col-span-2 space-y-4">
                    <h4 className="font-bold text-[#00205B] uppercase text-xs tracking-wide border-b border-slate-200 pb-2">
                      Notes
                    </h4>
                    <p className="text-sm text-slate-600">{selectedParticipant.notes || selectedParticipant.comments}</p>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="flex justify-between items-center pt-4 mt-4 border-t border-slate-200">
                <div>
                  {selectedParticipant.is_removed ? (
                    <Button
                      onClick={() => handleReinstateParticipant(selectedParticipant)}
                      className="bg-emerald-600 hover:bg-emerald-700 rounded-sm"
                      data-testid="reinstate-btn"
                    >
                      <RotateCcw className="w-4 h-4 mr-2" />
                      Reinstate Participant
                    </Button>
                  ) : canEdit() && (
                    <Button
                      variant="outline"
                      onClick={() => setIsRemovalModalOpen(true)}
                      className="border-red-300 text-red-600 hover:bg-red-50 rounded-sm"
                      data-testid="remove-from-encampment-btn"
                    >
                      <UserX className="w-4 h-4 mr-2" />
                      Remove from Encampment
                    </Button>
                  )}
                </div>
                <div className="flex gap-2">
                  {canEdit() && !selectedParticipant.is_removed && (
                    <Button
                      variant="outline"
                      onClick={() => {
                        handleEdit(selectedParticipant);
                        setIsDetailOpen(false);
                      }}
                      className="rounded-sm"
                    >
                      <Edit2 className="w-4 h-4 mr-2" />
                      Edit
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    onClick={() => setIsDetailOpen(false)}
                    className="rounded-sm"
                  >
                    Close
                  </Button>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Removal Reason Modal */}
      <Dialog open={isRemovalModalOpen} onOpenChange={setIsRemovalModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-[#BF0D3E]">Remove from Encampment</DialogTitle>
          </DialogHeader>
          {selectedParticipant && (
            <div className="space-y-4">
              <p className="text-sm text-slate-600">
                You are about to remove <strong>{selectedParticipant.rank} {selectedParticipant.first_name} {selectedParticipant.last_name}</strong> from the encampment roster.
              </p>
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-600">Reason for Removal *</Label>
                <Textarea
                  value={removalReason}
                  onChange={(e) => setRemovalReason(e.target.value)}
                  placeholder="e.g., Left early due to family emergency, Medical issue, etc."
                  className="mt-1 rounded-sm"
                  rows={3}
                  data-testid="removal-reason-input"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button 
                  variant="outline" 
                  onClick={() => {
                    setIsRemovalModalOpen(false);
                    setRemovalReason('');
                  }}
                  className="rounded-sm"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleRemoveParticipant}
                  disabled={!removalReason.trim()}
                  className="bg-[#BF0D3E] hover:bg-[#9a0a32] rounded-sm"
                  data-testid="confirm-removal-btn"
                >
                  <UserX className="w-4 h-4 mr-2" />
                  Remove Participant
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default RosterPage;
