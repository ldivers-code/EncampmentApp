import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  getMyFlightInfo, getFlightRoster, getSquadronRoster, 
  getFlightDocuments, getDocuments, createDocument, deleteDocument,
  getScoreCategories, recordMeritDemerit, getMeritDemerits, getIndividualLeaderboard,
  getFlightLeaderboard, getCumulativeStandings,
  getFlightReports, createFlightReport, reviewFlightReport, getReportSettings, updateReportSettings,
  escalateFlightReport, resolveFlightReport,
  getFlightLeadership, updateFlightLeadership,
  getHealthAlerts, updateHealthAlerts, getMemberProfile
} from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { toast } from 'sonner';
import { 
  Users, 
  FileText, 
  BookOpen, 
  ChevronRight,
  Plus,
  Minus,
  Trash2,
  ExternalLink,
  Shield,
  Star,
  User,
  Folder,
  GraduationCap,
  Upload,
  Filter,
  RefreshCw,
  Trophy,
  TrendingUp,
  Award,
  ClipboardList,
  AlertTriangle,
  CheckCircle,
  Clock,
  Send,
  Eye,
  Settings,
  ArrowUpCircle,
  History,
  CheckCircle2,
  Edit2,
  Heart,
  X,
  Mail
} from 'lucide-react';

const CATEGORY_LABELS = {
  tlp: 'Training Lesson Plans (TLPs)',
  pocket_class: 'Pocket Classes',
  handbook: 'Handbooks',
  sop: 'SOPs',
  form: 'Forms',
  checklist: 'Checklists',
  reference: 'Reference Materials',
  other: 'Other'
};

const CATEGORY_ICONS = {
  tlp: GraduationCap,
  pocket_class: BookOpen,
  handbook: BookOpen,
  sop: FileText,
  form: FileText,
  checklist: FileText,
  reference: Folder,
  other: FileText
};

