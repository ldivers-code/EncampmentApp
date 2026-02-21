import React, { useState, useEffect, useMemo } from 'react';
import { getParticipants, createParticipant, updateParticipant, deleteParticipant, importParticipants, getParticipantStats } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
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
  RefreshCw
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
  const [editingParticipant, setEditingParticipant] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
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
      const matchesSearch = 
        `${p.first_name} ${p.last_name} ${p.capid} ${p.unit}`.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = typeFilter === 'all' || p.participant_type === typeFilter;
      const matchesPaid = paidFilter === 'all' || 
        (paidFilter === 'paid' && (p.paid || p.paid_in_full)) ||
        (paidFilter === 'unpaid' && !p.paid && !p.paid_in_full);
      return matchesSearch && matchesType && matchesPaid;
    });
  }, [participants, searchTerm, typeFilter, paidFilter]);

  const paginatedParticipants = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredParticipants.slice(start, start + itemsPerPage);
  }, [filteredParticipants, currentPage]);

  const totalPages = Math.ceil(filteredParticipants.length / itemsPerPage);

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
                className="hidden"
                data-testid="import-file-input"
              />
              <Button variant="outline" className="rounded-sm border-[#00205B] text-[#00205B] hover:bg-[#00205B]/10" asChild>
                <span>
                  <Upload className="w-4 h-4 mr-2" />
                  Import Excel
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
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-5 h-5 text-emerald-600" />
              <div>
                <p className="font-medium text-emerald-800">Import Complete</p>
                <p className="text-sm text-emerald-600">
                  {importResult.imported} new participants, {importResult.updated} updated
                </p>
              </div>
            </div>
            <div className="text-right text-sm">
              <div className="space-x-4">
                <span className="text-emerald-700">Seniors: {importResult.stats?.seniors || 0}</span>
                <span className="text-emerald-700">Cadets: {importResult.stats?.cadets || 0}</span>
                <span className="text-emerald-700">Staff: {importResult.stats?.staff || 0}</span>
                <span className="text-emerald-700">Cadre: {importResult.stats?.cadre || 0}</span>
              </div>
              <div className="mt-1">
                <span className="text-emerald-600">Total Collected: {formatCurrency(importResult.stats?.total_collected || 0)}</span>
              </div>
            </div>
            <button onClick={() => setImportResult(null)} className="text-emerald-400 hover:text-emerald-600">
              ×
            </button>
          </div>
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
                <th className="text-left">Type</th>
                <th className="text-left">Squadron</th>
                <th className="text-left">Paid</th>
                {canEdit() && <th className="text-right">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {paginatedParticipants.length === 0 ? (
                <tr>
                  <td colSpan={canEdit() ? 8 : 7} className="text-center py-8 text-slate-400">
                    {searchTerm || typeFilter !== 'all' ? 'No matching participants found' : 'No participants yet. Add your first participant or import from Excel.'}
                  </td>
                </tr>
              ) : (
                paginatedParticipants.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50" data-testid={`roster-row-${p.capid}`}>
                    <td className="font-mono text-[#00205B] font-medium">{p.capid}</td>
                    <td>{p.rank}</td>
                    <td className="font-medium">{p.last_name}, {p.first_name}</td>
                    <td className="font-mono">{p.unit}</td>
                    <td>
                      <span className={`inline-block px-2 py-0.5 text-[10px] uppercase tracking-wider font-bold rounded-sm border ${getTypeBadgeColor(p.participant_type)}`}>
                        {p.participant_type?.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td>{p.squadron || '-'}</td>
                    <td>
                      <span className={`inline-block w-2 h-2 rounded-full ${p.paid ? 'bg-emerald-500' : 'bg-red-500'}`}></span>
                    </td>
                    {canEdit() && (
                      <td className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEdit(p)}
                            className="h-8 w-8 p-0"
                            data-testid={`edit-participant-${p.capid}`}
                          >
                            <Edit2 className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(p.id)}
                            className="h-8 w-8 p-0 text-[#BF0D3E] hover:text-[#BF0D3E] hover:bg-red-50"
                            data-testid={`delete-participant-${p.capid}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </td>
                    )}
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
    </div>
  );
};

export default RosterPage;
