import React, { useState, useEffect, useMemo } from 'react';
import { getParticipants, createParticipant, updateParticipant, deleteParticipant, importParticipants, getParticipantStats, removeParticipantFromEncampment, reinstateParticipant, uploadStudents, getFlightDistribution, updateParticipantAssignment, uploadCadetPhoto, getCadetPhotoUrl, deleteCadetPhoto, autoAssignUnassignedStudents, bulkChangeParticipantType, bulkDeleteParticipants, bulkChangeParticipantAssignment } from '../services/api';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import CadetHealthSection from '../components/CadetHealthSection';
import FlightManager from '../components/FlightManager';
import ImportPreviewModal from '../components/ImportPreviewModal';
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
  Eye,
  Edit3,
  Check,
  GraduationCap,
  Briefcase,
  Star,
  FileText,
  Camera,
  Shuffle,
  Printer
} from 'lucide-react';

// ── Canonical Participant Type taxonomy (Phase 2 backend migration) ─────────
// The backend now uses `student`, `cadre`, `senior_staff` (with `is_exec_cadre`
// flag) and `needs_review`. Legacy literals (`basic_student`, `advanced_student`,
// `staff`, `senior_member`) may still exist on unmigrated rows, so the
// recognized sets below include both new and legacy values. The
// canonical_value() helper returns the value we want to STORE on writes.
const STUDENT_TYPES = ['student', 'basic_student', 'advanced_student'];
const CADRE_TYPES = ['cadre', 'exec_cadre'];
const STAFF_TYPES = ['senior_staff', 'staff', 'senior_member'];
const NEEDS_REVIEW_TYPES = ['needs_review'];

const isStudentType = (t) => STUDENT_TYPES.includes(t);
const isCadreType = (t) => CADRE_TYPES.includes(t);
const isStaffType = (t) => STAFF_TYPES.includes(t);
const isNeedsReviewType = (t) => NEEDS_REVIEW_TYPES.includes(t);

// Human-readable labels — match the backend's canonical vocabulary.
// "Senior Staff" — never "Cadet Staff" or just "Staff" for cadets.
// "Executive Cadre" — never "Exec Cadre" in user-facing copy.
const TYPE_LABELS = {
  student: 'Student',
  basic_student: 'Student',
  advanced_student: 'Student',
  cadre: 'Cadre',
  exec_cadre: 'Executive Cadre',
  senior_staff: 'Senior Staff',
  staff: 'Senior Staff',
  senior_member: 'Senior Staff',
  needs_review: 'Needs Review',
};
const labelForType = (t) => TYPE_LABELS[t] || t;

// Simple avatar component that shows photo or initials
const CadetAvatar = ({ participant, size = 'sm' }) => {
  const [hasPhoto, setHasPhoto] = React.useState(!!participant?.photo_path);
  const [imgError, setImgError] = React.useState(false);
  const sizeClasses = size === 'lg' ? 'w-20 h-20 text-2xl' : size === 'md' ? 'w-10 h-10 text-sm' : 'w-7 h-7 text-[10px]';
  const initials = `${participant?.first_name?.charAt(0) || ''}${participant?.last_name?.charAt(0) || ''}`;
  
  if (hasPhoto && !imgError) {
    return (
      <img
        src={getCadetPhotoUrl(participant.id)}
        alt={`${participant.first_name} ${participant.last_name}`}
        className={`${sizeClasses} rounded-full object-cover flex-shrink-0 border border-slate-200`}
        onError={() => { setImgError(true); setHasPhoto(false); }}
        data-testid={`cadet-photo-${participant.capid}`}
      />
    );
  }
  return (
    <div className={`${sizeClasses} rounded-full bg-[#00205B] text-white flex items-center justify-center font-bold flex-shrink-0`} data-testid={`cadet-initials-${participant?.capid}`}>
      {initials}
    </div>
  );
};

