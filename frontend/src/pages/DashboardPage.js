import React, { useState, useEffect } from 'react';
import { getDashboardStats } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { 
  Users, 
  DollarSign, 
  Calendar, 
  TrendingUp, 
  TrendingDown,
  UserCheck,
  UserX
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const DashboardPage = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const data = await getDashboardStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const participantTypeData = stats?.participants?.by_type 
    ? Object.entries(stats.participants.by_type).map(([name, value]) => ({
        name: name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        value
      }))
    : [];

  const genderData = stats?.participants?.by_gender
    ? Object.entries(stats.participants.by_gender).map(([name, value]) => ({
        name: name === 'M' ? 'Male' : name === 'F' ? 'Female' : 'Other',
        value
      }))
    : [];

  const COLORS = ['#00205B', '#BF0D3E', '#475569', '#94A3B8'];

  if (loading) {
    return (
      <div className="p-6 lg:p-8 animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-400">Loading dashboard...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 lg:p-8 animate-fade-in">
      {/* Encampment Banner */}
      <div className="mb-6 rounded-lg overflow-hidden shadow-lg">
        <img 
          src="/encampment-banner.png" 
          alt="2026 Tennessee Wing Encampment" 
          className="w-full h-auto object-cover"
        />
      </div>

      {/* Welcome Message */}
      <div className="mb-8">
        <h1 className="text-xl md:text-2xl lg:text-3xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
          Welcome back, {user?.name?.split(' ')[0]}
        </h1>
        <p className="text-slate-500 text-sm mt-1">
          July 17-24, 2026 • VTS Catoosa, GA
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {/* Total Participants */}
        <div className="bg-white border border-slate-200 rounded-sm p-4" data-testid="stat-total-participants">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">Total Participants</p>
              <p className="text-3xl font-bold text-[#00205B] font-mono">{stats?.participants?.total || 0}</p>
            </div>
            <div className="p-2 bg-[#00205B]/10 rounded-sm">
              <Users className="w-5 h-5 text-[#00205B]" />
            </div>
          </div>
        </div>

        {/* Paid Status */}
        <div className="bg-white border border-slate-200 rounded-sm p-4" data-testid="stat-paid-status">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">Payment Status</p>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold text-emerald-600 font-mono">{stats?.participants?.paid || 0}</span>
                <span className="text-sm text-slate-400">/</span>
                <span className="text-lg text-[#BF0D3E] font-mono">{stats?.participants?.unpaid || 0}</span>
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-1 text-xs text-emerald-600">
                <UserCheck className="w-4 h-4" /> Paid
              </div>
              <div className="flex items-center gap-1 text-xs text-[#BF0D3E]">
                <UserX className="w-4 h-4" /> Unpaid
              </div>
            </div>
          </div>
        </div>

        {/* Budget Estimated */}
        <div className="bg-white border border-slate-200 rounded-sm p-4" data-testid="stat-budget-estimated">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">Budget Estimated</p>
              <p className="text-3xl font-bold text-[#00205B] font-mono">{formatCurrency(stats?.budget?.total_estimated || 0)}</p>
            </div>
            <div className="p-2 bg-[#00205B]/10 rounded-sm">
              <DollarSign className="w-5 h-5 text-[#00205B]" />
            </div>
          </div>
        </div>

        {/* Budget Variance */}
        <div className="bg-white border border-slate-200 rounded-sm p-4" data-testid="stat-budget-variance">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">Budget Variance</p>
              <p className={`text-3xl font-bold font-mono ${(stats?.budget?.variance || 0) >= 0 ? 'text-emerald-600' : 'text-[#BF0D3E]'}`}>
                {formatCurrency(stats?.budget?.variance || 0)}
              </p>
            </div>
            <div className={`p-2 rounded-sm ${(stats?.budget?.variance || 0) >= 0 ? 'bg-emerald-100' : 'bg-red-100'}`}>
              {(stats?.budget?.variance || 0) >= 0 
                ? <TrendingUp className="w-5 h-5 text-emerald-600" />
                : <TrendingDown className="w-5 h-5 text-[#BF0D3E]" />
              }
            </div>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Participant Types */}
        <div className="bg-white border border-slate-200 rounded-sm">
          <div className="border-b border-slate-100 p-4">
            <h2 className="font-bold uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Participants by Type
            </h2>
          </div>
          <div className="p-4">
            {participantTypeData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={participantTypeData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis 
                    dataKey="name" 
                    tick={{ fontSize: 10, fill: '#64748B' }}
                    axisLine={{ stroke: '#E2E8F0' }}
                  />
                  <YAxis 
                    tick={{ fontSize: 10, fill: '#64748B' }}
                    axisLine={{ stroke: '#E2E8F0' }}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#fff', 
                      border: '1px solid #E2E8F0',
                      borderRadius: '2px'
                    }}
                  />
                  <Bar dataKey="value" fill="#00205B" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[250px] flex items-center justify-center text-slate-400">
                No participant data available
              </div>
            )}
          </div>
        </div>

        {/* Gender Distribution */}
        <div className="bg-white border border-slate-200 rounded-sm">
          <div className="border-b border-slate-100 p-4">
            <h2 className="font-bold uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Gender Distribution
            </h2>
          </div>
          <div className="p-4">
            {genderData.some(d => d.value > 0) ? (
              <div className="flex items-center justify-center gap-8">
                <ResponsiveContainer width={200} height={200}>
                  <PieChart>
                    <Pie
                      data={genderData}
                      cx="50%"
                      cy="50%"
                      innerRadius={40}
                      outerRadius={80}
                      dataKey="value"
                      paddingAngle={2}
                    >
                      {genderData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                {/* Legend beside the chart */}
                <div className="space-y-3">
                  {genderData.map((entry, index) => (
                    <div key={entry.name} className="flex items-center gap-3">
                      <div 
                        className="w-4 h-4 rounded-sm" 
                        style={{ backgroundColor: COLORS[index % COLORS.length] }}
                      />
                      <div>
                        <p className="font-medium text-slate-700">{entry.name}</p>
                        <p className="text-sm text-slate-500">
                          {entry.value} ({((entry.value / genderData.reduce((a, b) => a + b.value, 0)) * 100).toFixed(0) || 0}%)
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="h-[200px] flex items-center justify-center text-slate-400">
                No gender data available
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Schedule Info */}
      <div className="bg-white border border-slate-200 rounded-sm">
        <div className="border-b border-slate-100 p-4">
          <h2 className="font-bold uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Schedule Overview
          </h2>
        </div>
        <div className="p-6">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-3">
              <Calendar className="w-8 h-8 text-[#00205B]" />
              <div>
                <p className="text-2xl font-bold text-[#00205B] font-mono">{stats?.schedule?.total_events || 0}</p>
                <p className="text-xs uppercase tracking-wide text-slate-500">Total Events</p>
              </div>
            </div>
            <div className="w-px h-12 bg-slate-200"></div>
            <div>
              <p className="text-2xl font-bold text-emerald-600 font-mono">{stats?.schedule?.upcoming_events || 0}</p>
              <p className="text-xs uppercase tracking-wide text-slate-500">Upcoming Events</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
