import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  getHealthDashboardSummary, getMedsDue, getOverdueMeds, getOpenIncidents,
  searchHealthCadets, getHealthReferenceLists, getHealthAuditLog, 
  getHealthSettings, updateHealthSettings, importMedicalData, getImportSummary
} from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { 
  Heart, Pill, AlertTriangle, Clock, Search, Users, Activity,
  CheckCircle, XCircle, AlertCircle, ChevronRight, RefreshCw,
  Thermometer, Filter, Save, Upload, FileSpreadsheet
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const HealthServicesDashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [medsDue, setMedsDue] = useState([]);
  const [overdueMeds, setOverdueMeds] = useState([]);
  const [openIncidents, setOpenIncidents] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchFilters, setSearchFilters] = useState({
    squadron: 'all',
    flight: 'all',
    hasMedication: null,
    hasIncident: null
  });
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [referenceLists, setReferenceLists] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  
  // Audit Log Modal
  const [showAuditLog, setShowAuditLog] = useState(false);
  const [auditLog, setAuditLog] = useState([]);
  const [loadingAudit, setLoadingAudit] = useState(false);
  
  // Settings Modal
  const [showSettings, setShowSettings] = useState(false);
  const [eventSettings, setEventSettings] = useState({
    event_id: '',
    event_year: new Date().getFullYear(),
    event_name: ''
  });
  const [savingSettings, setSavingSettings] = useState(false);

  // Import Modal
  const [showImport, setShowImport] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [importSummary, setImportSummary] = useState(null);

  // Check if user has full health access
  const hasFullAccess = () => {
    return ['commander', 'health_services'].includes(user?.role);
  };

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [summaryData, dueData, overdueData, incidentsData, refData, impSummary] = await Promise.all([
        getHealthDashboardSummary(),
        hasFullAccess() ? getMedsDue(60) : Promise.resolve([]),
        hasFullAccess() ? getOverdueMeds() : Promise.resolve([]),
        getOpenIncidents(),
        getHealthReferenceLists(),
        hasFullAccess() ? getImportSummary().catch(() => null) : Promise.resolve(null)
      ]);
      
      setSummary(summaryData);
      setMedsDue(dueData);
      setOverdueMeds(overdueData);
      setOpenIncidents(incidentsData);
      setReferenceLists(refData);
      if (impSummary) setImportSummary(impSummary);
    } catch (error) {
      console.error('Failed to load dashboard:', error);
      toast.error('Failed to load health services data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
    
    // Auto-refresh every 2 minutes
    let interval;
    if (autoRefresh) {
      interval = setInterval(loadDashboardData, 120000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  // Load audit log
  const loadAuditLog = async () => {
    try {
      setLoadingAudit(true);
      const logs = await getHealthAuditLog(100);
      setAuditLog(logs);
    } catch (error) {
      toast.error('Failed to load audit log');
    } finally {
      setLoadingAudit(false);
    }
  };

  // Load and save settings
  const loadSettings = async () => {
    try {
      const settings = await getHealthSettings();
      setEventSettings({
        event_id: settings.event_id || '',
        event_year: settings.event_year || new Date().getFullYear(),
        event_name: settings.event_name || ''
      });
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  };

  const saveSettings = async () => {
    try {
      setSavingSettings(true);
      await updateHealthSettings(eventSettings);
      toast.success('Settings saved');
      setShowSettings(false);
      loadDashboardData();
    } catch (error) {
      toast.error('Failed to save settings');
    } finally {
      setSavingSettings(false);
    }
  };

  // Load audit log when modal opens
  useEffect(() => {
    if (showAuditLog) {
      loadAuditLog();
    }
  }, [showAuditLog]);

  // Load settings when modal opens
  useEffect(() => {
    if (showSettings) {
      loadSettings();
    }
  }, [showSettings]);

  const handleImportFile = async () => {
    if (!importFile) return;
    try {
      setImporting(true);
      setImportResult(null);
      const result = await importMedicalData(importFile);
      setImportResult(result);
      toast.success(`Imported ${result.imported || 0} records successfully`);
      loadDashboardData();
    } catch (error) {
      const detail = error.response?.data?.detail || 'Import failed';
      toast.error(detail);
      setImportResult({ error: detail });
    } finally {
      setImporting(false);
    }
  };

  const handleSearch = async () => {
    try {
      const results = await searchHealthCadets(
        searchQuery || null,
        searchFilters.squadron !== 'all' ? searchFilters.squadron : null,
        searchFilters.flight !== 'all' ? searchFilters.flight : null,
        searchFilters.hasMedication,
        searchFilters.hasIncident
      );
      setSearchResults(results);
      setShowSearchResults(true);
    } catch (error) {
      toast.error('Search failed');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'due': return 'bg-amber-100 text-amber-700 border-amber-200';
      case 'overdue': return 'bg-red-100 text-red-700 border-red-200';
      case 'open': return 'bg-red-100 text-red-700';
      case 'monitoring': return 'bg-amber-100 text-amber-700';
      case 'escalated': return 'bg-red-200 text-red-800';
      default: return 'bg-slate-100 text-slate-600';
    }
  };

  const formatTime = (timeStr) => {
    if (!timeStr || timeStr.length < 4) return timeStr;
    return `${timeStr.slice(0, 2)}:${timeStr.slice(2, 4)}`;
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 flex items-center justify-center min-h-[400px]">
        <div className="flex items-center gap-3 text-slate-500">
          <RefreshCw className="w-5 h-5 animate-spin" />
          <span>Loading Health Services Dashboard...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl lg:text-3xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
            <Heart className="inline w-8 h-8 mr-2 text-red-500" />
            Health Services
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            {summary?.event_name || 'Encampment Health Management'}
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          {hasFullAccess() && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => { setShowImport(true); setImportFile(null); setImportResult(null); }}
              className="rounded-sm"
              data-testid="import-medical-data-btn"
            >
              <Upload className="w-4 h-4 mr-2" />
              Import Medical Data
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={loadDashboardData}
            className="rounded-sm"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input 
              type="checkbox" 
              checked={autoRefresh} 
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            Auto-refresh
          </label>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
        <div className="bg-white border border-slate-200 rounded-sm p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Tracked</p>
              <p className="text-2xl font-bold text-[#00205B]">{summary?.total_cadets_tracked || 0}</p>
            </div>
            <Users className="w-5 h-5 text-[#00205B]" />
          </div>
        </div>
        
        <div className="bg-white border border-slate-200 rounded-sm p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">On Meds</p>
              <p className="text-2xl font-bold text-blue-600">{summary?.cadets_with_medications || 0}</p>
            </div>
            <Pill className="w-5 h-5 text-blue-500" />
          </div>
        </div>
        
        <div className="bg-white border border-slate-200 rounded-sm p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Rescue Meds</p>
              <p className="text-2xl font-bold text-orange-600">{summary?.cadets_with_rescue_meds || 0}</p>
            </div>
            <AlertTriangle className="w-5 h-5 text-orange-500" />
          </div>
        </div>
        
        {hasFullAccess() && (
          <div className={`bg-white border rounded-sm p-4 ${summary?.meds_due_now > 0 ? 'border-amber-300 bg-amber-50' : 'border-slate-200'}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Meds Due</p>
                <p className={`text-2xl font-bold ${summary?.meds_due_now > 0 ? 'text-amber-600' : 'text-slate-600'}`}>
                  {summary?.meds_due_now || 0}
                </p>
              </div>
              <Clock className="w-5 h-5 text-amber-500" />
            </div>
          </div>
        )}
        
        {hasFullAccess() && (
          <div className={`bg-white border rounded-sm p-4 ${summary?.overdue_meds > 0 ? 'border-red-300 bg-red-50' : 'border-slate-200'}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Overdue</p>
                <p className={`text-2xl font-bold ${summary?.overdue_meds > 0 ? 'text-red-600' : 'text-slate-600'}`}>
                  {summary?.overdue_meds || 0}
                </p>
              </div>
              <XCircle className="w-5 h-5 text-red-500" />
            </div>
          </div>
        )}
        
        <div className={`bg-white border rounded-sm p-4 ${summary?.open_incidents > 0 ? 'border-red-300 bg-red-50' : 'border-slate-200'}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Incidents</p>
              <p className={`text-2xl font-bold ${summary?.open_incidents > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                {summary?.open_incidents || 0}
              </p>
            </div>
            <Activity className="w-5 h-5 text-red-500" />
          </div>
        </div>
      </div>

      {/* Import Data Summary */}
      {importSummary && (importSummary.allergy_records > 0 || importSummary.otc_records > 0) && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white border border-slate-200 rounded-sm p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Allergy Records</p>
                <p className="text-2xl font-bold text-rose-600">{importSummary.allergy_records}</p>
                <p className="text-xs text-slate-400">{importSummary.cadets_with_allergies} cadets</p>
              </div>
              <AlertTriangle className="w-5 h-5 text-rose-500" />
            </div>
          </div>
          <div className="bg-white border border-slate-200 rounded-sm p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">OTC Approvals</p>
                <p className="text-2xl font-bold text-teal-600">{importSummary.otc_records}</p>
                <p className="text-xs text-slate-400">{importSummary.otc_with_approvals} approved</p>
              </div>
              <FileSpreadsheet className="w-5 h-5 text-teal-500" />
            </div>
          </div>
        </div>
      )}

      {/* Search Section */}
      <div className="bg-white border border-slate-200 rounded-sm p-4 mb-6">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search by name, CAPID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="pl-10 rounded-sm"
            />
          </div>
          
          <div className="flex items-center gap-2 flex-wrap">
            <Select value={searchFilters.squadron} onValueChange={(v) => setSearchFilters({...searchFilters, squadron: v})}>
              <SelectTrigger className="w-32 rounded-sm">
                <SelectValue placeholder="Squadron" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Squadrons</SelectItem>
                {referenceLists?.squadrons?.map(sq => (
                  <SelectItem key={sq} value={sq}>{sq}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            <Select value={searchFilters.flight} onValueChange={(v) => setSearchFilters({...searchFilters, flight: v})}>
              <SelectTrigger className="w-32 rounded-sm">
                <SelectValue placeholder="Flight" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Flights</SelectItem>
                {referenceLists?.flights?.map(fl => (
                  <SelectItem key={fl} value={fl}>{fl}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            <Button onClick={handleSearch} className="bg-[#00205B] hover:bg-[#001540] rounded-sm">
              <Search className="w-4 h-4 mr-2" />
              Search
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Meds Due Now - Only for full access */}
        {hasFullAccess() && (
          <div className="bg-white border border-slate-200 rounded-sm">
            <div className="p-4 border-b border-slate-200 flex items-center justify-between">
              <h2 className="font-bold text-[#00205B] uppercase text-sm flex items-center gap-2">
                <Clock className="w-4 h-4 text-amber-500" />
                Medications Due (Next Hour)
              </h2>
              <span className="text-xs text-slate-500">{medsDue.length} items</span>
            </div>
            <div className="max-h-80 overflow-y-auto">
              {medsDue.length === 0 ? (
                <div className="p-8 text-center text-slate-500">
                  <CheckCircle className="w-8 h-8 mx-auto mb-2 text-emerald-500" />
                  <p>No medications due in the next hour</p>
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {medsDue.map((med, idx) => (
                    <div 
                      key={idx} 
                      className={`p-3 hover:bg-slate-50 cursor-pointer ${med.status === 'overdue' ? 'bg-red-50' : ''}`}
                      onClick={() => navigate(`/roster?cadet=${med.cadet_id_internal}`)}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-medium text-sm">{med.cadet_name || med.capid}</p>
                          <p className="text-xs text-slate-500">{med.flight} • {med.squadron}</p>
                        </div>
                        <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(med.status)}`}>
                          {formatTime(med.time_due)}
                        </span>
                      </div>
                      <div className="mt-1 flex items-center gap-2">
                        <Pill className="w-3 h-3 text-blue-500" />
                        <span className="text-sm">{med.medication_name} - {med.dose}</span>
                        {med.rescue_med && (
                          <span className="text-[10px] px-1.5 py-0.5 bg-orange-100 text-orange-700 rounded font-medium">
                            RESCUE
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Overdue Meds - Only for full access */}
        {hasFullAccess() && overdueMeds.length > 0 && (
          <div className="bg-white border border-red-200 rounded-sm">
            <div className="p-4 border-b border-red-200 bg-red-50 flex items-center justify-between">
              <h2 className="font-bold text-red-700 uppercase text-sm flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Overdue Medications
              </h2>
              <span className="text-xs text-red-600 font-bold">{overdueMeds.length} OVERDUE</span>
            </div>
            <div className="max-h-80 overflow-y-auto">
              <div className="divide-y divide-red-100">
                {overdueMeds.map((med, idx) => (
                  <div 
                    key={idx} 
                    className="p-3 hover:bg-red-50 cursor-pointer bg-red-50/50"
                    onClick={() => navigate(`/roster?cadet=${med.cadet_id_internal}`)}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-medium text-sm text-red-800">{med.cadet_name || med.capid}</p>
                        <p className="text-xs text-red-600">{med.flight} • {med.squadron}</p>
                      </div>
                      <span className="text-xs px-2 py-0.5 rounded bg-red-200 text-red-800 font-medium">
                        {med.minutes_overdue}m overdue
                      </span>
                    </div>
                    <div className="mt-1 flex items-center gap-2">
                      <Pill className="w-3 h-3 text-red-500" />
                      <span className="text-sm text-red-700">{med.medication_name} - {med.dose}</span>
                      <span className="text-xs text-red-600">Due: {formatTime(med.time_due)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Open Incidents */}
        <div className={`bg-white border rounded-sm ${openIncidents.length > 0 ? 'border-amber-200' : 'border-slate-200'}`}>
          <div className={`p-4 border-b flex items-center justify-between ${openIncidents.length > 0 ? 'border-amber-200 bg-amber-50' : 'border-slate-200'}`}>
            <h2 className={`font-bold uppercase text-sm flex items-center gap-2 ${openIncidents.length > 0 ? 'text-amber-700' : 'text-[#00205B]'}`}>
              <Activity className="w-4 h-4" />
              Open Incidents
            </h2>
            <span className="text-xs text-slate-500">{openIncidents.length} active</span>
          </div>
          <div className="max-h-80 overflow-y-auto">
            {openIncidents.length === 0 ? (
              <div className="p-8 text-center text-slate-500">
                <CheckCircle className="w-8 h-8 mx-auto mb-2 text-emerald-500" />
                <p>No open incidents</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {openIncidents.map((inc, idx) => (
                  <div 
                    key={idx} 
                    className="p-3 hover:bg-slate-50 cursor-pointer"
                    onClick={() => navigate(`/roster?cadet=${inc.cadet_id_internal}`)}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-medium text-sm">{inc.cadet_name || inc.capid}</p>
                        <p className="text-xs text-slate-500">{inc.incident_date} at {inc.incident_time}</p>
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(inc.resolution_status)}`}>
                        {inc.resolution_status}
                      </span>
                    </div>
                    <div className="mt-1">
                      <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 rounded mr-2">
                        {inc.incident_type?.replace('_', ' ')}
                      </span>
                      <span className="text-sm text-slate-600 line-clamp-1">{inc.description}</span>
                    </div>
                    {inc.parent_contacted && (
                      <span className="text-[10px] text-amber-600 mt-1 block">Parent contacted</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Quick Links */}
        <div className="bg-white border border-slate-200 rounded-sm">
          <div className="p-4 border-b border-slate-200">
            <h2 className="font-bold text-[#00205B] uppercase text-sm">Quick Actions</h2>
          </div>
          <div className="p-4 space-y-2">
            <Button 
              variant="outline" 
              className="w-full justify-between rounded-sm"
              onClick={() => navigate('/roster')}
            >
              <span className="flex items-center gap-2">
                <Users className="w-4 h-4" />
                View Roster / Add Health Data
              </span>
              <ChevronRight className="w-4 h-4" />
            </Button>
            {hasFullAccess() && (
              <>
                <Button 
                  variant="outline" 
                  className="w-full justify-between rounded-sm"
                  onClick={() => { setShowImport(true); setImportFile(null); setImportResult(null); }}
                  data-testid="quick-action-import"
                >
                  <span className="flex items-center gap-2">
                    <Upload className="w-4 h-4" />
                    Import Medical Data (Excel)
                  </span>
                  <ChevronRight className="w-4 h-4" />
                </Button>
                <Button 
                  variant="outline" 
                  className="w-full justify-between rounded-sm"
                  onClick={() => setShowAuditLog(true)}
                >
                  <span className="flex items-center gap-2">
                    <Filter className="w-4 h-4" />
                    View Audit Log
                  </span>
                  <ChevronRight className="w-4 h-4" />
                </Button>
                <Button 
                  variant="outline" 
                  className="w-full justify-between rounded-sm"
                  onClick={() => setShowSettings(true)}
                >
                  <span className="flex items-center gap-2">
                    <Thermometer className="w-4 h-4" />
                    Event Settings
                  </span>
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Search Results Modal */}
      <Dialog open={showSearchResults} onOpenChange={setShowSearchResults}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-[#00205B] uppercase font-bold">
              Search Results ({searchResults.length})
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-2 mt-4">
            {searchResults.length === 0 ? (
              <p className="text-center text-slate-500 py-8">No cadets found matching your search</p>
            ) : (
              searchResults.map((cadet) => (
                <div 
                  key={cadet.cadet_id}
                  className="p-3 border border-slate-200 rounded-sm hover:bg-slate-50 cursor-pointer"
                  onClick={() => {
                    setShowSearchResults(false);
                    navigate(`/roster?cadet=${cadet.cadet_id}`);
                  }}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">{cadet.name}</p>
                      <p className="text-xs text-slate-500">CAPID: {cadet.capid} • {cadet.flight} • {cadet.squadron}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {cadet.has_medication && (
                        <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                          <Pill className="w-3 h-3 inline mr-1" />
                          Medications
                        </span>
                      )}
                      {cadet.has_open_incident && (
                        <span className="text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded">
                          <AlertCircle className="w-3 h-3 inline mr-1" />
                          Incident
                        </span>
                      )}
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        cadet.hs_status === 'cleared' ? 'bg-emerald-100 text-emerald-700' :
                        cadet.hs_status === 'medical_hold' ? 'bg-red-100 text-red-700' :
                        'bg-amber-100 text-amber-700'
                      }`}>
                        {cadet.hs_status?.replace('_', ' ')}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Audit Log Modal */}
      <Dialog open={showAuditLog} onOpenChange={setShowAuditLog}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-[#00205B] uppercase font-bold">
              Health Services Audit Log
            </DialogTitle>
          </DialogHeader>
          <div className="mt-4">
            {loadingAudit ? (
              <div className="flex items-center justify-center py-8">
                <RefreshCw className="w-5 h-5 animate-spin text-slate-400" />
              </div>
            ) : auditLog.length === 0 ? (
              <p className="text-center text-slate-500 py-8">No audit entries yet</p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {auditLog.map((log, idx) => (
                  <div key={idx} className="p-3 border border-slate-200 rounded-sm text-sm">
                    <div className="flex justify-between items-start">
                      <div>
                        <span className={`text-xs px-2 py-0.5 rounded mr-2 ${
                          log.action_type === 'CREATE' ? 'bg-emerald-100 text-emerald-700' :
                          log.action_type === 'UPDATE' ? 'bg-blue-100 text-blue-700' :
                          log.action_type === 'DELETE' ? 'bg-red-100 text-red-700' :
                          'bg-slate-100 text-slate-600'
                        }`}>
                          {log.action_type}
                        </span>
                        <span className="text-xs text-slate-500">{log.table_name}</span>
                      </div>
                      <span className="text-xs text-slate-400">
                        {new Date(log.changed_at).toLocaleString()}
                      </span>
                    </div>
                    {log.field_changed && (
                      <p className="text-xs mt-1">
                        <span className="text-slate-500">Field:</span> {log.field_changed}
                        {log.old_value && <span className="text-red-500 ml-2">"{log.old_value}"</span>}
                        {log.new_value && <span className="text-emerald-500 ml-1">→ "{log.new_value}"</span>}
                      </p>
                    )}
                    <p className="text-xs text-slate-400 mt-1">By: {log.changed_by || 'System'}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Settings Modal */}
      <Dialog open={showSettings} onOpenChange={setShowSettings}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-[#00205B] uppercase font-bold">
              Health Services Event Settings
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div>
              <Label className="text-xs">Event ID</Label>
              <Input 
                value={eventSettings.event_id}
                onChange={(e) => setEventSettings({...eventSettings, event_id: e.target.value})}
                placeholder="e.g., 2026_TN_ENCAMPMENT"
                className="rounded-sm"
              />
              <p className="text-xs text-slate-500 mt-1">Unique identifier for this encampment</p>
            </div>
            <div>
              <Label className="text-xs">Event Year</Label>
              <Input 
                type="number"
                value={eventSettings.event_year}
                onChange={(e) => setEventSettings({...eventSettings, event_year: parseInt(e.target.value)})}
                className="rounded-sm"
              />
            </div>
            <div>
              <Label className="text-xs">Event Name</Label>
              <Input 
                value={eventSettings.event_name}
                onChange={(e) => setEventSettings({...eventSettings, event_name: e.target.value})}
                placeholder="e.g., Tennessee Wing Encampment 2026"
                className="rounded-sm"
              />
            </div>
            <div className="flex justify-end gap-2 pt-4">
              <Button variant="outline" onClick={() => setShowSettings(false)}>Cancel</Button>
              <Button 
                onClick={saveSettings} 
                disabled={savingSettings}
                className="bg-[#00205B]"
              >
                {savingSettings ? <RefreshCw className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
                Save Settings
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Import Medical Data Modal */}
      <Dialog open={showImport} onOpenChange={(open) => { setShowImport(open); if (!open) { setImportFile(null); setImportResult(null); } }}>
        <DialogContent className="max-w-lg" data-testid="import-medical-data-modal">
          <DialogHeader>
            <DialogTitle className="text-[#00205B] uppercase font-bold">
              <Upload className="w-5 h-5 inline mr-2" />
              Import Medical Data
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div className="bg-blue-50 border border-blue-200 rounded-sm p-3 text-sm">
              <p className="font-medium text-blue-800 mb-1">Supported CAP Reports:</p>
              <ul className="text-blue-700 text-xs space-y-1 list-disc list-inside">
                <li><strong>Allergies Report</strong> (.xlsx) - Imports allergy data per cadet</li>
                <li><strong>OTC Medication Approvals Report</strong> (.xlsx) - Imports OTC approvals per cadet</li>
              </ul>
              <p className="text-blue-600 text-xs mt-2">Data is matched to roster participants by CAPID.</p>
            </div>
            
            <div>
              <Label className="text-xs mb-2 block">Select Excel File (.xlsx)</Label>
              <div className="border-2 border-dashed border-slate-300 rounded-sm p-6 text-center hover:border-[#00205B] transition-colors">
                <input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={(e) => { setImportFile(e.target.files[0]); setImportResult(null); }}
                  className="hidden"
                  id="medical-file-input"
                  data-testid="medical-file-input"
                />
                <label htmlFor="medical-file-input" className="cursor-pointer">
                  <FileSpreadsheet className="w-10 h-10 mx-auto mb-2 text-slate-400" />
                  {importFile ? (
                    <p className="text-sm font-medium text-[#00205B]">{importFile.name}</p>
                  ) : (
                    <p className="text-sm text-slate-500">Click to select a file</p>
                  )}
                </label>
              </div>
            </div>

            {importResult && !importResult.error && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-sm p-3" data-testid="import-result">
                <p className="font-medium text-emerald-800 text-sm mb-1">
                  <CheckCircle className="w-4 h-4 inline mr-1" />
                  Import Complete - {importResult.type === 'allergies' ? 'Allergies Report' : 'OTC Approvals'}
                </p>
                <div className="text-xs text-emerald-700 space-y-0.5">
                  <p>Total rows processed: {importResult.total_rows}</p>
                  <p>Records imported: {importResult.imported}</p>
                  {importResult.updated > 0 && <p>Records updated: {importResult.updated}</p>}
                  <p>Skipped (duplicates/empty): {importResult.skipped}</p>
                  {importResult.unique_cadets && <p>Unique cadets: {importResult.unique_cadets}</p>}
                </div>
              </div>
            )}

            {importResult?.error && (
              <div className="bg-red-50 border border-red-200 rounded-sm p-3">
                <p className="text-sm text-red-700">
                  <XCircle className="w-4 h-4 inline mr-1" />
                  {importResult.error}
                </p>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={() => setShowImport(false)}>
                {importResult ? 'Close' : 'Cancel'}
              </Button>
              {!importResult && (
                <Button 
                  onClick={handleImportFile} 
                  disabled={!importFile || importing}
                  className="bg-[#00205B]"
                  data-testid="import-submit-btn"
                >
                  {importing ? <RefreshCw className="w-4 h-4 animate-spin mr-2" /> : <Upload className="w-4 h-4 mr-2" />}
                  {importing ? 'Importing...' : 'Import Data'}
                </Button>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default HealthServicesDashboard;
