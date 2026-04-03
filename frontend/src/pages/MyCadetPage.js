import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { useAuth } from '../context/AuthContext';
import { User, Calendar, Heart, Award, Utensils, CheckCircle2, AlertTriangle, Clock, MapPin, Shield } from 'lucide-react';

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
          <div className="w-14 h-14 rounded-full bg-white/20 flex items-center justify-center">
            <Shield className="w-7 h-7" />
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
        <TabsList className="w-full bg-slate-100 rounded-sm">
          <TabsTrigger value="overview" className="flex-1 text-xs" data-testid="tab-overview">Overview</TabsTrigger>
          <TabsTrigger value="schedule" className="flex-1 text-xs" data-testid="tab-schedule">Schedule</TabsTrigger>
          <TabsTrigger value="health" className="flex-1 text-xs" data-testid="tab-health">Health</TabsTrigger>
          <TabsTrigger value="points" className="flex-1 text-xs" data-testid="tab-points">Points</TabsTrigger>
          <TabsTrigger value="meals" className="flex-1 text-xs" data-testid="tab-meals">Meals</TabsTrigger>
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
                    <div key={i} className="p-3 bg-red-50 rounded-sm border border-red-100">
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
                    <Badge key={i} variant="outline" className="text-xs">{a.allergen || a.allergy_name} ({a.allergy_type || 'general'})</Badge>
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
                    <div key={i} className="p-2 bg-slate-50 rounded-sm text-sm">
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
                    <div key={i} className="flex items-center gap-2 p-2 bg-amber-50 rounded-sm border border-amber-100">
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
                    <div key={i} className="flex justify-between items-center p-2 text-sm border-b border-slate-100 last:border-0">
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
                    <Badge key={i} className="bg-amber-100 text-amber-800 text-xs">{d}</Badge>
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
                    <Badge key={i} variant="outline" className="text-xs">{a}</Badge>
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
                    <div key={i} className="p-3 bg-slate-50 rounded-sm border border-slate-100">
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
      </Tabs>
    </div>
  );
}