const MyFlightPage = () => {
  const { user, canEdit } = useAuth();
  const [loading, setLoading] = useState(true);
  const [flightInfo, setFlightInfo] = useState(null);
  const [selectedFlight, setSelectedFlight] = useState('');
  const [viewMode, setViewMode] = useState('flight'); // flight or squadron
  const [roster, setRoster] = useState(null);
  const [documents, setDocuments] = useState({});
  const [activeTab, setActiveTab] = useState('roster');
  const [selectedCategory, setSelectedCategory] = useState('all');
  
  // Points state
  const [flightCadets, setFlightCadets] = useState([]);
  const [cadetPoints, setCadetPoints] = useState({});
  const [flightStanding, setFlightStanding] = useState(null);
  const [recentMerits, setRecentMerits] = useState([]);
  const [isMeritModalOpen, setIsMeritModalOpen] = useState(false);
  const [selectedCadet, setSelectedCadet] = useState(null);
  const [memberDetail, setMemberDetail] = useState(null);
  const [memberAlerts, setMemberAlerts] = useState(null);
  const [memberPanelOpen, setMemberPanelOpen] = useState(false);
  const [editingAlerts, setEditingAlerts] = useState(false);
  const [alertForm, setAlertForm] = useState({ alerts: [], notes: '', shared_notes: '' });
  const [meritForm, setMeritForm] = useState({
    entry_type: 'merit',
    points: '',
    reason: ''
  });
  
  // Document upload form
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadForm, setUploadForm] = useState({
    title: '',
    description: '',
    doc_type: 'tlp',
    category: 'tlp',
    content: '',
    file_url: '',
    scope: 'flight',
    flight: '',
    squadron: ''
  });

  // Reports state
  const [reports, setReports] = useState([]);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [isViewReportModalOpen, setIsViewReportModalOpen] = useState(false);
  const [selectedReport, setSelectedReport] = useState(null);
  const [reportSettings, setReportSettings] = useState({ deadline_time: '21:00', is_enabled: true });
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);

  // Leadership state
  const [leadership, setLeadership] = useState(null);
  const [editingLeadership, setEditingLeadership] = useState(false);
  const [leadershipForm, setLeadershipForm] = useState({
    flight_sergeant: { name: '', rank: '' },
    flight_commander: { name: '', rank: '' },
    squadron_commander: { name: '', rank: '' }
  });
  const [reportForm, setReportForm] = useState({
    report_date: new Date().toISOString().split('T')[0],
    reporter_role: 'flight_sergeant',
    morale: { content: '', has_issues: false },
    safety_concerns: { content: '', has_issues: false },
    discipline_issues: { content: '', has_issues: false },
    training_performance: { content: '', has_issues: false },
    significant_events: { content: '', has_issues: false },
    recommendations: { content: '', has_issues: false },
    commander_issues: { content: '', has_issues: false }
  });

  const allFlights = [
    { value: 'alpha', label: 'Alpha Flight', squadron: '6th_cts' },
    { value: 'bravo', label: 'Bravo Flight', squadron: '6th_cts' },
    { value: 'charlie', label: 'Charlie Flight', squadron: '21st_cts' },
    { value: 'delta', label: 'Delta Flight', squadron: '21st_cts' },
    { value: 'echo', label: 'Echo Flight', squadron: '22nd_cts' },
    { value: 'foxtrot', label: 'Foxtrot Flight', squadron: '22nd_cts' }
  ];

  const allSquadrons = [
    { value: '6th_cts', label: '6th CTS' },
    { value: '21st_cts', label: '21st CTS' },
    { value: '22nd_cts', label: '22nd CTS' }
  ];

  useEffect(() => {
    loadFlightInfo();
  }, []);

  useEffect(() => {
    if (selectedFlight) {
      loadRoster();
      loadDocuments();
      loadFlightPoints();
      loadLeadership();
    }
  }, [selectedFlight, viewMode]);

  useEffect(() => {
    if (activeTab === 'points' && selectedFlight) {
      loadFlightPoints();
    }
  }, [activeTab]);

  useEffect(() => {
    if (activeTab === 'reports' && selectedFlight) {
      loadReports();
      loadReportSettings();
    }
  }, [activeTab, selectedFlight]);

  const loadFlightInfo = async () => {
    try {
      const info = await getMyFlightInfo();
      setFlightInfo(info);
      
      // Set default selected flight
      if (info.user_flight) {
        setSelectedFlight(info.user_flight);
      } else if (info.accessible_flights.length > 0) {
        setSelectedFlight(info.accessible_flights[0]);
      }
    } catch (error) {
      toast.error('Failed to load flight information');
    } finally {
      setLoading(false);
    }
  };

  const loadFlightPoints = async () => {
    if (!selectedFlight) return;
    
    try {
      // Get roster for cadets
      const rosterData = await getFlightRoster(selectedFlight);
      const cadets = rosterData.roster?.filter(m => m.is_student) || [];
      setFlightCadets(cadets);
      
      // Get individual leaderboard to get point totals
      const leaderboard = await getIndividualLeaderboard('cadet');
      const pointsMap = {};
      leaderboard.forEach(entry => {
        pointsMap[entry.participant_id] = entry.total_points;
      });
      setCadetPoints(pointsMap);
      
      // Get flight standing from cumulative standings
      const standings = await getCumulativeStandings();
      const flightData = standings.flights?.find(f => f.flight.toLowerCase() === selectedFlight.toLowerCase());
      setFlightStanding(flightData);
      
      // Get recent merits for this flight's cadets
      const merits = await getMeritDemerits({ limit: 20 });
      const cadetIds = cadets.map(c => c.id);
      const flightMerits = merits.filter(m => cadetIds.includes(m.participant_id));
      setRecentMerits(flightMerits.slice(0, 10));
    } catch (error) {
      console.error('Failed to load flight points:', error);
    }
  };

  // ================= REPORTS FUNCTIONS =================

  const loadReports = async () => {
    try {
      // Exec Cadre and Commander can see all reports, others see only their flight
      let filters = {};
      if (!canViewAllFlights()) {
        const flightData = allFlights.find(f => f.value === selectedFlight);
        filters = { 
          flight: selectedFlight,
          squadron: flightData?.squadron 
        };
      } else if (selectedFlight) {
        // If a flight is selected, filter by it even for admins
        filters = { flight: selectedFlight };
      }
      const data = await getFlightReports(filters);
      setReports(data);
    } catch (error) {
      console.error('Failed to load reports:', error);
    }
  };

  const loadReportSettings = async () => {
    try {
      const settings = await getReportSettings();
      setReportSettings(settings);
    } catch (error) {
      console.error('Failed to load report settings:', error);
    }
  };

  const resetReportForm = () => {
    setReportForm({
      report_date: new Date().toISOString().split('T')[0],
      reporter_role: getAutoReporterRole(),
      morale: { content: '', has_issues: false },
      safety_concerns: { content: '', has_issues: false },
      discipline_issues: { content: '', has_issues: false },
      training_performance: { content: '', has_issues: false },
      significant_events: { content: '', has_issues: false },
      recommendations: { content: '', has_issues: false },
      commander_issues: { content: '', has_issues: false }
    });
  };

  const handleSubmitReport = async (e) => {
    e.preventDefault();
    
    // Cadre can only submit for their assigned flight
    if (canOnlySubmitOwnFlight() && selectedFlight !== user?.flight?.toLowerCase()) {
      toast.error('You can only submit reports for your assigned flight');
      return;
    }
    
    if (!selectedFlight) {
      toast.error('Please select a flight');
      return;
    }

    // Validate at least morale section has content
    if (!reportForm.morale.content.trim()) {
      toast.error('Please fill in the Morale section at minimum');
      return;
    }

    try {
      const flightData = allFlights.find(f => f.value === selectedFlight);
      const payload = {
        ...reportForm,
        flight: selectedFlight,
        squadron: flightData?.squadron || ''
      };
      
      await createFlightReport(payload);
      toast.success('Report submitted successfully');
      setIsReportModalOpen(false);
      resetReportForm();
      loadReports();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit report');
    }
  };

  const handleReviewReport = async (reportId) => {
    try {
      await reviewFlightReport(reportId);
      toast.success('Report marked as reviewed');
      loadReports();
      setIsViewReportModalOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to review report');
    }
  };

  const handleSaveReportSettings = async () => {
    try {
      await updateReportSettings(reportSettings);
      toast.success('Settings saved');
      setIsSettingsModalOpen(false);
    } catch (error) {
      toast.error('Failed to save settings');
    }
  };

  const getReportStatusBadge = (status, escalationLevel = null) => {
    const statusConfig = {
      submitted: { bg: 'bg-blue-100', text: 'text-blue-700', icon: Clock, label: 'Submitted' },
      reviewed: { bg: 'bg-emerald-100', text: 'text-emerald-700', icon: CheckCircle, label: 'Reviewed' },
      escalated: { bg: 'bg-red-100', text: 'text-red-700', icon: AlertTriangle, label: 'Escalated' },
      // New detailed escalation chain statuses
      escalated_flight_commander: { bg: 'bg-yellow-100', text: 'text-yellow-700', icon: ArrowUpCircle, label: 'Flight Commander' },
      escalated_squadron: { bg: 'bg-amber-100', text: 'text-amber-700', icon: ArrowUpCircle, label: 'Sq. Commander' },
      escalated_exec: { bg: 'bg-orange-100', text: 'text-orange-700', icon: ArrowUpCircle, label: 'Exec Cadre' },
      escalated_dcs: { bg: 'bg-rose-100', text: 'text-rose-700', icon: ArrowUpCircle, label: 'DCS & Commandant' },
      escalated_commander: { bg: 'bg-red-100', text: 'text-red-700', icon: ArrowUpCircle, label: 'Encampment Cmdr' },
      at_commander: { bg: 'bg-red-200', text: 'text-red-800', icon: AlertTriangle, label: 'At Cmdr Level' },
      resolved: { bg: 'bg-emerald-100', text: 'text-emerald-700', icon: CheckCircle2, label: 'Resolved' }
    };
    const config = statusConfig[status] || statusConfig.submitted;
    const Icon = config.icon;
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${config.bg} ${config.text}`}>
        <Icon className="w-3 h-3" />
        {config.label}
      </span>
    );
  };

  const canSubmitReports = () => {
    // Staff, cadre, commanders can submit reports
    return ['commander', 'executive_staff', 'staff', 'cadre', 'plans_programs', 'exec_cadre'].includes(user?.role);
  };

  const canReviewReports = () => {
    // Commanders and exec cadre can review
    return ['commander', 'executive_staff', 'exec_cadre'].includes(user?.role);
  };

  // Auto-detect reporter role based on user's actual role/position
  const getAutoReporterRole = () => {
    const userRole = user?.role?.toLowerCase();
    const userPosition = user?.position?.toLowerCase() || '';
    
    // Check if user is a Squadron Commander
    if (userPosition.includes('squadron commander') || userPosition.includes('sq cc') || 
        userPosition.includes('squadron cc')) {
      return 'squadron_commander';
    }
    
    // Check if user is a Flight Commander
    if (userPosition.includes('flight commander') || userPosition.includes('flt cc') ||
        userPosition.includes('flight cc')) {
      return 'flight_commander';
    }
    
    // Check if user is a Flight Sergeant
    if (userPosition.includes('flight sergeant') || userPosition.includes('flt sgt') ||
        userPosition.includes('first sergeant')) {
      return 'flight_sergeant';
    }
    
    // Default based on general role
    if (userRole === 'commander' || userRole === 'executive_staff' || userRole === 'exec_cadre') {
      return 'squadron_commander';
    }
    
    if (userRole === 'staff' || userRole === 'cadre') {
      return 'flight_sergeant';
    }
    
    return 'flight_sergeant';
  };

  // Check if user can view all flights (Exec Cadre, Commander, Staff, Plans & Programs)
  const canViewAllFlights = () => {
    return ['commander', 'executive_staff', 'training_officer', 'exec_cadre', 'staff', 'plans_programs'].includes(user?.role);
  };

  // Check if user can only submit reports for their assigned flight
  const canOnlySubmitOwnFlight = () => {
    return ['cadre'].includes(user?.role) && !canViewAllFlights();
  };

  // Check if user can escalate reports
  const canEscalateReports = () => {
    return ['commander', 'executive_staff', 'training_officer', 'exec_cadre', 'staff', 'plans_programs'].includes(user?.role);
  };

  // Check if user can resolve escalated reports
  const canResolveReports = () => {
    return ['commander', 'executive_staff', 'exec_cadre'].includes(user?.role);
  };

  // Get the next escalation level for a report based on current level
  const getNextEscalationLevel = (currentLevel) => {
    // Complete chain: flight_sergeant -> flight_commander -> squadron_commander -> exec_cadre -> dcs_commandant -> encampment_commander
    const escalationOrder = {
      'flight_sergeant': 'flight_commander',
      'flight_commander': 'squadron_commander',
      'squadron_commander': 'exec_cadre',
      'exec_cadre': 'dcs_commandant',
      'dcs_commandant': 'encampment_commander',
      'encampment_commander': null
    };
    
    if (!currentLevel) return 'flight_commander'; // Default first escalation
    return escalationOrder[currentLevel] || null;
  };

  // Get escalation level label
  const getEscalationLabel = (level) => {
    const labels = {
      'flight_sergeant': 'Flight Sergeant',
      'flight_commander': 'Flight Commander',
      'squadron_commander': 'Squadron Commander',
      'exec_cadre': 'Exec Cadre',
      'dcs_commandant': 'DCS & Commandant',
      'encampment_commander': 'Encampment Commander'
    };
    return labels[level] || level?.replace('_', ' ');
  };

  // Handle escalation
  const handleEscalateReport = async (reportId, targetLevel, notes = '') => {
    try {
      await escalateFlightReport(reportId, targetLevel, notes);
      toast.success(`Report escalated to ${getEscalationLabel(targetLevel)}`);
      loadReports();
      setIsViewReportModalOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to escalate report');
    }
  };

  // Handle resolution
  const handleResolveReport = async (reportId, notes = '') => {
    try {
      await resolveFlightReport(reportId, notes);
      toast.success('Report marked as resolved');
      loadReports();
      setIsViewReportModalOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to resolve report');
    }
  };

  // Get available reporter roles for this user
  const getAvailableReporterRoles = () => {
    const autoRole = getAutoReporterRole();
    
    // If user is exec_cadre or commander, they can choose any role
    if (canViewAllFlights()) {
      return [
        { value: 'flight_sergeant', label: 'Flight Sergeant' },
        { value: 'flight_commander', label: 'Flight Commander' },
        { value: 'squadron_commander', label: 'Squadron Commander' }
      ];
    }
    
    // For cadre/staff, only allow their detected role
    return [{ value: autoRole, label: autoRole.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) }];
  };

  const handleQuickMerit = (cadet, type) => {
    setSelectedCadet(cadet);
    setMeritForm({
      entry_type: type,
      points: type === 'merit' ? '5' : '5',
      reason: ''
    });
    setIsMeritModalOpen(true);
  };

  const handleSubmitMerit = async (e) => {
    e.preventDefault();
    if (!selectedCadet || !meritForm.points || !meritForm.reason) {
      toast.error('Please fill all fields');
      return;
    }

    try {
      await recordMeritDemerit({
        participant_id: selectedCadet.id,
        entry_type: meritForm.entry_type,
        points: parseFloat(meritForm.points),
        reason: meritForm.reason,
        date: new Date().toISOString().split('T')[0]
      });
      
      toast.success(`${meritForm.entry_type === 'merit' ? 'Merit' : 'Demerit'} recorded for ${selectedCadet.name}`);
      setIsMeritModalOpen(false);
      setSelectedCadet(null);
      setMeritForm({ entry_type: 'merit', points: '', reason: '' });
      loadFlightPoints();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record');
    }
  };

  const loadRoster = async () => {
    try {
      if (viewMode === 'flight') {
        const data = await getFlightRoster(selectedFlight);
        setRoster(data);
      } else {
        const flight = allFlights.find(f => f.value === selectedFlight);
        if (flight) {
          const data = await getSquadronRoster(flight.squadron);
          setRoster(data);
        }
      }
    } catch (error) {
      console.error('Failed to load roster:', error);
    }
  };

  const HEALTH_ALERT_ITEMS = [
    { key: 'epipen', label: 'Has EpiPen' },
    { key: 'fainting', label: 'Prone to Fainting' },
    { key: 'heat_sensitive', label: 'Heat Sensitive' },
    { key: 'sensory_issues', label: 'Sensory Issues' },
    { key: 'seizures', label: 'Seizure Risk' },
    { key: 'diabetes', label: 'Diabetes' },
    { key: 'asthma', label: 'Asthma' },
    { key: 'severe_allergies', label: 'Severe Allergies' },
    { key: 'wheelchair_mobility', label: 'Wheelchair / Mobility' },
    { key: 'hearing_impaired', label: 'Hearing Impaired' },
    { key: 'vision_impaired', label: 'Vision Impaired' },
    { key: 'other', label: 'Other' },
  ];

  const canEditHealth = ['commander', 'executive_staff', 'health_services'].includes(user?.role);

  const openMemberDetail = async (member) => {
    setMemberDetail(member);
    setMemberPanelOpen(true);
    setEditingAlerts(false);
    try {
      const alerts = await getHealthAlerts(member.id);
      setMemberAlerts(alerts);
      setAlertForm({
        alerts: alerts.alerts || [],
        notes: alerts.notes || '',
        shared_notes: alerts.shared_notes || '',
      });
    } catch {
      setMemberAlerts({ alerts: [], notes: '' });
      setAlertForm({ alerts: [], notes: '', shared_notes: '' });
    }
  };

  const closeMemberDetail = () => {
    setMemberPanelOpen(false);
    setMemberDetail(null);
    setMemberAlerts(null);
    setEditingAlerts(false);
  };

  const toggleAlertItem = (key) => {
    setAlertForm(prev => {
      const existing = prev.alerts.find(a => a.key === key);
      if (existing) {
        return { ...prev, alerts: prev.alerts.filter(a => a.key !== key) };
      }
      return { ...prev, alerts: [...prev.alerts, { key, details: '', shared_with: ['flight_commander'] }] };
    });
  };

  const updateAlertSharing = (key, level) => {
    setAlertForm(prev => ({
      ...prev,
      alerts: prev.alerts.map(a => {
        if (a.key !== key) return a;
        const shared = a.shared_with || [];
        return { ...a, shared_with: shared.includes(level) ? shared.filter(l => l !== level) : [...shared, level] };
      })
    }));
  };

  const updateAlertDetails = (key, details) => {
    setAlertForm(prev => ({
      ...prev,
      alerts: prev.alerts.map(a => a.key === key ? { ...a, details } : a)
    }));
  };

  const saveHealthAlerts = async () => {
    if (!memberDetail) return;
    try {
      await updateHealthAlerts(memberDetail.id, alertForm);
      toast.success('Health alerts saved');
      const updated = await getHealthAlerts(memberDetail.id);
      setMemberAlerts(updated);
      setEditingAlerts(false);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to save');
    }
  };



  const loadDocuments = async () => {
    try {
      const data = await getFlightDocuments(selectedFlight);
      setDocuments(data.documents || {});
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  };

  const loadLeadership = async () => {
    try {
      const data = await getFlightLeadership(selectedFlight);
      setLeadership(data);
    } catch (error) {
      console.error('Failed to load leadership:', error);
    }
  };

  const startEditLeadership = () => {
    setLeadershipForm({
      flight_sergeant: { ...leadership?.flight_sergeant || { name: '', rank: '' } },
      flight_commander: { ...leadership?.flight_commander || { name: '', rank: '' } },
      squadron_commander: { ...leadership?.squadron_commander || { name: '', rank: '' } }
    });
    setEditingLeadership(true);
  };

  const saveLeadership = async () => {
    try {
      const data = await updateFlightLeadership(selectedFlight, leadershipForm);
      setLeadership(data);
      setEditingLeadership(false);
      toast.success('Leadership updated');
    } catch (error) {
      toast.error('Failed to update leadership');
    }
  };

  const handleUploadDocument = async (e) => {
    e.preventDefault();
    if (!uploadForm.title) {
      toast.error('Title is required');
      return;
    }

    try {
      const docData = {
        ...uploadForm,
        flight: uploadForm.scope === 'flight' ? selectedFlight : null,
        squadron: uploadForm.scope === 'squadron' ? (allFlights.find(f => f.value === selectedFlight)?.squadron || null) : null
      };
      
      await createDocument(docData);
      toast.success('Document uploaded successfully');
      setIsUploadModalOpen(false);
      setUploadForm({
        title: '',
        description: '',
        doc_type: 'tlp',
        category: 'tlp',
        content: '',
        file_url: '',
        scope: 'flight',
        flight: '',
        squadron: ''
      });
      loadDocuments();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload document');
    }
  };

  const handleDeleteDocument = async (docId) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    
    try {
      await deleteDocument(docId);
      toast.success('Document deleted');
      loadDocuments();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete document');
    }
  };

  const getAccessibleFlights = () => {
    if (!flightInfo) return [];
    return allFlights.filter(f => flightInfo.accessible_flights.includes(f.value));
  };

  const getFlightLabel = (flightValue) => {
    return allFlights.find(f => f.value === flightValue)?.label || flightValue;
  };

  const getDocumentCount = () => {
    return Object.values(documents).reduce((sum, docs) => sum + docs.length, 0);
  };

  const getFilteredDocuments = () => {
    if (selectedCategory === 'all') {
      return documents;
    }
    return { [selectedCategory]: documents[selectedCategory] || [] };
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-400">Loading flight information...</div>
        </div>
      </div>
    );
  }

  if (!flightInfo || flightInfo.accessible_flights.length === 0) {
    return (
      <div className="p-6 lg:p-8 animate-fade-in">
        <div className="bg-amber-50 border border-amber-200 rounded-sm p-8 text-center">
          <Users className="w-12 h-12 mx-auto mb-4 text-amber-500" />
          <h2 className="text-xl font-bold text-amber-800 mb-2">No Flight Assigned</h2>
          <p className="text-amber-600">
            You haven't been assigned to a flight yet. Please contact your commander for flight assignment.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <Shield className="w-8 h-8 text-[#00205B]" />
          <div>
            <h1 className="text-2xl lg:text-3xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
              My Flight
            </h1>
            <p className="text-slate-500 text-sm">
              {flightInfo.has_full_access ? 'Full Access - All Flights' : `Assigned to ${getFlightLabel(flightInfo.user_flight)}`}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3 flex-wrap">
          {/* Flight Selector */}
          {getAccessibleFlights().length > 1 && (
            <Select value={selectedFlight} onValueChange={setSelectedFlight}>
              <SelectTrigger className="w-48 rounded-sm" data-testid="flight-selector">
                <SelectValue placeholder="Select Flight" />
              </SelectTrigger>
              <SelectContent>
                {getAccessibleFlights().map(f => (
                  <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          
          {/* View Mode Toggle */}
          {flightInfo.has_full_access && (
            <div className="flex rounded-sm border border-slate-200 overflow-hidden">
              <button
                onClick={() => setViewMode('flight')}
                className={`px-3 py-2 text-sm font-medium transition-colors ${
                  viewMode === 'flight' 
                    ? 'bg-[#00205B] text-white' 
                    : 'bg-white text-slate-600 hover:bg-slate-50'
                }`}
              >
                Flight
              </button>
              <button
                onClick={() => setViewMode('squadron')}
                className={`px-3 py-2 text-sm font-medium transition-colors ${
                  viewMode === 'squadron' 
                    ? 'bg-[#00205B] text-white' 
                    : 'bg-white text-slate-600 hover:bg-slate-50'
                }`}
              >
                Squadron
              </button>
            </div>
          )}
          
          <Button variant="outline" onClick={() => { loadRoster(); loadDocuments(); }} className="rounded-sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Flight Leadership */}
      {leadership && (
        <div className="bg-white border border-slate-200 rounded-sm mb-6" data-testid="flight-leadership">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50">
            <h3 className="text-sm font-bold uppercase tracking-wide text-[#00205B] flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Chain of Command
            </h3>
            {canEdit() && !editingLeadership && (
              <Button variant="ghost" size="sm" onClick={startEditLeadership} className="h-7 text-xs" data-testid="edit-leadership-btn">
                <Edit2 className="w-3 h-3 mr-1" /> Edit
              </Button>
            )}
            {editingLeadership && (
              <div className="flex gap-1">
                <Button variant="ghost" size="sm" onClick={() => setEditingLeadership(false)} className="h-7 text-xs">Cancel</Button>
                <Button size="sm" onClick={saveLeadership} className="h-7 text-xs bg-[#00205B]" data-testid="save-leadership-btn">Save</Button>
              </div>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-slate-100">
            {[
              { key: 'flight_sergeant', label: 'Flight Sergeant' },
              { key: 'flight_commander', label: 'Flight Commander' },
              { key: 'squadron_commander', label: 'Squadron Commander' }
            ].map(({ key, label }) => (
              <div key={key} className="px-4 py-3" data-testid={`leadership-${key}`}>
                <p className="text-[10px] uppercase tracking-wider text-slate-400 mb-1">{label}</p>
                {editingLeadership ? (
                  <div className="flex gap-2">
                    <Input
                      placeholder="Rank"
                      value={leadershipForm[key]?.rank || ''}
                      onChange={(e) => setLeadershipForm(prev => ({
                        ...prev, [key]: { ...prev[key], rank: e.target.value }
                      }))}
                      className="w-24 h-8 text-sm rounded-sm"
                      data-testid={`leadership-${key}-rank-input`}
                    />
                    <Input
                      placeholder="Name"
                      value={leadershipForm[key]?.name || ''}
                      onChange={(e) => setLeadershipForm(prev => ({
                        ...prev, [key]: { ...prev[key], name: e.target.value }
                      }))}
                      className="flex-1 h-8 text-sm rounded-sm"
                      data-testid={`leadership-${key}-name-input`}
                    />
                  </div>
                ) : (
                  <p className="text-sm font-medium text-slate-800">
                    {leadership[key]?.rank && leadership[key]?.name
                      ? `${leadership[key].rank} ${leadership[key].name}`
                      : <span className="text-slate-300 italic">Not assigned</span>
                    }
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-slate-200 overflow-x-auto">
        {[
          { id: 'roster', label: 'Roster', icon: Users },
          { id: 'points', label: 'Points', icon: Trophy, count: flightCadets.length },
          { id: 'documents', label: 'Documents', icon: FileText, count: getDocumentCount() },
          { id: 'reports', label: 'Reports', icon: ClipboardList, count: reports.filter(r => 
            ['escalated_flight_commander', 'escalated_squadron', 'escalated_exec', 'escalated_dcs', 'escalated_commander', 'at_commander'].includes(r.status)
          ).length || undefined }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeTab === tab.id
                ? 'border-[#00205B] text-[#00205B]'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
            data-testid={`tab-${tab.id}`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
            {tab.count !== undefined && (
              <span className="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-slate-100">{tab.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* Roster Tab */}
      {activeTab === 'roster' && roster && (
        <div className="bg-white border border-slate-200 rounded-sm">
          <div className="border-b border-slate-100 p-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5 text-[#00205B]" />
              <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm">
                {viewMode === 'flight' ? getFlightLabel(selectedFlight) : `Squadron ${roster.squadron?.replace('sq', '')}`} Roster
              </h2>
            </div>
            <div className="flex gap-4 text-sm text-slate-500">
              {viewMode === 'flight' && roster.cadre_count !== undefined && (
                <>
                  <span>{roster.cadre_count} Cadre</span>
                  <span>{roster.cadet_count} Cadets</span>
                </>
              )}
              <span className="font-medium text-[#00205B]">
                {viewMode === 'flight' ? roster.count : roster.total_count} Total
              </span>
            </div>
          </div>
          
          <div className="divide-y divide-slate-100">
            {viewMode === 'flight' ? (
              // Flight roster view
              roster.roster?.length === 0 ? (
                <div className="p-8 text-center text-slate-400">
                  <Users className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>No members in this flight</p>
                </div>
              ) : (
                roster.roster?.map((member) => (
                  <div 
                    key={member.id} 
                    className="p-4 hover:bg-slate-50 transition-colors flex items-center gap-4 cursor-pointer"
                    onClick={() => openMemberDetail(member)}
                    data-testid={`member-row-${member.id}`}
                  >
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                      member.is_student ? 'bg-blue-100 text-blue-600' : 'bg-emerald-100 text-emerald-600'
                    }`}>
                      {member.is_student ? <Star className="w-5 h-5" /> : <User className="w-5 h-5" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-slate-900 truncate">{member.name}</p>
                      {member.position && (
                        <p className="text-sm text-slate-500">{member.position}</p>
                      )}
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-300" />
                    <div className="text-right">
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        member.is_student 
                          ? 'bg-blue-50 text-blue-700' 
                          : 'bg-emerald-50 text-emerald-700'
                      }`}>
                        {member.is_student ? 'Cadet' : 'Cadre'}
                      </span>
                    </div>
                  </div>
                ))
              )
            ) : (
              // Squadron roster view (grouped by flight)
              Object.entries(roster.flights || {}).map(([flight, members]) => (
                <div key={flight} className="p-4">
                  <h3 className="font-bold text-[#00205B] uppercase text-sm mb-3 flex items-center gap-2">
                    <Shield className="w-4 h-4" />
                    {getFlightLabel(flight)}
                    <span className="font-normal text-slate-400 ml-2">{members.length} members</span>
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {members.map((member) => (
                      <div 
                        key={member.id}
                        className="p-2 bg-slate-50 rounded-sm flex items-center gap-2 cursor-pointer hover:bg-slate-100 transition-colors"
                        onClick={() => openMemberDetail(member)}
                      >
                        <span className={`w-2 h-2 rounded-full ${member.is_student ? 'bg-blue-500' : 'bg-emerald-500'}`} />
                        <span className="text-sm truncate">{member.name}</span>
                        {member.position && (
                          <span className="text-xs text-slate-400 ml-auto truncate">{member.position}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Documents Tab */}
      {activeTab === 'documents' && (
        <div className="space-y-6">
          {/* Documents Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-3">
              <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                <SelectTrigger className="w-56 rounded-sm">
                  <Filter className="w-4 h-4 mr-2 text-slate-400" />
                  <SelectValue placeholder="Filter by category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
                    <SelectItem key={key} value={key}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            {['commander', 'executive_staff'].includes(user?.role) && (
              <Dialog open={isUploadModalOpen} onOpenChange={setIsUploadModalOpen}>
                <DialogTrigger asChild>
                  <Button className="bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="upload-document-btn">
                    <Upload className="w-4 h-4 mr-2" />
                    Upload Document
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-lg">
                  <DialogHeader>
                    <DialogTitle className="text-[#00205B] uppercase font-bold">Upload Document</DialogTitle>
                  </DialogHeader>
                  <form onSubmit={handleUploadDocument} className="space-y-4 mt-4">
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Title *</Label>
                      <Input
                        value={uploadForm.title}
                        onChange={(e) => setUploadForm({...uploadForm, title: e.target.value})}
                        required
                        className="mt-1 rounded-sm"
                        placeholder="Document title"
                      />
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Category *</Label>
                      <Select
                        value={uploadForm.category}
                        onValueChange={(v) => setUploadForm({...uploadForm, category: v, doc_type: v})}
                      >
                        <SelectTrigger className="mt-1 rounded-sm">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
                            <SelectItem key={key} value={key}>{label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Scope *</Label>
                      <Select
                        value={uploadForm.scope}
                        onValueChange={(v) => setUploadForm({...uploadForm, scope: v})}
                      >
                        <SelectTrigger className="mt-1 rounded-sm">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="flight">This Flight Only</SelectItem>
                          <SelectItem value="squadron">Entire Squadron</SelectItem>
                          <SelectItem value="global">All Flights (Global)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Description</Label>
                      <Input
                        value={uploadForm.description}
                        onChange={(e) => setUploadForm({...uploadForm, description: e.target.value})}
                        className="mt-1 rounded-sm"
                        placeholder="Brief description"
                      />
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">External Link (PDF, Google Doc, etc.)</Label>
                      <Input
                        type="url"
                        value={uploadForm.file_url}
                        onChange={(e) => setUploadForm({...uploadForm, file_url: e.target.value})}
                        className="mt-1 rounded-sm"
                        placeholder="https://..."
                      />
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Content (Optional)</Label>
                      <Textarea
                        value={uploadForm.content}
                        onChange={(e) => setUploadForm({...uploadForm, content: e.target.value})}
                        className="mt-1 rounded-sm"
                        rows={4}
                        placeholder="Enter document content or notes..."
                      />
                    </div>
                    <div className="flex justify-end gap-2 pt-2">
                      <Button type="button" variant="outline" onClick={() => setIsUploadModalOpen(false)}>Cancel</Button>
                      <Button type="submit" className="bg-[#00205B]">Upload Document</Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>
            )}
          </div>

          {/* Documents Grid */}
          {getDocumentCount() === 0 ? (
            <div className="bg-white border border-slate-200 rounded-sm p-12 text-center">
              <FileText className="w-16 h-16 mx-auto mb-4 text-slate-300" />
              <p className="text-lg text-slate-500">No documents available</p>
              <p className="text-sm text-slate-400 mt-2">Documents uploaded for this flight will appear here</p>
            </div>
          ) : (
            <div className="space-y-6">
              {Object.entries(getFilteredDocuments()).map(([category, docs]) => {
                if (!docs || docs.length === 0) return null;
                const CategoryIcon = CATEGORY_ICONS[category] || FileText;
                
                return (
                  <div key={category} className="bg-white border border-slate-200 rounded-sm">
                    <div className="border-b border-slate-100 p-4 flex items-center gap-2">
                      <CategoryIcon className="w-5 h-5 text-[#00205B]" />
                      <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm">
                        {CATEGORY_LABELS[category] || category}
                      </h2>
                      <span className="ml-auto text-xs text-slate-400">{docs.length} documents</span>
                    </div>
                    <div className="divide-y divide-slate-100">
                      {docs.map((doc) => (
                        <div 
                          key={doc.id}
                          className="p-4 hover:bg-slate-50 transition-colors flex items-start gap-4 group"
                        >
                          <div className="w-10 h-10 bg-slate-100 rounded-sm flex items-center justify-center flex-shrink-0">
                            <FileText className="w-5 h-5 text-slate-500" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-slate-900">{doc.title}</p>
                            {doc.description && (
                              <p className="text-sm text-slate-500 mt-0.5 line-clamp-2">{doc.description}</p>
                            )}
                            <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
                              {doc.scope && doc.scope !== 'global' && (
                                <span className="px-2 py-0.5 bg-slate-100 rounded-full">
                                  {doc.scope === 'flight' ? doc.flight?.toUpperCase() : doc.squadron?.toUpperCase()}
                                </span>
                              )}
                              {doc.scope === 'global' && (
                                <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">Global</span>
                              )}
                              {doc.version > 1 && (
                                <span>v{doc.version}</span>
                              )}
                              {doc.uploaded_by && (
                                <span>by {doc.uploaded_by}</span>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {doc.file_url && (
                              <a
                                href={doc.file_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="p-2 text-[#00205B] hover:bg-[#00205B]/10 rounded-sm transition-colors"
                              >
                                <ExternalLink className="w-4 h-4" />
                              </a>
                            )}
                            {['commander', 'executive_staff'].includes(user?.role) && (
                              <button
                                onClick={() => handleDeleteDocument(doc.id)}
                                className="p-2 text-red-500 hover:bg-red-50 rounded-sm transition-colors opacity-0 group-hover:opacity-100"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Points Tab */}
      {activeTab === 'points' && (
        <div className="space-y-6">
          {/* Flight Standing Card */}
          {flightStanding && (
            <div className="bg-gradient-to-r from-[#00205B] to-[#003087] text-white rounded-sm p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center">
                    <Trophy className="w-8 h-8 text-yellow-300" />
                  </div>
                  <div>
                    <p className="text-blue-200 text-sm uppercase tracking-wide">Flight Standing</p>
                    <p className="text-3xl font-black">{getFlightLabel(selectedFlight)}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-5xl font-black">#{flightStanding.rank}</p>
                  <p className="text-blue-200">{flightStanding.total_points.toFixed(0)} points</p>
                </div>
              </div>
            </div>
          )}

          {/* Cadets Point List */}
          <div className="bg-white border border-slate-200 rounded-sm">
            <div className="border-b border-slate-100 p-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Star className="w-5 h-5 text-yellow-500" />
                <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm">
                  Flight Cadets
                </h2>
                <span className="text-xs text-slate-400 ml-2">{flightCadets.length} cadets</span>
              </div>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={loadFlightPoints}
                className="rounded-sm"
              >
                <RefreshCw className="w-4 h-4 mr-1" />
                Refresh
              </Button>
            </div>
            
            {flightCadets.length === 0 ? (
              <div className="p-8 text-center text-slate-400">
                <Users className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>No cadets assigned to this flight</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {flightCadets
                  .sort((a, b) => (cadetPoints[b.id] || 0) - (cadetPoints[a.id] || 0))
                  .map((cadet, idx) => (
                  <div 
                    key={cadet.id}
                    className="p-4 hover:bg-slate-50 transition-colors flex items-center gap-4"
                  >
                    {/* Rank Badge */}
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                      idx === 0 ? 'bg-yellow-100 text-yellow-700' :
                      idx === 1 ? 'bg-slate-200 text-slate-700' :
                      idx === 2 ? 'bg-orange-100 text-orange-700' :
                      'bg-slate-100 text-slate-500'
                    }`}>
                      {idx + 1}
                    </div>
                    
                    {/* Cadet Info */}
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-slate-900 truncate">{cadet.name}</p>
                      <p className="text-xs text-slate-400">{cadet.rank}</p>
                    </div>
                    
                    {/* Points */}
                    <div className="text-right mr-4">
                      <p className="text-xl font-bold text-[#00205B]">
                        {(cadetPoints[cadet.id] || 0).toFixed(0)}
                      </p>
                      <p className="text-[10px] text-slate-400 uppercase">Points</p>
                    </div>
                    
                    {/* Quick Actions */}
                    <div className="flex gap-1">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleQuickMerit(cadet, 'merit')}
                        className="h-8 w-8 p-0 rounded-sm text-emerald-600 hover:bg-emerald-50 hover:text-emerald-700"
                        title="Give Merit"
                        data-testid={`merit-${cadet.id}`}
                      >
                        <Plus className="w-4 h-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleQuickMerit(cadet, 'demerit')}
                        className="h-8 w-8 p-0 rounded-sm text-red-500 hover:bg-red-50 hover:text-red-600"
                        title="Give Demerit"
                        data-testid={`demerit-${cadet.id}`}
                      >
                        <Minus className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent Activity */}
          {recentMerits.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-sm">
              <div className="border-b border-slate-100 p-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-[#00205B]" />
                <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm">
                  Recent Activity
                </h2>
              </div>
              <div className="divide-y divide-slate-100 max-h-[300px] overflow-y-auto">
                {recentMerits.map((merit) => {
                  const cadet = flightCadets.find(c => c.id === merit.participant_id);
                  return (
                    <div key={merit.id} className="p-3 flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                        merit.entry_type === 'merit' 
                          ? 'bg-emerald-100 text-emerald-600' 
                          : 'bg-red-100 text-red-600'
                      }`}>
                        {merit.entry_type === 'merit' ? <Plus className="w-4 h-4" /> : <Minus className="w-4 h-4" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">
                          {cadet?.name || 'Unknown'}
                        </p>
                        <p className="text-xs text-slate-400 truncate">{merit.reason}</p>
                      </div>
                      <div className={`text-sm font-bold ${
                        merit.entry_type === 'merit' ? 'text-emerald-600' : 'text-red-600'
                      }`}>
                        {merit.entry_type === 'merit' ? '+' : '-'}{merit.points}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Link to Full Point Tracker */}
          <div className="text-center">
            <a 
              href="/points" 
              className="inline-flex items-center gap-2 text-sm text-[#00205B] hover:underline"
            >
              <Award className="w-4 h-4" />
              View Full Point Tracker & Leaderboards
            </a>
          </div>
        </div>
      )}

      {/* Reports Tab */}
      {activeTab === 'reports' && (
        <div className="space-y-6">
          {/* Header with Actions */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <ClipboardList className="w-6 h-6 text-[#00205B]" />
              <div>
                <h2 className="font-bold uppercase tracking-tight text-[#00205B]">
                  Flight Reports
                </h2>
                <p className="text-xs text-slate-500">
                  {canViewAllFlights() 
                    ? (selectedFlight ? `Viewing ${getFlightLabel(selectedFlight)}` : 'All Flights (Exec View)')
                    : `Daily reports for ${getFlightLabel(selectedFlight)}`
                  }
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              {canReviewReports() && (
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setIsSettingsModalOpen(true)}
                  className="rounded-sm"
                >
                  <Settings className="w-4 h-4 mr-2" />
                  Deadline Settings
                </Button>
              )}
              
              {canSubmitReports() && (
                <Button 
                  onClick={() => {
                    // Set the auto-detected reporter role when opening the modal
                    setReportForm(prev => ({...prev, reporter_role: getAutoReporterRole()}));
                    setIsReportModalOpen(true);
                  }}
                  className="bg-[#00205B] hover:bg-[#00205B]/90 rounded-sm"
                  data-testid="new-report-btn"
                  disabled={canOnlySubmitOwnFlight() && selectedFlight !== user?.flight?.toLowerCase()}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Submit Report
                </Button>
              )}
            </div>
          </div>

          {/* Role restriction notice for cadre */}
          {canOnlySubmitOwnFlight() && selectedFlight !== user?.flight?.toLowerCase() && (
            <div className="bg-amber-50 border border-amber-200 rounded-sm p-3 flex items-center gap-3">
              <Shield className="w-5 h-5 text-amber-600" />
              <p className="text-sm text-amber-800">
                You can only submit reports for your assigned flight: <strong className="capitalize">{user?.flight}</strong>. 
                Switch to your flight to submit a report.
              </p>
            </div>
          )}

          {/* Exec Cadre notice - viewing all flights */}
          {canViewAllFlights() && !selectedFlight && (
            <div className="bg-blue-50 border border-blue-200 rounded-sm p-3 flex items-center gap-3">
              <Eye className="w-5 h-5 text-blue-600" />
              <p className="text-sm text-blue-800">
                As <strong className="capitalize">{user?.role?.replace('_', ' ')}</strong>, you can view reports from all flights. 
                Select a specific flight to filter, or view all below.
              </p>
            </div>
          )}

          {/* Report Deadline Info */}
          {reportSettings.is_enabled && (
            <div className="bg-slate-50 border border-slate-200 rounded-sm p-3 flex items-center gap-3">
              <Clock className="w-5 h-5 text-slate-600" />
              <p className="text-sm text-slate-700">
                Daily reports are due by <strong>{reportSettings.deadline_time}</strong>
              </p>
            </div>
          )}

          {/* Reports List */}
          <div className="bg-white border border-slate-200 rounded-sm">
            <div className="border-b border-slate-100 p-4 flex items-center justify-between">
              <h3 className="font-bold text-sm uppercase text-[#00205B]">
                Submitted Reports
              </h3>
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={loadReports}
                className="text-slate-500"
              >
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
            
            {reports.length === 0 ? (
              <div className="p-8 text-center text-slate-400">
                <ClipboardList className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No reports submitted yet</p>
                {canSubmitReports() && (
                  <p className="text-sm mt-2">Click "Submit Report" to create your first daily report</p>
                )}
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {reports.map(report => (
                  <div 
                    key={report.id} 
                    className="p-4 hover:bg-slate-50 transition-colors cursor-pointer"
                    onClick={() => { setSelectedReport(report); setIsViewReportModalOpen(true); }}
                    data-testid={`report-${report.id}`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-bold text-sm text-[#00205B]">
                            {new Date(report.report_date).toLocaleDateString('en-US', { 
                              weekday: 'short', 
                              month: 'short', 
                              day: 'numeric' 
                            })}
                          </span>
                          {getReportStatusBadge(report.status)}
                        </div>
                        <p className="text-sm text-slate-600">
                          Submitted by <span className="font-medium">{report.submitted_by_name}</span>
                          {' · '}
                          <span className="capitalize">{report.reporter_role.replace('_', ' ')}</span>
                        </p>
                        <p className="text-xs text-slate-400 mt-1">
                          {new Date(report.created_at).toLocaleString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {report.commander_issues?.has_issues && (
                          <span className="flex items-center gap-1 text-xs text-red-600 bg-red-50 px-2 py-1 rounded">
                            <AlertTriangle className="w-3 h-3" />
                            Cmd Issue
                          </span>
                        )}
                        <Eye className="w-4 h-4 text-slate-400" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Submit Report Modal */}
      <Dialog open={isReportModalOpen} onOpenChange={setIsReportModalOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-[#00205B] uppercase font-bold flex items-center gap-2">
              <ClipboardList className="w-5 h-5" />
              Submit Daily Report
            </DialogTitle>
          </DialogHeader>
          
          <form onSubmit={handleSubmitReport} className="space-y-6 mt-4">
            {/* Meta Info */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-600">Report Date *</Label>
                <Input
                  type="date"
                  value={reportForm.report_date}
                  onChange={(e) => setReportForm({...reportForm, report_date: e.target.value})}
                  className="mt-1 rounded-sm"
                  required
                />
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-600">Reporter Role *</Label>
                {canViewAllFlights() ? (
                  <Select
                    value={reportForm.reporter_role}
                    onValueChange={(v) => setReportForm({...reportForm, reporter_role: v})}
                  >
                    <SelectTrigger className="mt-1 rounded-sm">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {getAvailableReporterRoles().map(role => (
                        <SelectItem key={role.value} value={role.value}>{role.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <div className="mt-1 px-3 py-2 bg-slate-100 border border-slate-200 rounded-sm text-sm font-medium capitalize">
                    {getAutoReporterRole().replace(/_/g, ' ')}
                    <span className="text-xs text-slate-500 ml-2">(Auto-detected)</span>
                  </div>
                )}
              </div>
            </div>

            <div className="text-sm text-slate-500 bg-slate-50 p-3 rounded-sm">
              <strong>Flight:</strong> {getFlightLabel(selectedFlight)}
              {canOnlySubmitOwnFlight() && selectedFlight !== user?.flight?.toLowerCase() && (
                <span className="ml-2 text-amber-600 text-xs font-medium">
                  (You can only submit reports for your assigned flight: {user?.flight})
                </span>
              )}
              {' · '}
              <strong>Squadron:</strong> {allFlights.find(f => f.value === selectedFlight)?.squadron?.replace('_', ' ').toUpperCase() || 'N/A'}
            </div>

            {/* Report Sections */}
            <div className="space-y-4">
              {/* 1. Morale */}
              <div className="border border-slate-200 rounded-sm">
                <div className="bg-slate-50 p-3 border-b border-slate-200">
                  <h4 className="font-bold text-sm text-[#00205B]">1. Morale *</h4>
                  <p className="text-xs text-slate-500">Describe overall motivation and emotional tone. Identify reasons for high or low morale.</p>
                </div>
                <div className="p-3">
                  <Textarea
                    value={reportForm.morale.content}
                    onChange={(e) => setReportForm({
                      ...reportForm, 
                      morale: { ...reportForm.morale, content: e.target.value }
                    })}
                    className="rounded-sm"
                    rows={3}
                    placeholder="e.g., Morale was strong in the morning, but dipped during afternoon drill due to heat..."
                    required
                  />
                </div>
              </div>

              {/* 2. Safety Concerns */}
              <div className="border border-slate-200 rounded-sm">
                <div className="bg-slate-50 p-3 border-b border-slate-200 flex items-center justify-between">
                  <div>
                    <h4 className="font-bold text-sm text-[#00205B]">2. Safety Concerns</h4>
                    <p className="text-xs text-slate-500">Hazards, medical issues, environmental risks. Actions taken and unresolved risks.</p>
                  </div>
                  <label className="flex items-center gap-2 text-xs">
                    <input
                      type="checkbox"
                      checked={reportForm.safety_concerns.has_issues}
                      onChange={(e) => setReportForm({
                        ...reportForm,
                        safety_concerns: { ...reportForm.safety_concerns, has_issues: e.target.checked }
                      })}
                      className="rounded"
                    />
                    <span className="text-amber-600 font-medium">Has Issues</span>
                  </label>
                </div>
                <div className="p-3">
                  <Textarea
                    value={reportForm.safety_concerns.content}
                    onChange={(e) => setReportForm({
                      ...reportForm,
                      safety_concerns: { ...reportForm.safety_concerns, content: e.target.value }
                    })}
                    className="rounded-sm"
                    rows={2}
                    placeholder="e.g., Two heat stress incidents. Medical responded and monitored both cadets..."
                  />
                </div>
              </div>

              {/* 3. Discipline Issues */}
              <div className="border border-slate-200 rounded-sm">
                <div className="bg-slate-50 p-3 border-b border-slate-200 flex items-center justify-between">
                  <div>
                    <h4 className="font-bold text-sm text-[#00205B]">3. Discipline Issues</h4>
                    <p className="text-xs text-slate-500">Violations of standards, corrective actions, patterns or repeat offenders.</p>
                  </div>
                  <label className="flex items-center gap-2 text-xs">
                    <input
                      type="checkbox"
                      checked={reportForm.discipline_issues.has_issues}
                      onChange={(e) => setReportForm({
                        ...reportForm,
                        discipline_issues: { ...reportForm.discipline_issues, has_issues: e.target.checked }
                      })}
                      className="rounded"
                    />
                    <span className="text-amber-600 font-medium">Has Issues</span>
                  </label>
                </div>
                <div className="p-3">
                  <Textarea
                    value={reportForm.discipline_issues.content}
                    onChange={(e) => setReportForm({
                      ...reportForm,
                      discipline_issues: { ...reportForm.discipline_issues, content: e.target.value }
                    })}
                    className="rounded-sm"
                    rows={2}
                    placeholder="e.g., C/Amn J.R. repeatedly talked during instruction. Received verbal counseling..."
                  />
                </div>
              </div>

              {/* 4. Training Performance */}
              <div className="border border-slate-200 rounded-sm">
                <div className="bg-slate-50 p-3 border-b border-slate-200">
                  <h4 className="font-bold text-sm text-[#00205B]">4. Training Performance</h4>
                  <p className="text-xs text-slate-500">How well objectives were met, strengths/weaknesses, engagement level.</p>
                </div>
                <div className="p-3">
                  <Textarea
                    value={reportForm.training_performance.content}
                    onChange={(e) => setReportForm({
                      ...reportForm,
                      training_performance: { ...reportForm.training_performance, content: e.target.value }
                    })}
                    className="rounded-sm"
                    rows={2}
                    placeholder="e.g., Basics mastered basic facing movements. Need more practice on column movements..."
                  />
                </div>
              </div>

              {/* 5. Significant Events */}
              <div className="border border-slate-200 rounded-sm">
                <div className="bg-slate-50 p-3 border-b border-slate-200">
                  <h4 className="font-bold text-sm text-[#00205B]">5. Significant Events</h4>
                  <p className="text-xs text-slate-500">Important activities, visitors, disruptions, medical runs, weather delays, achievements.</p>
                </div>
                <div className="p-3">
                  <Textarea
                    value={reportForm.significant_events.content}
                    onChange={(e) => setReportForm({
                      ...reportForm,
                      significant_events: { ...reportForm.significant_events, content: e.target.value }
                    })}
                    className="rounded-sm"
                    rows={2}
                    placeholder="e.g., Wing Commander visited Bravo Flight during academics. One cadet sent to medical..."
                  />
                </div>
              </div>

              {/* 6. Recommendations */}
              <div className="border border-slate-200 rounded-sm">
                <div className="bg-slate-50 p-3 border-b border-slate-200">
                  <h4 className="font-bold text-sm text-[#00205B]">6. Recommendations</h4>
                  <p className="text-xs text-slate-500">Suggestions to improve safety, training, morale. Corrective measures, needed resources.</p>
                </div>
                <div className="p-3">
                  <Textarea
                    value={reportForm.recommendations.content}
                    onChange={(e) => setReportForm({
                      ...reportForm,
                      recommendations: { ...reportForm.recommendations, content: e.target.value }
                    })}
                    className="rounded-sm"
                    rows={2}
                    placeholder="e.g., Recommend shaded rest area near drill pad. Consider moving PT to early morning..."
                  />
                </div>
              </div>

              {/* 7. Commander Issue Items */}
              <div className="border-2 border-red-200 rounded-sm bg-red-50/30">
                <div className="bg-red-100 p-3 border-b border-red-200 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-red-600" />
                    <div>
                      <h4 className="font-bold text-sm text-red-700">7. Commander Issue Items</h4>
                      <p className="text-xs text-red-600">Items requiring escalation to higher authority. This is the most important section.</p>
                    </div>
                  </div>
                  <label className="flex items-center gap-2 text-xs">
                    <input
                      type="checkbox"
                      checked={reportForm.commander_issues.has_issues}
                      onChange={(e) => setReportForm({
                        ...reportForm,
                        commander_issues: { ...reportForm.commander_issues, has_issues: e.target.checked }
                      })}
                      className="rounded"
                    />
                    <span className="text-red-600 font-bold">ESCALATE</span>
                  </label>
                </div>
                <div className="p-3">
                  <Textarea
                    value={reportForm.commander_issues.content}
                    onChange={(e) => setReportForm({
                      ...reportForm,
                      commander_issues: { ...reportForm.commander_issues, content: e.target.value }
                    })}
                    className="rounded-sm border-red-200"
                    rows={2}
                    placeholder="e.g., Logistics cannot supply enough water coolers for barracks. Request support from Supply..."
                  />
                  <p className="text-xs text-red-500 mt-2">
                    Check "ESCALATE" if this report contains items beyond your authority that require command attention.
                  </p>
                </div>
              </div>
            </div>

            {/* Submit Actions */}
            <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
              <Button 
                type="button" 
                variant="outline" 
                onClick={() => { setIsReportModalOpen(false); resetReportForm(); }}
              >
                Cancel
              </Button>
              <Button type="submit" className="bg-[#00205B] hover:bg-[#00205B]/90">
                <Send className="w-4 h-4 mr-2" />
                Submit Report
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* View Report Modal */}
      <Dialog open={isViewReportModalOpen} onOpenChange={setIsViewReportModalOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-[#00205B] uppercase font-bold flex items-center gap-2">
              <ClipboardList className="w-5 h-5" />
              Flight Report Details
            </DialogTitle>
          </DialogHeader>
          
          {selectedReport && (
            <div className="space-y-4 mt-4">
              {/* Report Meta */}
              <div className="bg-slate-50 rounded-sm p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-slate-500">Report Date</p>
                    <p className="font-bold text-[#00205B]">
                      {new Date(selectedReport.report_date).toLocaleDateString('en-US', { 
                        weekday: 'long', 
                        year: 'numeric',
                        month: 'long', 
                        day: 'numeric' 
                      })}
                    </p>
                  </div>
                  {getReportStatusBadge(selectedReport.status, selectedReport.escalation_level)}
                </div>
                <div className="grid grid-cols-4 gap-4 pt-2 border-t border-slate-200">
                  <div>
                    <p className="text-xs text-slate-400 uppercase">Submitted By</p>
                    <p className="text-sm font-medium">{selectedReport.submitted_by_name}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 uppercase">Role</p>
                    <p className="text-sm font-medium capitalize">{selectedReport.reporter_role?.replace('_', ' ')}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 uppercase">Flight</p>
                    <p className="text-sm font-medium">{getFlightLabel(selectedReport.flight)}</p>
                  </div>
                  {selectedReport.escalation_level && (
                    <div>
                      <p className="text-xs text-slate-400 uppercase">Current Level</p>
                      <p className="text-sm font-medium text-amber-600">{getEscalationLabel(selectedReport.escalation_level)}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Escalation History */}
              {selectedReport.escalation_history && selectedReport.escalation_history.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-sm p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <History className="w-4 h-4 text-amber-600" />
                    <h4 className="font-bold text-sm text-amber-700">Escalation History</h4>
                  </div>
                  <div className="space-y-2">
                    {selectedReport.escalation_history.map((entry, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-sm">
                        <div className="w-2 h-2 bg-amber-500 rounded-full mt-1.5" />
                        <div>
                          {entry.action === 'resolved' ? (
                            <p className="text-emerald-700">
                              <strong>Resolved</strong> by {entry.resolved_by_name} on {new Date(entry.resolved_at).toLocaleString()}
                            </p>
                          ) : (
                            <p className="text-amber-700">
                              <strong>{getEscalationLabel(entry.from_level)}</strong> → <strong>{getEscalationLabel(entry.to_level)}</strong>
                              {' by '}{entry.escalated_by_name} on {new Date(entry.escalated_at).toLocaleString()}
                            </p>
                          )}
                          {entry.notes && <p className="text-slate-600 text-xs mt-0.5">"{entry.notes}"</p>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Report Sections */}
              <div className="space-y-3">
                {[
                  { key: 'morale', label: '1. Morale', color: 'blue' },
                  { key: 'safety_concerns', label: '2. Safety Concerns', color: 'amber' },
                  { key: 'discipline_issues', label: '3. Discipline Issues', color: 'orange' },
                  { key: 'training_performance', label: '4. Training Performance', color: 'teal' },
                  { key: 'significant_events', label: '5. Significant Events', color: 'purple' },
                  { key: 'recommendations', label: '6. Recommendations', color: 'indigo' },
                  { key: 'commander_issues', label: '7. Commander Issue Items', color: 'red' }
                ].map(section => {
                  const data = selectedReport[section.key];
                  if (!data?.content) return null;
                  return (
                    <div 
                      key={section.key} 
                      className={`border rounded-sm ${section.key === 'commander_issues' && data.has_issues ? 'border-red-300 bg-red-50' : 'border-slate-200'}`}
                    >
                      <div className={`px-3 py-2 border-b ${section.key === 'commander_issues' && data.has_issues ? 'bg-red-100 border-red-200' : 'bg-slate-50 border-slate-200'} flex items-center gap-2`}>
                        <h4 className={`font-bold text-sm ${section.key === 'commander_issues' && data.has_issues ? 'text-red-700' : 'text-[#00205B]'}`}>
                          {section.label}
                        </h4>
                        {data.has_issues && (
                          <span className="text-xs bg-red-600 text-white px-2 py-0.5 rounded">ISSUE FLAGGED</span>
                        )}
                      </div>
                      <div className="p-3">
                        <p className="text-sm text-slate-700 whitespace-pre-wrap">{data.content}</p>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Resolution Info */}
              {selectedReport.status === 'resolved' && selectedReport.reviewed_by && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-sm p-3">
                  <p className="text-sm text-emerald-700">
                    <CheckCircle2 className="w-4 h-4 inline mr-1" />
                    <strong>Resolved</strong> on {new Date(selectedReport.reviewed_at).toLocaleString()}
                  </p>
                  {selectedReport.review_notes && (
                    <p className="text-sm text-emerald-600 mt-1">{selectedReport.review_notes}</p>
                  )}
                </div>
              )}

              {/* Review Info (for non-escalated reports) */}
              {selectedReport.status === 'reviewed' && selectedReport.reviewed_by && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-sm p-3">
                  <p className="text-sm text-emerald-700">
                    <CheckCircle className="w-4 h-4 inline mr-1" />
                    Reviewed on {new Date(selectedReport.reviewed_at).toLocaleString()}
                  </p>
                  {selectedReport.review_notes && (
                    <p className="text-sm text-emerald-600 mt-1">{selectedReport.review_notes}</p>
                  )}
                </div>
              )}

              {/* Actions */}
              <div className="flex flex-wrap justify-end gap-3 pt-4 border-t border-slate-200">
                <Button variant="outline" onClick={() => setIsViewReportModalOpen(false)}>
                  Close
                </Button>
                
                {/* Regular review button for non-escalated reports */}
                {canReviewReports() && selectedReport.status === 'submitted' && (
                  <Button 
                    className="bg-emerald-600 hover:bg-emerald-700"
                    onClick={() => handleReviewReport(selectedReport.id)}
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Mark as Reviewed
                  </Button>
                )}

                {/* Escalation buttons for reports with commander issues - dynamic chain */}
                {canEscalateReports() && selectedReport.commander_issues?.has_issues && 
                 !['resolved', 'reviewed'].includes(selectedReport.status) && (
                  <>
                    {/* Dynamic escalation button based on current level */}
                    {getNextEscalationLevel(selectedReport.escalation_level) && (
                      <Button 
                        className={
                          selectedReport.escalation_level === 'dcs_commandant' ? 'bg-red-600 hover:bg-red-700' :
                          selectedReport.escalation_level === 'exec_cadre' ? 'bg-rose-600 hover:bg-rose-700' :
                          selectedReport.escalation_level === 'squadron_commander' ? 'bg-orange-600 hover:bg-orange-700' :
                          selectedReport.escalation_level === 'flight_commander' ? 'bg-amber-600 hover:bg-amber-700' :
                          'bg-yellow-600 hover:bg-yellow-700'
                        }
                        onClick={() => handleEscalateReport(
                          selectedReport.id, 
                          getNextEscalationLevel(selectedReport.escalation_level)
                        )}
                      >
                        <ArrowUpCircle className="w-4 h-4 mr-2" />
                        Escalate to {getEscalationLabel(getNextEscalationLevel(selectedReport.escalation_level))}
                      </Button>
                    )}
                  </>
                )}

                {/* Resolve button for escalated reports */}
                {canResolveReports() && 
                 ['escalated_flight_commander', 'escalated_squadron', 'escalated_exec', 'escalated_dcs', 'escalated_commander', 'at_commander'].includes(selectedReport.status) && (
                  <Button 
                    className="bg-emerald-600 hover:bg-emerald-700"
                    onClick={() => handleResolveReport(selectedReport.id)}
                  >
                    <CheckCircle2 className="w-4 h-4 mr-2" />
                    Mark as Resolved
                  </Button>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Deadline Settings Modal */}
      <Dialog open={isSettingsModalOpen} onOpenChange={setIsSettingsModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-[#00205B] uppercase font-bold flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Report Deadline Settings
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 mt-4">
            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-600">Daily Deadline Time</Label>
              <Input
                type="time"
                value={reportSettings.deadline_time}
                onChange={(e) => setReportSettings({...reportSettings, deadline_time: e.target.value})}
                className="mt-1 rounded-sm"
              />
              <p className="text-xs text-slate-400 mt-1">Reports should be submitted by this time daily</p>
            </div>
            
            <div className="flex items-center justify-between">
              <Label className="text-sm">Enable deadline reminders</Label>
              <input
                type="checkbox"
                checked={reportSettings.is_enabled}
                onChange={(e) => setReportSettings({...reportSettings, is_enabled: e.target.checked})}
                className="rounded"
              />
            </div>
            
            <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
              <Button variant="outline" onClick={() => setIsSettingsModalOpen(false)}>
                Cancel
              </Button>
              <Button className="bg-[#00205B]" onClick={handleSaveReportSettings}>
                Save Settings
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Merit/Demerit Modal */}
      <Dialog open={isMeritModalOpen} onOpenChange={setIsMeritModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-[#00205B] uppercase font-bold flex items-center gap-2">
              {meritForm.entry_type === 'merit' ? (
                <><Plus className="w-5 h-5 text-emerald-600" /> Give Merit</>
              ) : (
                <><Minus className="w-5 h-5 text-red-500" /> Give Demerit</>
              )}
            </DialogTitle>
          </DialogHeader>
          {selectedCadet && (
            <form onSubmit={handleSubmitMerit} className="space-y-4 mt-4">
              <div className="p-3 bg-slate-50 rounded-sm">
                <p className="text-sm text-slate-500">Cadet:</p>
                <p className="font-bold text-slate-900">{selectedCadet.name}</p>
              </div>
              
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-600">Type</Label>
                <Select
                  value={meritForm.entry_type}
                  onValueChange={(v) => setMeritForm({...meritForm, entry_type: v})}
                >
                  <SelectTrigger className="mt-1 rounded-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="merit">Merit (+)</SelectItem>
                    <SelectItem value="demerit">Demerit (-)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-600">Points</Label>
                <Input
                  type="number"
                  min="1"
                  max="100"
                  value={meritForm.points}
                  onChange={(e) => setMeritForm({...meritForm, points: e.target.value})}
                  className="mt-1 rounded-sm"
                  placeholder="5"
                  required
                />
              </div>
              
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-600">Reason *</Label>
                <Textarea
                  value={meritForm.reason}
                  onChange={(e) => setMeritForm({...meritForm, reason: e.target.value})}
                  className="mt-1 rounded-sm"
                  rows={2}
                  placeholder="Reason for this merit/demerit..."
                  required
                />
              </div>
              
              <div className="flex justify-end gap-2 pt-2">
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => {
                    setIsMeritModalOpen(false);
                    setSelectedCadet(null);
                  }}
                >
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  className={meritForm.entry_type === 'merit' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-red-600 hover:bg-red-700'}
                >
                  {meritForm.entry_type === 'merit' ? 'Award Merit' : 'Issue Demerit'}
                </Button>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>

      {/* ===== MEMBER DETAIL PANEL ===== */}
      <Dialog open={memberPanelOpen} onOpenChange={(o) => { if (!o) closeMemberDetail(); }}>
        <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
          {memberDetail && (
            <>
              <DialogHeader>
                <DialogTitle className="text-[#00205B] uppercase font-bold text-sm flex items-center gap-2">
                  <User className="w-4 h-4" /> Member Details
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4 mt-2">
                {/* Basic Info */}
                <div className="bg-slate-50 rounded-sm p-4 border border-slate-200">
                  <div className="flex items-center gap-3 mb-3">
                    <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                      memberDetail.is_student ? 'bg-blue-100 text-blue-600' : 'bg-emerald-100 text-emerald-600'
                    }`}>
                      {memberDetail.is_student ? <Star className="w-6 h-6" /> : <User className="w-6 h-6" />}
                    </div>
                    <div>
                      <div className="font-bold text-lg text-[#00205B]">{memberDetail.name}</div>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        memberDetail.is_student ? 'bg-blue-50 text-blue-700' : 'bg-emerald-50 text-emerald-700'
                      }`}>{memberDetail.is_student ? 'Cadet' : 'Cadre'}</span>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    {memberDetail.capid && (
                      <div><span className="text-slate-400 text-xs uppercase">CAPID</span><div className="font-mono">{memberDetail.capid}</div></div>
                    )}
                    {memberDetail.email && (
                      <div><span className="text-slate-400 text-xs uppercase">Email</span><div className="truncate flex items-center gap-1"><Mail className="w-3 h-3 text-slate-400" />{memberDetail.email}</div></div>
                    )}
                    {memberDetail.rank && (
                      <div><span className="text-slate-400 text-xs uppercase">Rank</span><div>{memberDetail.rank}</div></div>
                    )}
                    {memberDetail.position && (
                      <div><span className="text-slate-400 text-xs uppercase">Position</span><div>{memberDetail.position}</div></div>
                    )}
                    {memberDetail.flight && (
                      <div><span className="text-slate-400 text-xs uppercase">Flight</span><div className="capitalize">{memberDetail.flight}</div></div>
                    )}
                    {memberDetail.squadron && (
                      <div><span className="text-slate-400 text-xs uppercase">Squadron</span><div className="capitalize">{memberDetail.squadron}</div></div>
                    )}
                  </div>
                </div>

                {/* Health Services Section */}
                <div className="border border-slate-200 rounded-sm overflow-hidden" data-testid="health-alerts-section">
                  <div className="bg-red-50 px-4 py-2 flex items-center justify-between border-b border-red-100">
                    <div className="flex items-center gap-2">
                      <Heart className="w-4 h-4 text-red-500" />
                      <span className="font-bold text-sm text-red-800 uppercase tracking-wide">Health Alerts</span>
                    </div>
                    {canEditHealth && !editingAlerts && (
                      <Button size="sm" variant="ghost" className="h-7 text-xs text-red-600" onClick={() => setEditingAlerts(true)} data-testid="edit-health-btn">
                        <Edit2 className="w-3 h-3 mr-1" /> Edit
                      </Button>
                    )}
                  </div>
                  <div className="p-4">
                    {!editingAlerts ? (
                      /* View Mode */
                      <>
                        {(!memberAlerts?.alerts || memberAlerts.alerts.length === 0) ? (
                          <p className="text-sm text-slate-400 text-center py-3">No health alerts on file</p>
                        ) : (
                          <div className="space-y-2">
                            {memberAlerts.alerts.map(alert => {
                              const item = HEALTH_ALERT_ITEMS.find(h => h.key === alert.key);
                              return (
                                <div key={alert.key} className="flex items-start gap-2 bg-red-50/50 rounded p-2 border border-red-100">
                                  <AlertTriangle className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
                                  <div className="flex-1">
                                    <div className="font-medium text-sm text-red-800">{item?.label || alert.key}</div>
                                    {alert.details && <div className="text-xs text-red-600 mt-0.5">{alert.details}</div>}
                                    {canEditHealth && alert.shared_with && (
                                      <div className="flex gap-1 mt-1">
                                        {alert.shared_with.map(s => (
                                          <span key={s} className="text-[9px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 uppercase">
                                            {s.replace('_', ' ')}
                                          </span>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                        {memberAlerts?.notes && canEditHealth && (
                          <div className="mt-3 p-2 bg-amber-50 rounded border border-amber-100 text-xs text-amber-800">
                            <span className="font-bold">Internal Note:</span> {memberAlerts.notes}
                          </div>
                        )}
                        {(memberAlerts?.shared_notes || memberAlerts?.notes) && !canEditHealth && memberAlerts?.shared_notes && (
                          <div className="mt-3 p-2 bg-amber-50 rounded border border-amber-100 text-xs text-amber-800">
                            <span className="font-bold">Note:</span> {memberAlerts.shared_notes}
                          </div>
                        )}
                      </>
                    ) : (
                      /* Edit Mode (Health Services only) */
                      <div className="space-y-3">
                        <p className="text-xs text-slate-500">Select conditions and choose who can see each alert.</p>
                        {HEALTH_ALERT_ITEMS.map(item => {
                          const active = alertForm.alerts.find(a => a.key === item.key);
                          return (
                            <div key={item.key} className={`border rounded-sm p-3 ${active ? 'border-red-200 bg-red-50/30' : 'border-slate-200'}`}>
                              <div className="flex items-center gap-2">
                                <input
                                  type="checkbox"
                                  checked={!!active}
                                  onChange={() => toggleAlertItem(item.key)}
                                  className="accent-red-500"
                                  data-testid={`alert-check-${item.key}`}
                                />
                                <span className={`text-sm font-medium ${active ? 'text-red-800' : 'text-slate-600'}`}>{item.label}</span>
                              </div>
                              {active && (
                                <div className="mt-2 ml-6 space-y-2">
                                  <Input
                                    value={active.details || ''}
                                    onChange={(e) => updateAlertDetails(item.key, e.target.value)}
                                    placeholder="Additional details..."
                                    className="h-7 text-xs rounded-sm"
                                  />
                                  <div className="flex items-center gap-3">
                                    <span className="text-[10px] text-slate-500 uppercase">Share with:</span>
                                    {[
                                      { key: 'flight_commander', label: 'Flight Cmdr' },
                                      { key: 'squadron_commander', label: 'Sqdn Cmdr' },
                                      { key: 'exec_cadre', label: 'Exec Cadre' },
                                    ].map(level => (
                                      <label key={level.key} className="flex items-center gap-1 text-[10px]">
                                        <input
                                          type="checkbox"
                                          checked={(active.shared_with || []).includes(level.key)}
                                          onChange={() => updateAlertSharing(item.key, level.key)}
                                          className="accent-blue-500"
                                          data-testid={`share-${item.key}-${level.key}`}
                                        />
                                        <span className="text-slate-600">{level.label}</span>
                                      </label>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                        <div>
                          <Label className="text-xs">Internal Notes (Health Services only)</Label>
                          <Textarea
                            value={alertForm.notes}
                            onChange={(e) => setAlertForm(p => ({ ...p, notes: e.target.value }))}
                            rows={2} className="text-xs rounded-sm"
                            placeholder="Confidential notes..."
                          />
                        </div>
                        <div>
                          <Label className="text-xs">Shared Notes (visible to those with access)</Label>
                          <Textarea
                            value={alertForm.shared_notes || ''}
                            onChange={(e) => setAlertForm(p => ({ ...p, shared_notes: e.target.value }))}
                            rows={2} className="text-xs rounded-sm"
                            placeholder="Notes shared with flight/squadron commanders..."
                          />
                        </div>
                        <div className="flex justify-end gap-2 pt-1">
                          <Button variant="outline" size="sm" onClick={() => setEditingAlerts(false)} className="rounded-sm">Cancel</Button>
                          <Button size="sm" className="bg-red-600 hover:bg-red-700 rounded-sm" onClick={saveHealthAlerts} data-testid="save-health-btn">Save Health Alerts</Button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MyFlightPage;
