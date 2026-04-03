import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  getCadetHealthSummary, getCadetMedications, getCadetMedicationLog,
  getCadetIncidents, getCadetCustodyLog, createCadetMedication,
  logMedicationAdministration, logCadetIncident, logCustodyAction,
  updateIncidentStatus, updateCadetHealthStatus, deactivateMedication,
  getHealthReferenceLists, getCadetAllergies, getCadetOtcApprovals
} from '../services/api';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import {
  Heart, Pill, AlertTriangle, Clock, Plus, CheckCircle, XCircle,
  Activity, Package, History, RefreshCw, Thermometer,
  AlertCircle, ChevronDown, ChevronUp
} from 'lucide-react';
import MedicationFormDialog from './health/MedicationFormDialog';
import AdminLogFormDialog from './health/AdminLogFormDialog';
import IncidentFormDialog from './health/IncidentFormDialog';
import CustodyFormDialog from './health/CustodyFormDialog';

const CadetHealthSection = ({ cadetId, capid, cadetName }) => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [medications, setMedications] = useState([]);
  const [medicationLog, setMedicationLog] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [custodyLog, setCustodyLog] = useState([]);
  const [referenceLists, setReferenceLists] = useState(null);
  const [activeTab, setActiveTab] = useState('summary');
  const [expanded, setExpanded] = useState(true);
  const [allergies, setAllergies] = useState([]);
  const [otcApprovals, setOtcApprovals] = useState(null);
  
  // Form states
  const [showMedForm, setShowMedForm] = useState(false);
  const [showAdminForm, setShowAdminForm] = useState(false);
  const [showIncidentForm, setShowIncidentForm] = useState(false);
  const [showCustodyForm, setShowCustodyForm] = useState(false);
  const [selectedMedForAdmin, setSelectedMedForAdmin] = useState(null);

  // Check permissions
  const hasFullAccess = () => {
    return ['commander', 'executive_staff', 'health_services'].includes(user?.role);
  };

  const hasViewAccess = () => {
    return ['commander', 'executive_staff', 'health_services', 'staff'].includes(user?.role);
  };

  const loadHealthData = async () => {
    if (!hasViewAccess()) return;
    
    try {
      setLoading(true);
      const [summaryData, refData, allergyData, otcData] = await Promise.all([
        getCadetHealthSummary(cadetId),
        getHealthReferenceLists(),
        getCadetAllergies(capid).catch(() => []),
        getCadetOtcApprovals(capid).catch(() => null)
      ]);
      
      setSummary(summaryData);
      setReferenceLists(refData);
      setAllergies(allergyData);
      setOtcApprovals(otcData);
      
      if (hasFullAccess()) {
        const [medsData, logData, incData, custData] = await Promise.all([
          getCadetMedications(cadetId),
          getCadetMedicationLog(cadetId),
          getCadetIncidents(cadetId),
          getCadetCustodyLog(cadetId)
        ]);
        
        setMedications(medsData);
        setMedicationLog(logData);
        setIncidents(incData);
        setCustodyLog(custData);
      } else {
        // Staff can see incidents but not medications
        const incData = await getCadetIncidents(cadetId);
        setIncidents(incData);
      }
    } catch (error) {
      console.error('Failed to load health data:', error);
      if (error.response?.status !== 403) {
        toast.error('Failed to load health data');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (cadetId) {
      loadHealthData();
    }
  }, [cadetId]);

  // Don't render if user doesn't have access
  if (!hasViewAccess()) {
    return null;
  }

  const formatDateTime = (dateStr) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  const formatTime = (timeStr) => {
    if (!timeStr || timeStr.length < 4) return timeStr;
    return `${timeStr.slice(0, 2)}:${timeStr.slice(2, 4)}`;
  };

  const getStatusBadge = (status) => {
    const styles = {
      cleared: 'bg-emerald-100 text-emerald-700',
      restricted_activity: 'bg-amber-100 text-amber-700',
      restricted_heat: 'bg-orange-100 text-orange-700',
      medical_hold: 'bg-red-100 text-red-700',
      sent_home: 'bg-slate-100 text-slate-700',
      open: 'bg-red-100 text-red-700',
      monitoring: 'bg-amber-100 text-amber-700',
      resolved: 'bg-emerald-100 text-emerald-700',
      escalated: 'bg-red-200 text-red-800'
    };
    return styles[status] || 'bg-slate-100 text-slate-600';
  };

  // Form Handlers
  const handleCreateMedication = async (formData) => {
    try {
      await createCadetMedication(cadetId, {
        ...formData,
        capid: capid
      });
      toast.success('Medication profile created');
      setShowMedForm(false);
      loadHealthData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create medication profile');
    }
  };

  const handleLogAdministration = async (formData) => {
    try {
      await logMedicationAdministration(cadetId, {
        ...formData,
        capid: capid,
        med_profile_id: selectedMedForAdmin.med_profile_id
      });
      toast.success('Administration logged');
      setShowAdminForm(false);
      setSelectedMedForAdmin(null);
      loadHealthData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to log administration');
    }
  };

  const handleLogIncident = async (formData) => {
    try {
      await logCadetIncident(cadetId, {
        ...formData,
        capid: capid
      });
      toast.success('Incident logged');
      setShowIncidentForm(false);
      loadHealthData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to log incident');
    }
  };

  const handleLogCustody = async (formData) => {
    try {
      await logCustodyAction(cadetId, {
        ...formData,
        capid: capid
      });
      toast.success('Custody action logged');
      setShowCustodyForm(false);
      loadHealthData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to log custody action');
    }
  };

  const handleUpdateIncidentStatus = async (incidentId, newStatus) => {
    try {
      await updateIncidentStatus(incidentId, newStatus);
      toast.success('Incident status updated');
      loadHealthData();
    } catch (error) {
      toast.error('Failed to update incident status');
    }
  };

  const handleUpdateHealthStatus = async (newStatus) => {
    try {
      await updateCadetHealthStatus(cadetId, newStatus, capid);
      toast.success('Health status updated');
      loadHealthData();
    } catch (error) {
      toast.error('Failed to update health status');
    }
  };

  if (loading) {
    return (
      <div className="bg-white border border-slate-200 rounded-sm p-4 mt-4">
        <div className="flex items-center gap-2 text-slate-500">
          <RefreshCw className="w-4 h-4 animate-spin" />
          <span>Loading health data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-sm mt-4">
      {/* Header */}
      <div 
        className="p-4 border-b border-slate-200 flex items-center justify-between cursor-pointer hover:bg-slate-50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <Heart className="w-5 h-5 text-red-500" />
          <h3 className="font-bold text-[#00205B] uppercase text-sm">Health Services</h3>
          {summary?.medication_on_file && (
            <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
              <Pill className="w-3 h-3 inline mr-1" />
              {summary.active_med_count} meds
            </span>
          )}
          {summary?.rescue_med_flag && (
            <span className="text-xs px-2 py-0.5 bg-orange-100 text-orange-700 rounded font-medium">
              RESCUE MED
            </span>
          )}
          {allergies.length > 0 && (
            <span className="text-xs px-2 py-0.5 bg-rose-100 text-rose-700 rounded" data-testid="allergy-badge">
              <AlertTriangle className="w-3 h-3 inline mr-1" />
              {allergies.length} allerg{allergies.length === 1 ? 'y' : 'ies'}
            </span>
          )}
          {allergies.some(a => a.is_anaphylaxis) && (
            <span className="text-xs px-2 py-0.5 bg-red-200 text-red-800 rounded font-bold">
              ANAPHYLAXIS
            </span>
          )}
          {allergies.some(a => a.has_epipen) && (
            <span className="text-xs px-2 py-0.5 bg-orange-200 text-orange-800 rounded font-bold">
              EPIPEN
            </span>
          )}
          {summary?.open_incidents > 0 && (
            <span className="text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded">
              <AlertCircle className="w-3 h-3 inline mr-1" />
              {summary.open_incidents} incidents
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded font-medium ${getStatusBadge(summary?.final_hs_status)}`}>
            {summary?.final_hs_status?.replace('_', ' ').toUpperCase() || 'CLEARED'}
          </span>
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </div>

      {expanded && (
        <div className="p-4">
          {/* Summary Card */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="text-center p-3 bg-slate-50 rounded-sm">
              <Pill className="w-5 h-5 mx-auto mb-1 text-blue-500" />
              <p className="text-lg font-bold text-[#00205B]">{summary?.active_med_count || 0}</p>
              <p className="text-xs text-slate-500">Active Medications</p>
            </div>
            <div className="text-center p-3 bg-slate-50 rounded-sm">
              <Clock className="w-5 h-5 mx-auto mb-1 text-amber-500" />
              <p className="text-lg font-bold text-[#00205B]">
                {summary?.next_dose_due ? formatTime(summary.next_dose_due) : '-'}
              </p>
              <p className="text-xs text-slate-500">Next Dose Due</p>
            </div>
            <div className="text-center p-3 bg-slate-50 rounded-sm">
              <History className="w-5 h-5 mx-auto mb-1 text-slate-500" />
              <p className="text-sm font-medium text-[#00205B]">
                {summary?.last_med_pass_time ? formatDateTime(summary.last_med_pass_time).split(',')[1] : '-'}
              </p>
              <p className="text-xs text-slate-500">Last Med Pass</p>
            </div>
            <div className="text-center p-3 bg-slate-50 rounded-sm">
              <Activity className="w-5 h-5 mx-auto mb-1 text-red-500" />
              <p className="text-lg font-bold text-[#00205B]">{summary?.open_incidents || 0}</p>
              <p className="text-xs text-slate-500">Open Incidents</p>
            </div>
          </div>

          {/* Status Update - Full access only */}
          {hasFullAccess() && (
            <div className="flex items-center gap-2 mb-4">
              <Label className="text-xs">Health Status:</Label>
              <Select value={summary?.final_hs_status || 'cleared'} onValueChange={handleUpdateHealthStatus}>
                <SelectTrigger className="w-48 h-8 text-xs rounded-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {referenceLists?.hs_statuses?.map(status => (
                    <SelectItem key={status} value={status}>
                      {status.replace('_', ' ').toUpperCase()}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full" style={{ gridTemplateColumns: `repeat(${hasFullAccess() ? 6 : 2}, minmax(0, 1fr))` }}>
              <TabsTrigger value="allergies" className="text-xs">Allergies</TabsTrigger>
              <TabsTrigger value="otc" className="text-xs">OTC</TabsTrigger>
              {hasFullAccess() && <TabsTrigger value="medications" className="text-xs">Medications</TabsTrigger>}
              {hasFullAccess() && <TabsTrigger value="administration" className="text-xs">Admin Log</TabsTrigger>}
              <TabsTrigger value="incidents" className="text-xs">Incidents</TabsTrigger>
              {hasFullAccess() && <TabsTrigger value="custody" className="text-xs">Custody</TabsTrigger>}
            </TabsList>

            {/* Allergies Tab */}
            <TabsContent value="allergies" className="mt-4">
              <h4 className="text-sm font-medium mb-3">Allergy Information</h4>
              {allergies.length === 0 ? (
                <p className="text-center text-slate-500 py-4">No allergy data on file</p>
              ) : (
                <div className="space-y-2">
                  {allergies.map((allergy) => (
                    <div key={allergy.allergy_id} className={`p-3 border rounded-sm ${allergy.is_anaphylaxis ? 'border-red-300 bg-red-50' : 'border-slate-200'}`}>
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-medium text-sm">{allergy.allergy_name}</p>
                          <p className="text-xs text-slate-500">{allergy.allergy_type}</p>
                        </div>
                        <div className="flex items-center gap-1">
                          {allergy.is_anaphylaxis && (
                            <span className="text-[10px] px-1.5 py-0.5 bg-red-200 text-red-800 rounded font-bold">ANAPHYLAXIS</span>
                          )}
                          {allergy.has_epipen && (
                            <span className="text-[10px] px-1.5 py-0.5 bg-orange-200 text-orange-800 rounded font-bold">EPIPEN</span>
                          )}
                          {allergy.has_albuterol_inhaler && (
                            <span className="text-[10px] px-1.5 py-0.5 bg-blue-200 text-blue-800 rounded font-bold">INHALER</span>
                          )}
                        </div>
                      </div>
                      {allergy.typical_reactions && (
                        <p className="text-xs text-amber-700 mt-1">Reactions: {allergy.typical_reactions}</p>
                      )}
                      {allergy.other_reactions && (
                        <p className="text-xs text-amber-700">Other reactions: {allergy.other_reactions}</p>
                      )}
                      {allergy.treatments && (
                        <p className="text-xs text-emerald-700 mt-1">Treatment: {allergy.treatments}</p>
                      )}
                      {allergy.other_medications && (
                        <p className="text-xs text-blue-700">Other medications: {allergy.other_medications}</p>
                      )}
                      {(allergy.contact_name || allergy.emergency_contact) && (
                        <div className="text-xs text-slate-500 mt-1 pt-1 border-t border-slate-100">
                          {allergy.contact_name && <span>Contact: {allergy.contact_name}</span>}
                          {allergy.emergency_contact && <span className="ml-2">Emergency: {allergy.emergency_contact}</span>}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* OTC Approvals Tab */}
            <TabsContent value="otc" className="mt-4">
              <h4 className="text-sm font-medium mb-3">OTC Medication Approvals</h4>
              {!otcApprovals || Object.keys(otcApprovals).length === 0 ? (
                <p className="text-center text-slate-500 py-4">No OTC approval data on file</p>
              ) : (
                <div>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {Object.entries(otcApprovals.approvals || {}).map(([med, approved]) => (
                      <div 
                        key={med}
                        className={`p-2 rounded-sm border text-sm flex items-center gap-2 ${
                          approved 
                            ? 'bg-emerald-50 border-emerald-200 text-emerald-800' 
                            : 'bg-slate-50 border-slate-200 text-slate-400'
                        }`}
                      >
                        {approved ? (
                          <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                        ) : (
                          <XCircle className="w-4 h-4 text-slate-300 flex-shrink-0" />
                        )}
                        <span className="capitalize">{med}</span>
                      </div>
                    ))}
                  </div>
                  {otcApprovals.organization && (
                    <p className="text-xs text-slate-500 mt-3">Organization: {otcApprovals.organization}</p>
                  )}
                </div>
              )}
            </TabsContent>

            {/* Medications Tab */}
            {hasFullAccess() && (
              <TabsContent value="medications" className="mt-4">
                <div className="flex justify-between items-center mb-3">
                  <h4 className="text-sm font-medium">Medication Profiles</h4>
                  <Button size="sm" onClick={() => setShowMedForm(true)} className="h-8 rounded-sm">
                    <Plus className="w-3 h-3 mr-1" />
                    Add Medication
                  </Button>
                </div>
                
                {medications.length === 0 ? (
                  <p className="text-center text-slate-500 py-4">No medications on file</p>
                ) : (
                  <div className="space-y-2">
                    {medications.filter(m => m.is_active).map((med) => (
                      <div key={med.med_profile_id} className="p-3 border border-slate-200 rounded-sm">
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-medium">{med.medication_name}</p>
                            <p className="text-sm text-slate-600">{med.dose} - {med.route}</p>
                            <p className="text-xs text-slate-500">{med.schedule_text}</p>
                            <p className="text-xs text-slate-400">Due: {med.due_times?.split(',').map(t => formatTime(t)).join(', ')}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            {med.rescue_med_flag && (
                              <span className="text-xs px-2 py-0.5 bg-orange-100 text-orange-700 rounded font-medium">
                                RESCUE
                              </span>
                            )}
                            {med.refrigeration_required && (
                              <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                                <Thermometer className="w-3 h-3 inline" /> Refrig
                              </span>
                            )}
                            <Button 
                              size="sm" 
                              variant="outline"
                              className="h-7 text-xs"
                              onClick={() => {
                                setSelectedMedForAdmin(med);
                                setShowAdminForm(true);
                              }}
                            >
                              Log Dose
                            </Button>
                          </div>
                        </div>
                        {med.special_instructions && (
                          <p className="text-xs text-amber-600 mt-2">
                            <AlertTriangle className="w-3 h-3 inline mr-1" />
                            {med.special_instructions}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </TabsContent>
            )}

            {/* Administration History Tab */}
            {hasFullAccess() && (
              <TabsContent value="administration" className="mt-4">
                <h4 className="text-sm font-medium mb-3">Administration History</h4>
                
                {medicationLog.length === 0 ? (
                  <p className="text-center text-slate-500 py-4">No administration records</p>
                ) : (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {medicationLog.map((log) => {
                      const med = medications.find(m => m.med_profile_id === log.med_profile_id);
                      return (
                        <div key={log.med_log_id} className="p-2 border border-slate-100 rounded-sm text-sm">
                          <div className="flex justify-between">
                            <span className="font-medium">{med?.medication_name || 'Unknown'}</span>
                            <span className={`text-xs px-2 py-0.5 rounded ${
                              log.result === 'taken' ? 'bg-emerald-100 text-emerald-700' :
                              log.result === 'refused' ? 'bg-red-100 text-red-700' :
                              log.result === 'missed' ? 'bg-amber-100 text-amber-700' :
                              'bg-slate-100 text-slate-600'
                            }`}>
                              {log.result}
                            </span>
                          </div>
                          <div className="text-xs text-slate-500 mt-1">
                            {log.date} • Due: {formatTime(log.time_due)} • Taken: {formatTime(log.time_taken) || '-'}
                          </div>
                          <div className="text-xs text-slate-400">
                            Observer: {log.observer_initials} {log.cadet_initials && `• Cadet: ${log.cadet_initials}`}
                          </div>
                          {log.notes && <p className="text-xs text-slate-600 mt-1">{log.notes}</p>}
                        </div>
                      );
                    })}
                  </div>
                )}
              </TabsContent>
            )}

            {/* Incidents Tab */}
            <TabsContent value="incidents" className="mt-4">
              <div className="flex justify-between items-center mb-3">
                <h4 className="text-sm font-medium">Incident History</h4>
                {hasFullAccess() && (
                  <Button size="sm" onClick={() => setShowIncidentForm(true)} className="h-8 rounded-sm">
                    <Plus className="w-3 h-3 mr-1" />
                    Log Incident
                  </Button>
                )}
              </div>
              
              {incidents.length === 0 ? (
                <p className="text-center text-slate-500 py-4">No incidents recorded</p>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {incidents.map((inc) => (
                    <div key={inc.incident_id} className={`p-3 border rounded-sm ${
                      inc.resolution_status === 'open' ? 'border-red-200 bg-red-50' :
                      inc.resolution_status === 'monitoring' ? 'border-amber-200 bg-amber-50' :
                      'border-slate-200'
                    }`}>
                      <div className="flex justify-between items-start">
                        <div>
                          <span className="text-xs px-2 py-0.5 bg-slate-200 text-slate-700 rounded mr-2">
                            {inc.incident_type?.replace('_', ' ')}
                          </span>
                          <span className="text-xs text-slate-500">
                            {inc.incident_date} at {inc.incident_time}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs px-2 py-0.5 rounded ${getStatusBadge(inc.resolution_status)}`}>
                            {inc.resolution_status}
                          </span>
                          {hasFullAccess() && inc.resolution_status !== 'resolved' && (
                            <Select 
                              value={inc.resolution_status} 
                              onValueChange={(v) => handleUpdateIncidentStatus(inc.incident_id, v)}
                            >
                              <SelectTrigger className="h-6 w-24 text-xs">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {referenceLists?.resolution_statuses?.map(s => (
                                  <SelectItem key={s} value={s}>{s}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          )}
                        </div>
                      </div>
                      <p className="text-sm mt-2">{inc.description}</p>
                      {inc.parent_contacted && (
                        <p className="text-xs text-amber-600 mt-1">
                          Parent contacted {inc.parent_contact_time && `at ${inc.parent_contact_time}`}
                        </p>
                      )}
                      {inc.command_notified && (
                        <p className="text-xs text-blue-600">Command notified</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* Custody Tab */}
            {hasFullAccess() && (
              <TabsContent value="custody" className="mt-4">
                <div className="flex justify-between items-center mb-3">
                  <h4 className="text-sm font-medium">Medication Custody Log</h4>
                  <Button size="sm" onClick={() => setShowCustodyForm(true)} className="h-8 rounded-sm">
                    <Plus className="w-3 h-3 mr-1" />
                    Log Action
                  </Button>
                </div>
                
                {custodyLog.length === 0 ? (
                  <p className="text-center text-slate-500 py-4">No custody records</p>
                ) : (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {custodyLog.map((log) => (
                      <div key={log.custody_log_id} className="p-2 border border-slate-100 rounded-sm text-sm">
                        <div className="flex justify-between">
                          <span className="font-medium">{log.medication_name}</span>
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            log.action_type === 'check_in' ? 'bg-emerald-100 text-emerald-700' :
                            log.action_type === 'check_out' ? 'bg-blue-100 text-blue-700' :
                            log.action_type === 'disposal' ? 'bg-red-100 text-red-700' :
                            'bg-slate-100 text-slate-600'
                          }`}>
                            {log.action_type?.replace('_', ' ')}
                          </span>
                        </div>
                        <div className="text-xs text-slate-500">
                          {formatDateTime(log.performed_at)} • By: {log.performed_by}
                        </div>
                        {log.quantity && <span className="text-xs">Qty: {log.quantity}</span>}
                        {log.notes && <p className="text-xs text-slate-600 mt-1">{log.notes}</p>}
                      </div>
                    ))}
                  </div>
                )}
              </TabsContent>
            )}
          </Tabs>
        </div>
      )}

      {/* Add Medication Form Dialog */}
      <MedicationFormDialog 
        open={showMedForm} 
        onClose={() => setShowMedForm(false)}
        onSubmit={handleCreateMedication}
        referenceLists={referenceLists}
      />

      {/* Log Administration Form Dialog */}
      <AdminLogFormDialog
        open={showAdminForm}
        onClose={() => { setShowAdminForm(false); setSelectedMedForAdmin(null); }}
        onSubmit={handleLogAdministration}
        medication={selectedMedForAdmin}
        referenceLists={referenceLists}
      />

      {/* Log Incident Form Dialog */}
      <IncidentFormDialog
        open={showIncidentForm}
        onClose={() => setShowIncidentForm(false)}
        onSubmit={handleLogIncident}
        referenceLists={referenceLists}
        medications={medications}
      />

      {/* Log Custody Form Dialog */}
      <CustodyFormDialog
        open={showCustodyForm}
        onClose={() => setShowCustodyForm(false)}
        onSubmit={handleLogCustody}
        referenceLists={referenceLists}
        medications={medications}
      />
    </div>
  );
};

export default CadetHealthSection;

