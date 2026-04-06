import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { useAuth } from '../context/AuthContext';
import { User, Calendar, Heart, Award, Utensils, CheckCircle2, AlertTriangle, Clock, MapPin, Shield, FileCheck, Pill, Camera } from 'lucide-react';
import { toast } from 'sonner';
import { uploadCadetPhoto, getCadetPhotoUrl, deleteCadetPhoto } from '../services/api';

const API = process.env.REACT_APP_BACKEND_URL;

export default function MyCadetPage() {
  const { token } = useAuth();
  const [cadet, setCadet] = useState(null);
  const [schedule, setSchedule] = useState(null);
  const [health, setHealth] = useState(null);
  const [points, setPoints] = useState(null);
  const [meals, setMeals] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  // OTC form state
  const [otcData, setOtcData] = useState(null);
  const [otcLoading, setOtcLoading] = useState(false);
  const [otcSubmitting, setOtcSubmitting] = useState(false);
  const [photoUploading, setPhotoUploading] = useState(false);
  const [otcForm, setOtcForm] = useState({
    parent_name: '', parent_relationship: '', parent_phone: '', parent_email: '',
    medications: {},
    ack_otc_only: false, ack_staff_discretion: false,
    ack_prescription_separate: false, ack_accurate_info: false,
    notes_for_hso: '', signature: '',
  });

  const headers = { Authorization: `Bearer ${token}` };

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [cadetRes, schedRes, healthRes, pointsRes, mealsRes] = await Promise.all([
        fetch(`${API}/api/parent/my-cadet`, { headers }),
        fetch(`${API}/api/parent/my-cadet/schedule`, { headers }),
        fetch(`${API}/api/parent/my-cadet/health-incidents`, { headers }),
        fetch(`${API}/api/parent/my-cadet/points`, { headers }),
        fetch(`${API}/api/parent/my-cadet/meals`, { headers }),
      ]);

      if (!cadetRes.ok) {
        const err = await cadetRes.json();
        throw new Error(err.detail || 'Failed to load cadet data');
      }

      setCadet(await cadetRes.json());
      setSchedule(await schedRes.json());
      setHealth(await healthRes.json());
      setPoints(await pointsRes.json());
      setMeals(await mealsRes.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const loadOtcForm = useCallback(async () => {
    if (!token) return;
    setOtcLoading(true);
    try {
      const res = await fetch(`${API}/api/parent/my-cadet/otc-permission`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setOtcData(data);
        // Pre-fill form if already submitted
        if (data.form) {
          setOtcForm({
            parent_name: data.form.parent_name || '',
            parent_relationship: data.form.parent_relationship || '',
            parent_phone: data.form.parent_phone || '',
            parent_email: data.form.parent_email || '',
            medications: data.form.medications || {},
            ack_otc_only: data.form.ack_otc_only || false,
            ack_staff_discretion: data.form.ack_staff_discretion || false,
            ack_prescription_separate: data.form.ack_prescription_separate || false,
            ack_accurate_info: data.form.ack_accurate_info || false,
            notes_for_hso: data.form.notes_for_hso || '',
            signature: data.form.signature || '',
          });
        }
      }
    } catch (e) {
      console.error('Failed to load OTC form:', e);
    } finally {
      setOtcLoading(false);
    }
  }, [token]);

  const submitOtcForm = async () => {
    // Client-side validation
    if (!otcForm.parent_name || !otcForm.parent_relationship || !otcForm.parent_phone || !otcForm.parent_email) {
      toast.error('Please fill in all parent/guardian information');
      return;
    }
    const medsList = otcData?.medications_list || [];
    const unanswered = medsList.filter(m => otcForm.medications[m] === undefined || otcForm.medications[m] === null);
    if (unanswered.length > 0) {
      toast.error(`Please answer all medication questions. Missing: ${unanswered.map(m => otcData.medication_labels[m]).join(', ')}`);
      return;
    }
    if (!otcForm.ack_otc_only || !otcForm.ack_staff_discretion || !otcForm.ack_prescription_separate || !otcForm.ack_accurate_info) {
      toast.error('Please accept all required acknowledgments');
      return;
    }
    if (!otcForm.signature || otcForm.signature.trim().length < 2) {
      toast.error('Typed signature is required');
      return;
    }
    setOtcSubmitting(true);
    try {
      const res = await fetch(`${API}/api/parent/my-cadet/otc-permission`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(otcForm),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Submission failed');
      toast.success('OTC Permission Form submitted successfully');
      loadOtcForm();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setOtcSubmitting(false);
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-[60vh]" data-testid="my-cadet-loading">
      <div className="animate-spin rounded-full h-8 w-8 border-2 border-[#00205B] border-t-transparent" />
    </div>
  );

  if (error) return (
    <div className="max-w-2xl mx-auto mt-12 p-6 bg-red-50 border border-red-200 rounded-sm" data-testid="my-cadet-error">
      <h2 className="text-lg font-bold text-red-800 mb-2">Unable to Load Cadet Information</h2>
      <p className="text-red-700">{error}</p>
      <p className="text-sm text-red-600 mt-3">Please ensure your CAPID is correctly linked to your account. Contact administration if this persists.</p>
    </div>
  );

  if (!cadet) return null;

  const flightColors = {
    alpha: 'bg-red-100 text-red-800', bravo: 'bg-blue-100 text-blue-800',
    charlie: 'bg-green-100 text-green-800', delta: 'bg-yellow-100 text-yellow-800',
    echo: 'bg-purple-100 text-purple-800', foxtrot: 'bg-orange-100 text-orange-800',
  };

  const checkSteps = ['arrival', 'paperwork', 'bunk_assignment', 'gear_issue'];
  const stepLabels = { arrival: 'Arrival', paperwork: 'Paperwork', bunk_assignment: 'Bunk Assignment', gear_issue: 'Gear Issue' };
  const completedSteps = checkSteps.filter(s => cadet.check_in?.[s]?.completed).length;

  return (
    <div className="space-y-6" data-testid="my-cadet-page">
      {/* Cadet Header */}
      <div className="bg-[#00205B] text-white p-6 rounded-sm">
        <div className="flex items-center gap-4">
          <div className="relative group">
            {cadet.photo_path ? (
              <img
                src={getCadetPhotoUrl(cadet.id)}
                alt={`${cadet.first_name} ${cadet.last_name}`}
                className="w-16 h-16 rounded-full object-cover border-2 border-white/30"
                data-testid="cadet-photo"
                onError={(e) => {
                  e.target.style.display = 'none';
                  e.target.nextSibling.style.display = 'flex';
                }}
              />
            ) : null}
            <div 
              className={`w-16 h-16 rounded-full bg-white/20 items-center justify-center text-xl font-bold ${cadet.photo_path ? 'hidden' : 'flex'}`}
              data-testid="cadet-initials-avatar"
            >
              {cadet.first_name?.charAt(0)}{cadet.last_name?.charAt(0)}
            </div>
            <label className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-full opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer" data-testid="parent-upload-photo">
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                disabled={photoUploading}
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  setPhotoUploading(true);
                  try {
                    await uploadCadetPhoto(cadet.id, file);
                    toast.success('Photo uploaded successfully!');
                    setCadet(prev => ({ ...prev, photo_path: 'uploaded' }));
                  } catch (err) {
                    toast.error(err?.response?.data?.detail || 'Failed to upload photo');
                  } finally {
                    setPhotoUploading(false);
                  }
                }}
              />
              {photoUploading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <Camera className="w-5 h-5 text-white" />
              )}
            </label>
          </div>
          <div className="flex-1">
            <h1 className="text-xl font-bold" data-testid="cadet-name">
              {cadet.rank} {cadet.first_name} {cadet.last_name}
            </h1>
            <div className="flex items-center gap-3 mt-1 text-sm text-white/80">
              <span>CAPID: {cadet.capid}</span>
              {cadet.flight && (
                <Badge className={`${flightColors[cadet.flight] || 'bg-white/20 text-white'} text-xs`}>
                  {cadet.flight.charAt(0).toUpperCase() + cadet.flight.slice(1)} Flight
                </Badge>
              )}
              {cadet.squadron && <span>{cadet.squadron.replace('_', ' ').toUpperCase()}</span>}
            </div>
            <p className="text-xs text-white/50 mt-1">Hover on photo to update</p>
          </div>
        </div>
      </div>

      {/* Quick Status Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="border-none shadow-sm">
          <CardContent className="p-4 text-center">
            <CheckCircle2 className={`w-6 h-6 mx-auto mb-1 ${completedSteps === 4 ? 'text-green-600' : 'text-amber-500'}`} />
            <div className="text-lg font-bold">{completedSteps}/4</div>
            <div className="text-xs text-slate-500">Check-in Steps</div>
          </CardContent>
        </Card>
        <Card className="border-none shadow-sm">
          <CardContent className="p-4 text-center">
            <Award className="w-6 h-6 mx-auto mb-1 text-[#00205B]" />
            <div className="text-lg font-bold">{points?.total_points || 0}</div>
            <div className="text-xs text-slate-500">Points</div>
          </CardContent>
        </Card>
        <Card className="border-none shadow-sm">
          <CardContent className="p-4 text-center">
            <Heart className={`w-6 h-6 mx-auto mb-1 ${(health?.incidents?.length || 0) > 0 ? 'text-red-500' : 'text-green-600'}`} />
            <div className="text-lg font-bold">{health?.incidents?.length || 0}</div>
            <div className="text-xs text-slate-500">Health Incidents</div>
          </CardContent>
        </Card>
        <Card className="border-none shadow-sm">
          <CardContent className="p-4 text-center">
            <Utensils className="w-6 h-6 mx-auto mb-1 text-amber-600" />
            <div className="text-lg font-bold">{meals?.dietary_restrictions?.length || 0}</div>
            <div className="text-xs text-slate-500">Dietary Notes</div>
          </CardContent>
        </Card>
      </div>

      {/* Tabbed Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="w-full bg-slate-100 rounded-sm flex-wrap h-auto">
          <TabsTrigger value="overview" className="flex-1 text-xs" data-testid="tab-overview">Overview</TabsTrigger>
          <TabsTrigger value="schedule" className="flex-1 text-xs" data-testid="tab-schedule">Schedule</TabsTrigger>
          <TabsTrigger value="health" className="flex-1 text-xs" data-testid="tab-health">Health</TabsTrigger>
          <TabsTrigger value="points" className="flex-1 text-xs" data-testid="tab-points">Points</TabsTrigger>
          <TabsTrigger value="meals" className="flex-1 text-xs" data-testid="tab-meals">Meals</TabsTrigger>
          <TabsTrigger value="otc" className="flex-1 text-xs" data-testid="tab-otc"
            onClick={() => { if (!otcData) loadOtcForm(); }}
          >
            OTC Meds
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4 mt-4">
          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm font-semibold text-slate-700">Cadet Information</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                {[
                  ['Unit', cadet.unit], ['Wing', cadet.wing], ['Gender', cadet.gender],
                  ['Age', cadet.age], ['Type', cadet.participant_type],
                ].map(([label, val]) => val && (
                  <div key={label}><span className="text-slate-500 text-xs uppercase">{label}</span><div className="font-medium">{val}</div></div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm font-semibold text-slate-700">Check-In Progress</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {checkSteps.map(step => {
                  const done = cadet.check_in?.[step]?.completed;
                  return (
                    <div key={step} className={`p-3 rounded-sm text-center text-xs font-medium ${done ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-slate-50 text-slate-400 border border-slate-200'}`}>
                      {done ? <CheckCircle2 className="w-4 h-4 mx-auto mb-1" /> : <Clock className="w-4 h-4 mx-auto mb-1" />}
                      {stepLabels[step]}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {cadet.barracks && (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm font-semibold text-slate-700">Barracks Assignment</CardTitle></CardHeader>
              <CardContent className="text-sm">
                <span className="font-medium">{cadet.barracks.barracks_id}</span> - Bunk {cadet.barracks.bunk_number} ({cadet.barracks.position})
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Schedule Tab */}
        <TabsContent value="schedule" className="mt-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold text-slate-700">
                {cadet.flight ? `${cadet.flight.charAt(0).toUpperCase() + cadet.flight.slice(1)} Flight Schedule` : 'Schedule'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!schedule?.events?.length ? (
                <p className="text-sm text-slate-500">No scheduled events yet.</p>
              ) : (
                <div className="space-y-2 max-h-[60vh] overflow-y-auto">
                  {schedule.events.map((e, i) => (
                    <div key={e.id || i} className="flex items-start gap-3 p-3 bg-slate-50 rounded-sm border border-slate-100 hover:bg-slate-100 transition-colors">
                      <div className="text-center min-w-[50px]">
                        {e.day_number && <div className="text-xs text-slate-400 uppercase">Day {e.day_number}</div>}
                        <div className="text-xs font-mono text-slate-600">{e.start_time?.slice(0, 5)}</div>
                      </div>
                      <div className="flex-1">
                        <div className="font-medium text-sm">{e.title}</div>
                        <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
                          {e.location && <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{e.location}</span>}
                          {e.uniform && <Badge variant="outline" className="text-xs py-0">{e.uniform}</Badge>}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Health Tab */}
        <TabsContent value="health" className="space-y-4 mt-4">
          {(health?.incidents?.length > 0) && (
            <Card className="border-red-200">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold text-red-700 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" /> Health Incidents
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {health.incidents.map((inc, i) => (
                    <div key={inc.id || `incident-${i}`} className="p-3 bg-red-50 rounded-sm border border-red-100">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-sm">{inc.incident_type || inc.type || 'Incident'}</span>
                        <Badge variant={inc.severity === 'critical' ? 'destructive' : 'outline'} className="text-xs">
                          {inc.severity || 'Unknown'}
                        </Badge>
                      </div>
                      {inc.description && <p className="text-xs text-slate-600 mt-1">{inc.description}</p>}
                      {inc.treatment && <p className="text-xs text-green-700 mt-1">Treatment: {inc.treatment}</p>}
                      <div className="text-xs text-slate-400 mt-1">{new Date(inc.created_at).toLocaleString()}</div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm font-semibold text-slate-700">Allergies</CardTitle></CardHeader>
            <CardContent>
              {!health?.allergies?.length ? <p className="text-sm text-slate-500">No allergies on record.</p> : (
                <div className="flex flex-wrap gap-2">
                  {health.allergies.map((a, i) => (
                    <Badge key={`allergy-${a.allergen || a.allergy_name}-${i}`} variant="outline" className="text-xs">{a.allergen || a.allergy_name} ({a.allergy_type || 'general'})</Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm font-semibold text-slate-700">Prescriptions</CardTitle></CardHeader>
            <CardContent>
              {!health?.prescriptions?.length ? <p className="text-sm text-slate-500">No prescriptions on record.</p> : (
                <div className="space-y-2">
                  {health.prescriptions.map((p, i) => (
                    <div key={`rx-${p.medication_name || p.name}-${i}`} className="p-2 bg-slate-50 rounded-sm text-sm">
                      <span className="font-medium">{p.medication_name || p.name}</span>
                      {p.dosage && <span className="text-slate-500 ml-2">{p.dosage}</span>}
                      {p.frequency && <span className="text-slate-400 ml-2">({p.frequency})</span>}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Points Tab */}
        <TabsContent value="points" className="space-y-4 mt-4">
          <div className="grid grid-cols-3 gap-3">
            <Card className="border-none shadow-sm">
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-[#00205B]">{points?.total_points || 0}</div>
                <div className="text-xs text-slate-500">Total Points</div>
              </CardContent>
            </Card>
            <Card className="border-none shadow-sm bg-green-50">
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-green-700">{points?.total_merits || 0}</div>
                <div className="text-xs text-green-600">Merits</div>
              </CardContent>
            </Card>
            <Card className="border-none shadow-sm bg-red-50">
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-red-700">{points?.total_demerits || 0}</div>
                <div className="text-xs text-red-600">Demerits</div>
              </CardContent>
            </Card>
          </div>

          {points?.awards?.length > 0 && (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm font-semibold text-slate-700">Awards</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {points.awards.map((a, i) => (
                    <div key={a.id || `award-${a.award_name || a.name}-${i}`} className="flex items-center gap-2 p-2 bg-amber-50 rounded-sm border border-amber-100">
                      <Award className="w-4 h-4 text-amber-600" />
                      <span className="text-sm font-medium">{a.award_name || a.name}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {points?.entries?.length > 0 && (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm font-semibold text-slate-700">Recent Point Activity</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-1">
                  {points.entries.map((e, i) => (
                    <div key={e.id || `entry-${e.reason || e.category}-${i}`} className="flex justify-between items-center p-2 text-sm border-b border-slate-100 last:border-0">
                      <span className="text-slate-700">{e.reason || e.category || 'Points'}</span>
                      <span className={`font-mono font-bold ${e.points >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {e.points >= 0 ? '+' : ''}{e.points}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Meals Tab */}
        <TabsContent value="meals" className="space-y-4 mt-4">
          {meals?.dietary_restrictions?.length > 0 && (
            <Card className="border-amber-200">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold text-amber-700">Dietary Restrictions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {meals.dietary_restrictions.map((d, i) => (
                    <Badge key={`diet-${d}`} className="bg-amber-100 text-amber-800 text-xs">{d}</Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {meals?.all_allergies?.length > 0 && (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm font-semibold text-slate-700">All Allergies</CardTitle></CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {meals.all_allergies.map((a, i) => (
                    <Badge key={`meal-allergy-${a}`} variant="outline" className="text-xs">{a}</Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm font-semibold text-slate-700">Meal Schedule</CardTitle></CardHeader>
            <CardContent>
              {!meals?.meal_plans?.length ? <p className="text-sm text-slate-500">No meal plans posted yet.</p> : (
                <div className="space-y-3 max-h-[50vh] overflow-y-auto">
                  {meals.meal_plans.map((mp, i) => (
                    <div key={mp.id || `meal-${mp.date || mp.day_number || i}`} className="p-3 bg-slate-50 rounded-sm border border-slate-100">
                      <div className="font-medium text-sm mb-2">{mp.date || `Day ${mp.day_number || i + 1}`}</div>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs">
                        {mp.breakfast && <div><span className="text-slate-400 uppercase">Breakfast:</span> <span className="text-slate-700">{mp.breakfast}</span></div>}
                        {mp.lunch && <div><span className="text-slate-400 uppercase">Lunch:</span> <span className="text-slate-700">{mp.lunch}</span></div>}
                        {mp.dinner && <div><span className="text-slate-400 uppercase">Dinner:</span> <span className="text-slate-700">{mp.dinner}</span></div>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* OTC Medication Permission Form Tab */}
        <TabsContent value="otc" className="space-y-4 mt-4">
          {otcLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-[#00205B] border-t-transparent" />
            </div>
          ) : !otcData ? (
            <Card><CardContent className="p-6 text-center text-slate-500">
              <Pill className="w-8 h-8 mx-auto mb-2 text-slate-300" />
              <p>Loading OTC permission form...</p>
              <Button variant="outline" className="mt-3 rounded-sm" onClick={loadOtcForm} data-testid="load-otc-btn">Load Form</Button>
            </CardContent></Card>
          ) : otcData.form?.status === 'submitted' || otcData.form?.status === 'reviewed' ? (
            /* ---- SUBMITTED STATE ---- */
            <div className="space-y-4">
              <Card className="border-emerald-200 bg-emerald-50">
                <CardContent className="p-4 flex items-center gap-3">
                  <FileCheck className="w-6 h-6 text-emerald-600 flex-shrink-0" />
                  <div>
                    <p className="font-semibold text-emerald-800">OTC Permission Form {otcData.form.status === 'reviewed' ? 'Reviewed' : 'Submitted'}</p>
                    <p className="text-xs text-emerald-700">
                      Signed by {otcData.form.parent_name} on {new Date(otcData.form.submitted_at).toLocaleString()}
                      {otcData.form.reviewed_by && ` — Reviewed by ${otcData.form.reviewed_by}`}
                    </p>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm font-semibold text-slate-700">Medication Permissions</CardTitle></CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {(otcData.medications_list || []).map(med => (
                      <div key={med} className="flex items-center gap-2 p-2 bg-slate-50 rounded-sm border border-slate-100" data-testid={`otc-status-${med}`}>
                        <div className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                          otcData.form.medications[med] ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white'
                        }`}>
                          {otcData.form.medications[med] ? 'Y' : 'N'}
                        </div>
                        <span className="text-sm">{otcData.medication_labels[med]}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
              {otcData.form.notes_for_hso && (
                <Card>
                  <CardHeader className="pb-2"><CardTitle className="text-sm font-semibold text-slate-700">Notes for Health Services</CardTitle></CardHeader>
                  <CardContent><p className="text-sm text-slate-600">{otcData.form.notes_for_hso}</p></CardContent>
                </Card>
              )}
              <Button variant="outline" className="rounded-sm" onClick={() => {
                setOtcData(prev => ({ ...prev, form: null }));
              }} data-testid="otc-edit-btn">Edit & Resubmit</Button>
            </div>
          ) : (
            /* ---- FORM STATE ---- */
            <div className="space-y-5">
              <Card className="border-amber-200 bg-amber-50">
                <CardContent className="p-4 flex items-center gap-3">
                  <AlertTriangle className="w-6 h-6 text-amber-600 flex-shrink-0" />
                  <div>
                    <p className="font-semibold text-amber-800">OTC Permission Form Required</p>
                    <p className="text-xs text-amber-700">Please complete this form to authorize over-the-counter medication use during encampment.</p>
                  </div>
                </CardContent>
              </Card>

              {/* Cadet Info (auto-filled) */}
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm font-semibold text-slate-700">Cadet Information</CardTitle></CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div><span className="text-xs text-slate-400 uppercase">Name</span><div className="font-medium">{otcData.cadet?.name}</div></div>
                    <div><span className="text-xs text-slate-400 uppercase">CAPID</span><div className="font-medium">{otcData.cadet?.capid}</div></div>
                    <div><span className="text-xs text-slate-400 uppercase">Unit</span><div className="font-medium">{otcData.cadet?.unit || '-'}</div></div>
                    <div><span className="text-xs text-slate-400 uppercase">Role</span><div className="font-medium">{otcData.cadet?.role}</div></div>
                  </div>
                </CardContent>
              </Card>

              {/* Parent/Guardian Info */}
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm font-semibold text-slate-700">Parent / Guardian Information</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-medium text-slate-600">Full Name *</label>
                      <Input value={otcForm.parent_name} onChange={e => setOtcForm(f => ({ ...f, parent_name: e.target.value }))}
                        placeholder="Full Name" className="rounded-sm mt-1" data-testid="otc-parent-name" />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-slate-600">Relationship *</label>
                      <Input value={otcForm.parent_relationship} onChange={e => setOtcForm(f => ({ ...f, parent_relationship: e.target.value }))}
                        placeholder="Mother, Father, Guardian..." className="rounded-sm mt-1" data-testid="otc-parent-relationship" />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-slate-600">Phone Number *</label>
                      <Input value={otcForm.parent_phone} onChange={e => setOtcForm(f => ({ ...f, parent_phone: e.target.value }))}
                        placeholder="(555) 555-5555" type="tel" className="rounded-sm mt-1" data-testid="otc-parent-phone" />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-slate-600">Email Address *</label>
                      <Input value={otcForm.parent_email} onChange={e => setOtcForm(f => ({ ...f, parent_email: e.target.value }))}
                        placeholder="email@example.com" type="email" className="rounded-sm mt-1" data-testid="otc-parent-email" />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* OTC Medication Checklist */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-semibold text-slate-700">OTC Medication Approval</CardTitle>
                  <p className="text-xs text-slate-500 mt-1">Select Yes or No for each medication. All must be answered.</p>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {(otcData.medications_list || []).map(med => {
                      const val = otcForm.medications[med];
                      const unanswered = val === undefined || val === null;
                      return (
                        <div key={med} className={`flex items-center justify-between p-3 rounded-sm border transition-colors ${
                          unanswered ? 'border-red-200 bg-red-50/30' :
                          val ? 'border-emerald-200 bg-emerald-50/30' : 'border-slate-200 bg-slate-50/30'
                        }`} data-testid={`otc-med-${med}`}>
                          <span className="font-medium text-sm">{otcData.medication_labels[med]}</span>
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={() => setOtcForm(f => ({ ...f, medications: { ...f.medications, [med]: true } }))}
                              className={`px-4 py-1.5 text-sm font-medium rounded-sm transition-colors ${
                                val === true ? 'bg-emerald-600 text-white shadow-sm' : 'bg-white border border-slate-200 text-slate-600 hover:bg-emerald-50'
                              }`}
                              data-testid={`otc-med-${med}-yes`}
                            >
                              Yes
                            </button>
                            <button
                              type="button"
                              onClick={() => setOtcForm(f => ({ ...f, medications: { ...f.medications, [med]: false } }))}
                              className={`px-4 py-1.5 text-sm font-medium rounded-sm transition-colors ${
                                val === false ? 'bg-red-600 text-white shadow-sm' : 'bg-white border border-slate-200 text-slate-600 hover:bg-red-50'
                              }`}
                              data-testid={`otc-med-${med}-no`}
                            >
                              No
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>

              {/* Acknowledgments */}
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm font-semibold text-slate-700">Required Acknowledgments</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                  {[
                    { key: 'ack_otc_only', text: 'I understand these permissions apply only to over-the-counter medications listed above.' },
                    { key: 'ack_staff_discretion', text: 'I understand encampment health staff will use these medications only if needed and according to encampment procedures.' },
                    { key: 'ack_prescription_separate', text: 'I understand I am responsible for ensuring my cadet\'s prescription medications are separately disclosed and handled according to encampment medication procedures.' },
                    { key: 'ack_accurate_info', text: 'I certify that the information I provided is accurate.' },
                  ].map(ack => (
                    <label key={ack.key} className={`flex items-start gap-3 p-3 rounded-sm border cursor-pointer transition-colors ${
                      otcForm[ack.key] ? 'border-emerald-200 bg-emerald-50/30' : 'border-red-200 bg-red-50/30'
                    }`} data-testid={`otc-${ack.key}`}>
                      <input
                        type="checkbox" checked={otcForm[ack.key]}
                        onChange={e => setOtcForm(f => ({ ...f, [ack.key]: e.target.checked }))}
                        className="mt-0.5 w-4 h-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                      />
                      <span className="text-sm text-slate-700">{ack.text}</span>
                    </label>
                  ))}
                </CardContent>
              </Card>

              {/* Notes for HSO */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-semibold text-slate-700">Notes for Health Services Officer (Optional)</CardTitle>
                  <p className="text-xs text-slate-500 mt-1">Known sensitivities, preferred restrictions, or special instructions</p>
                </CardHeader>
                <CardContent>
                  <Textarea value={otcForm.notes_for_hso} onChange={e => setOtcForm(f => ({ ...f, notes_for_hso: e.target.value }))}
                    placeholder="Any notes for the Health Services team..." rows={3} className="rounded-sm" data-testid="otc-notes" />
                </CardContent>
              </Card>

              {/* Signature */}
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm font-semibold text-slate-700">Authorization & Signature</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm text-slate-600 font-medium">I authorize the selections above for my cadet.</p>
                  <div>
                    <label className="text-xs font-medium text-slate-600">Typed Signature *</label>
                    <Input value={otcForm.signature} onChange={e => setOtcForm(f => ({ ...f, signature: e.target.value }))}
                      placeholder="Type your full name" className="rounded-sm mt-1 font-serif italic text-lg" data-testid="otc-signature" />
                  </div>
                  <p className="text-xs text-slate-400">Date/Time: {new Date().toLocaleString()}</p>
                </CardContent>
              </Card>

              {/* Submit */}
              <Button onClick={submitOtcForm} disabled={otcSubmitting}
                className="w-full bg-[#00205B] hover:bg-[#001845] text-white py-3 rounded-sm text-base font-semibold"
                data-testid="otc-submit-btn"
              >
                {otcSubmitting ? 'Submitting...' : 'Submit OTC Permission Form'}
              </Button>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
