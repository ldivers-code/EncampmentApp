import React from 'react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Receipt, DollarSign, AlertTriangle, Eye, Download, Trash2, FileImage, Search } from 'lucide-react';

const ReceiptRepositoryTab = ({
  items,
  filteredReceipts,
  itemsWithReceipts,
  receiptSearch,
  setReceiptSearch,
  setSelectedReceipt,
  handleReceiptDelete,
  formatCurrency
}) => {
  return (
    <div className="space-y-6">
      {/* Receipt Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200 rounded-sm p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-[#00205B]/10 rounded-sm">
              <Receipt className="w-5 h-5 text-[#00205B]" />
            </div>
            <div>
              <p className="text-2xl font-bold text-[#00205B]">{itemsWithReceipts.length}</p>
              <p className="text-xs uppercase tracking-wide text-slate-500">Total Receipts</p>
            </div>
          </div>
        </div>
        <div className="bg-white border border-slate-200 rounded-sm p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-100 rounded-sm">
              <DollarSign className="w-5 h-5 text-emerald-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-emerald-600">
                {formatCurrency(itemsWithReceipts.reduce((sum, item) => sum + (item.actual || 0), 0))}
              </p>
              <p className="text-xs uppercase tracking-wide text-slate-500">Documented Expenses</p>
            </div>
          </div>
        </div>
        <div className="bg-white border border-slate-200 rounded-sm p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-100 rounded-sm">
              <AlertTriangle className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-amber-600">
                {items.filter(i => i.item_type === 'expense' && i.actual > 0 && !i.receipt_url).length}
              </p>
              <p className="text-xs uppercase tracking-wide text-slate-500">Missing Receipts</p>
            </div>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            type="text"
            placeholder="Search receipts by item, category, or vendor..."
            value={receiptSearch}
            onChange={(e) => setReceiptSearch(e.target.value)}
            className="pl-10 rounded-sm"
            data-testid="receipt-search"
          />
        </div>
      </div>

      {/* Receipt Gallery */}
      {filteredReceipts.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-sm p-12 text-center">
          <Receipt className="w-16 h-16 mx-auto mb-4 text-slate-300" />
          <p className="text-lg text-slate-500">No receipts uploaded yet</p>
          <p className="text-sm text-slate-400 mt-2">
            Upload receipts to budget items in the Budget Items tab
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredReceipts.map((item) => (
            <div 
              key={item.id}
              className="bg-white border border-slate-200 rounded-sm overflow-hidden hover:shadow-md transition-shadow group"
            >
              <div 
                className="h-48 bg-slate-100 relative cursor-pointer"
                onClick={() => setSelectedReceipt(item)}
              >
                {item.receipt_url?.startsWith('data:application/pdf') ? (
                  <div className="h-full flex flex-col items-center justify-center">
                    <FileImage className="w-16 h-16 text-slate-400" />
                    <p className="text-sm text-slate-500 mt-2">PDF Document</p>
                  </div>
                ) : (
                  <img 
                    src={item.receipt_url} 
                    alt={`Receipt for ${item.item_name}`}
                    className="w-full h-full object-cover"
                  />
                )}
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
                  <Eye className="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              </div>
              
              <div className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-bold text-slate-900 truncate">{item.item_name}</h3>
                    <p className="text-sm text-slate-500">{item.category}</p>
                  </div>
                  <p className="text-lg font-bold text-[#00205B] whitespace-nowrap">
                    {formatCurrency(item.actual || 0)}
                  </p>
                </div>
                
                <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    {item.vendor && (
                      <span className="truncate max-w-[120px]">{item.vendor}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedReceipt(item)}
                      className="h-8 w-8 p-0"
                      title="View"
                    >
                      <Eye className="w-4 h-4" />
                    </Button>
                    <a 
                      href={item.receipt_url}
                      download={item.receipt_filename || 'receipt'}
                      className="h-8 w-8 p-0 inline-flex items-center justify-center hover:bg-slate-100 rounded"
                      title="Download"
                    >
                      <Download className="w-4 h-4" />
                    </a>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleReceiptDelete(item.id)}
                      className="h-8 w-8 p-0 text-red-500 hover:bg-red-50"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Items Missing Receipts */}
      {items.filter(i => i.item_type === 'expense' && i.actual > 0 && !i.receipt_url).length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-sm p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-bold text-amber-800 mb-2">Items Missing Receipts</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {items
                  .filter(i => i.item_type === 'expense' && i.actual > 0 && !i.receipt_url)
                  .slice(0, 6)
                  .map(item => (
                    <div key={item.id} className="flex items-center justify-between bg-white rounded px-3 py-2">
                      <span className="text-sm text-slate-700 truncate">{item.item_name}</span>
                      <span className="text-sm font-mono text-amber-700">{formatCurrency(item.actual)}</span>
                    </div>
                  ))
                }
              </div>
              {items.filter(i => i.item_type === 'expense' && i.actual > 0 && !i.receipt_url).length > 6 && (
                <p className="text-xs text-amber-600 mt-2">
                  +{items.filter(i => i.item_type === 'expense' && i.actual > 0 && !i.receipt_url).length - 6} more items
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReceiptRepositoryTab;
