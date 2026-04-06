import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  getHealthDashboardSummary, getMedsDue, getOverdueMeds, getOpenIncidents,
  searchHealthCadets, getHealthReferenceLists, getHealthAuditLog, 
  getHealthSettings, updateHealthSettings, importMedicalData, getImportSummary,
  getMedicalRoster, getCadetFullHealthProfile,
  addCadetAllergy, updateAllergy, deleteAllergy, updateCadetOtcApprovals
} from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '../components/ui/sheet';
import { Switch } from '../components/ui/switch';
import { toast } from 'sonner';
import { 
  Heart, Pill, AlertTriangle, Clock, Search, Users, Activity,
  CheckCircle, XCircle, AlertCircle, ChevronRight, RefreshCw,
  Thermometer, Filter, Save, Upload, FileSpreadsheet,
  Shield, Eye, Syringe, ClipboardList, ChevronDown, ChevronUp, 
  Phone, Mail, User, BadgeAlert, Plus, Edit2, Trash2, X
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

// ==================== CADET HEALTH DETAIL SHEET ====================
const CadetHealthDetail = ({ cadetId, isOpen, onClose, hasFullAccess }) => {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expandedSections, setExpandedSections] = useState({
    allergies: true, otc: true, medications: true, incidents: true, medLog: false, custody: false
  });
  
  // Inline editing state
  const [addAllergyOpen, setAddAllergyOpen] = useState(false);
  const [editAllergyId, setEditAllergyId] = useState(null);
  const [allergyForm, setAllergyForm] = useState({});
  const [savingAllergy, setSavingAllergy] = useState(false);
  const [editingOtc, setEditingOtc] = useState(false);
  const [otcForm, setOtcForm] = useState({});
  const [savingOtc, setSavingOtc] = useState(false);

  const blankAllergy = {
    allergy_name: '', allergy_type: 'Other', is_anaphylaxis: false,
    has_epipen: false, has_albuterol_inhaler: false, typical_reactions: '',
    other_reactions: '', treatments: '', other_medications: '',
    contact_name: '', emergency_contact: '', commander_name: '', commander_contact: ''
  };

  const OTC_MEDICATIONS = [
    'acetaminophen', 'ibuprofen', 'antacids', 'cough_drops', 'throat_lozenges',
    'antihistamine', 'decongestant', 'hydrocortisone', 'triple_antibiotic',
    'calamine', 'sunscreen', 'insect_repellent', 'aloe_vera'
  ];

  useEffect(() => {
    if (isOpen && cadetId) {
      loadProfile();
    }
  }, [isOpen, cadetId]);

  const loadProfile = async () => {
    try {
      setLoading(true);
      const data = await getCadetFullHealthProfile(cadetId);
      setProfile(data);
    } catch (error) {
      toast.error('Failed to load cadet health profile');
    } finally {
      setLoading(false);
    }
  };

  const toggleSection = (section) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // ─── Allergy handlers ───
  const handleAddAllergy = () => {
    setAllergyForm({ ...blankAllergy });
    setEditAllergyId(null);
    setAddAllergyOpen(true);
  };

  const handleEditAllergy = (allergy) => {
    setAllergyForm({ ...allergy });
    setEditAllergyId(allergy.id);
    setAddAllergyOpen(true);
  };

  const handleSaveAllergy = async () => {
    if (!allergyForm.allergy_name?.trim()) {
      toast.error('Allergy name is required');
      return;
    }
    setSavingAllergy(true);
    try {
      if (editAllergyId) {
        await updateAllergy(editAllergyId, allergyForm);
        toast.success('Allergy updated');
      } else {
        await addCadetAllergy(cadetId, allergyForm);
        toast.success('Allergy added');
      }
      setAddAllergyOpen(false);
      loadProfile();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save allergy');
    } finally {
      setSavingAllergy(false);
    }
  };

  const handleDeleteAllergy = async (allergyId) => {
    if (!window.confirm('Delete this allergy record?')) return;
    try {
      await deleteAllergy(allergyId);
      toast.success('Allergy deleted');
      loadProfile();
    } catch (error) {
      toast.error('Failed to delete allergy');
    }
  };

  // ─── OTC handlers ───
  const startEditOtc = () => {
    const meds = profile?.otc_approvals?.medications || {};
    const fullMeds = {};
    OTC_MEDICATIONS.forEach(m => { fullMeds[m] = meds[m] || false; });
    setOtcForm({ medications: fullMeds, organization: profile?.otc_approvals?.organization || '' });
    setEditingOtc(true);
  };

  const handleSaveOtc = async () => {
    setSavingOtc(true);
    try {
      await updateCadetOtcApprovals(cadetId, otcForm);
      toast.success('OTC approvals updated');
      setEditingOtc(false);
      loadProfile();
    } catch (error) {
      toast.error('Failed to update OTC approvals');
    } finally {
      setSavingOtc(false);
    }
  };

  const SectionHeader = ({ title, icon: Icon, count, section, color = "text-[#00205B]", badge }) => (
    <button
      onClick={() => toggleSection(section)}
      className="w-full flex items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-sm hover:bg-slate-100 transition-colors"
      data-testid={`section-toggle-${section}`}
    >
      <div className="flex items-center gap-2">
        <Icon className={`w-4 h-4 ${color}`} />
        <span className={`font-bold text-sm uppercase tracking-wide ${color}`}>{title}</span>
        {count !== undefined && (
          <span className="text-xs bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded-full">{count}</span>
        )}
        {badge && (
          <span className="text-[10px] px-1.5 py-0.5 bg-red-100 text-red-700 rounded font-bold">{badge}</span>
        )}
      </div>
      {expandedSections[section] ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
    </button>
  );

  if (!isOpen) return null;

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent className="w-full sm:max-w-2xl overflow-y-auto" data-testid="cadet-health-detail-sheet">
        <SheetHeader>
          <SheetTitle className="text-[#00205B] uppercase font-bold flex items-center gap-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
            <Heart className="w-5 h-5 text-red-500" />
            Health Profile
          </SheetTitle>
        </SheetHeader>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <RefreshCw className="w-5 h-5 animate-spin text-slate-400" />
          </div>
        ) : profile ? (
          <div className="mt-4 space-y-4">
            {/* Cadet Header */}
            <div className="bg-[#00205B] text-white rounded-sm p-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-bold">{profile.name}</h3>
                  <p className="text-blue-200 text-sm">CAPID: {profile.capid}</p>
                  <p className="text-blue-200 text-xs mt-1">
                    {profile.rank && `${profile.rank} | `}
                    {profile.flight && `Flight: ${profile.flight} | `}
                    {profile.squadron && `Sqdn: ${profile.squadron}`}
                    {profile.gender && ` | ${profile.gender}`}
                    {profile.age && ` | Age: ${profile.age}`}
                  </p>
                </div>
                <span className={`text-xs px-2 py-1 rounded font-bold ${
                  profile.hs_status === 'cleared' ? 'bg-emerald-500 text-white' :
                  profile.hs_status === 'medical_hold' ? 'bg-red-500 text-white' :
                  'bg-amber-500 text-white'
                }`} data-testid="cadet-hs-status">
                  {(profile.hs_status || 'cleared').replace(/_/g, ' ').toUpperCase()}
                </span>
              </div>
              {/* Critical Flags */}
              {(profile.has_anaphylaxis || profile.has_epipen || profile.has_inhaler || profile.has_rescue_med) && (
                <div className="flex flex-wrap gap-1 mt-3">
                  {profile.has_anaphylaxis && <span className="text-[10px] px-2 py-0.5 bg-red-600 text-white rounded font-bold">ANAPHYLAXIS RISK</span>}
                  {profile.has_epipen && <span className="text-[10px] px-2 py-0.5 bg-orange-500 text-white rounded font-bold">EPIPEN</span>}
                  {profile.has_inhaler && <span className="text-[10px] px-2 py-0.5 bg-blue-400 text-white rounded font-bold">INHALER</span>}
                  {profile.has_rescue_med && <span className="text-[10px] px-2 py-0.5 bg-purple-500 text-white rounded font-bold">RESCUE MED</span>}
                </div>
              )}
            </div>

            {/* Allergies Section */}
            <div>
              <div className="flex items-center gap-2">
                <div className="flex-1">
                  <SectionHeader 
                    title="Allergies" 
                    icon={AlertTriangle} 
                    count={profile.allergy_count} 
                    section="allergies"
                    color="text-rose-600"
                    badge={profile.has_anaphylaxis ? "ANAPHYLAXIS" : null}
                  />
                </div>
                {hasFullAccess && (
                  <Button size="sm" variant="outline" onClick={handleAddAllergy} className="rounded-sm h-9" data-testid="add-allergy-btn">
                    <Plus className="w-3.5 h-3.5 mr-1" /> Add
                  </Button>
                )}
              </div>
              {expandedSections.allergies && (
                <div className="mt-2 space-y-2">
                  {profile.allergies?.length === 0 ? (
                    <p className="text-sm text-slate-500 italic p-3">No allergies on file</p>
                  ) : (
                    profile.allergies?.map((a, idx) => (
                      <div key={a.id || `allergy-${a.allergy_name}-${idx}`} className={`p-3 border rounded-sm ${a.is_anaphylaxis ? 'border-red-300 bg-red-50' : 'border-slate-200 bg-white'}`} data-testid={`allergy-item-${idx}`}>
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-bold text-sm">{a.allergy_name}</p>
                            <p className="text-xs text-slate-500">{a.allergy_type}</p>
                          </div>
                          <div className="flex gap-1 items-center">
                            {a.is_anaphylaxis && <span className="text-[9px] px-1.5 py-0.5 bg-red-600 text-white rounded font-bold">ANAPHYLAXIS</span>}
                            {a.has_epipen && <span className="text-[9px] px-1.5 py-0.5 bg-orange-500 text-white rounded font-bold">EPIPEN</span>}
                            {a.has_albuterol_inhaler && <span className="text-[9px] px-1.5 py-0.5 bg-blue-500 text-white rounded font-bold">INHALER</span>}
                            {hasFullAccess && (
                              <>
                                <button onClick={() => handleEditAllergy(a)} className="ml-2 p-1 text-slate-400 hover:text-[#00205B] transition-colors" data-testid={`edit-allergy-${idx}`}>
                                  <Edit2 className="w-3.5 h-3.5" />
                                </button>
                                <button onClick={() => handleDeleteAllergy(a.id)} className="p-1 text-slate-400 hover:text-red-600 transition-colors" data-testid={`delete-allergy-${idx}`}>
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                        {a.typical_reactions && <p className="text-xs mt-1"><span className="font-medium text-slate-600">Reactions:</span> {a.typical_reactions}</p>}
                        {a.other_reactions && <p className="text-xs mt-0.5"><span className="font-medium text-slate-600">Other:</span> {a.other_reactions}</p>}
                        {a.treatments && <p className="text-xs mt-0.5"><span className="font-medium text-slate-600">Treatment:</span> {a.treatments}</p>}
                        {a.other_medications && <p className="text-xs mt-0.5"><span className="font-medium text-slate-600">Medications:</span> {a.other_medications}</p>}
                        {(a.emergency_contact || a.contact_name) && (
                          <div className="mt-2 pt-2 border-t border-slate-200 flex flex-wrap gap-3">
                            {a.contact_name && (
                              <span className="text-xs flex items-center gap-1 text-slate-500">
                                <User className="w-3 h-3" /> {a.contact_name}
                              </span>
                            )}
                            {a.emergency_contact && (
                              <span className="text-xs flex items-center gap-1 text-slate-500">
                                <Phone className="w-3 h-3" /> {a.emergency_contact}
                              </span>
                            )}
                            {a.commander_name && (
                              <span className="text-xs flex items-center gap-1 text-slate-500">
                                <Shield className="w-3 h-3" /> CC: {a.commander_name} {a.commander_contact ? `(${a.commander_contact})` : ''}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* OTC Approvals Section */}
            <div>
              <div className="flex items-center gap-2">
                <div className="flex-1">
                  <SectionHeader 
                    title="OTC Medication Approvals" 
                    icon={Pill} 
                    count={profile.otc_approvals?.approved_list?.length || 0}
                    section="otc"
                    color="text-teal-600"
                  />
                </div>
                {hasFullAccess && (
                  <Button size="sm" variant="outline" onClick={startEditOtc} className="rounded-sm h-9" data-testid="edit-otc-btn">
                    <Edit2 className="w-3.5 h-3.5 mr-1" /> Edit
                  </Button>
                )}
              </div>
              {expandedSections.otc && (
                <div className="mt-2">
                  {editingOtc ? (
                    <div className="p-3 border border-teal-200 rounded-sm bg-teal-50/50" data-testid="otc-edit-form">
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-3">
                        {OTC_MEDICATIONS.map((med) => (
                          <label key={med} className="flex items-center gap-2 px-2 py-1.5 rounded border bg-white border-slate-200 cursor-pointer hover:border-teal-300 transition-colors">
                            <Switch
                              checked={otcForm.medications?.[med] || false}
                              onCheckedChange={(checked) => setOtcForm(prev => ({
                                ...prev,
                                medications: { ...prev.medications, [med]: checked }
                              }))}
                              className="scale-75"
                              data-testid={`otc-toggle-${med}`}
                            />
                            <span className="text-xs capitalize">{med.replace(/_/g, ' ')}</span>
                          </label>
                        ))}
                      </div>
                      <div className="flex gap-2 pt-2 border-t border-teal-200">
                        <Button size="sm" onClick={handleSaveOtc} disabled={savingOtc} className="bg-[#00205B] rounded-sm" data-testid="save-otc-btn">
                          <Save className="w-3.5 h-3.5 mr-1" />{savingOtc ? 'Saving...' : 'Save OTC'}
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setEditingOtc(false)} className="rounded-sm">Cancel</Button>
                      </div>
                    </div>
                  ) : !profile.otc_approvals ? (
                    <p className="text-sm text-slate-500 italic p-3">No OTC data on file</p>
                  ) : (
                    <div className="p-3 border border-slate-200 rounded-sm bg-white">
                      {profile.otc_approvals.organization && (
                        <p className="text-xs text-slate-500 mb-2">Organization: {profile.otc_approvals.organization}</p>
                      )}
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
                        {Object.entries(profile.otc_approvals.medications || {}).map(([med, approved]) => (
                          <div key={med} className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs ${
                            approved ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-600 border border-red-200'
                          }`} data-testid={`otc-${med}`}>
                            {approved ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                            <span className="capitalize">{med}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Prescription Medications Section */}
            {hasFullAccess && (
              <div>
                <SectionHeader 
                  title="Prescription Medications" 
                  icon={Syringe}
                  count={profile.medication_count}
                  section="medications"
                  color="text-blue-600"
                  badge={profile.has_rescue_med ? "RESCUE" : null}
                />
                {expandedSections.medications && (
                  <div className="mt-2 space-y-2">
                    {profile.medications?.length === 0 ? (
                      <p className="text-sm text-slate-500 italic p-3">No prescription medications on file</p>
                    ) : (
                      profile.medications?.map((m, idx) => (
                        <div key={m.id || `med-${m.medication_name}-${idx}`} className={`p-3 border rounded-sm bg-white ${m.rescue_med_flag ? 'border-orange-300 bg-orange-50' : 'border-slate-200'}`} data-testid={`medication-item-${idx}`}>
                          <div className="flex items-start justify-between">
                            <div>
                              <p className="font-bold text-sm">{m.medication_name}</p>
                              <p className="text-xs text-slate-500">{m.dose} - {m.route}</p>
                            </div>
                            {m.rescue_med_flag && <span className="text-[9px] px-1.5 py-0.5 bg-orange-500 text-white rounded font-bold">RESCUE</span>}
                          </div>
                          <p className="text-xs mt-1"><span className="font-medium text-slate-600">Schedule:</span> {m.schedule_text}</p>
                          {m.due_times && <p className="text-xs mt-0.5"><span className="font-medium text-slate-600">Due Times:</span> {m.due_times}</p>}
                          {m.special_instructions && <p className="text-xs mt-0.5"><span className="font-medium text-slate-600">Instructions:</span> {m.special_instructions}</p>}
                          {m.refrigeration_required && <span className="text-[9px] px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded mt-1 inline-block">REFRIGERATE</span>}
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Incidents Section */}
            <div>
              <SectionHeader 
                title="Incidents" 
                icon={Activity}
                count={profile.incidents?.length || 0}
                section="incidents"
                color="text-amber-600"
                badge={profile.open_incident_count > 0 ? `${profile.open_incident_count} OPEN` : null}
              />
              {expandedSections.incidents && (
                <div className="mt-2 space-y-2">
                  {profile.incidents?.length === 0 ? (
                    <p className="text-sm text-slate-500 italic p-3">No incidents on file</p>
                  ) : (
                    profile.incidents?.map((inc, idx) => (
                      <div key={inc.id || `inc-${inc.incident_date}-${inc.incident_time}-${idx}`} className={`p-3 border rounded-sm bg-white ${
                        inc.resolution_status === 'open' ? 'border-red-300' :
                        inc.resolution_status === 'monitoring' ? 'border-amber-300' :
                        'border-slate-200'
                      }`} data-testid={`incident-item-${idx}`}>
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-bold text-sm capitalize">{inc.incident_type?.replace(/_/g, ' ')}</p>
                            <p className="text-xs text-slate-500">{inc.incident_date} at {inc.incident_time}</p>
                          </div>
                          <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                            inc.resolution_status === 'open' ? 'bg-red-100 text-red-700' :
                            inc.resolution_status === 'monitoring' ? 'bg-amber-100 text-amber-700' :
                            inc.resolution_status === 'escalated' ? 'bg-red-200 text-red-800' :
                            'bg-emerald-100 text-emerald-700'
                          }`}>{inc.resolution_status?.toUpperCase()}</span>
                        </div>
                        <p className="text-xs mt-1">{inc.description}</p>
                        <div className="flex gap-2 mt-1">
                          {inc.parent_contacted && <span className="text-[9px] text-amber-600">Parent Contacted</span>}
                          {inc.command_notified && <span className="text-[9px] text-blue-600">Command Notified</span>}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* Medication Administration Log */}
            {hasFullAccess && profile.medication_log?.length > 0 && (
              <div>
                <SectionHeader 
                  title="Medication Log" 
                  icon={ClipboardList}
                  count={profile.medication_log?.length}
                  section="medLog"
                  color="text-indigo-600"
                />
                {expandedSections.medLog && (
                  <div className="mt-2 max-h-60 overflow-y-auto border border-slate-200 rounded-sm">
                    <table className="w-full text-xs">
                      <thead className="bg-slate-50 sticky top-0">
                        <tr>
                          <th className="text-left p-2 font-medium text-slate-600">Date</th>
                          <th className="text-left p-2 font-medium text-slate-600">Medication</th>
                          <th className="text-left p-2 font-medium text-slate-600">Due</th>
                          <th className="text-left p-2 font-medium text-slate-600">Taken</th>
                          <th className="text-left p-2 font-medium text-slate-600">Result</th>
                          <th className="text-left p-2 font-medium text-slate-600">Observer</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {profile.medication_log.map((log, idx) => (
                          <tr key={log.id || `log-${log.date}-${log.medication_name}-${idx}`} className="hover:bg-slate-50">
                            <td className="p-2">{log.date}</td>
                            <td className="p-2 font-medium">{log.medication_name}</td>
                            <td className="p-2">{log.time_due}</td>
                            <td className="p-2">{log.time_taken || '-'}</td>
                            <td className="p-2">
                              <span className={`px-1.5 py-0.5 rounded ${
                                log.result === 'taken' ? 'bg-emerald-100 text-emerald-700' :
                                log.result === 'refused' ? 'bg-red-100 text-red-700' :
                                'bg-amber-100 text-amber-700'
                              }`}>{log.result}</span>
                            </td>
                            <td className="p-2">{log.observer_initials}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* Health Notes */}
            {(profile.health_notes || profile.shared_notes) && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-sm">
                <p className="text-xs font-bold text-amber-700 uppercase mb-1">Health Notes</p>
                {profile.health_notes && <p className="text-sm text-amber-800">{profile.health_notes}</p>}
                {profile.shared_notes && <p className="text-sm text-amber-700 mt-1 italic">{profile.shared_notes}</p>}
              </div>
            )}
          </div>
        ) : (
          <p className="text-center text-slate-500 py-8">No profile data available</p>
        )}

        {/* Add/Edit Allergy Dialog */}
        <Dialog open={addAllergyOpen} onOpenChange={setAddAllergyOpen}>
          <DialogContent className="max-w-lg" data-testid="allergy-form-dialog">
            <DialogHeader>
              <DialogTitle className="text-[#00205B]">{editAllergyId ? 'Edit Allergy' : 'Add Allergy'}</DialogTitle>
            </DialogHeader>
            <div className="space-y-3 pt-2 max-h-[60vh] overflow-y-auto">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">Allergy Name *</Label>
                  <Input value={allergyForm.allergy_name || ''} onChange={(e) => setAllergyForm(p => ({ ...p, allergy_name: e.target.value }))} placeholder="e.g., Peanuts" className="rounded-sm mt-1" data-testid="allergy-name-input" />
                </div>
                <div>
                  <Label className="text-xs">Type</Label>
                  <Select value={allergyForm.allergy_type || 'Other'} onValueChange={(v) => setAllergyForm(p => ({ ...p, allergy_type: v }))}>
                    <SelectTrigger className="rounded-sm mt-1"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Food">Food</SelectItem>
                      <SelectItem value="Drug">Drug</SelectItem>
                      <SelectItem value="Environmental">Environmental</SelectItem>
                      <SelectItem value="Insect">Insect</SelectItem>
                      <SelectItem value="Latex">Latex</SelectItem>
                      <SelectItem value="Other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex flex-wrap gap-4">
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input type="checkbox" checked={allergyForm.is_anaphylaxis || false} onChange={(e) => setAllergyForm(p => ({ ...p, is_anaphylaxis: e.target.checked }))} className="rounded" />
                  <span className="text-red-600 font-medium">Anaphylaxis Risk</span>
                </label>
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input type="checkbox" checked={allergyForm.has_epipen || false} onChange={(e) => setAllergyForm(p => ({ ...p, has_epipen: e.target.checked }))} className="rounded" />
                  <span className="text-orange-600 font-medium">EpiPen</span>
                </label>
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input type="checkbox" checked={allergyForm.has_albuterol_inhaler || false} onChange={(e) => setAllergyForm(p => ({ ...p, has_albuterol_inhaler: e.target.checked }))} className="rounded" />
                  <span className="text-blue-600 font-medium">Inhaler</span>
                </label>
              </div>
              <div>
                <Label className="text-xs">Typical Reactions</Label>
                <Input value={allergyForm.typical_reactions || ''} onChange={(e) => setAllergyForm(p => ({ ...p, typical_reactions: e.target.value }))} placeholder="e.g., Hives, swelling" className="rounded-sm mt-1" />
              </div>
              <div>
                <Label className="text-xs">Treatments</Label>
                <Input value={allergyForm.treatments || ''} onChange={(e) => setAllergyForm(p => ({ ...p, treatments: e.target.value }))} placeholder="e.g., Administer EpiPen, call 911" className="rounded-sm mt-1" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">Emergency Contact Name</Label>
                  <Input value={allergyForm.contact_name || ''} onChange={(e) => setAllergyForm(p => ({ ...p, contact_name: e.target.value }))} className="rounded-sm mt-1" />
                </div>
                <div>
                  <Label className="text-xs">Emergency Phone</Label>
                  <Input value={allergyForm.emergency_contact || ''} onChange={(e) => setAllergyForm(p => ({ ...p, emergency_contact: e.target.value }))} className="rounded-sm mt-1" />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-3 border-t">
                <Button variant="outline" size="sm" onClick={() => setAddAllergyOpen(false)} className="rounded-sm">Cancel</Button>
                <Button size="sm" onClick={handleSaveAllergy} disabled={savingAllergy} className="bg-[#00205B] rounded-sm" data-testid="save-allergy-btn">
                  <Save className="w-3.5 h-3.5 mr-1" />{savingAllergy ? 'Saving...' : (editAllergyId ? 'Update' : 'Add Allergy')}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </SheetContent>
    </Sheet>
  );
};

// ==================== MEDICAL ROSTER TAB ====================
const MedicalRosterTab = ({ hasFullAccess }) => {
  const [roster, setRoster] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [filterFlight, setFilterFlight] = useState('all');
  const [selectedCadetId, setSelectedCadetId] = useState(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  useEffect(() => {
    loadRoster();
  }, []);

  const loadRoster = async () => {
    try {
      setLoading(true);
      const data = await getMedicalRoster();
      setRoster(data);
    } catch (error) {
      toast.error('Failed to load medical roster');
    } finally {
      setLoading(false);
    }
  };

  const openCadetDetail = (participantId) => {
    setSelectedCadetId(participantId);
    setIsDetailOpen(true);
  };

  // Compute filter options from roster data
  const flights = [...new Set(roster.map(r => r.flight).filter(Boolean))].sort();

  // Filter roster
  const filtered = roster.filter(r => {
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      if (!r.name.toLowerCase().includes(q) && !r.capid?.includes(q)) return false;
    }
    if (filterFlight !== 'all' && r.flight !== filterFlight) return false;
    if (filterType === 'allergies' && !r.has_allergies) return false;
    if (filterType === 'otc' && !r.has_otc_data) return false;
    if (filterType === 'medications' && !r.has_medications) return false;
    if (filterType === 'incidents' && r.open_incidents === 0) return false;
    if (filterType === 'critical' && r.critical_flags.length === 0) return false;
    if (filterType === 'anaphylaxis' && !r.has_anaphylaxis) return false;
    return true;
  });

  // Stats
  const stats = {
    total: roster.length,
    withAllergies: roster.filter(r => r.has_allergies).length,
    withAnaphylaxis: roster.filter(r => r.has_anaphylaxis).length,
    withOtc: roster.filter(r => r.has_otc_data).length,
    withMeds: roster.filter(r => r.has_medications).length,
    withIncidents: roster.filter(r => r.open_incidents > 0).length,
    critical: roster.filter(r => r.critical_flags.length > 0).length
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <RefreshCw className="w-5 h-5 animate-spin text-slate-400 mr-2" />
        <span className="text-slate-500">Loading medical roster...</span>
      </div>
    );
  }

  return (
    <div data-testid="medical-roster-tab">
      {/* Quick Stats */}
      <div className="grid grid-cols-3 sm:grid-cols-7 gap-2 mb-4">
        {[
          { label: 'Total', value: stats.total, color: 'bg-slate-100 text-slate-700', filter: 'all' },
          { label: 'Allergies', value: stats.withAllergies, color: 'bg-rose-50 text-rose-700 border-rose-200', filter: 'allergies' },
          { label: 'Anaphylaxis', value: stats.withAnaphylaxis, color: 'bg-red-50 text-red-700 border-red-200', filter: 'anaphylaxis' },
          { label: 'OTC Data', value: stats.withOtc, color: 'bg-teal-50 text-teal-700 border-teal-200', filter: 'otc' },
          { label: 'Rx Meds', value: stats.withMeds, color: 'bg-blue-50 text-blue-700 border-blue-200', filter: 'medications' },
          { label: 'Incidents', value: stats.withIncidents, color: 'bg-amber-50 text-amber-700 border-amber-200', filter: 'incidents' },
          { label: 'Critical', value: stats.critical, color: 'bg-red-100 text-red-800 border-red-300', filter: 'critical' },
        ].map(s => (
          <button
            key={s.label}
            onClick={() => setFilterType(s.filter)}
            className={`p-2 rounded-sm border text-center transition-all ${s.color} ${filterType === s.filter ? 'ring-2 ring-[#00205B] ring-offset-1' : ''}`}
            data-testid={`filter-${s.filter}`}
          >
            <p className="text-lg font-bold">{s.value}</p>
            <p className="text-[10px] uppercase tracking-wide">{s.label}</p>
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
            data-testid="medical-roster-search"
          />
        </div>
        <Select value={filterFlight} onValueChange={setFilterFlight}>
          <SelectTrigger className="w-40 rounded-sm" data-testid="flight-filter">
            <SelectValue placeholder="All Flights" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Flights</SelectItem>
            {flights.map(f => <SelectItem key={f} value={f}>{f}</SelectItem>)}
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" onClick={loadRoster} className="rounded-sm">
          <RefreshCw className="w-4 h-4 mr-1" /> Refresh
        </Button>
      </div>

      {/* Results count */}
      <p className="text-xs text-slate-500 mb-2">{filtered.length} of {roster.length} cadets shown</p>

      {/* Roster Table */}
      {filtered.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-sm p-12 text-center">
          <Users className="w-12 h-12 mx-auto mb-3 text-slate-300" />
          <p className="text-slate-500">No cadets match your filters</p>
          <p className="text-xs text-slate-400 mt-1">Try adjusting your search or filter criteria</p>
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="medical-roster-table">
              <thead>
                <tr className="bg-[#00205B] text-white text-xs uppercase tracking-wide">
                  <th className="text-left p-3">Cadet</th>
                  <th className="text-left p-3">Flight</th>
                  <th className="text-center p-3">Allergies</th>
                  <th className="text-center p-3">OTC</th>
                  <th className="text-center p-3">Meds</th>
                  <th className="text-center p-3">Incidents</th>
                  <th className="text-center p-3">Flags</th>
                  <th className="text-center p-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((cadet) => (
                  <tr
                    key={cadet.participant_id}
                    onClick={() => openCadetDetail(cadet.participant_id)}
                    className={`hover:bg-blue-50 cursor-pointer transition-colors ${
                      cadet.critical_flags.length > 0 ? 'bg-red-50/30' : ''
                    }`}
                    data-testid={`roster-row-${cadet.capid}`}
                  >
                    <td className="p-3">
                      <p className="font-medium text-[#00205B]">{cadet.name}</p>
                      <p className="text-[10px] text-slate-500">CAPID: {cadet.capid}</p>
                    </td>
                    <td className="p-3">
                      <span className="text-xs capitalize">{cadet.flight || '-'}</span>
                    </td>
                    <td className="p-3 text-center">
                      {cadet.has_allergies ? (
                        <div className="flex flex-col items-center gap-0.5">
                          <span className={`inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded ${
                            cadet.has_anaphylaxis ? 'bg-red-100 text-red-700 font-bold' : 'bg-rose-50 text-rose-600'
                          }`}>
                            <AlertTriangle className="w-3 h-3" />
                            {cadet.allergy_count}
                          </span>
                          <span className="text-[9px] text-slate-400 max-w-[120px] truncate">{cadet.allergy_names?.join(', ')}</span>
                        </div>
                      ) : (
                        <span className="text-slate-300">-</span>
                      )}
                    </td>
                    <td className="p-3 text-center">
                      {cadet.has_otc_data ? (
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          cadet.otc_any_approved ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'
                        }`}>
                          {cadet.otc_approved_count} approved
                        </span>
                      ) : (
                        <span className="text-slate-300">-</span>
                      )}
                    </td>
                    <td className="p-3 text-center">
                      {cadet.has_medications ? (
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          cadet.has_rescue_med ? 'bg-orange-100 text-orange-700 font-bold' : 'bg-blue-50 text-blue-700'
                        }`}>
                          <Pill className="w-3 h-3 inline mr-0.5" />
                          {cadet.medication_count}
                        </span>
                      ) : (
                        <span className="text-slate-300">-</span>
                      )}
                    </td>
                    <td className="p-3 text-center">
                      {cadet.open_incidents > 0 ? (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-bold">
                          {cadet.open_incidents}
                        </span>
                      ) : (
                        <span className="text-slate-300">-</span>
                      )}
                    </td>
                    <td className="p-3 text-center">
                      {cadet.critical_flags.length > 0 ? (
                        <div className="flex flex-wrap justify-center gap-0.5">
                          {cadet.critical_flags.map((flag, i) => (
                            <span key={`flag-${flag}-${i}`} className="text-[8px] px-1 py-0.5 bg-red-600 text-white rounded font-bold">{flag}</span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-slate-300">-</span>
                      )}
                    </td>
                    <td className="p-3 text-center">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                        cadet.hs_status === 'cleared' ? 'bg-emerald-50 text-emerald-700' :
                        cadet.hs_status === 'medical_hold' ? 'bg-red-100 text-red-700' :
                        'bg-amber-50 text-amber-700'
                      }`}>
                        {(cadet.hs_status || 'cleared').replace(/_/g, ' ')}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Cadet Health Detail Sheet */}
      <CadetHealthDetail
        cadetId={selectedCadetId}
        isOpen={isDetailOpen}
        onClose={() => setIsDetailOpen(false)}
        hasFullAccess={hasFullAccess}
      />
    </div>
  );
};

// ==================== MAIN DASHBOARD ====================
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
  const [activeTab, setActiveTab] = useState('dashboard');
  // OTC Dashboard state
  const [otcDashboard, setOtcDashboard] = useState(null);
  const [otcLoading, setOtcLoading] = useState(false);
  const [otcSearch, setOtcSearch] = useState('');
  const [otcFilter, setOtcFilter] = useState('all');
  const [otcTypeFilter, setOtcTypeFilter] = useState('all');

  // Check if user has full health access
  const hasFullAccess = () => {
    return ['commander', 'executive_staff', 'health_services'].includes(user?.role);
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

  const loadOtcDashboard = async () => {
    setOtcLoading(true);
    try {
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/otc-permissions/dashboard`, {
        credentials: 'include'
      });
      if (res.ok) setOtcDashboard(await res.json());
    } catch (e) { console.error('Failed to load OTC dashboard:', e); }
    finally { setOtcLoading(false); }
  };

  const reviewOtcForm = async (capid) => {
    try {
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/otc-permissions/${capid}/review`, {
        method: 'POST', credentials: 'include'
      });
      if (res.ok) {
        toast.success('Form marked as reviewed');
        loadOtcDashboard();
      }
    } catch (e) { toast.error('Failed to review form'); }
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

      {/* Tab Navigation */}
      <div className="flex border-b border-slate-200 mb-6" data-testid="health-tabs">
        <button
          onClick={() => setActiveTab('dashboard')}
          className={`px-4 py-2.5 text-sm font-bold uppercase tracking-wide transition-colors border-b-2 -mb-px ${
            activeTab === 'dashboard'
              ? 'text-[#00205B] border-[#00205B]'
              : 'text-slate-500 border-transparent hover:text-slate-700 hover:border-slate-300'
          }`}
          data-testid="tab-dashboard"
        >
          <Activity className="w-4 h-4 inline mr-1.5 -mt-0.5" />
          Dashboard
        </button>
        <button
          onClick={() => setActiveTab('medical-roster')}
          className={`px-4 py-2.5 text-sm font-bold uppercase tracking-wide transition-colors border-b-2 -mb-px ${
            activeTab === 'medical-roster'
              ? 'text-[#00205B] border-[#00205B]'
              : 'text-slate-500 border-transparent hover:text-slate-700 hover:border-slate-300'
          }`}
          data-testid="tab-medical-roster"
        >
          <ClipboardList className="w-4 h-4 inline mr-1.5 -mt-0.5" />
          Medical Roster
        </button>
        <button
          onClick={() => setActiveTab('otc-permissions')}
          className={`px-4 py-2.5 text-sm font-bold uppercase tracking-wide transition-colors border-b-2 -mb-px ${
            activeTab === 'otc-permissions'
              ? 'text-[#00205B] border-[#00205B]'
              : 'text-slate-500 border-transparent hover:text-slate-700 hover:border-slate-300'
          }`}
          data-testid="tab-otc-permissions"
        >
          <Pill className="w-4 h-4 inline mr-1.5 -mt-0.5" />
          OTC Permissions
        </button>
      </div>

      {/* OTC Permissions Tab */}
      {activeTab === 'otc-permissions' && (
        <div className="space-y-6">
          {otcLoading || !otcDashboard ? (
            <div className="text-center py-8">
              {!otcDashboard && !otcLoading && (
                <Button onClick={loadOtcDashboard} className="bg-[#00205B]" data-testid="load-otc-dashboard">Load OTC Dashboard</Button>
              )}
              {otcLoading && <span className="text-slate-400">Loading OTC dashboard...</span>}
            </div>
          ) : (<>
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white border border-slate-200 rounded-sm p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Total Cadets</p>
                <p className="text-2xl font-bold text-[#00205B]">{otcDashboard.total}</p>
              </div>
              <div className="bg-white border border-emerald-200 rounded-sm p-4">
                <p className="text-xs uppercase tracking-wide text-emerald-600">Submitted</p>
                <p className="text-2xl font-bold text-emerald-600">{otcDashboard.submitted}</p>
              </div>
              <div className="bg-white border border-blue-200 rounded-sm p-4">
                <p className="text-xs uppercase tracking-wide text-blue-600">Reviewed</p>
                <p className="text-2xl font-bold text-blue-600">{otcDashboard.reviewed}</p>
              </div>
              <div className="bg-white border border-red-200 rounded-sm p-4">
                <p className="text-xs uppercase tracking-wide text-red-600">Missing</p>
                <p className="text-2xl font-bold text-red-600">{otcDashboard.missing}</p>
              </div>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-3">
              <Input placeholder="Search by name or CAPID..." value={otcSearch} onChange={e => setOtcSearch(e.target.value)}
                className="w-64 rounded-sm" data-testid="otc-dashboard-search" />
              <Select value={otcFilter} onValueChange={setOtcFilter}>
                <SelectTrigger className="w-36 rounded-sm"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="submitted">Submitted</SelectItem>
                  <SelectItem value="reviewed">Reviewed</SelectItem>
                  <SelectItem value="not_started">Missing</SelectItem>
                </SelectContent>
              </Select>
              <Select value={otcTypeFilter} onValueChange={setOtcTypeFilter}>
                <SelectTrigger className="w-32 rounded-sm"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="Student">Students</SelectItem>
                  <SelectItem value="Cadre">Cadre</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" size="sm" onClick={loadOtcDashboard} className="rounded-sm">
                <RefreshCw className="w-4 h-4 mr-1" /> Refresh
              </Button>
            </div>

            {/* Table */}
            <div className="bg-white border border-slate-200 rounded-sm overflow-hidden">
              <div className="overflow-x-auto max-h-[55vh] overflow-y-auto">
                <table className="w-full text-sm" data-testid="otc-dashboard-table">
                  <thead className="bg-slate-50 sticky top-0 z-10">
                    <tr>
                      <th className="text-left p-3 text-xs font-semibold text-slate-600 uppercase">Name</th>
                      <th className="text-left p-3 text-xs font-semibold text-slate-600 uppercase">Type</th>
                      <th className="text-center p-3 text-xs font-semibold text-slate-600 uppercase">Status</th>
                      {Object.entries(otcDashboard.medication_labels || {}).map(([key, label]) => (
                        <th key={key} className="text-center p-2 text-[10px] font-semibold text-slate-500 uppercase w-12" title={label}>
                          {label.substring(0, 4)}
                        </th>
                      ))}
                      <th className="text-left p-3 text-xs font-semibold text-slate-600 uppercase">Parent</th>
                      <th className="text-center p-3 text-xs font-semibold text-slate-600 uppercase">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {otcDashboard.items
                      .filter(i => {
                        const search = otcSearch.toLowerCase();
                        const matchSearch = !search || i.name?.toLowerCase().includes(search) || i.capid?.includes(search);
                        const matchStatus = otcFilter === 'all' || i.status === otcFilter;
                        const matchType = otcTypeFilter === 'all' || i.participant_type === otcTypeFilter;
                        return matchSearch && matchStatus && matchType;
                      })
                      .sort((a, b) => {
                        const order = { not_started: 0, submitted: 1, reviewed: 2 };
                        return (order[a.status] || 0) - (order[b.status] || 0);
                      })
                      .map(item => (
                        <tr key={item.capid} className={`border-t border-slate-100 ${item.status === 'not_started' ? 'bg-red-50/30' : ''}`}>
                          <td className="p-3">
                            <div className="font-medium text-sm">{item.name}</div>
                            <div className="text-xs text-slate-400">{item.capid} {item.flight && `- ${item.flight}`}</div>
                          </td>
                          <td className="p-3">
                            <span className={`text-xs px-1.5 py-0.5 rounded ${item.participant_type === 'Student' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'}`}>
                              {item.participant_type}
                            </span>
                          </td>
                          <td className="p-3 text-center">
                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                              item.status === 'reviewed' ? 'bg-blue-100 text-blue-700' :
                              item.status === 'submitted' ? 'bg-emerald-100 text-emerald-700' :
                              'bg-red-100 text-red-700'
                            }`}>
                              {item.status === 'not_started' ? 'Missing' : item.status}
                            </span>
                          </td>
                          {Object.keys(otcDashboard.medication_labels || {}).map(med => (
                            <td key={med} className="p-1 text-center">
                              {item.medications ? (
                                item.medications[med] ? (
                                  <CheckCircle className="w-4 h-4 text-emerald-500 mx-auto" />
                                ) : (
                                  <XCircle className="w-4 h-4 text-red-400 mx-auto" />
                                )
                              ) : (
                                <span className="text-slate-200">-</span>
                              )}
                            </td>
                          ))}
                          <td className="p-3 text-xs text-slate-500">{item.parent_name || '-'}</td>
                          <td className="p-3 text-center">
                            {item.status === 'submitted' && (
                              <Button size="sm" variant="outline" className="text-xs h-7 rounded-sm"
                                onClick={() => reviewOtcForm(item.capid)} data-testid={`review-otc-${item.capid}`}>
                                Review
                              </Button>
                            )}
                            {item.status === 'reviewed' && (
                              <span className="text-xs text-blue-600">Reviewed</span>
                            )}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>)}
        </div>
      )}

      {/* Medical Roster Tab */}
      {activeTab === 'medical-roster' && (
        <MedicalRosterTab hasFullAccess={hasFullAccess()} />
      )}

      {/* Dashboard Tab */}
      {activeTab === 'dashboard' && (<>

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
                      key={`due-${med.cadet_id_internal}-${med.medication_name}-${idx}`} 
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
                    key={`overdue-${med.cadet_id_internal}-${med.medication_name}-${idx}`} 
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
                    key={`oinc-${inc.cadet_id_internal}-${inc.incident_date}-${idx}`} 
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

      </>)}

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
                  <div key={log.id || `audit-${log.changed_at}-${idx}`} className="p-3 border border-slate-200 rounded-sm text-sm">
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
