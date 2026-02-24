import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  getScoreCategories, seedDefaultCategories, recordScore, getScores, deleteScore,
  recordMeritDemerit, getMeritDemerits, getFlightLeaderboard, getSquadronLeaderboard,
  getIndividualLeaderboard, getDailyWinners, getCumulativeStandings, getPointsSummary,
  getParticipants
} from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { toast } from 'sonner';
import { 
  Trophy, 
  Star, 
  Medal,
  Plus,
  Minus,
  Award,
  Users,
  TrendingUp,
  Calendar,
  RefreshCw,
  ChevronRight,
  Target,
  Zap,
  Crown,
  Shield
} from 'lucide-react';

const PointsPage = () => {
  const { canEdit, user } = useAuth();
  const [activeTab, setActiveTab] = useState('leaderboard');
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState([]);
  const [participants, setParticipants] = useState([]);
  const [standings, setStandings] = useState(null);
  const [dailyWinners, setDailyWinners] = useState(null);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [recentScores, setRecentScores] = useState([]);
  const [recentMerits, setRecentMerits] = useState([]);
  
  // Score entry form
  const [scoreForm, setScoreForm] = useState({
    category_id: '',
    target_type: 'flight',
    target_id: '',
    points: '',
    date: new Date().toISOString().split('T')[0],
    notes: ''
  });
  
  // Merit/Demerit form
  const [meritForm, setMeritForm] = useState({
    participant_id: '',
    entry_type: 'merit',
    points: '',
    reason: '',
    date: new Date().toISOString().split('T')[0]
  });

  const [isScoreModalOpen, setIsScoreModalOpen] = useState(false);
  const [isMeritModalOpen, setIsMeritModalOpen] = useState(false);

  const allFlights = [
    { value: 'alpha', label: 'Alpha Flight', squadron: 'sq1' },
    { value: 'bravo', label: 'Bravo Flight', squadron: 'sq1' },
    { value: 'charlie', label: 'Charlie Flight', squadron: 'sq2' },
    { value: 'delta', label: 'Delta Flight', squadron: 'sq2' },
    { value: 'echo', label: 'Echo Flight', squadron: 'sq3' },
    { value: 'foxtrot', label: 'Foxtrot Flight', squadron: 'sq3' }
  ];

  const allSquadrons = [
    { value: 'sq1', label: 'Squadron 1' },
    { value: 'sq2', label: 'Squadron 2' },
    { value: 'sq3', label: 'Squadron 3' }
  ];

  // Permission helpers - determines which flights/squadrons user can edit
  const hasFullAccess = () => {
    // Commanders and Executive Cadre have full access to all flights
    return ['commander', 'exec_cadre'].includes(user?.role);
  };

  const getUserAssignedFlights = () => {
    // Get flights the user is assigned to (Training Officers, etc.)
    if (hasFullAccess()) {
      return allFlights;
    }
    // User can only edit their assigned flight
    if (user?.flight) {
      return allFlights.filter(f => f.value === user.flight);
    }
    return [];
  };

  const getUserAssignedSquadrons = () => {
    if (hasFullAccess()) {
      return allSquadrons;
    }
    // Get squadron based on user's flight assignment
    if (user?.flight) {
      const flight = allFlights.find(f => f.value === user.flight);
      if (flight) {
        return allSquadrons.filter(s => s.value === flight.squadron);
      }
    }
    if (user?.squadron && ['sq1', 'sq2', 'sq3'].includes(user.squadron)) {
      return allSquadrons.filter(s => s.value === user.squadron);
    }
    return [];
  };

  const canEditFlight = (flightValue) => {
    if (hasFullAccess()) return true;
    return user?.flight === flightValue;
  };

  const canEditSquadron = (squadronValue) => {
    if (hasFullAccess()) return true;
    const userFlights = getUserAssignedFlights();
    return userFlights.some(f => f.squadron === squadronValue);
  };

  // Get accessible flights and squadrons for the current user
  const flights = getUserAssignedFlights();
  const squadrons = getUserAssignedSquadrons();

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (selectedDate) {
      loadDailyWinners();
    }
  }, [selectedDate]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [cats, standings, participants, scores, merits] = await Promise.all([
        getScoreCategories(),
        getCumulativeStandings(),
        getParticipants(),
        getScores({ limit: 20 }),
        getMeritDemerits({ limit: 20 })
      ]);
      setCategories(cats);
      setStandings(standings);
      setParticipants(participants.filter(p => !p.is_removed));
      setRecentScores(scores.slice(0, 10));
      setRecentMerits(merits.slice(0, 10));
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const loadDailyWinners = async () => {
    try {
      const winners = await getDailyWinners(selectedDate);
      setDailyWinners(winners);
    } catch (error) {
      console.error('Failed to load daily winners');
    }
  };

  const handleSeedCategories = async () => {
    try {
      const result = await seedDefaultCategories();
      toast.success(result.message);
      loadData();
    } catch (error) {
      toast.error('Failed to seed categories');
    }
  };

  const handleRecordScore = async (e) => {
    e.preventDefault();
    if (!scoreForm.category_id || !scoreForm.target_id || !scoreForm.points) {
      toast.error('Please fill all required fields');
      return;
    }
    
    try {
      const targetName = scoreForm.target_type === 'flight' 
        ? flights.find(f => f.value === scoreForm.target_id)?.label
        : scoreForm.target_type === 'squadron'
        ? squadrons.find(s => s.value === scoreForm.target_id)?.label
        : participants.find(p => p.id === scoreForm.target_id)?.first_name + ' ' + participants.find(p => p.id === scoreForm.target_id)?.last_name;
      
      await recordScore({
        ...scoreForm,
        target_name: targetName,
        points: parseFloat(scoreForm.points)
      });
      toast.success('Score recorded');
      setIsScoreModalOpen(false);
      setScoreForm({
        category_id: '',
        target_type: 'flight',
        target_id: '',
        points: '',
        date: new Date().toISOString().split('T')[0],
        notes: ''
      });
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record score');
    }
  };

  const handleRecordMerit = async (e) => {
    e.preventDefault();
    if (!meritForm.participant_id || !meritForm.points || !meritForm.reason) {
      toast.error('Please fill all required fields');
      return;
    }
    
    try {
      const participant = participants.find(p => p.id === meritForm.participant_id);
      await recordMeritDemerit({
        ...meritForm,
        participant_name: participant ? `${participant.first_name} ${participant.last_name}` : '',
        points: parseFloat(meritForm.points)
      });
      toast.success(`${meritForm.entry_type === 'merit' ? 'Merit' : 'Demerit'} recorded`);
      setIsMeritModalOpen(false);
      setMeritForm({
        participant_id: '',
        entry_type: 'merit',
        points: '',
        reason: '',
        date: new Date().toISOString().split('T')[0]
      });
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record');
    }
  };

  const getRankColor = (rank) => {
    switch(rank) {
      case 1: return 'bg-yellow-400 text-yellow-900';
      case 2: return 'bg-slate-300 text-slate-800';
      case 3: return 'bg-amber-600 text-white';
      default: return 'bg-slate-100 text-slate-600';
    }
  };

  const getFlightColor = (flight) => {
    const colors = {
      'alpha': 'bg-red-100 text-red-700 border-red-200',
      'bravo': 'bg-blue-100 text-blue-700 border-blue-200',
      'charlie': 'bg-green-100 text-green-700 border-green-200',
      'delta': 'bg-purple-100 text-purple-700 border-purple-200',
      'echo': 'bg-orange-100 text-orange-700 border-orange-200',
      'foxtrot': 'bg-pink-100 text-pink-700 border-pink-200'
    };
    return colors[flight?.toLowerCase()] || 'bg-slate-100 text-slate-700';
  };

  const canEnterScores = () => {
    const allowedRoles = ['commander', 'staff', 'plans_programs', 'exec_cadre'];
    if (!allowedRoles.includes(user?.role)) return false;
    // Full access roles can always enter scores
    if (hasFullAccess()) return true;
    // Other roles need a flight assignment to enter scores
    return flights.length > 0;
  };

  const getPermissionLabel = () => {
    if (hasFullAccess()) {
      return 'Full Access - All Flights';
    }
    if (flights.length > 0) {
      return `Assigned: ${flights.map(f => f.label).join(', ')}`;
    }
    return 'No flight assigned';
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-400">Loading point tracking...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <Trophy className="w-8 h-8 text-yellow-500" />
          <div>
            <h1 className="text-2xl lg:text-3xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Point Tracking
            </h1>
            <p className="text-slate-500 text-sm">Track scores, awards, and standings</p>
            {canEnterScores() && (
              <p className={`text-xs mt-1 px-2 py-0.5 rounded-full inline-block ${
                hasFullAccess() 
                  ? 'bg-emerald-100 text-emerald-700' 
                  : 'bg-blue-100 text-blue-700'
              }`}>
                {getPermissionLabel()}
              </p>
            )}
          </div>
        </div>
        <div className="flex gap-2 flex-wrap">
          {canEnterScores() && (
            <>
              <Dialog open={isScoreModalOpen} onOpenChange={setIsScoreModalOpen}>
                <DialogTrigger asChild>
                  <Button className="rounded-sm bg-[#00205B] hover:bg-[#001540]" data-testid="record-score-btn">
                    <Target className="w-4 h-4 mr-2" />
                    Record Score
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-md">
                  <DialogHeader>
                    <DialogTitle>Record Score</DialogTitle>
                  </DialogHeader>
                  <form onSubmit={handleRecordScore} className="space-y-4">
                    <div>
                      <Label>Category *</Label>
                      <Select
                        value={scoreForm.category_id}
                        onValueChange={(v) => setScoreForm({...scoreForm, category_id: v})}
                      >
                        <SelectTrigger className="mt-1 rounded-sm">
                          <SelectValue placeholder="Select category" />
                        </SelectTrigger>
                        <SelectContent>
                          {categories.map(cat => (
                            <SelectItem key={cat.id} value={cat.id}>
                              {cat.name} ({cat.category_type})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label>Target Type *</Label>
                      <Select
                        value={scoreForm.target_type}
                        onValueChange={(v) => setScoreForm({...scoreForm, target_type: v, target_id: ''})}
                      >
                        <SelectTrigger className="mt-1 rounded-sm">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="flight">Flight</SelectItem>
                          <SelectItem value="squadron">Squadron</SelectItem>
                          <SelectItem value="individual">Individual</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label>Target *</Label>
                      <Select
                        value={scoreForm.target_id}
                        onValueChange={(v) => setScoreForm({...scoreForm, target_id: v})}
                      >
                        <SelectTrigger className="mt-1 rounded-sm">
                          <SelectValue placeholder="Select target" />
                        </SelectTrigger>
                        <SelectContent>
                          {scoreForm.target_type === 'flight' && flights.map(f => (
                            <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
                          ))}
                          {scoreForm.target_type === 'squadron' && squadrons.map(s => (
                            <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                          ))}
                          {scoreForm.target_type === 'individual' && participants.map(p => (
                            <SelectItem key={p.id} value={p.id}>
                              {p.rank} {p.first_name} {p.last_name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label>Points *</Label>
                        <Input
                          type="number"
                          value={scoreForm.points}
                          onChange={(e) => setScoreForm({...scoreForm, points: e.target.value})}
                          className="mt-1 rounded-sm"
                          placeholder="0-100"
                        />
                      </div>
                      <div>
                        <Label>Date *</Label>
                        <Input
                          type="date"
                          value={scoreForm.date}
                          onChange={(e) => setScoreForm({...scoreForm, date: e.target.value})}
                          className="mt-1 rounded-sm"
                        />
                      </div>
                    </div>
                    <div>
                      <Label>Notes</Label>
                      <Textarea
                        value={scoreForm.notes}
                        onChange={(e) => setScoreForm({...scoreForm, notes: e.target.value})}
                        className="mt-1 rounded-sm"
                        rows={2}
                      />
                    </div>
                    <div className="flex justify-end gap-2 pt-2">
                      <Button type="button" variant="outline" onClick={() => setIsScoreModalOpen(false)}>Cancel</Button>
                      <Button type="submit" className="bg-[#00205B]">Record Score</Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>

              <Dialog open={isMeritModalOpen} onOpenChange={setIsMeritModalOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline" className="rounded-sm" data-testid="record-merit-btn">
                    <Zap className="w-4 h-4 mr-2" />
                    Merit/Demerit
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-md">
                  <DialogHeader>
                    <DialogTitle>Record Merit or Demerit</DialogTitle>
                  </DialogHeader>
                  <form onSubmit={handleRecordMerit} className="space-y-4">
                    <div>
                      <Label>Type *</Label>
                      <Select
                        value={meritForm.entry_type}
                        onValueChange={(v) => setMeritForm({...meritForm, entry_type: v})}
                      >
                        <SelectTrigger className="mt-1 rounded-sm">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="merit">
                            <span className="flex items-center gap-2 text-emerald-600">
                              <Plus className="w-4 h-4" /> Merit (+)
                            </span>
                          </SelectItem>
                          <SelectItem value="demerit">
                            <span className="flex items-center gap-2 text-red-600">
                              <Minus className="w-4 h-4" /> Demerit (-)
                            </span>
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label>Participant *</Label>
                      <Select
                        value={meritForm.participant_id}
                        onValueChange={(v) => setMeritForm({...meritForm, participant_id: v})}
                      >
                        <SelectTrigger className="mt-1 rounded-sm">
                          <SelectValue placeholder="Select participant" />
                        </SelectTrigger>
                        <SelectContent>
                          {participants.map(p => (
                            <SelectItem key={p.id} value={p.id}>
                              {p.rank} {p.first_name} {p.last_name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label>Points *</Label>
                        <Input
                          type="number"
                          value={meritForm.points}
                          onChange={(e) => setMeritForm({...meritForm, points: e.target.value})}
                          className="mt-1 rounded-sm"
                          placeholder="5, 10, 15..."
                          min="1"
                        />
                      </div>
                      <div>
                        <Label>Date *</Label>
                        <Input
                          type="date"
                          value={meritForm.date}
                          onChange={(e) => setMeritForm({...meritForm, date: e.target.value})}
                          className="mt-1 rounded-sm"
                        />
                      </div>
                    </div>
                    <div>
                      <Label>Reason *</Label>
                      <Textarea
                        value={meritForm.reason}
                        onChange={(e) => setMeritForm({...meritForm, reason: e.target.value})}
                        className="mt-1 rounded-sm"
                        rows={2}
                        placeholder="Describe why this merit/demerit is being awarded..."
                      />
                    </div>
                    <div className="flex justify-end gap-2 pt-2">
                      <Button type="button" variant="outline" onClick={() => setIsMeritModalOpen(false)}>Cancel</Button>
                      <Button 
                        type="submit" 
                        className={meritForm.entry_type === 'merit' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-red-600 hover:bg-red-700'}
                      >
                        Record {meritForm.entry_type === 'merit' ? 'Merit' : 'Demerit'}
                      </Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>
            </>
          )}
          <Button variant="outline" onClick={loadData} className="rounded-sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Seed categories if none exist */}
      {categories.length === 0 && canEnterScores() && (
        <div className="bg-amber-50 border border-amber-200 rounded-sm p-4 mb-6 flex items-center justify-between">
          <div>
            <p className="font-medium text-amber-800">No score categories configured</p>
            <p className="text-sm text-amber-600">Seed default categories to get started</p>
          </div>
          <Button onClick={handleSeedCategories} className="bg-amber-600 hover:bg-amber-700">
            <Plus className="w-4 h-4 mr-2" />
            Seed Default Categories
          </Button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-slate-200 overflow-x-auto">
        {[
          { id: 'leaderboard', label: 'Leaderboard', icon: Trophy },
          { id: 'daily', label: 'Daily Awards', icon: Award },
          { id: 'individuals', label: 'Individual Rankings', icon: Medal },
          { id: 'history', label: 'Score History', icon: TrendingUp }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeTab === tab.id
                ? 'border-[#00205B] text-[#00205B]'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Leaderboard Tab */}
      {activeTab === 'leaderboard' && standings && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Flight Standings */}
          <div className="bg-white border border-slate-200 rounded-sm">
            <div className="border-b border-slate-100 p-4 flex items-center gap-2">
              <Shield className="w-5 h-5 text-[#00205B]" />
              <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm">Flight Standings</h2>
            </div>
            <div className="p-4">
              {standings.flights.length === 0 ? (
                <p className="text-center text-slate-400 py-8">No scores recorded yet</p>
              ) : (
                <div className="space-y-3">
                  {standings.flights.map((flight, idx) => (
                    <div key={flight.flight} className="flex items-center gap-3 p-3 rounded-sm bg-slate-50 hover:bg-slate-100 transition-colors">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${getRankColor(flight.rank)}`}>
                        {flight.rank}
                      </div>
                      <div className="flex-1">
                        <p className={`font-bold uppercase text-sm px-2 py-0.5 rounded inline-block ${getFlightColor(flight.flight)}`}>
                          {flight.flight}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-[#00205B]">{flight.total_points.toFixed(0)}</p>
                        <p className="text-xs text-slate-400">points</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Squadron Standings */}
          <div className="bg-white border border-slate-200 rounded-sm">
            <div className="border-b border-slate-100 p-4 flex items-center gap-2">
              <Users className="w-5 h-5 text-[#00205B]" />
              <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm">Squadron Standings</h2>
            </div>
            <div className="p-4">
              {standings.squadrons.length === 0 ? (
                <p className="text-center text-slate-400 py-8">No scores recorded yet</p>
              ) : (
                <div className="space-y-3">
                  {standings.squadrons.map((sq) => (
                    <div key={sq.squadron} className="flex items-center gap-3 p-3 rounded-sm bg-slate-50 hover:bg-slate-100 transition-colors">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${getRankColor(sq.rank)}`}>
                        {sq.rank}
                      </div>
                      <div className="flex-1">
                        <p className="font-bold text-[#00205B]">{sq.squadron}</p>
                        <p className="text-xs text-slate-400">{sq.flights?.join(', ')}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-[#00205B]">{sq.total_points.toFixed(0)}</p>
                        <p className="text-xs text-slate-400">points</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Top Cadets */}
          <div className="bg-white border border-slate-200 rounded-sm">
            <div className="border-b border-slate-100 p-4 flex items-center gap-2">
              <Star className="w-5 h-5 text-yellow-500" />
              <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm">Top Cadets</h2>
            </div>
            <div className="p-4">
              {standings.top_cadets.length === 0 ? (
                <p className="text-center text-slate-400 py-8">No individual scores yet</p>
              ) : (
                <div className="space-y-2">
                  {standings.top_cadets.slice(0, 5).map((cadet) => (
                    <div key={cadet.participant_id} className="flex items-center gap-3 p-2 rounded-sm hover:bg-slate-50">
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${getRankColor(cadet.rank)}`}>
                        {cadet.rank}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate">{cadet.name}</p>
                        <p className="text-xs text-slate-400">{cadet.flight}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-bold text-[#00205B]">{cadet.total_points.toFixed(0)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Top Cadre */}
          <div className="bg-white border border-slate-200 rounded-sm">
            <div className="border-b border-slate-100 p-4 flex items-center gap-2">
              <Crown className="w-5 h-5 text-purple-500" />
              <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm">Top Cadre</h2>
            </div>
            <div className="p-4">
              {standings.top_cadre.length === 0 ? (
                <p className="text-center text-slate-400 py-8">No cadre scores yet</p>
              ) : (
                <div className="space-y-2">
                  {standings.top_cadre.slice(0, 5).map((cadre) => (
                    <div key={cadre.participant_id} className="flex items-center gap-3 p-2 rounded-sm hover:bg-slate-50">
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${getRankColor(cadre.rank)}`}>
                        {cadre.rank}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate">{cadre.name}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-bold text-[#00205B]">{cadre.total_points.toFixed(0)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Daily Awards Tab */}
      {activeTab === 'daily' && (
        <div className="space-y-6">
          {/* Date Selector */}
          <div className="flex items-center gap-4">
            <Label className="font-bold">Select Date:</Label>
            <Input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-48 rounded-sm"
            />
          </div>

          {/* Daily Winners */}
          {dailyWinners && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Flight of the Day */}
              <div className="bg-gradient-to-br from-yellow-50 to-amber-50 border border-yellow-200 rounded-sm p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Trophy className="w-5 h-5 text-yellow-600" />
                  <h3 className="font-bold text-yellow-800 uppercase text-sm">Flight of the Day</h3>
                </div>
                {dailyWinners.flight_of_day ? (
                  <div className="text-center">
                    <p className={`text-2xl font-black uppercase ${getFlightColor(dailyWinners.flight_of_day.flight)}`}>
                      {dailyWinners.flight_of_day.flight}
                    </p>
                    <p className="text-lg font-bold text-yellow-700 mt-1">
                      {dailyWinners.flight_of_day.total_points.toFixed(0)} pts
                    </p>
                  </div>
                ) : (
                  <p className="text-center text-yellow-600 text-sm">No scores for this date</p>
                )}
              </div>

              {/* Squadron of the Day */}
              <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-sm p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Shield className="w-5 h-5 text-blue-600" />
                  <h3 className="font-bold text-blue-800 uppercase text-sm">Squadron of the Day</h3>
                </div>
                {dailyWinners.squadron_of_day ? (
                  <div className="text-center">
                    <p className="text-2xl font-black text-blue-700">
                      {dailyWinners.squadron_of_day.squadron}
                    </p>
                    <p className="text-lg font-bold text-blue-600 mt-1">
                      {dailyWinners.squadron_of_day.total_points.toFixed(0)} pts
                    </p>
                  </div>
                ) : (
                  <p className="text-center text-blue-600 text-sm">No scores for this date</p>
                )}
              </div>

              {/* Cadet of the Day */}
              <div className="bg-gradient-to-br from-emerald-50 to-green-50 border border-emerald-200 rounded-sm p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Star className="w-5 h-5 text-emerald-600" />
                  <h3 className="font-bold text-emerald-800 uppercase text-sm">Cadet of the Day</h3>
                </div>
                {dailyWinners.cadet_of_day ? (
                  <div className="text-center">
                    <p className="text-lg font-black text-emerald-700">
                      {dailyWinners.cadet_of_day.name}
                    </p>
                    <p className="text-sm text-emerald-600">{dailyWinners.cadet_of_day.flight}</p>
                    <p className="text-lg font-bold text-emerald-600 mt-1">
                      {dailyWinners.cadet_of_day.total_points.toFixed(0)} pts
                    </p>
                  </div>
                ) : (
                  <p className="text-center text-emerald-600 text-sm">No scores for this date</p>
                )}
              </div>

              {/* Cadre of the Day */}
              <div className="bg-gradient-to-br from-purple-50 to-violet-50 border border-purple-200 rounded-sm p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Crown className="w-5 h-5 text-purple-600" />
                  <h3 className="font-bold text-purple-800 uppercase text-sm">Cadre of the Day</h3>
                </div>
                {dailyWinners.cadre_of_day ? (
                  <div className="text-center">
                    <p className="text-lg font-black text-purple-700">
                      {dailyWinners.cadre_of_day.name}
                    </p>
                    <p className="text-lg font-bold text-purple-600 mt-1">
                      {dailyWinners.cadre_of_day.total_points.toFixed(0)} pts
                    </p>
                  </div>
                ) : (
                  <p className="text-center text-purple-600 text-sm">No scores for this date</p>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Individuals Tab */}
      {activeTab === 'individuals' && standings && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Full Cadet Rankings */}
          <div className="bg-white border border-slate-200 rounded-sm">
            <div className="border-b border-slate-100 p-4 flex items-center gap-2">
              <Star className="w-5 h-5 text-yellow-500" />
              <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm">Cadet Rankings</h2>
            </div>
            <div className="p-4 max-h-[500px] overflow-y-auto">
              {standings.top_cadets.length === 0 ? (
                <p className="text-center text-slate-400 py-8">No individual scores yet</p>
              ) : (
                <div className="space-y-2">
                  {standings.top_cadets.map((cadet) => (
                    <div key={cadet.participant_id} className="flex items-center gap-3 p-3 rounded-sm bg-slate-50 hover:bg-slate-100">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${getRankColor(cadet.rank)}`}>
                        {cadet.rank}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{cadet.name}</p>
                        <div className="flex items-center gap-2 text-xs text-slate-400">
                          <span className={`px-1.5 py-0.5 rounded ${getFlightColor(cadet.flight)}`}>{cadet.flight || '-'}</span>
                          {cadet.merit_points > 0 && <span className="text-emerald-600">+{cadet.merit_points} merits</span>}
                          {cadet.demerit_points > 0 && <span className="text-red-500">-{cadet.demerit_points} demerits</span>}
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-xl font-bold text-[#00205B]">{cadet.total_points.toFixed(0)}</p>
                        <p className="text-xs text-slate-400">points</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Full Cadre Rankings */}
          <div className="bg-white border border-slate-200 rounded-sm">
            <div className="border-b border-slate-100 p-4 flex items-center gap-2">
              <Crown className="w-5 h-5 text-purple-500" />
              <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm">Cadre Rankings</h2>
            </div>
            <div className="p-4 max-h-[500px] overflow-y-auto">
              {standings.top_cadre.length === 0 ? (
                <p className="text-center text-slate-400 py-8">No cadre scores yet</p>
              ) : (
                <div className="space-y-2">
                  {standings.top_cadre.map((cadre) => (
                    <div key={cadre.participant_id} className="flex items-center gap-3 p-3 rounded-sm bg-slate-50 hover:bg-slate-100">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${getRankColor(cadre.rank)}`}>
                        {cadre.rank}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{cadre.name}</p>
                        <div className="flex items-center gap-2 text-xs text-slate-400">
                          {cadre.merit_points > 0 && <span className="text-emerald-600">+{cadre.merit_points} merits</span>}
                          {cadre.demerit_points > 0 && <span className="text-red-500">-{cadre.demerit_points} demerits</span>}
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-xl font-bold text-[#00205B]">{cadre.total_points.toFixed(0)}</p>
                        <p className="text-xs text-slate-400">points</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Scores */}
          <div className="bg-white border border-slate-200 rounded-sm">
            <div className="border-b border-slate-100 p-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-[#00205B]" />
              <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm">Recent Scores</h2>
            </div>
            <div className="p-4 max-h-[400px] overflow-y-auto">
              {recentScores.length === 0 ? (
                <p className="text-center text-slate-400 py-8">No scores recorded yet</p>
              ) : (
                <div className="space-y-2">
                  {recentScores.map((score) => (
                    <div key={score.id} className="p-3 bg-slate-50 rounded-sm">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-sm">{score.target_name || score.target_id}</p>
                          <p className="text-xs text-slate-400">{score.category_name}</p>
                        </div>
                        <div className="text-right">
                          <p className="font-bold text-[#00205B]">+{score.points}</p>
                          <p className="text-xs text-slate-400">{score.date}</p>
                        </div>
                      </div>
                      {score.notes && <p className="text-xs text-slate-500 mt-1">{score.notes}</p>}
                      <p className="text-xs text-slate-300 mt-1">by {score.entered_by}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Recent Merits/Demerits */}
          <div className="bg-white border border-slate-200 rounded-sm">
            <div className="border-b border-slate-100 p-4 flex items-center gap-2">
              <Zap className="w-5 h-5 text-yellow-500" />
              <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm">Recent Merits/Demerits</h2>
            </div>
            <div className="p-4 max-h-[400px] overflow-y-auto">
              {recentMerits.length === 0 ? (
                <p className="text-center text-slate-400 py-8">No merits/demerits recorded yet</p>
              ) : (
                <div className="space-y-2">
                  {recentMerits.map((entry) => (
                    <div key={entry.id} className={`p-3 rounded-sm ${entry.entry_type === 'merit' ? 'bg-emerald-50' : 'bg-red-50'}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-sm">{entry.participant_name}</p>
                          <p className="text-xs text-slate-500">{entry.reason}</p>
                        </div>
                        <div className="text-right">
                          <p className={`font-bold ${entry.entry_type === 'merit' ? 'text-emerald-600' : 'text-red-600'}`}>
                            {entry.entry_type === 'merit' ? '+' : '-'}{entry.points}
                          </p>
                          <p className="text-xs text-slate-400">{entry.date}</p>
                        </div>
                      </div>
                      <p className="text-xs text-slate-300 mt-1">by {entry.entered_by}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PointsPage;
