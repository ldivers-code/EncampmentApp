import React from 'react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Upload, DollarSign, Search, CheckCircle, AlertCircle } from 'lucide-react';

const PaymentReportsTab = ({
  paymentSummary,
  paymentHistory,
  paymentLoading,
  paymentUploading,
  paymentSearch,
  setPaymentSearch,
  paymentTypeFilter,
  setPaymentTypeFilter,
  paymentStatusFilter,
  setPaymentStatusFilter,
  paymentFlightFilter,
  setPaymentFlightFilter,
  handlePaymentUpload,
  loadPaymentData
}) => {
  return (
    <div className="space-y-6">
      {/* Upload Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-[#00205B]">Daily Payment Reports</h2>
          <p className="text-sm text-slate-500">
            Upload eCAP Event Admin Reports to update payment statuses for all roster members
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="cursor-pointer" data-testid="upload-payment-report">
            <input type="file" accept=".xlsx,.xls" onChange={handlePaymentUpload} className="hidden" />
            <span className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-sm transition-colors ${
              paymentUploading ? 'bg-slate-200 text-slate-500' : 'bg-[#00205B] text-white hover:bg-[#001845]'
            }`}>
              <Upload className="w-4 h-4" />
              {paymentUploading ? 'Importing...' : 'Upload eCAP Report'}
            </span>
          </label>
          <Button variant="outline" size="sm" onClick={loadPaymentData} className="rounded-sm" data-testid="refresh-payments">
            <Search className="w-4 h-4 mr-1" />
            Refresh
          </Button>
        </div>
      </div>

      {paymentLoading ? (
        <div className="text-center py-12 text-slate-400">Loading payment data...</div>
      ) : !paymentSummary ? (
        <div className="text-center py-12 text-slate-400">
          <DollarSign className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="text-lg">No payment data loaded</p>
          <p className="text-sm mt-1">Click Refresh to load or upload an eCAP report</p>
        </div>
      ) : (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-white border border-slate-200 rounded-sm p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Total</p>
              <p className="text-2xl font-bold text-[#00205B]">{paymentSummary.total}</p>
            </div>
            <div className="bg-white border border-emerald-200 rounded-sm p-4">
              <p className="text-xs uppercase tracking-wide text-emerald-600">Paid</p>
              <p className="text-2xl font-bold text-emerald-600">{paymentSummary.paid}</p>
              <p className="text-xs text-slate-400">{paymentSummary.total > 0 ? Math.round(paymentSummary.paid / paymentSummary.total * 100) : 0}%</p>
            </div>
            <div className="bg-white border border-red-200 rounded-sm p-4">
              <p className="text-xs uppercase tracking-wide text-red-600">Unpaid</p>
              <p className="text-2xl font-bold text-red-600">{paymentSummary.unpaid}</p>
            </div>
            <div className="bg-white border border-blue-200 rounded-sm p-4">
              <p className="text-xs uppercase tracking-wide text-blue-600">Unit Approved</p>
              <p className="text-2xl font-bold text-blue-600">{paymentSummary.unit_approved}</p>
            </div>
            <div className="bg-white border border-indigo-200 rounded-sm p-4">
              <p className="text-xs uppercase tracking-wide text-indigo-600">Wing Approved</p>
              <p className="text-2xl font-bold text-indigo-600">{paymentSummary.wing_approved}</p>
            </div>
          </div>

          {/* By Type Breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white border border-slate-200 rounded-sm p-4">
              <h3 className="font-semibold text-sm text-slate-700 mb-3 uppercase tracking-wide">By Participant Type</h3>
              <div className="space-y-2">
                {Object.entries(paymentSummary.by_type).map(([type, data]) => (
                  <div key={type} className="flex items-center justify-between p-2 bg-slate-50 rounded-sm">
                    <span className="text-sm font-medium capitalize">{type.replace(/_/g, ' ')}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-emerald-600 font-mono">{data.paid} paid</span>
                      <span className="text-xs text-red-500 font-mono">{data.unpaid} unpaid</span>
                      <span className="text-xs text-slate-400">/ {data.total}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-sm p-4">
              <h3 className="font-semibold text-sm text-slate-700 mb-3 uppercase tracking-wide">By Flight</h3>
              <div className="space-y-2">
                {Object.entries(paymentSummary.by_flight).map(([flight, data]) => (
                  <div key={flight} className="flex items-center justify-between p-2 bg-slate-50 rounded-sm">
                    <span className="text-sm font-medium capitalize">{flight}</span>
                    <div className="flex items-center gap-3">
                      <div className="w-24 bg-slate-200 rounded-full h-2 overflow-hidden">
                        <div className="bg-emerald-500 h-2 rounded-full" style={{ width: `${data.total > 0 ? (data.paid / data.total * 100) : 0}%` }} />
                      </div>
                      <span className="text-xs font-mono text-slate-600">{data.paid}/{data.total}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Last Import Info */}
          {paymentSummary.last_import && (
            <div className="bg-blue-50 border border-blue-200 rounded-sm p-3 text-sm text-blue-800">
              <span className="font-medium">Last Import:</span> {paymentSummary.last_import.filename} — {paymentSummary.last_import.matched} matched, {paymentSummary.last_import.updated} updated — by {paymentSummary.last_import.imported_by} on {new Date(paymentSummary.last_import.imported_at).toLocaleString()}
            </div>
          )}

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3 py-2 border-y border-slate-200">
            <Input
              placeholder="Search by name, CAPID, or email..."
              value={paymentSearch}
              onChange={(e) => setPaymentSearch(e.target.value)}
              className="w-64 rounded-sm"
              data-testid="payment-search"
            />
            <Select value={paymentTypeFilter} onValueChange={setPaymentTypeFilter}>
              <SelectTrigger className="w-40 rounded-sm" data-testid="payment-type-filter">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="basic_student">Students</SelectItem>
                <SelectItem value="advanced_student">Advanced Students</SelectItem>
                <SelectItem value="cadre">Cadre</SelectItem>
                <SelectItem value="staff">Staff</SelectItem>
                <SelectItem value="senior_member">Senior Members</SelectItem>
              </SelectContent>
            </Select>
            <Select value={paymentStatusFilter} onValueChange={setPaymentStatusFilter}>
              <SelectTrigger className="w-32 rounded-sm" data-testid="payment-status-filter">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="paid">Paid</SelectItem>
                <SelectItem value="unpaid">Unpaid</SelectItem>
              </SelectContent>
            </Select>
            <Select value={paymentFlightFilter} onValueChange={setPaymentFlightFilter}>
              <SelectTrigger className="w-36 rounded-sm" data-testid="payment-flight-filter">
                <SelectValue placeholder="Flight" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Flights</SelectItem>
                <SelectItem value="alpha">Alpha</SelectItem>
                <SelectItem value="bravo">Bravo</SelectItem>
                <SelectItem value="charlie">Charlie</SelectItem>
                <SelectItem value="delta">Delta</SelectItem>
                <SelectItem value="echo">Echo</SelectItem>
                <SelectItem value="foxtrot">Foxtrot</SelectItem>
                <SelectItem value="unassigned">Unassigned</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Individual Payment Table */}
          <div className="bg-white border border-slate-200 rounded-sm overflow-hidden">
            <div className="overflow-x-auto max-h-[50vh] overflow-y-auto">
              <table className="w-full text-sm" data-testid="payment-report-table">
                <thead className="bg-slate-50 sticky top-0 z-10">
                  <tr>
                    <th className="text-left p-3 font-semibold text-slate-600 text-xs uppercase">Name</th>
                    <th className="text-left p-3 font-semibold text-slate-600 text-xs uppercase">CAPID</th>
                    <th className="text-left p-3 font-semibold text-slate-600 text-xs uppercase">Type</th>
                    <th className="text-left p-3 font-semibold text-slate-600 text-xs uppercase">Flight</th>
                    <th className="text-center p-3 font-semibold text-slate-600 text-xs uppercase">Paid</th>
                    <th className="text-center p-3 font-semibold text-slate-600 text-xs uppercase">Status</th>
                    <th className="text-center p-3 font-semibold text-slate-600 text-xs uppercase">Unit</th>
                    <th className="text-center p-3 font-semibold text-slate-600 text-xs uppercase">Wing</th>
                    <th className="text-left p-3 font-semibold text-slate-600 text-xs uppercase">Contact</th>
                  </tr>
                </thead>
                <tbody>
                  {paymentSummary.participants
                    .filter(p => {
                      const search = paymentSearch.toLowerCase();
                      const matchesSearch = !search || p.name?.toLowerCase().includes(search) || p.capid?.includes(search) || p.email?.toLowerCase().includes(search);
                      const matchesType = paymentTypeFilter === 'all' || p.participant_type === paymentTypeFilter;
                      const matchesStatus = paymentStatusFilter === 'all' || (paymentStatusFilter === 'paid' && p.paid) || (paymentStatusFilter === 'unpaid' && !p.paid);
                      const matchesFlight = paymentFlightFilter === 'all' || p.flight === paymentFlightFilter;
                      return matchesSearch && matchesType && matchesStatus && matchesFlight;
                    })
                    .map((p) => (
                      <tr key={p.capid} className="border-t border-slate-100 hover:bg-slate-50">
                        <td className="p-3 font-medium">{p.name}</td>
                        <td className="p-3 font-mono text-xs text-slate-500">{p.capid}</td>
                        <td className="p-3">
                          <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600 capitalize">
                            {p.participant_type?.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="p-3 capitalize text-xs">{p.flight}</td>
                        <td className="p-3 text-center">
                          {p.paid ? (
                            <CheckCircle className="w-4 h-4 text-emerald-500 mx-auto" />
                          ) : (
                            <AlertCircle className="w-4 h-4 text-red-500 mx-auto" />
                          )}
                        </td>
                        <td className="p-3 text-center text-xs">{p.registration_status || '-'}</td>
                        <td className="p-3 text-center">
                          {p.unit_approved ? <span className="text-[10px] px-1 bg-blue-100 text-blue-700 rounded">Yes</span> : <span className="text-slate-300">-</span>}
                        </td>
                        <td className="p-3 text-center">
                          {p.wing_approved ? <span className="text-[10px] px-1 bg-emerald-100 text-emerald-700 rounded">Yes</span> : <span className="text-slate-300">-</span>}
                        </td>
                        <td className="p-3 text-xs text-slate-500 max-w-[200px] truncate">{p.email || p.parent_email || '-'}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Import History */}
          {paymentHistory.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-sm p-4">
              <h3 className="font-semibold text-sm text-slate-700 mb-3 uppercase tracking-wide">Import History</h3>
              <div className="space-y-2">
                {paymentHistory.map((imp) => (
                  <div key={imp.id} className="flex items-center justify-between p-2 bg-slate-50 rounded-sm text-sm">
                    <div>
                      <span className="font-medium">{imp.filename}</span>
                      <span className="text-slate-400 ml-2">by {imp.imported_by}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs">
                      <span className="text-emerald-600">{imp.matched} matched</span>
                      <span className="text-blue-600">{imp.updated} updated</span>
                      {imp.not_found_count > 0 && <span className="text-amber-600">{imp.not_found_count} not found</span>}
                      <span className="text-slate-400">{new Date(imp.imported_at).toLocaleString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default PaymentReportsTab;
