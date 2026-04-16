import React, { useState, useEffect, useMemo } from 'react';
import { getDetailedAnalytics, getPendingPayments, exportAnalytics, exportAnalyticsSummary } from '../services/api';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { 
  Users, 
  UserCheck, 
  BarChart3, 
  PieChart,
  MapPin,
  Calendar,
  DollarSign,
  Mail,
  Phone,
  AlertCircle,
  Download,
  RefreshCw,
  FileSpreadsheet,
  FileText
} from 'lucide-react';

const AnalyticsPage = () => {
  const [analytics, setAnalytics] = useState(null);
  const [pendingPayments, setPendingPayments] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [exporting, setExporting] = useState(false);

  // Memoize expensive sort/entries computations
  const sortedRanks = useMemo(() => analytics ? Object.entries(analytics.by_rank).sort((a, b) => b[1] - a[1]) : [], [analytics]);
  const sortedWings = useMemo(() => analytics ? Object.entries(analytics.by_wing).sort((a, b) => b[1] - a[1]) : [], [analytics]);
  const sortedRegions = useMemo(() => analytics ? Object.entries(analytics.by_region).sort((a, b) => b[1] - a[1]) : [], [analytics]);
  const sortedGroups = useMemo(() => analytics ? Object.entries(analytics.by_group).sort((a, b) => a[0].localeCompare(b[0])) : [], [analytics]);
  const sortedSquadrons = useMemo(() => analytics ? Object.entries(analytics.by_squadron).sort((a, b) => b[1] - a[1]) : [], [analytics]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [analyticsData, paymentsData] = await Promise.all([
        getDetailedAnalytics(),
        getPendingPayments()
      ]);
      setAnalytics(analyticsData);
      setPendingPayments(paymentsData);
    } catch (error) {
      toast.error('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (type) => {
    setExporting(true);
    try {
      let response;
      let filename;
      
      if (type === 'csv') {
        response = await exportAnalytics('csv');
        filename = `cap_analytics_${new Date().toISOString().split('T')[0]}.csv`;
      } else if (type === 'excel') {
        response = await exportAnalytics('excel');
        filename = `cap_analytics_${new Date().toISOString().split('T')[0]}.xlsx`;
      } else if (type === 'full-report') {
        response = await exportAnalyticsSummary();
        filename = `cap_full_report_${new Date().toISOString().split('T')[0]}.xlsx`;
      }
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success(`Exported successfully: ${filename}`);
    } catch (error) {
      toast.error('Failed to export data');
    } finally {
      setExporting(false);
    }
  };

  const formatPercent = (value) => `${value}%`;

  if (loading) {
    return (
      <div className="p-6 lg:p-8 animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-6 h-6 animate-spin text-slate-400" />
        </div>
      </div>
    );
  }

  // Handle null, error, or missing data
  if (!analytics || analytics.error) {
    return (
      <div className="p-6 lg:p-8 animate-fade-in">
        <div className="text-center py-12">
          <AlertCircle className="w-12 h-12 mx-auto text-slate-400 mb-4" />
          <p className="text-slate-500">No analytics data available. Import a roster first.</p>
        </div>
      </div>
    );
  }

  // Helper function to safely get nested values with defaults
  const safeGet = (obj, path, defaultValue = 0) => {
    return path.split('.').reduce((acc, part) => acc?.[part], obj) ?? defaultValue;
  };

  return (
    <div className="p-6 lg:p-8 animate-fade-in overflow-visible">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl lg:text-3xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Encampment Analytics
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            {analytics.total_count || 0} total participants
          </p>
        </div>
        <div className="flex flex-wrap gap-2 items-center overflow-visible">
          {/* Export Dropdown */}
          <div className="relative group">
            <Button 
              variant="outline" 
              className="rounded-sm border-emerald-600 text-emerald-600 hover:bg-emerald-50"
              disabled={exporting}
              data-testid="export-dropdown-btn"
            >
              <Download className="w-4 h-4 mr-2" />
              {exporting ? 'Exporting...' : 'Export'}
            </Button>
            <div className="absolute right-0 mt-1 w-48 bg-white border border-slate-200 rounded-sm shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
              <button
                onClick={() => handleExport('csv')}
                className="w-full px-4 py-2 text-left text-sm hover:bg-slate-50 flex items-center gap-2"
                data-testid="export-csv-btn"
              >
                <FileText className="w-4 h-4 text-slate-400" />
                Export as CSV
              </button>
              <button
                onClick={() => handleExport('excel')}
                className="w-full px-4 py-2 text-left text-sm hover:bg-slate-50 flex items-center gap-2"
                data-testid="export-excel-btn"
              >
                <FileSpreadsheet className="w-4 h-4 text-emerald-500" />
                Export as Excel
              </button>
              <div className="border-t border-slate-100" />
              <button
                onClick={() => handleExport('full-report')}
                className="w-full px-4 py-2 text-left text-sm hover:bg-slate-50 flex items-center gap-2"
                data-testid="export-full-report-btn"
              >
                <FileSpreadsheet className="w-4 h-4 text-blue-500" />
                Full Report (Multi-sheet)
              </button>
            </div>
          </div>
          <Button 
            variant="outline" 
            className="rounded-sm border-[#00205B] text-[#00205B]"
            onClick={loadData}
            data-testid="refresh-analytics-btn"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-slate-200">
        {[
          { id: 'overview', label: 'Overview' },
          { id: 'demographics', label: 'Demographics' },
          { id: 'distribution', label: 'Distribution' },
          { id: 'pending', label: `Pending Payments (${pendingPayments?.count || 0})` }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.id 
                ? 'text-[#00205B] border-b-2 border-[#00205B] -mb-px' 
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Role Counts */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white border border-slate-200 rounded-sm p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">Seniors</p>
                  <p className="text-3xl font-bold text-[#00205B]">{safeGet(analytics, 'by_role.seniors.count', 0)}</p>
                  <p className="text-xs text-slate-400 mt-1">Senior Members</p>
                </div>
                <UserCheck className="w-8 h-8 text-[#00205B]/20" />
              </div>
            </div>
            
            <div className="bg-white border border-slate-200 rounded-sm p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">Staff</p>
                  <p className="text-3xl font-bold text-amber-600">{safeGet(analytics, 'by_role.staff.count', 0)}</p>
                  <p className="text-xs text-slate-400 mt-1">Avg age: {safeGet(analytics, 'by_role.staff.avg_age', null) || 'N/A'}</p>
                </div>
                <Users className="w-8 h-8 text-amber-600/20" />
              </div>
            </div>
            
            <div className="bg-white border border-slate-200 rounded-sm p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">Cadre</p>
                  <p className="text-3xl font-bold text-emerald-600">{safeGet(analytics, 'by_role.cadre.count', 0)}</p>
                  <p className="text-xs text-slate-400 mt-1">Avg age: {safeGet(analytics, 'by_role.cadre.avg_age', null) || 'N/A'}</p>
                </div>
                <Users className="w-8 h-8 text-emerald-600/20" />
              </div>
            </div>
            
            <div className="bg-white border border-slate-200 rounded-sm p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">Students</p>
                  <p className="text-3xl font-bold text-blue-600">{safeGet(analytics, 'by_role.students.count', 0)}</p>
                  <p className="text-xs text-slate-400 mt-1">Avg age: {safeGet(analytics, 'by_role.students.avg_age', null) || 'N/A'}</p>
                </div>
                <Users className="w-8 h-8 text-blue-600/20" />
              </div>
            </div>
          </div>

          {/* Age Statistics */}
          <div className="bg-white border border-slate-200 rounded-sm p-4">
            <h3 className="font-bold text-[#00205B] uppercase text-sm tracking-wide mb-4 flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              Cadet Age Statistics
            </h3>
            <p className="text-xs text-slate-400 mb-3">Excludes Senior Members</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-3 bg-slate-50 rounded">
                <p className="text-xs uppercase text-slate-500">Average Age</p>
                <p className="text-2xl font-bold text-[#00205B]">{safeGet(analytics, 'age_stats.total.avg', null) || 'N/A'}</p>
              </div>
              <div className="text-center p-3 bg-slate-50 rounded">
                <p className="text-xs uppercase text-slate-500">Youngest</p>
                <p className="text-2xl font-bold text-emerald-600">{safeGet(analytics, 'age_stats.total.min', null) || 'N/A'}</p>
              </div>
              <div className="text-center p-3 bg-slate-50 rounded">
                <p className="text-xs uppercase text-slate-500">Oldest</p>
                <p className="text-2xl font-bold text-amber-600">{safeGet(analytics, 'age_stats.total.max', null) || 'N/A'}</p>
              </div>
              <div className="text-center p-3 bg-slate-50 rounded">
                <p className="text-xs uppercase text-slate-500">Age Range</p>
                <p className="text-2xl font-bold text-slate-700">
                  {safeGet(analytics, 'age_stats.total.max', null) && safeGet(analytics, 'age_stats.total.min', null) 
                    ? `${analytics.age_stats.total.max - analytics.age_stats.total.min} yrs`
                    : 'N/A'}
                </p>
              </div>
            </div>
          </div>

          {/* Gender by Role */}
          <div className="bg-white border border-slate-200 rounded-sm p-4">
            <h3 className="font-bold text-[#00205B] uppercase text-sm tracking-wide mb-4 flex items-center gap-2">
              <PieChart className="w-4 h-4" />
              Gender Distribution by Role
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-2 px-3 font-medium text-slate-600">Role</th>
                    <th className="text-center py-2 px-3 font-medium text-slate-600">Total</th>
                    <th className="text-center py-2 px-3 font-medium text-blue-600">Male</th>
                    <th className="text-center py-2 px-3 font-medium text-pink-600">Female</th>
                    <th className="text-center py-2 px-3 font-medium text-slate-600">M %</th>
                    <th className="text-center py-2 px-3 font-medium text-slate-600">F %</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { name: 'Staff', key: 'staff', color: 'bg-amber-50' },
                    { name: 'Cadre', key: 'cadre', color: 'bg-emerald-50' },
                    { name: 'Students', key: 'students', color: 'bg-blue-50' },
                  ].map(({ name, key, color }) => {
                    const data = analytics.by_role?.[key] || { count: 0, male: 0, female: 0, male_pct: 0, female_pct: 0 };
                    return (
                      <tr key={name} className={`border-b border-slate-100 ${color}`}>
                        <td className="py-2 px-3 font-medium">{name}</td>
                        <td className="py-2 px-3 text-center font-bold">{data.count || 0}</td>
                        <td className="py-2 px-3 text-center text-blue-600">{data.male || 0}</td>
                        <td className="py-2 px-3 text-center text-pink-600">{data.female || 0}</td>
                        <td className="py-2 px-3 text-center">
                          <span className="inline-block bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-xs font-mono">
                            {formatPercent(data.male_pct || 0)}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-center">
                          <span className="inline-block bg-pink-100 text-pink-700 px-2 py-0.5 rounded text-xs font-mono">
                            {formatPercent(data.female_pct || 0)}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Demographics Tab */}
      {activeTab === 'demographics' && (
        <div className="space-y-6">
          {/* Gender Overview */}
          <div className="bg-white border border-slate-200 rounded-sm p-4">
            <h3 className="font-bold text-[#00205B] uppercase text-sm tracking-wide mb-4">
              Overall Gender Distribution
            </h3>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-blue-600 font-medium">Male</span>
                  <span className="font-mono">{analytics.by_gender?.M || 0}</span>
                </div>
                <div className="h-4 bg-slate-100 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-blue-500 rounded-full transition-all"
                    style={{ width: `${analytics.total_count > 0 ? ((analytics.by_gender?.M || 0) / analytics.total_count) * 100 : 0}%` }}
                  />
                </div>
              </div>
              <div className="flex-1">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-pink-600 font-medium">Female</span>
                  <span className="font-mono">{analytics.by_gender?.F || 0}</span>
                </div>
                <div className="h-4 bg-slate-100 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-pink-500 rounded-full transition-all"
                    style={{ width: `${analytics.total_count > 0 ? ((analytics.by_gender?.F || 0) / analytics.total_count) * 100 : 0}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Rank Distribution */}
          <div className="bg-white border border-slate-200 rounded-sm p-4">
            <h3 className="font-bold text-[#00205B] uppercase text-sm tracking-wide mb-4 flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Rank Distribution
            </h3>
            {Object.keys(analytics.by_rank || {}).length > 0 ? (
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
                {sortedRanks.map(([rank, count]) => (
                    <div key={rank} className="bg-slate-50 p-3 rounded text-center">
                      <p className="text-xs uppercase text-slate-500 truncate">{rank}</p>
                      <p className="text-xl font-bold text-[#00205B]">{count}</p>
                    </div>
                  ))}
              </div>
            ) : (
              <p className="text-slate-400 text-sm text-center py-4">No rank data available</p>
            )}
          </div>

          {/* Average Age by Squadron/Flight */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white border border-slate-200 rounded-sm p-4">
              <h3 className="font-bold text-[#00205B] uppercase text-sm tracking-wide mb-4">
                Average Age by Squadron
              </h3>
              {Object.keys(analytics.age_stats?.by_squadron || {}).length > 0 ? (
                <div className="space-y-2">
                  {Object.entries(analytics.age_stats.by_squadron).map(([sq, avg]) => (
                    <div key={sq} className="flex items-center justify-between py-2 border-b border-slate-100">
                      <span className="font-medium">{sq}</span>
                      <span className="bg-[#00205B] text-white px-2 py-0.5 rounded text-sm font-mono">{avg}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-slate-400 text-sm">No squadron assignments yet</p>
              )}
            </div>

            <div className="bg-white border border-slate-200 rounded-sm p-4">
              <h3 className="font-bold text-[#00205B] uppercase text-sm tracking-wide mb-4">
                Average Age by Flight
              </h3>
              {Object.keys(analytics.age_stats?.by_flight || {}).length > 0 ? (
                <div className="space-y-2">
                  {Object.entries(analytics.age_stats.by_flight).map(([fl, avg]) => (
                    <div key={fl} className="flex items-center justify-between py-2 border-b border-slate-100">
                      <span className="font-medium">{fl}</span>
                      <span className="bg-emerald-600 text-white px-2 py-0.5 rounded text-sm font-mono">{avg}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-slate-400 text-sm">No flight assignments yet</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Distribution Tab */}
      {activeTab === 'distribution' && (
        <div className="space-y-6">
          {/* Wing Distribution */}
          <div className="bg-white border border-slate-200 rounded-sm p-4">
            <h3 className="font-bold text-[#00205B] uppercase text-sm tracking-wide mb-4 flex items-center gap-2">
              <MapPin className="w-4 h-4" />
              Wing Distribution
            </h3>
            {Object.keys(analytics.by_wing || {}).length > 0 ? (
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
                {sortedWings.map(([wing, count]) => (
                    <div key={wing} className="bg-slate-50 p-3 rounded text-center">
                      <p className="text-xs uppercase text-slate-500">{wing}</p>
                      <p className="text-xl font-bold text-[#00205B]">{count}</p>
                      <p className="text-xs text-slate-400">
                        {analytics.total_count > 0 ? ((count / analytics.total_count) * 100).toFixed(0) : 0}%
                      </p>
                    </div>
                  ))}
              </div>
            ) : (
              <p className="text-slate-400 text-sm text-center py-4">No wing data available</p>
            )}
          </div>

          {/* Region Distribution */}
          <div className="bg-white border border-slate-200 rounded-sm p-4">
            <h3 className="font-bold text-[#00205B] uppercase text-sm tracking-wide mb-4">
              Region Distribution
            </h3>
            {Object.keys(analytics.by_region || {}).length > 0 ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {sortedRegions.map(([region, count]) => (
                    <div key={region} className="bg-slate-50 p-3 rounded text-center">
                      <p className="text-xs uppercase text-slate-500">{region}</p>
                      <p className="text-xl font-bold text-[#00205B]">{count}</p>
                    </div>
                  ))}
              </div>
            ) : (
              <p className="text-slate-400 text-sm text-center py-4">No region data available</p>
            )}
          </div>

          {/* TN Group Distribution */}
          {Object.keys(analytics.by_group || {}).length > 0 && (
            <div className="bg-white border border-slate-200 rounded-sm p-4">
              <h3 className="font-bold text-[#00205B] uppercase text-sm tracking-wide mb-4">
                Tennessee Group Distribution
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                {sortedGroups.map(([group, count]) => (
                    <div key={group} className="bg-amber-50 border border-amber-200 p-3 rounded text-center">
                      <p className="text-xs uppercase text-amber-700">{group}</p>
                      <p className="text-xl font-bold text-amber-800">{count}</p>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Squadron/Flight Distribution */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white border border-slate-200 rounded-sm p-4">
              <h3 className="font-bold text-[#00205B] uppercase text-sm tracking-wide mb-4">
                Squadron Distribution
              </h3>
              {Object.keys(analytics.by_squadron || {}).length > 0 ? (
                <div className="space-y-2">
                  {sortedSquadrons.map(([sq, count]) => (
                      <div key={sq} className="flex items-center gap-2">
                        <span className="flex-1 text-sm">{sq}</span>
                        <div className="flex-1 bg-slate-100 rounded-full h-4 overflow-hidden">
                          <div 
                            className="h-full bg-[#00205B] rounded-full"
                            style={{ width: `${analytics.total_count > 0 ? (count / analytics.total_count) * 100 : 0}%` }}
                          />
                        </div>
                        <span className="text-sm font-mono w-8 text-right">{count}</span>
                      </div>
                    ))}
                </div>
              ) : (
                <p className="text-slate-400 text-sm text-center py-4">No squadron assignments yet</p>
              )}
            </div>

            <div className="bg-white border border-slate-200 rounded-sm p-4">
              <h3 className="font-bold text-[#00205B] uppercase text-sm tracking-wide mb-4">
                Flight Distribution
              </h3>
              {Object.keys(analytics.by_flight || {}).length > 0 ? (
                <div className="space-y-2">
                  {Object.entries(analytics.by_flight)
                    .sort((a, b) => b[1] - a[1])
                    .map(([fl, count]) => (
                      <div key={fl} className="flex items-center gap-2">
                        <span className="flex-1 text-sm">{fl}</span>
                        <div className="flex-1 bg-slate-100 rounded-full h-4 overflow-hidden">
                          <div 
                            className="h-full bg-emerald-500 rounded-full"
                            style={{ width: `${analytics.total_count > 0 ? (count / analytics.total_count) * 100 : 0}%` }}
                          />
                        </div>
                        <span className="text-sm font-mono w-8 text-right">{count}</span>
                      </div>
                    ))}
                </div>
              ) : (
                <p className="text-slate-400 text-sm text-center py-4">No flight assignments yet</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Pending Payments Tab */}
      {activeTab === 'pending' && (
        <div className="space-y-6">
          <div className="bg-amber-50 border border-amber-200 rounded-sm p-4">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-amber-600" />
              <div>
                <p className="font-medium text-amber-800">
                  {pendingPayments?.count || 0} Participants with Pending Payments
                </p>
                <p className="text-sm text-amber-600">
                  Contact information provided for follow-up
                </p>
              </div>
            </div>
          </div>

          {pendingPayments?.participants?.length > 0 ? (
            <div className="bg-white border border-slate-200 rounded-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="text-left py-3 px-4 font-medium text-slate-600">CAPID</th>
                      <th className="text-left py-3 px-4 font-medium text-slate-600">Name</th>
                      <th className="text-left py-3 px-4 font-medium text-slate-600">Type</th>
                      <th className="text-left py-3 px-4 font-medium text-slate-600">Unit</th>
                      <th className="text-left py-3 px-4 font-medium text-slate-600">Email</th>
                      <th className="text-left py-3 px-4 font-medium text-slate-600">Phone</th>
                      <th className="text-left py-3 px-4 font-medium text-slate-600">Parent Contact</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pendingPayments.participants.map((p, idx) => (
                      <tr key={p.capid || `pay-${idx}`} className="border-t border-slate-100 hover:bg-slate-50">
                        <td className="py-3 px-4 font-mono text-[#00205B]">{p.capid}</td>
                        <td className="py-3 px-4">
                          <span className="font-medium">{p.name}</span>
                          <br />
                          <span className="text-xs text-slate-400">{p.rank}</span>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            p.participant_type === 'staff' ? 'bg-amber-100 text-amber-700' :
                            p.participant_type === 'cadre' ? 'bg-emerald-100 text-emerald-700' :
                            'bg-blue-100 text-blue-700'
                          }`}>
                            {p.participant_type}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-sm">{p.unit}</td>
                        <td className="py-3 px-4">
                          {p.email ? (
                            <a href={`mailto:${p.email}`} className="text-[#00205B] hover:underline flex items-center gap-1">
                              <Mail className="w-3 h-3" />
                              {p.email}
                            </a>
                          ) : '-'}
                        </td>
                        <td className="py-3 px-4">
                          {p.phone ? (
                            <a href={`tel:${p.phone}`} className="text-[#00205B] hover:underline flex items-center gap-1">
                              <Phone className="w-3 h-3" />
                              {p.phone}
                            </a>
                          ) : '-'}
                        </td>
                        <td className="py-3 px-4 text-xs">
                          {p.parent_email && (
                            <a href={`mailto:${p.parent_email}`} className="text-[#00205B] hover:underline block">
                              {p.parent_email}
                            </a>
                          )}
                          {p.parent_phone && (
                            <a href={`tel:${p.parent_phone}`} className="text-slate-500 hover:underline">
                              {p.parent_phone}
                            </a>
                          )}
                          {!p.parent_email && !p.parent_phone && '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="bg-white border border-slate-200 rounded-sm p-8 text-center">
              <DollarSign className="w-12 h-12 mx-auto text-emerald-500 mb-4" />
              <p className="text-lg font-medium text-emerald-600">All payments collected!</p>
              <p className="text-slate-500 text-sm">No pending payments at this time.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AnalyticsPage;
