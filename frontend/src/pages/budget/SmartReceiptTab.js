import React from 'react';
import { Button } from '../../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Upload, Receipt } from 'lucide-react';

const SmartReceiptTab = ({
  receiptUploading,
  parsedReceipt,
  receiptItems,
  setReceiptItems,
  receiptHistory,
  confirming,
  handleSmartReceiptUpload,
  handleConfirmReceipt,
  handleDiscardReceipt,
  budgetCategories
}) => {
  return (
    <div className="space-y-6">
      {/* Upload Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-[#00205B]">Smart Receipt Upload</h2>
          <p className="text-sm text-slate-500">
            Upload receipt images — items are auto-extracted and categorized to your budget
          </p>
        </div>
        <label className="cursor-pointer" data-testid="upload-smart-receipt">
          <input type="file" accept=".jpg,.jpeg,.png,.webp,.pdf,.heic" onChange={handleSmartReceiptUpload} className="hidden" />
          <span className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-sm transition-colors ${
            receiptUploading ? 'bg-slate-200 text-slate-500' : 'bg-[#00205B] text-white hover:bg-[#001845]'
          }`}>
            <Upload className="w-4 h-4" />
            {receiptUploading ? 'Processing...' : 'Upload Receipt'}
          </span>
        </label>
      </div>

      {/* Parsed Receipt Review */}
      {parsedReceipt && (
        <div className="bg-white border-2 border-[#00205B]/20 rounded-sm p-5 space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="font-bold text-[#00205B]">
                {parsedReceipt.vendor || 'Receipt'}
              </h3>
              <div className="flex gap-4 text-sm text-slate-500 mt-1">
                {parsedReceipt.date && <span>Date: {parsedReceipt.date}</span>}
                {parsedReceipt.total && <span>Total: <strong className="text-slate-700">${parsedReceipt.total.toFixed(2)}</strong></span>}
              </div>
            </div>
            {parsedReceipt.receipt_url && !parsedReceipt.receipt_url.startsWith('data:') && (
              <a href={parsedReceipt.receipt_url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 underline">
                View Image
              </a>
            )}
          </div>

          {/* Line Items with Category Selection */}
          <div className="border border-slate-200 rounded-sm overflow-hidden">
            <table className="w-full text-sm" data-testid="receipt-items-table">
              <thead className="bg-slate-50">
                <tr>
                  <th className="w-8 p-3"><input type="checkbox" checked={receiptItems.every(i => i.include)} onChange={(e) => setReceiptItems(receiptItems.map(i => ({ ...i, include: e.target.checked })))} /></th>
                  <th className="text-left p-3 text-xs font-semibold text-slate-600 uppercase">Item</th>
                  <th className="text-right p-3 text-xs font-semibold text-slate-600 uppercase w-28">Amount</th>
                  <th className="text-left p-3 text-xs font-semibold text-slate-600 uppercase w-52">Category</th>
                  <th className="text-center p-3 text-xs font-semibold text-slate-600 uppercase w-20">Match</th>
                </tr>
              </thead>
              <tbody>
                {receiptItems.map((item, idx) => (
                  <tr key={item.key} className={`border-t border-slate-100 ${!item.include ? 'opacity-40' : ''}`}>
                    <td className="p-3">
                      <input type="checkbox" checked={item.include} onChange={(e) => {
                        const updated = [...receiptItems];
                        updated[idx] = { ...updated[idx], include: e.target.checked };
                        setReceiptItems(updated);
                      }} />
                    </td>
                    <td className="p-3">{item.description}</td>
                    <td className="p-3 text-right font-mono">${item.amount.toFixed(2)}</td>
                    <td className="p-3">
                      <Select value={item.category} onValueChange={(val) => {
                        const updated = [...receiptItems];
                        updated[idx] = { ...updated[idx], category: val };
                        setReceiptItems(updated);
                      }}>
                        <SelectTrigger className="w-full rounded-sm text-xs h-8" data-testid={`receipt-category-${idx}`}>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {(parsedReceipt.available_categories || budgetCategories).map(cat => (
                            <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </td>
                    <td className="p-3 text-center">
                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                        item.confidence >= 0.5 ? 'bg-emerald-100 text-emerald-700' :
                        item.confidence >= 0.2 ? 'bg-amber-100 text-amber-700' :
                        'bg-slate-100 text-slate-500'
                      }`}>
                        {Math.round(item.confidence * 100)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-slate-50">
                <tr>
                  <td className="p-3" />
                  <td className="p-3 font-semibold">
                    Selected: {receiptItems.filter(i => i.include).length} items
                  </td>
                  <td className="p-3 text-right font-mono font-bold">
                    ${receiptItems.filter(i => i.include).reduce((s, i) => s + i.amount, 0).toFixed(2)}
                  </td>
                  <td className="p-3" colSpan={2}>
                    <Button
                      onClick={handleConfirmReceipt}
                      disabled={confirming || receiptItems.filter(i => i.include).length === 0}
                      className="w-full bg-emerald-600 hover:bg-emerald-700 text-white rounded-sm"
                      data-testid="confirm-receipt-btn"
                    >
                      {confirming ? 'Adding...' : 'Add to Budget'}
                    </Button>
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
          
          <Button variant="outline" size="sm" onClick={handleDiscardReceipt} className="rounded-sm">
            Discard
          </Button>
        </div>
      )}

      {/* No receipt uploaded yet */}
      {!parsedReceipt && !receiptUploading && (
        <div className="bg-white border border-dashed border-slate-300 rounded-sm p-12 text-center">
          <Receipt className="w-12 h-12 mx-auto mb-3 text-slate-300" />
          <p className="text-slate-500">Upload a receipt photo to auto-extract line items</p>
          <p className="text-xs text-slate-400 mt-1">Supports JPG, PNG, WEBP, PDF</p>
        </div>
      )}

      {receiptUploading && (
        <div className="bg-white border border-slate-200 rounded-sm p-12 text-center">
          <div className="animate-pulse">
            <Receipt className="w-12 h-12 mx-auto mb-3 text-[#00205B]/40" />
            <p className="text-[#00205B] font-medium">Analyzing receipt...</p>
            <p className="text-xs text-slate-400 mt-1">Extracting items and matching categories</p>
          </div>
        </div>
      )}

      {/* Receipt History */}
      {receiptHistory.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-sm p-4">
          <h3 className="font-semibold text-sm text-slate-700 mb-3 uppercase tracking-wide">Previous Uploads</h3>
          <div className="space-y-2">
            {receiptHistory.map((r) => (
              <div key={r.id} className="flex items-center justify-between p-2 bg-slate-50 rounded-sm text-sm">
                <div className="flex items-center gap-3">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                    r.status === 'confirmed' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                  }`}>
                    {r.status === 'confirmed' ? 'Added' : 'Pending'}
                  </span>
                  <span className="font-medium">{r.vendor || r.filename}</span>
                  {r.total && <span className="text-xs font-mono text-slate-500">${r.total.toFixed(2)}</span>}
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-400">
                  <span>{r.line_items?.length || 0} items</span>
                  <span>{new Date(r.uploaded_at).toLocaleDateString()}</span>
                  <span>by {r.uploaded_by}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default SmartReceiptTab;