const RosterPage = () => {
  const { canEdit, user } = useAuth();
  const [participants, setParticipants] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  // Import preview modal
  const [importPreviewOpen, setImportPreviewOpen] = useState(false);
  const [importPreviewFile, setImportPreviewFile] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [paidFilter, setPaidFilter] = useState('all');
  const [flightFilter, setFlightFilter] = useState('all');
  const [squadronFilter, setSquadronFilter] = useState('all');
  const [genderFilter, setGenderFilter] = useState('all');
  const [wingFilter, setWingFilter] = useState('all');
  const [rankFilter, setRankFilter] = useState('all');
  const [showRemoved, setShowRemoved] = useState(false);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [rosterView, setRosterView] = useState('master'); // 'master' or 'full'
  const [categoryTab, setCategoryTab] = useState('students'); // 'staff', 'cadre', 'students'
  const [editingParticipant, setEditingParticipant] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  // Student upload state
  const [uploadingStudents, setUploadingStudents] = useState(false);
  const [flightDistribution, setFlightDistribution] = useState(null);
  // Inline editing state
  const [inlineEditId, setInlineEditId] = useState(null);
  const [inlineEditFlight, setInlineEditFlight] = useState('');
  const [inlineEditSquadron, setInlineEditSquadron] = useState('');
  // Participant detail view
  const [selectedParticipant, setSelectedParticipant] = useState(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  // PDF Export
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  // Flight Manager view
  const [showFlightManager, setShowFlightManager] = useState(false);
  // Removal modal
  const [isRemovalModalOpen, setIsRemovalModalOpen] = useState(false);
  const [removalReason, setRemovalReason] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;
  // Flight-grouped view
  const [viewMode, setViewMode] = useState('table'); // 'table' or 'flight'
  const [flightGroupedData, setFlightGroupedData] = useState([]);
  const [autoBalancing, setAutoBalancing] = useState(false);
  // Bulk selection / actions
  const [selectedParticipantIds, setSelectedParticipantIds] = useState(new Set());
  const [bulkActionLoading, setBulkActionLoading] = useState(false);
  const [bulkTypeMenuOpen, setBulkTypeMenuOpen] = useState(false);
  const [bulkAssignOpen, setBulkAssignOpen] = useState(false);
  const [bulkAssignFlight, setBulkAssignFlight] = useState('__nochange__');
  const [bulkAssignSquadron, setBulkAssignSquadron] = useState('__nochange__');

  // Check if user can see full roster details (sensitive info)
  const canViewSensitiveData = () => {
    const privilegedRoles = ['dcp', 'commander', 'executive_staff', 'exec_cadre', 'plans_programs', 'finance', 'staff'];
    return privilegedRoles.includes(user?.role);
  };

  // Check if participant is "accepted" (on org chart or has flight/squadron assignment)
  const isAccepted = (participant) => {
    const hasFlight = participant.flight && participant.flight !== 'None' && participant.flight !== '';
    const hasSquadron = participant.squadron && participant.squadron !== 'None' && participant.squadron !== '';
    const isOnOrgChart = participant.is_on_org_chart === true;
    return hasFlight || hasSquadron || isOnOrgChart;
  };

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
    participant_type: 'student',
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
    loadFlightDistribution();
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

  const loadFlightDistribution = async () => {
    try {
      const data = await getFlightDistribution();
      setFlightDistribution(data);
    } catch (error) {
      console.error('Failed to load flight distribution');
    }
  };

  const loadFlightGrouped = async () => {
    try {
      const res = await axios.get(`${API}/api/participants/by-flight`);
      setFlightGroupedData(res.data);
    } catch (error) {
      console.error('Failed to load flight-grouped data');
    }
  };

  useEffect(() => {
    if (viewMode === 'flight') loadFlightGrouped();
  }, [viewMode]);

  // Handle student roster upload
  const handleStudentUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploadingStudents(true);
    try {
      const result = await uploadStudents(file, true);
      toast.success(`${result.message}`);
      if (result.flight_distribution) {
        const flightCounts = Object.entries(result.flight_distribution)
          .map(([f, c]) => `${f.charAt(0).toUpperCase() + f.slice(1)}: ${c}`)
          .join(', ');
        toast.info(`Flight distribution: ${flightCounts}`);
      }
      loadParticipants();
      loadStats();
      loadFlightDistribution();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload student roster');
    } finally {
      setUploadingStudents(false);
      e.target.value = '';
    }
  };

  const filteredParticipants = useMemo(() => {
    return participants.filter(p => {
      // Filter out removed participants unless showRemoved is true
      if (!showRemoved && p.is_removed) return false;
      if (showRemoved && !p.is_removed) return false;
      
      // Category tab filter (Senior Staff | Cadre | Students)
      if (categoryTab === 'students') {
        if (!isStudentType(p.participant_type)) return false;
      } else if (categoryTab === 'cadre') {
        if (!isCadreType(p.participant_type)) return false;
      } else if (categoryTab === 'staff') {
        if (!isStaffType(p.participant_type)) return false;
      } else if (categoryTab === 'needs_review') {
        if (!isNeedsReviewType(p.participant_type)) return false;
      }
      
      // Master vs Full roster view
      if (rosterView === 'master' && !isAccepted(p)) return false;
      
      // Search across multiple fields
      const searchLower = searchTerm.toLowerCase();
      const matchesSearch = searchTerm === '' || 
        `${p.first_name} ${p.last_name} ${p.capid} ${p.unit} ${p.wing} ${p.rank} ${p.email || ''}`.toLowerCase().includes(searchLower);
      
      // Type filter
      const matchesType = typeFilter === 'all' || p.participant_type === typeFilter;
      
      // Paid filter
      const matchesPaid = paidFilter === 'all' || 
        (paidFilter === 'paid' && (p.paid || p.paid_in_full)) ||
        (paidFilter === 'unpaid' && !p.paid && !p.paid_in_full);
      
      // Flight filter
      const matchesFlight = flightFilter === 'all' || 
        (flightFilter === 'unassigned' && (!p.flight || p.flight === 'None')) ||
        (p.flight?.toLowerCase() === flightFilter.toLowerCase());
      
      // Squadron filter
      const matchesSquadron = squadronFilter === 'all' || 
        (squadronFilter === 'unassigned' && (!p.squadron || p.squadron === 'None')) ||
        (p.squadron?.toLowerCase().replace(/\s+/g, '_') === squadronFilter.toLowerCase());
      
      // Gender filter
      const matchesGender = genderFilter === 'all' || 
        (p.gender?.toLowerCase() === genderFilter.toLowerCase()) ||
        (genderFilter === 'male' && p.gender?.toUpperCase() === 'MALE') ||
        (genderFilter === 'female' && p.gender?.toUpperCase() === 'FEMALE');
      
      // Wing filter
      const matchesWing = wingFilter === 'all' || 
        (p.wing?.toUpperCase() === wingFilter.toUpperCase());
      
      // Rank filter (category-based)
      const matchesRank = rankFilter === 'all' || 
        (rankFilter === 'officer' && (p.rank?.includes('Lt') || p.rank?.includes('Capt') || p.rank?.includes('Maj') || p.rank?.includes('Col'))) ||
        (rankFilter === 'nco' && (p.rank?.includes('Sgt') || p.rank?.includes('MSgt') || p.rank?.includes('SMSgt') || p.rank?.includes('CMSgt'))) ||
        (rankFilter === 'airman' && (p.rank?.includes('Amn') || p.rank?.includes('A1C') || p.rank?.includes('SrA'))) ||
        (rankFilter === 'senior' && !p.rank?.startsWith('C/'));
      
      return matchesSearch && matchesType && matchesPaid && matchesFlight && matchesSquadron && matchesGender && matchesWing && matchesRank;
    });
  }, [participants, searchTerm, typeFilter, paidFilter, flightFilter, squadronFilter, genderFilter, wingFilter, rankFilter, showRemoved, rosterView, categoryTab]);

  // Category counts
  const categoryCounts = useMemo(() => {
    const active = participants.filter(p => !p.is_removed);
    return {
      students: active.filter(p => isStudentType(p.participant_type)).length,
      cadre: active.filter(p => isCadreType(p.participant_type)).length,
      staff: active.filter(p => isStaffType(p.participant_type)).length,
      needs_review: active.filter(p => isNeedsReviewType(p.participant_type)).length,
    };
  }, [participants]);

  // Count accepted participants
  const acceptedCount = useMemo(() => {
    return participants.filter(p => !p.is_removed && isAccepted(p)).length;
  }, [participants]);

  // Get unique values for filter dropdowns
  const uniqueWings = useMemo(() => {
    const wings = [...new Set(participants.map(p => p.wing).filter(Boolean))];
    return wings.sort();
  }, [participants]);

  // Count active filters
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (typeFilter !== 'all') count++;
    if (paidFilter !== 'all') count++;
    if (flightFilter !== 'all') count++;
    if (squadronFilter !== 'all') count++;
    if (genderFilter !== 'all') count++;
    if (wingFilter !== 'all') count++;
    if (rankFilter !== 'all') count++;
    return count;
  }, [typeFilter, paidFilter, flightFilter, squadronFilter, genderFilter, wingFilter, rankFilter]);

  // Reset all filters
  const resetFilters = () => {
    setSearchTerm('');
    setTypeFilter('all');
    setPaidFilter('all');
    setFlightFilter('all');
    setSquadronFilter('all');
    setGenderFilter('all');
    setWingFilter('all');
    setRankFilter('all');
    setCurrentPage(1);
  };

  const paginatedParticipants = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredParticipants.slice(start, start + itemsPerPage);
  }, [filteredParticipants, currentPage]);

  const totalPages = Math.ceil(filteredParticipants.length / itemsPerPage);

  // Count removed participants
  const removedCount = useMemo(() => {
    return participants.filter(p => p.is_removed).length;
  }, [participants]);

  // Start inline editing
  const startInlineEdit = (participant) => {
    setInlineEditId(participant.id);
    setInlineEditFlight(participant.flight || '');
    setInlineEditSquadron(participant.squadron || '');
  };

  // Cancel inline editing
  const cancelInlineEdit = () => {
    setInlineEditId(null);
    setInlineEditFlight('');
    setInlineEditSquadron('');
  };

  // Save inline edit
  const saveInlineEdit = async (participantId) => {
    try {
      // Use the new assignment endpoint with role-based permissions
      await updateParticipantAssignment(participantId, {
        flight: inlineEditFlight || null,
        squadron: inlineEditSquadron || null
      });
      toast.success('Assignment updated');
      cancelInlineEdit();
      loadParticipants();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update assignment');
    }
  };

  // Check if user can edit assignments for a specific participant type
  const canEditAssignment = (participant) => {
    if (!user) return false;
    
    const participantType = participant?.participant_type || '';
    const isStudent = isStudentType(participantType);
    const isCadre = isCadreType(participantType);
    
    // Full access roles - can edit both students and cadre
    const fullAccessRoles = ['dcp', 'commander', 'executive_staff', 'plans_programs', 'staff'];
    
    // Cadre-only edit roles
    const cadreOnlyRoles = ['exec_cadre'];
    
    if (fullAccessRoles.includes(user.role)) {
      return true; // Can edit all
    }
    
    if (cadreOnlyRoles.includes(user.role)) {
      return isCadre; // Can only edit cadre, not students
    }
    
    return false;
  };

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
    // Open the preview modal instead of auto-applying.
    // The modal handles preview + conflict resolution + apply.
    setImportPreviewFile(file);
    setImportPreviewOpen(true);
    e.target.value = '';
  };

  const handleImportApplied = (result) => {
    setImportResult(result);
    toast.success(result.message || `Imported ${result.imported} new, ${result.updated} updated`);
    loadParticipants();
    loadStats();
    loadFlightDistribution();
  };

  const handleAutoBalance = async () => {
    setAutoBalancing(true);
    try {
      const result = await autoAssignUnassignedStudents();
      if (result.assigned === 0) {
        toast.info('All students already have flight assignments');
      } else {
        toast.success(`Auto-assigned ${result.assigned} student${result.assigned > 1 ? 's' : ''} to flights`);
        loadParticipants();
        loadStats();
        loadFlightDistribution();
        if (viewMode === 'flight') loadFlightGrouped();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Auto-balance failed');
    } finally {
      setAutoBalancing(false);
    }
  };

  const handleExportPdf = async (format) => {
    setExporting(true);
    setExportMenuOpen(false);
    try {
      const API = process.env.REACT_APP_BACKEND_URL;
      const response = await fetch(`${API}/api/participants/export-pdf?format=${format}`, {
        credentials: 'include'
      });
      if (!response.ok) throw new Error('Export failed');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cap_roster_${format}_${new Date().toISOString().slice(0,10)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success('PDF exported successfully');
    } catch (error) {
      toast.error('Failed to export PDF');
    } finally {
      setExporting(false);
    }
  };

  const handleExportExcel = async () => {
    setExporting(true);
    setExportMenuOpen(false);
    try {
      const API = process.env.REACT_APP_BACKEND_URL;
      const response = await fetch(`${API}/api/participants/analytics/export?format=excel`, {
        credentials: 'include'
      });
      if (!response.ok) throw new Error('Export failed');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cap_roster_${new Date().toISOString().slice(0,10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Excel exported successfully (includes shirt sizes)');
    } catch (error) {
      toast.error('Failed to export Excel');
    } finally {
      setExporting(false);
    }
  };

  // ─── Bulk actions ────────────────────────────────────────────
  const toggleSelectAll = (visibleIds) => {
    setSelectedParticipantIds((prev) => {
      const next = new Set(prev);
      const allSelected = visibleIds.every((id) => next.has(id));
      if (allSelected) {
        visibleIds.forEach((id) => next.delete(id));
      } else {
        visibleIds.forEach((id) => next.add(id));
      }
      return next;
    });
  };

  const toggleSelectOne = (id) => {
    setSelectedParticipantIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const clearBulkSelection = () => setSelectedParticipantIds(new Set());

  const handleBulkChangeType = async (newType) => {
    const ids = Array.from(selectedParticipantIds);
    if (ids.length === 0) {
      toast.warning('No participants selected');
      return;
    }
    const typeLabel = labelForType(newType);
    if (!window.confirm(`Change ${ids.length} participant(s) to ${typeLabel}?`)) return;
    setBulkActionLoading(true);
    setBulkTypeMenuOpen(false);
    try {
      const result = await bulkChangeParticipantType(ids, newType);
      toast.success(result.message || `Updated ${ids.length} participants`);
      clearBulkSelection();
      await loadParticipants();
      await loadStats();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to change participant types');
    } finally {
      setBulkActionLoading(false);
    }
  };

  const handleBulkDelete = async () => {
    const ids = Array.from(selectedParticipantIds);
    if (ids.length === 0) {
      toast.warning('No participants selected');
      return;
    }
    if (!window.confirm(`Permanently DELETE ${ids.length} participant(s)? This will also remove their health diary, supplements, and contraband records and unlink any user accounts. This cannot be undone.`)) return;
    setBulkActionLoading(true);
    try {
      const result = await bulkDeleteParticipants(ids);
      toast.success(result.message || `Deleted ${ids.length} participants`);
      clearBulkSelection();
      await loadParticipants();
      await loadStats();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete participants');
    } finally {
      setBulkActionLoading(false);
    }
  };

  const handleBulkAssign = async () => {
    const ids = Array.from(selectedParticipantIds);
    if (ids.length === 0) {
      toast.warning('No participants selected');
      return;
    }
    const payload = {};
    if (bulkAssignFlight !== '__nochange__') payload.flight = bulkAssignFlight;
    if (bulkAssignSquadron !== '__nochange__') payload.squadron = bulkAssignSquadron;
    if (Object.keys(payload).length === 0) {
      toast.warning('Choose a Flight and/or Squadron value to apply');
      return;
    }
    setBulkActionLoading(true);
    try {
      const result = await bulkChangeParticipantAssignment(ids, payload);
      toast.success(result.message || `Updated ${ids.length} participants`);
      setBulkAssignOpen(false);
      setBulkAssignFlight('__nochange__');
      setBulkAssignSquadron('__nochange__');
      clearBulkSelection();
      await loadParticipants();
      await loadStats();
      await loadFlightDistribution();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update assignments');
    } finally {
      setBulkActionLoading(false);
    }
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
      participant_type: 'student',
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
    { value: 'student', label: 'Student' },
    { value: 'cadre', label: 'Cadre' },
    { value: 'senior_staff', label: 'Senior Staff' },
    { value: 'needs_review', label: 'Needs Review' },
  ];

  const getTypeBadgeColor = (type) => {
    const colors = {
      student: 'bg-blue-100 text-blue-800 border-blue-200',
      basic_student: 'bg-blue-100 text-blue-800 border-blue-200',
      advanced_student: 'bg-blue-100 text-blue-800 border-blue-200',
      cadre: 'bg-amber-100 text-amber-800 border-amber-200',
      exec_cadre: 'bg-amber-200 text-amber-900 border-amber-300',
      senior_staff: 'bg-emerald-100 text-emerald-800 border-emerald-200',
      staff: 'bg-emerald-100 text-emerald-800 border-emerald-200',
      senior_member: 'bg-emerald-100 text-emerald-800 border-emerald-200',
      needs_review: 'bg-orange-100 text-orange-800 border-orange-200',
    };
    return colors[type] || colors.student;
  };

  // Flight/Squadron colors matching the master roster spreadsheet
  const getFlightColors = (flight) => {
    const flightLower = (flight || '').toLowerCase();
    const flightColors = {
      // 6th CTS - Light Blue
      'alpha': { bg: 'bg-sky-50', border: 'border-l-4 border-l-sky-500', text: 'text-sky-700', badge: 'bg-sky-500 text-white' },
      'bravo': { bg: 'bg-sky-50', border: 'border-l-4 border-l-sky-500', text: 'text-sky-700', badge: 'bg-sky-500 text-white' },
      // 21st CTS - Dark Red
      'charlie': { bg: 'bg-red-50', border: 'border-l-4 border-l-red-700', text: 'text-red-700', badge: 'bg-red-700 text-white' },
      'delta': { bg: 'bg-red-50', border: 'border-l-4 border-l-red-700', text: 'text-red-700', badge: 'bg-red-700 text-white' },
      // 22nd CTS - Dark Blue
      'echo': { bg: 'bg-indigo-50', border: 'border-l-4 border-l-indigo-800', text: 'text-indigo-800', badge: 'bg-indigo-800 text-white' },
      'foxtrot': { bg: 'bg-indigo-50', border: 'border-l-4 border-l-indigo-800', text: 'text-indigo-800', badge: 'bg-indigo-800 text-white' },
    };
    return flightColors[flightLower] || { bg: '', border: '', text: 'text-slate-500', badge: 'bg-slate-200 text-slate-700' };
  };

  const getSquadronDisplay = (squadron) => {
    // Convert squadron code to display name with color
    const squadronLower = (squadron || '').toLowerCase().replace(/\s+/g, '_');
    const squadronMap = {
      '6th_cts': { name: '6th CTS', color: 'text-sky-600', badge: 'bg-sky-100 text-sky-700 border-sky-300' },
      '21st_cts': { name: '21st CTS', color: 'text-red-700', badge: 'bg-red-100 text-red-700 border-red-300' },
      '22nd_cts': { name: '22nd CTS', color: 'text-indigo-800', badge: 'bg-indigo-100 text-indigo-800 border-indigo-300' },
      // Handle space-separated versions too
      '6th cts': { name: '6th CTS', color: 'text-sky-600', badge: 'bg-sky-100 text-sky-700 border-sky-300' },
      '21st cts': { name: '21st CTS', color: 'text-red-700', badge: 'bg-red-100 text-red-700 border-red-300' },
      '22nd cts': { name: '22nd CTS', color: 'text-indigo-800', badge: 'bg-indigo-100 text-indigo-800 border-indigo-300' },
    };
    return squadronMap[squadronLower] || { name: '-', color: 'text-slate-400', badge: 'bg-slate-100 text-slate-500 border-slate-200' };
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
    <div className="p-6 lg:p-8 animate-fade-in print-container">
      {/* Print-only header */}
      <div className="print-header">
        <h1>Tennessee Wing CAP Encampment — Roster</h1>
        <div className="print-meta">
          <div>Printed {new Date().toLocaleDateString()}</div>
          <div>{participants.length} participants</div>
        </div>
      </div>

      {/* Header */}
      <div className="flex flex-col 2xl:flex-row 2xl:items-center 2xl:justify-between gap-4 mb-4 no-print">
        <div className="min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl lg:text-3xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Encampment Roster
            </h1>
          </div>
          <p className="text-slate-500 text-sm mt-1">
            {filteredParticipants.length} {categoryTab} • {rosterView === 'master' ? 'with assignments' : 'total'}
          </p>
        </div>
        
        {canEdit() && (
          <div className="flex items-center gap-2 flex-wrap">
            {/* Student Upload Button */}
            {categoryTab === 'students' && (
              <label className="cursor-pointer">
                <input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleStudentUpload}
                  className="hidden"
                  data-testid="upload-students-input"
                />
                <Button 
                  variant="outline" 
                  className="rounded-sm border-emerald-600 text-emerald-600 hover:bg-emerald-50" 
                  asChild
                  disabled={uploadingStudents}
                >
                  <span>
                    {uploadingStudents ? (
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <GraduationCap className="w-4 h-4 mr-2" />
                    )}
                    {uploadingStudents ? 'Uploading...' : 'Upload Students'}
                  </span>
                </Button>
              </label>
            )}
            
            {/* Auto-Balance Flights button (students tab only) */}
            {categoryTab === 'students' && canEdit() && (
              <Button
                variant="outline"
                className="rounded-sm border-violet-600 text-violet-600 hover:bg-violet-50"
                disabled={autoBalancing}
                onClick={handleAutoBalance}
                data-testid="auto-balance-flights-btn"
              >
                {autoBalancing ? (
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Shuffle className="w-4 h-4 mr-2" />
                )}
                {autoBalancing ? 'Balancing...' : 'Auto-Balance Flights'}
              </Button>
            )}

            {/* General Import */}
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

            {/* PDF Export Dropdown */}
            <div className="relative">
              <Button
                variant="outline"
                className="rounded-sm border-slate-300 text-slate-700 hover:bg-slate-50"
                onClick={() => setExportMenuOpen(!exportMenuOpen)}
                disabled={exporting}
                data-testid="export-pdf-btn"
              >
                {exporting ? (
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <FileText className="w-4 h-4 mr-2" />
                )}
                {exporting ? 'Exporting...' : 'Export PDF'}
              </Button>
              {exportMenuOpen && (
                <div className="absolute right-0 top-full mt-1 z-50 bg-white border border-slate-200 rounded-sm shadow-lg w-56" data-testid="export-pdf-menu">
                  <button
                    onClick={() => handleExportPdf('simple')}
                    className="w-full text-left px-4 py-2.5 text-sm hover:bg-slate-50 transition-colors flex items-center gap-2"
                    data-testid="export-simple"
                  >
                    <FileText className="w-4 h-4 text-[#00205B]" />
                    <div>
                      <p className="font-medium text-slate-900">Complete Roster</p>
                      <p className="text-xs text-slate-500">All participants in one table</p>
                    </div>
                  </button>
                  <button
                    onClick={() => handleExportPdf('by_flight')}
                    className="w-full text-left px-4 py-2.5 text-sm hover:bg-slate-50 transition-colors flex items-center gap-2 border-t border-slate-100"
                    data-testid="export-by-flight"
                  >
                    <Users className="w-4 h-4 text-[#00205B]" />
                    <div>
                      <p className="font-medium text-slate-900">By Flight</p>
                      <p className="text-xs text-slate-500">Grouped by flight assignment</p>
                    </div>
                  </button>
                  <button
                    onClick={() => handleExportPdf('by_type')}
                    className="w-full text-left px-4 py-2.5 text-sm hover:bg-slate-50 transition-colors flex items-center gap-2 border-t border-slate-100"
                    data-testid="export-by-type"
                  >
                    <Shield className="w-4 h-4 text-[#00205B]" />
                    <div>
                      <p className="font-medium text-slate-900">By Type</p>
                      <p className="text-xs text-slate-500">Staff, Cadre, Students sections</p>
                    </div>
                  </button>
                  <button
                    onClick={handleExportExcel}
                    className="w-full text-left px-4 py-2.5 text-sm hover:bg-slate-50 transition-colors flex items-center gap-2 border-t border-slate-100"
                    data-testid="export-excel"
                  >
                    <FileSpreadsheet className="w-4 h-4 text-emerald-700" />
                    <div>
                      <p className="font-medium text-slate-900">Excel (with Shirt Sizes)</p>
                      <p className="text-xs text-slate-500">Full spreadsheet incl. shirt size, contact, payment</p>
                    </div>
                  </button>
                </div>
              )}
            </div>

            {/* Print Roster */}
            <Button
              variant="outline"
              className="rounded-sm border-slate-300 text-slate-700 hover:bg-slate-50 no-print"
              onClick={() => window.print()}
              data-testid="print-roster-btn"
            >
              <Printer className="w-4 h-4 mr-2" />
              Print
            </Button>
            
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
                  <span key={`budget-${u.item}`} className="text-emerald-600">
                    {u.item}: {formatCurrency(u.actual)} ({u.count} participants)
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Category Tabs: Staff | Cadre | Students */}
      <div className="flex items-center gap-1 mb-4 border-b border-slate-200 overflow-x-auto scrollbar-hide">
        <button
          onClick={() => { setCategoryTab('students'); setCurrentPage(1); }}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-2 ${
            categoryTab === 'students'
              ? 'border-[#00205B] text-[#00205B]'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
          data-testid="students-tab"
        >
          <GraduationCap className="w-4 h-4" />
          Students
          <span className={`text-xs px-1.5 py-0.5 rounded-full ${
            categoryTab === 'students' ? 'bg-[#00205B] text-white' : 'bg-slate-100 text-slate-600'
          }`}>{categoryCounts.students}</span>
        </button>
        <button
          onClick={() => { setCategoryTab('cadre'); setCurrentPage(1); }}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-2 ${
            categoryTab === 'cadre'
              ? 'border-amber-600 text-amber-700'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
          data-testid="cadre-tab"
        >
          <Star className="w-4 h-4" />
          Cadre
          <span className={`text-xs px-1.5 py-0.5 rounded-full ${
            categoryTab === 'cadre' ? 'bg-amber-600 text-white' : 'bg-slate-100 text-slate-600'
          }`}>{categoryCounts.cadre}</span>
        </button>
        <button
          onClick={() => { setCategoryTab('staff'); setCurrentPage(1); }}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-2 ${
            categoryTab === 'staff'
              ? 'border-emerald-600 text-emerald-700'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
          data-testid="staff-tab"
        >
          <Briefcase className="w-4 h-4" />
          Senior Staff
          <span className={`text-xs px-1.5 py-0.5 rounded-full ${
            categoryTab === 'staff' ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-600'
          }`}>{categoryCounts.staff}</span>
        </button>
        
        {/* Roster View Toggle - moved here */}
        <div className="ml-auto flex items-center gap-2">
          <div className="flex bg-slate-100 rounded-sm p-0.5">
            <button
              onClick={() => { setShowFlightManager(false); setRosterView('master'); setCurrentPage(1); }}
              className={`px-3 py-1 text-xs font-medium rounded-sm transition-colors ${
                !showFlightManager && rosterView === 'master' 
                  ? 'bg-[#00205B] text-white' 
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Assigned
            </button>
            <button
              onClick={() => { setShowFlightManager(false); setRosterView('full'); setCurrentPage(1); }}
              className={`px-3 py-1 text-xs font-medium rounded-sm transition-colors ${
                !showFlightManager && rosterView === 'full' 
                  ? 'bg-[#00205B] text-white' 
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              All
            </button>
            {canEdit() && (
              <button
                onClick={() => setShowFlightManager(!showFlightManager)}
                className={`px-3 py-1 text-xs font-medium rounded-sm transition-colors flex items-center gap-1 ${
                  showFlightManager 
                    ? 'bg-[#00205B] text-white' 
                    : 'text-slate-600 hover:text-slate-900'
                }`}
                data-testid="flight-manager-toggle"
              >
                <Users className="w-3 h-3" />
                Flights
              </button>
            )}
            <button
              onClick={() => { setShowFlightManager(false); setViewMode(viewMode === 'flight' ? 'table' : 'flight'); }}
              className={`px-3 py-1 text-xs font-medium rounded-sm transition-colors flex items-center gap-1 ${
                viewMode === 'flight' 
                  ? 'bg-[#00205B] text-white' 
                  : 'text-slate-600 hover:text-slate-900'
              }`}
              data-testid="by-flight-toggle"
            >
              By Flight
            </button>
          </div>
        </div>
      </div>

      {/* Flight Distribution (Students tab only) */}
      {!showFlightManager && categoryTab === 'students' && flightDistribution && (
        <div className="bg-white border border-slate-200 rounded-sm p-4 mb-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold uppercase tracking-tight text-[#00205B]">Flight Distribution</h3>
            <span className="text-xs text-slate-500">
              {flightDistribution.total_students} / {flightDistribution.total_capacity} ({flightDistribution.utilization}% capacity)
            </span>
          </div>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
            {Object.entries(flightDistribution.flights || {}).map(([flight, data]) => {
              const flightColors = getFlightColors(flight);
              return (
                <div key={flight} className={`p-2 rounded-sm border ${flightColors.badge} bg-opacity-20`}>
                  <div className="flex items-center justify-between">
                    <span className={`text-xs font-bold uppercase`}>
                      {flight.charAt(0).toUpperCase() + flight.slice(1)}
                    </span>
                    <span className={`text-xs font-medium`}>
                      {data.total}/{data.capacity}
                    </span>
                  </div>
                  <div className="flex gap-2 mt-1 text-xs opacity-80">
                    <span>M: {data.male}</span>
                    <span>F: {data.female}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Stats Dashboard */}
      {!showFlightManager && stats && (
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

      {/* Flight Manager View */}
      {showFlightManager ? (
        <FlightManager participants={participants} onUpdate={loadParticipants} />
      ) : viewMode === 'flight' ? (
        /* Flight-Grouped View */
        <div className="space-y-6" data-testid="flight-grouped-view">
          {flightGroupedData.length === 0 ? (
            <div className="text-center py-12 text-slate-500">Loading flight data...</div>
          ) : (
            flightGroupedData.map((group) => {
              const fColors = {
                alpha: 'border-l-red-500 bg-red-50/30', bravo: 'border-l-blue-500 bg-blue-50/30',
                charlie: 'border-l-green-500 bg-green-50/30', delta: 'border-l-yellow-500 bg-yellow-50/30',
                echo: 'border-l-purple-500 bg-purple-50/30', foxtrot: 'border-l-orange-500 bg-orange-50/30',
                unassigned: 'border-l-slate-400 bg-slate-50/30',
              };
              return (
                <div key={group.flight} className={`border border-slate-200 rounded-sm border-l-4 ${fColors[group.flight] || 'border-l-slate-400'}`}>
                  <div className="p-4 flex items-center justify-between bg-white/80">
                    <div className="flex items-center gap-3">
                      <h3 className="text-base font-bold text-[#00205B]">{group.flight_label} Flight</h3>
                      <span className="text-xs bg-slate-100 px-2 py-0.5 rounded-full font-medium">{group.count} members</span>
                    </div>
                    <button
                      onClick={() => {
                        const emails = group.members.filter(m => m.email).map(m => m.email).join(', ');
                        if (emails) { navigator.clipboard.writeText(emails); }
                      }}
                      className="text-xs px-3 py-1.5 bg-slate-100 hover:bg-slate-200 rounded-sm font-medium transition-colors"
                      data-testid={`copy-emails-${group.flight}`}
                    >
                      Copy Emails
                    </button>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                          <th className="px-4 py-2">Name</th>
                          <th className="px-4 py-2">CAPID</th>
                          <th className="px-4 py-2">Unit</th>
                          <th className="px-4 py-2">Gender</th>
                          <th className="px-4 py-2">Email</th>
                          <th className="px-4 py-2">Phone</th>
                          <th className="px-4 py-2">Parent Contact</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {group.members.map((m) => (
                          <tr key={m.id} className="hover:bg-white/60 transition-colors">
                            <td className="px-4 py-2.5 font-medium">
                              <div className="flex items-center gap-2">
                                <CadetAvatar participant={m} size="sm" />
                                <span>{m.rank} {m.last_name}, {m.first_name}</span>
                              </div>
                            </td>
                            <td className="px-4 py-2.5 font-mono text-xs">{m.capid}</td>
                            <td className="px-4 py-2.5 text-xs">{m.unit}</td>
                            <td className="px-4 py-2.5 text-xs">{m.gender}</td>
                            <td className="px-4 py-2.5">
                              {m.email && <a href={`mailto:${m.email}`} className="text-blue-600 hover:underline text-xs">{m.email}</a>}
                            </td>
                            <td className="px-4 py-2.5 text-xs">{m.phone}</td>
                            <td className="px-4 py-2.5 text-xs">
                              {m.parent_name && <div className="font-medium">{m.parent_name}</div>}
                              {m.parent_email && <a href={`mailto:${m.parent_email}`} className="text-blue-600 hover:underline">{m.parent_email}</a>}
                              {m.parent_phone && <div className="text-slate-500">{m.parent_phone}</div>}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              );
            })
          )}
        </div>
      ) : (
      <>
      {/* Filters */}
      <div className="bg-white border border-slate-200 rounded-sm p-4 mb-6 no-print">
        {/* Main filter row */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search by name, CAPID, unit, wing, rank, or email..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              className="pl-10 rounded-sm"
              data-testid="roster-search-input"
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {/* Type Filter */}
            <Select value={typeFilter} onValueChange={(value) => {
              setTypeFilter(value);
              setCurrentPage(1);
            }}>
              <SelectTrigger className="w-36 rounded-sm" data-testid="roster-type-filter">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                {participantTypes.map(type => (
                  <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Flight Filter */}
            <Select value={flightFilter} onValueChange={(value) => {
              setFlightFilter(value);
              setCurrentPage(1);
            }}>
              <SelectTrigger className="w-32 rounded-sm" data-testid="roster-flight-filter">
                <SelectValue placeholder="Flight" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Flights</SelectItem>
                <SelectItem value="unassigned">Unassigned</SelectItem>
                <SelectItem value="alpha">Alpha</SelectItem>
                <SelectItem value="bravo">Bravo</SelectItem>
                <SelectItem value="charlie">Charlie</SelectItem>
                <SelectItem value="delta">Delta</SelectItem>
                <SelectItem value="echo">Echo</SelectItem>
                <SelectItem value="foxtrot">Foxtrot</SelectItem>
              </SelectContent>
            </Select>

            {/* Squadron Filter */}
            <Select value={squadronFilter} onValueChange={(value) => {
              setSquadronFilter(value);
              setCurrentPage(1);
            }}>
              <SelectTrigger className="w-32 rounded-sm" data-testid="roster-squadron-filter">
                <SelectValue placeholder="Squadron" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Squadrons</SelectItem>
                <SelectItem value="unassigned">Unassigned</SelectItem>
                <SelectItem value="6th_cts">6th CTS</SelectItem>
                <SelectItem value="21st_cts">21st CTS</SelectItem>
                <SelectItem value="22nd_cts">22nd CTS</SelectItem>
              </SelectContent>
            </Select>

            {/* Advanced Filters Toggle */}
            <Button
              variant={showAdvancedFilters ? "default" : "outline"}
              size="sm"
              onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
              className={`rounded-sm text-xs ${showAdvancedFilters ? 'bg-[#00205B]' : ''}`}
            >
              <Filter className="w-3 h-3 mr-1" />
              More {activeFilterCount > 0 && `(${activeFilterCount})`}
            </Button>

            {/* Clear Filters */}
            {(activeFilterCount > 0 || searchTerm) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={resetFilters}
                className="rounded-sm text-xs text-red-600 hover:text-red-700 hover:bg-red-50"
              >
                <X className="w-3 h-3 mr-1" />
                Clear
              </Button>
            )}

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

        {/* Advanced Filters Row */}
        {showAdvancedFilters && (
          <div className="flex flex-wrap gap-3 mt-4 pt-4 border-t border-slate-200">
            {/* Gender Filter */}
            <Select value={genderFilter} onValueChange={(value) => {
              setGenderFilter(value);
              setCurrentPage(1);
            }}>
              <SelectTrigger className="w-28 rounded-sm" data-testid="roster-gender-filter">
                <SelectValue placeholder="Gender" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Genders</SelectItem>
                <SelectItem value="male">Male</SelectItem>
                <SelectItem value="female">Female</SelectItem>
              </SelectContent>
            </Select>

            {/* Wing Filter */}
            <Select value={wingFilter} onValueChange={(value) => {
              setWingFilter(value);
              setCurrentPage(1);
            }}>
              <SelectTrigger className="w-28 rounded-sm" data-testid="roster-wing-filter">
                <SelectValue placeholder="Wing" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Wings</SelectItem>
                {uniqueWings.map(wing => (
                  <SelectItem key={wing} value={wing}>{wing}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Rank Category Filter */}
            <Select value={rankFilter} onValueChange={(value) => {
              setRankFilter(value);
              setCurrentPage(1);
            }}>
              <SelectTrigger className="w-32 rounded-sm" data-testid="roster-rank-filter">
                <SelectValue placeholder="Rank" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Ranks</SelectItem>
                <SelectItem value="officer">Officers (Lt-Col)</SelectItem>
                <SelectItem value="nco">NCOs (Sgt+)</SelectItem>
                <SelectItem value="airman">Airmen (Amn-SrA)</SelectItem>
                <SelectItem value="senior">Senior Members</SelectItem>
              </SelectContent>
            </Select>

            {/* Paid Filter (if privileged) */}
            {canViewSensitiveData() && (
              <Select value={paidFilter} onValueChange={(value) => {
                setPaidFilter(value);
                setCurrentPage(1);
              }}>
                <SelectTrigger className="w-28 rounded-sm" data-testid="roster-paid-filter">
                  <SelectValue placeholder="Payment" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Payment</SelectItem>
                  <SelectItem value="paid">Paid</SelectItem>
                  <SelectItem value="unpaid">Unpaid</SelectItem>
                </SelectContent>
              </Select>
            )}

            {/* Filter summary */}
            <div className="flex items-center text-xs text-slate-500 ml-auto">
              Showing {filteredParticipants.length} of {participants.filter(p => showRemoved ? p.is_removed : !p.is_removed).length} participants
            </div>
          </div>
        )}
      </div>

      {/* Bulk Action Toolbar */}
      {canEdit() && selectedParticipantIds.size > 0 && (
        <div
          className="mb-3 flex flex-wrap items-center justify-between gap-3 bg-amber-50 border border-amber-300 rounded-sm px-4 py-3"
          data-testid="bulk-action-toolbar"
        >
          <div className="flex items-center gap-2 text-sm text-amber-900">
            <CheckCircle className="w-4 h-4" />
            <span data-testid="bulk-selected-count">
              <span className="font-bold">{selectedParticipantIds.size}</span> selected
            </span>
            <button
              type="button"
              onClick={clearBulkSelection}
              className="ml-2 underline text-amber-800 hover:text-amber-950 text-xs"
              data-testid="bulk-clear-selection"
            >
              clear
            </button>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Button
                variant="outline"
                size="sm"
                className="rounded-sm border-amber-600 text-amber-800 hover:bg-amber-100"
                onClick={() => setBulkTypeMenuOpen((v) => !v)}
                disabled={bulkActionLoading}
                data-testid="bulk-change-type-btn"
              >
                <UserCheck className="w-4 h-4 mr-1.5" />
                Change Type
                <ChevronRight className={`w-3 h-3 ml-1 transition-transform ${bulkTypeMenuOpen ? 'rotate-90' : ''}`} />
              </Button>
              {bulkTypeMenuOpen && (
                <div
                  className="absolute right-0 top-full mt-1 z-50 bg-white border border-slate-200 rounded-sm shadow-lg w-56"
                  data-testid="bulk-change-type-menu"
                >
                  <button
                    onClick={() => handleBulkChangeType('student')}
                    className="w-full text-left px-4 py-2 text-sm hover:bg-slate-50 flex items-center gap-2"
                    data-testid="bulk-set-student"
                  >
                    <GraduationCap className="w-4 h-4 text-blue-600" />
                    Set as Student
                  </button>
                  <button
                    onClick={() => handleBulkChangeType('cadre')}
                    className="w-full text-left px-4 py-2 text-sm hover:bg-slate-50 flex items-center gap-2 border-t border-slate-100"
                    data-testid="bulk-set-cadre"
                  >
                    <Star className="w-4 h-4 text-amber-600" />
                    Set as Cadre
                  </button>
                  <button
                    onClick={() => handleBulkChangeType('senior_staff')}
                    className="w-full text-left px-4 py-2 text-sm hover:bg-slate-50 flex items-center gap-2 border-t border-slate-100"
                    data-testid="bulk-set-senior-staff"
                  >
                    <Briefcase className="w-4 h-4 text-emerald-700" />
                    Set as Senior Staff
                  </button>
                  <button
                    onClick={() => handleBulkChangeType('needs_review')}
                    className="w-full text-left px-4 py-2 text-sm hover:bg-slate-50 flex items-center gap-2 border-t border-slate-100"
                    data-testid="bulk-set-needs-review"
                  >
                    <Shield className="w-4 h-4 text-orange-600" />
                    Set as Needs Review
                  </button>
                </div>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              className="rounded-sm border-amber-600 text-amber-800 hover:bg-amber-100"
              onClick={() => setBulkAssignOpen(true)}
              disabled={bulkActionLoading}
              data-testid="bulk-edit-assignment-btn"
            >
              <Edit3 className="w-4 h-4 mr-1.5" />
              Edit Flight / Squadron
            </Button>
            {['dcp', 'commander', 'executive_staff'].includes(user?.role) && (
              <Button
                variant="outline"
                size="sm"
                className="rounded-sm border-red-500 text-red-600 hover:bg-red-50"
                onClick={handleBulkDelete}
                disabled={bulkActionLoading}
                data-testid="bulk-delete-btn"
              >
                {bulkActionLoading ? (
                  <RefreshCw className="w-4 h-4 mr-1.5 animate-spin" />
                ) : (
                  <Trash2 className="w-4 h-4 mr-1.5" />
                )}
                Delete Selected
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Import Preview Modal */}
      <ImportPreviewModal
        open={importPreviewOpen}
        file={importPreviewFile}
        onClose={() => { setImportPreviewOpen(false); setImportPreviewFile(null); }}
        onApplied={handleImportApplied}
      />

      {/* Bulk Assignment Dialog */}
      <Dialog open={bulkAssignOpen} onOpenChange={(o) => { setBulkAssignOpen(o); if (!o) { setBulkAssignFlight('__nochange__'); setBulkAssignSquadron('__nochange__'); } }}>
        <DialogContent className="rounded-sm max-w-md" data-testid="bulk-assignment-dialog">
          <DialogHeader>
            <DialogTitle>Bulk Edit Flight / Squadron</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-slate-600">
              Apply Flight and/or Squadron to <span className="font-semibold">{selectedParticipantIds.size}</span> selected participant{selectedParticipantIds.size === 1 ? '' : 's'}. Choose <span className="italic">Don't change</span> on a field to leave it untouched.
            </p>
            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-500">Flight</Label>
              <Select value={bulkAssignFlight} onValueChange={setBulkAssignFlight}>
                <SelectTrigger className="mt-1 rounded-sm" data-testid="bulk-assign-flight-select">
                  <SelectValue placeholder="Don't change" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__nochange__">Don't change</SelectItem>
                  <SelectItem value="None">Clear (None)</SelectItem>
                  <SelectItem value="alpha">Alpha</SelectItem>
                  <SelectItem value="bravo">Bravo</SelectItem>
                  <SelectItem value="charlie">Charlie</SelectItem>
                  <SelectItem value="delta">Delta</SelectItem>
                  <SelectItem value="echo">Echo</SelectItem>
                  <SelectItem value="foxtrot">Foxtrot</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-500">Squadron</Label>
              <Select value={bulkAssignSquadron} onValueChange={setBulkAssignSquadron}>
                <SelectTrigger className="mt-1 rounded-sm" data-testid="bulk-assign-squadron-select">
                  <SelectValue placeholder="Don't change" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__nochange__">Don't change</SelectItem>
                  <SelectItem value="None">Clear (None)</SelectItem>
                  <SelectItem value="6th_cts">6th CTS</SelectItem>
                  <SelectItem value="21st_cts">21st CTS</SelectItem>
                  <SelectItem value="22nd_cts">22nd CTS</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="outline"
                className="rounded-sm"
                onClick={() => setBulkAssignOpen(false)}
                disabled={bulkActionLoading}
                data-testid="bulk-assign-cancel"
              >
                Cancel
              </Button>
              <Button
                className="rounded-sm bg-[#00205B] hover:bg-[#001540] text-white"
                onClick={handleBulkAssign}
                disabled={bulkActionLoading || (bulkAssignFlight === '__nochange__' && bulkAssignSquadron === '__nochange__')}
                data-testid="bulk-assign-apply"
              >
                {bulkActionLoading ? (
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Check className="w-4 h-4 mr-2" />
                )}
                Apply to {selectedParticipantIds.size}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Table */}
      <div className="bg-white border border-slate-200 rounded-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full cap-table" data-testid="roster-table">
            <thead>
              <tr>
                {canEdit() && (
                  <th className="text-left w-8 px-2">
                    <input
                      type="checkbox"
                      className="cursor-pointer"
                      data-testid="select-all-checkbox"
                      aria-label="Select all visible"
                      checked={
                        paginatedParticipants.length > 0 &&
                        paginatedParticipants.every((p) => selectedParticipantIds.has(p.id))
                      }
                      onChange={() => toggleSelectAll(paginatedParticipants.map((p) => p.id))}
                    />
                  </th>
                )}
                <th className="text-left">CAP ID</th>
                <th className="text-left">Rank</th>
                <th className="text-left">Name</th>
                <th className="text-left">Flight</th>
                <th className="text-left">Squadron</th>
                <th className="text-left">Gender</th>
                <th className="text-left">Age</th>
                {canViewSensitiveData() && <th className="text-left">Unit</th>}
                {canViewSensitiveData() && <th className="text-left">Wing</th>}
                <th className="text-left">Type</th>
                {canViewSensitiveData() && <th className="text-center">Paid</th>}
                {canViewSensitiveData() && !showRemoved && <th className="text-center">Approved</th>}
                {showRemoved && <th className="text-left">Removal Reason</th>}
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginatedParticipants.length === 0 ? (
                <tr>
                  <td colSpan={canEdit() ? 12 : 11} className="text-center py-8 text-slate-400">
                    {showRemoved 
                      ? 'No removed participants' 
                      : (searchTerm || typeFilter !== 'all' || paidFilter !== 'all' 
                        ? 'No matching participants found' 
                        : 'No participants yet. Import a CAP Event Admin Report to get started.')}
                  </td>
                </tr>
              ) : (
                paginatedParticipants.map((p) => {
                  const flightColors = getFlightColors(p.flight);
                  const squadronDisplay = getSquadronDisplay(p.squadron);
                  const isEditing = inlineEditId === p.id;
                  return (
                  <tr 
                    key={p.id} 
                    className={`hover:bg-slate-50 transition-colors ${p.is_removed ? 'bg-red-50/50' : flightColors.bg} ${flightColors.border}`}
                    data-testid={`roster-row-${p.capid}`}
                  >
                    {canEdit() && (
                      <td className="px-2 w-8" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          className="cursor-pointer"
                          checked={selectedParticipantIds.has(p.id)}
                          onChange={() => toggleSelectOne(p.id)}
                          aria-label={`Select ${p.first_name} ${p.last_name}`}
                          data-testid={`select-row-${p.capid}`}
                        />
                      </td>
                    )}
                    <td className="font-mono text-[#00205B] font-medium cursor-pointer" onClick={() => handleViewParticipant(p)}>{p.capid}</td>
                    <td className="cursor-pointer" onClick={() => handleViewParticipant(p)}>{p.rank}</td>
                    <td className="font-medium cursor-pointer" onClick={() => handleViewParticipant(p)}>
                      <div className="flex items-center gap-2">
                        <CadetAvatar participant={p} size="sm" />
                        <span>
                          {p.last_name}, {p.first_name}
                          {p.is_removed && <span className="ml-2 text-xs text-red-500">(Removed)</span>}
                        </span>
                      </div>
                    </td>
                    {/* Editable Flight Cell */}
                    <td onClick={(e) => e.stopPropagation()}>
                      {isEditing ? (
                        <Select value={inlineEditFlight} onValueChange={setInlineEditFlight}>
                          <SelectTrigger className="h-7 w-24 text-xs rounded-sm">
                            <SelectValue placeholder="Flight" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="None">None</SelectItem>
                            <SelectItem value="Alpha">Alpha</SelectItem>
                            <SelectItem value="Bravo">Bravo</SelectItem>
                            <SelectItem value="Charlie">Charlie</SelectItem>
                            <SelectItem value="Delta">Delta</SelectItem>
                            <SelectItem value="Echo">Echo</SelectItem>
                            <SelectItem value="Foxtrot">Foxtrot</SelectItem>
                          </SelectContent>
                        </Select>
                      ) : (
                        <div 
                          className="cursor-pointer group flex items-center gap-1"
                          onClick={() => canEdit() && startInlineEdit(p)}
                        >
                          {p.flight && p.flight !== 'None' ? (
                            <span className={`inline-block px-2 py-0.5 text-[10px] uppercase tracking-wider font-bold rounded-sm ${flightColors.badge}`}>
                              {p.flight}
                            </span>
                          ) : (
                            <span className="text-slate-300">-</span>
                          )}
                          {canEdit() && (
                            <Edit3 className="w-3 h-3 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                          )}
                        </div>
                      )}
                    </td>
                    {/* Editable Squadron Cell */}
                    <td onClick={(e) => e.stopPropagation()}>
                      {isEditing ? (
                        <Select value={inlineEditSquadron} onValueChange={setInlineEditSquadron}>
                          <SelectTrigger className="h-7 w-24 text-xs rounded-sm">
                            <SelectValue placeholder="Squadron" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="None">None</SelectItem>
                            <SelectItem value="6th_cts">6th CTS</SelectItem>
                            <SelectItem value="21st_cts">21st CTS</SelectItem>
                            <SelectItem value="22nd_cts">22nd CTS</SelectItem>
                          </SelectContent>
                        </Select>
                      ) : (
                        <div 
                          className="cursor-pointer group flex items-center gap-1"
                          onClick={() => canEdit() && startInlineEdit(p)}
                        >
                          {p.squadron && p.squadron !== 'None' ? (
                            <span className={`inline-block px-2 py-0.5 text-[10px] uppercase tracking-wider font-bold rounded-sm border ${squadronDisplay.badge}`}>
                              {squadronDisplay.name}
                            </span>
                          ) : (
                            <span className="text-slate-300">-</span>
                          )}
                          {canEdit() && (
                            <Edit3 className="w-3 h-3 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                          )}
                        </div>
                      )}
                    </td>
                    <td className="text-sm">{p.gender === 'M' ? 'Male' : p.gender === 'F' ? 'Female' : p.gender || '-'}</td>
                    <td className="font-mono text-sm">{p.age || p.age_at_event || '-'}</td>
                    {canViewSensitiveData() && <td className="font-mono text-sm">{p.unit || '-'}</td>}
                    {canViewSensitiveData() && <td className="text-sm text-slate-500">{p.wing || '-'}</td>}
                    <td>
                      <span className={`inline-block px-2 py-0.5 text-[10px] uppercase tracking-wider font-bold rounded-sm border ${getTypeBadgeColor(p.participant_type)}`}>
                        {labelForType(p.participant_type)}
                      </span>
                    </td>
                    {canViewSensitiveData() && (
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
                    )}
                    {canViewSensitiveData() && !showRemoved && (
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
                        {/* Inline edit save/cancel buttons */}
                        {isEditing ? (
                          <>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => saveInlineEdit(p.id)}
                              className="h-7 w-7 p-0 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50"
                              data-testid={`save-assignment-${p.capid}`}
                            >
                              <Check className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={cancelInlineEdit}
                              className="h-7 w-7 p-0 text-red-500 hover:text-red-600 hover:bg-red-50"
                              data-testid={`cancel-assignment-${p.capid}`}
                            >
                              <X className="w-4 h-4" />
                            </Button>
                          </>
                        ) : (
                          <>
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
                            ) : (
                              <>
                                {/* Edit Assignment button - uses role-based permission check */}
                                {canEditAssignment(p) && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      startInlineEdit(p);
                                    }}
                                    className="h-8 w-8 p-0 text-amber-600 hover:text-amber-700 hover:bg-amber-50"
                                    title={`Edit Assignment${user?.role === 'exec_cadre' && isStudentType(p.participant_type) ? ' (Students: Contact Plans & Programs)' : ''}`}
                                    data-testid={`edit-assignment-${p.capid}`}
                                  >
                                    <Edit3 className="w-4 h-4" />
                                  </Button>
                                )}
                                {/* Edit All Details - only for full edit roles */}
                                {canEdit() && (
                                  <>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleEdit(p);
                                      }}
                                      className="h-8 w-8 p-0"
                                      title="Edit All Details"
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
                              </>
                            )}
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                  );
                })
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

      </>
      )}

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
                  <div className="relative group">
                    <CadetAvatar participant={selectedParticipant} size="lg" />
                    {(user?.role === 'commander' || user?.role === 'dcp' || user?.role === 'executive_staff' ||
                      user?.role === 'exec_cadre' || user?.role === 'staff' || user?.role === 'plans_programs' ||
                      user?.role === 'cadre' || user?.role === 'finance' ||
                      user?.role === 'squadron_commander' || user?.role === 'training_officer') && (
                      <label className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-full opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer" data-testid="upload-photo-overlay">
                        <input
                          type="file"
                          accept="image/jpeg,image/png,image/webp"
                          className="hidden"
                          onChange={async (e) => {
                            const file = e.target.files?.[0];
                            if (!file) return;
                            try {
                              await uploadCadetPhoto(selectedParticipant.id, file);
                              toast.success('Photo uploaded successfully');
                              setSelectedParticipant(prev => ({ ...prev, photo_path: 'uploaded' }));
                              loadParticipants();
                            } catch (err) {
                              toast.error(err?.response?.data?.detail || 'Failed to upload photo');
                            }
                          }}
                        />
                        <Camera className="w-5 h-5 text-white" />
                      </label>
                    )}
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

              <div className="space-y-6 mt-4">
                {/* SECTION 1: Basic Info */}
                <div className="space-y-3">
                  <h4 className="font-bold text-[#00205B] uppercase text-xs tracking-wide border-b border-slate-200 pb-2">
                    Basic Information
                  </h4>
                  <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-500">CAPID:</span>
                      <span className="font-mono font-medium">{selectedParticipant.capid}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Rank:</span>
                      <span className="font-medium">{selectedParticipant.rank || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Unit:</span>
                      <span className="font-mono font-medium">{selectedParticipant.unit || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Gender:</span>
                      <span className="font-medium">{selectedParticipant.gender || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Age:</span>
                      <span className="font-medium">{selectedParticipant.age || selectedParticipant.age_at_event || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Wing:</span>
                      <span className="font-medium">{selectedParticipant.wing || '-'}</span>
                    </div>
                  </div>
                </div>

                {/* SECTION 2: Encampment Info */}
                <div className="space-y-3">
                  <h4 className="font-bold text-[#00205B] uppercase text-xs tracking-wide border-b border-slate-200 pb-2">
                    Encampment Information
                  </h4>
                  <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Squadron:</span>
                      <span className="font-medium">{selectedParticipant.squadron?.replace('_', ' ').toUpperCase() || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Flight:</span>
                      <span className="font-medium capitalize">{selectedParticipant.flight || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Registration Status:</span>
                      <span className="font-medium">{selectedParticipant.registration_status || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Shirt Size:</span>
                      <span className="font-medium">{selectedParticipant.shirt_size || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Student Type:</span>
                      <span className={`px-2 py-0.5 text-xs uppercase font-bold rounded-sm border ${getTypeBadgeColor(selectedParticipant.participant_type)}`}>
                        {labelForType(selectedParticipant.participant_type)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Last Encampment:</span>
                      <span className="font-medium">{selectedParticipant.last_encampment || '-'}</span>
                    </div>
                  </div>
                  {(selectedParticipant.conflicts || selectedParticipant.comments) && (
                    <div className="mt-3 space-y-2">
                      {selectedParticipant.conflicts && (
                        <div className="bg-amber-50 border border-amber-200 rounded-sm p-2">
                          <p className="text-xs font-bold uppercase text-amber-700 mb-1">Conflicts</p>
                          <p className="text-sm text-amber-800">{selectedParticipant.conflicts}</p>
                        </div>
                      )}
                      {selectedParticipant.comments && (
                        <div className="bg-slate-50 border border-slate-200 rounded-sm p-2">
                          <p className="text-xs font-bold uppercase text-slate-600 mb-1">Comments</p>
                          <p className="text-sm text-slate-700">{selectedParticipant.comments}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* SECTION 3: Emergency Contact */}
                {canViewSensitiveData() && (
                  <div className="space-y-3">
                    <h4 className="font-bold text-[#00205B] uppercase text-xs tracking-wide border-b border-slate-200 pb-2 flex items-center gap-1">
                      <AlertCircle className="w-3 h-3" /> Emergency Contact
                    </h4>
                    <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Name:</span>
                        <span className="font-medium">{selectedParticipant.emergency_contact || '-'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Phone:</span>
                        <span className="font-medium">{selectedParticipant.emergency_phone || '-'}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* SECTION 4: Parent Contact */}
                {canViewSensitiveData() && (
                  <div className="space-y-3">
                    <h4 className="font-bold text-[#00205B] uppercase text-xs tracking-wide border-b border-slate-200 pb-2 flex items-center gap-1">
                      <Users className="w-3 h-3" /> Parent/Guardian Contact
                    </h4>
                    <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Primary Phone:</span>
                        <span className="font-medium">{selectedParticipant.cadet_parent_phone || '-'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Secondary Phone:</span>
                        <span className="font-medium">{selectedParticipant.cadet_parent_phone_secondary || '-'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Emergency Phone:</span>
                        <span className="font-medium">{selectedParticipant.cadet_parent_phone_emergency || '-'}</span>
                      </div>
                      <div className="col-span-2 flex justify-between">
                        <span className="text-slate-500">Primary Email:</span>
                        <span className="font-medium">{selectedParticipant.cadet_parent_email || '-'}</span>
                      </div>
                      <div className="col-span-2 flex justify-between">
                        <span className="text-slate-500">Secondary Email:</span>
                        <span className="font-medium">{selectedParticipant.cadet_parent_email_secondary || '-'}</span>
                      </div>
                      <div className="col-span-2 flex justify-between">
                        <span className="text-slate-500">Emergency Email:</span>
                        <span className="font-medium">{selectedParticipant.cadet_parent_email_emergency || '-'}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* SECTION 5: Address */}
                {canViewSensitiveData() && (selectedParticipant.address || selectedParticipant.city) && (
                  <div className="space-y-3">
                    <h4 className="font-bold text-[#00205B] uppercase text-xs tracking-wide border-b border-slate-200 pb-2 flex items-center gap-1">
                      <MapPin className="w-3 h-3" /> Address
                    </h4>
                    <div className="text-sm space-y-1">
                      {selectedParticipant.address && <p>{selectedParticipant.address}</p>}
                      {selectedParticipant.address2 && <p>{selectedParticipant.address2}</p>}
                      <p>
                        {selectedParticipant.city && <span>{selectedParticipant.city}, </span>}
                        {selectedParticipant.state && <span>{selectedParticipant.state} </span>}
                        {selectedParticipant.zip_code && <span>{selectedParticipant.zip_code}</span>}
                      </p>
                    </div>
                  </div>
                )}

                {/* Restricted Data Notice for non-privileged users */}
                {!canViewSensitiveData() && (
                  <div className="bg-slate-50 border border-slate-200 rounded-sm p-4 text-center">
                    <Shield className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                    <p className="text-sm text-slate-600 font-medium">Contact & Address Information Restricted</p>
                    <p className="text-xs text-slate-500 mt-1">Emergency contact and parent information is only visible to authorized staff roles.</p>
                  </div>
                )}
              </div>

              {/* Health Services Section */}
              <CadetHealthSection 
                cadetId={selectedParticipant.id}
                capid={selectedParticipant.capid}
                cadetName={`${selectedParticipant.first_name} ${selectedParticipant.last_name}`}
              />

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
