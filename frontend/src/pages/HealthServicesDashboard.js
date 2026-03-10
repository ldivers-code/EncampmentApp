import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  getHealthDashboardSummary, getMedsDue, getOverdueMeds, getOpenIncidents,
  searchHealthCadets, getHealthReferenceLists
} from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { 
  Heart, Pill, AlertTriangle, Clock, Search, Users, Activity,
  CheckCircle, XCircle, AlertCircle, ChevronRight, RefreshCw,
  Thermometer, Filter
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

  // Check if user has full health access
  const hasFullAccess = () => {
    return ['commander', 'health_services'].includes(user?.role);
  };

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [summaryData, dueData, overdueData, incidentsData, refData] = await Promise.all([
        getHealthDashboardSummary(),
        hasFullAccess() ? getMedsDue(60) : Promise.resolve([]),
        hasFullAccess() ? getOverdueMeds() : Promise.resolve([]),
        getOpenIncidents(),
        getHealthReferenceLists()
      ]);
      
      setSummary(summaryData);
      setMedsDue(dueData);
      setOverdueMeds(overdueData);
      setOpenIncidents(incidentsData);
      setReferenceLists(refData);
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
              onClick={() => navigate('/health/reports')}
            >
              <span className="flex items-center gap-2">
                <Activity className="w-4 h-4" />
                Historical Reports
              </span>
              <ChevronRight className="w-4 h-4" />
            </Button>
            {hasFullAccess() && (
              <>
                <Button 
                  variant="outline" 
                  className="w-full justify-between rounded-sm"
                  onClick={() => navigate('/health/audit')}
                >
                  <span className="flex items-center gap-2">
                    <Filter className="w-4 h-4" />
                    Audit Log
                  </span>
                  <ChevronRight className="w-4 h-4" />
                </Button>
                <Button 
                  variant="outline" 
                  className="w-full justify-between rounded-sm"
                  onClick={() => navigate('/health/settings')}
                >
                  <span className="flex items-center gap-2">
                    <Thermometer className="w-4 h-4" />
                    Health Settings
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
    </div>
  );
};

export default HealthServicesDashboard;
