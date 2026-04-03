import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { 
  getBudget, 
  getBudgetSummary, 
  createBudgetItem, 
  updateBudgetItem, 
  deleteBudgetItem, 
  importBudget,
  uploadReceipt,
  deleteReceipt,
  seedTNWGBudgetTemplate,
  updateBudgetActual,
  markBudgetItemPaid,
  importPaymentReport,
  getPaymentSummary,
  getPaymentImportHistory,
  smartReceiptUpload,
  confirmReceiptItems,
  getReceiptUploads
} from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, PieChart, Pie, Cell } from 'recharts';
import { 
  Plus, 
  Upload, 
  Edit2, 
  Trash2, 
  DollarSign,
  TrendingUp,
  TrendingDown,
  Filter,
  Receipt,
  Users,
  Calendar,
  Calculator,
  X,
  FileImage,
  AlertCircle,
  AlertTriangle,
  Lock,
  FileSpreadsheet,
  Check,
  CheckCircle,
  Clock,
  Banknote,
  ArrowUpDown,
  Target,
  Eye,
  Download,
  Search
} from 'lucide-react';

const BudgetPage = () => {
  const { canAccessFinance, user } = useAuth();
  const [items, setItems] = useState([]);
  const [loadingTemplate, setLoadingTemplate] = useState(false);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [accessDenied, setAccessDenied] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [receiptPreview, setReceiptPreview] = useState(null);
  const [uploadingReceipt, setUploadingReceipt] = useState(null);
  // Inline editing state
  const [editingActual, setEditingActual] = useState(null);
  const [editingActualValue, setEditingActualValue] = useState('');
  // Receipt repository state
  const [activeTab, setActiveTab] = useState('budget'); // 'budget' or 'receipts'
  const [receiptSearch, setReceiptSearch] = useState('');
  const [selectedReceipt, setSelectedReceipt] = useState(null);
  // Payment report state
  const [paymentSummary, setPaymentSummary] = useState(null);
  const [paymentHistory, setPaymentHistory] = useState([]);
  const [paymentLoading, setPaymentLoading] = useState(false);
  const [paymentUploading, setPaymentUploading] = useState(false);
  const [paymentSearch, setPaymentSearch] = useState('');
  const [paymentTypeFilter, setPaymentTypeFilter] = useState('all');
  const [paymentStatusFilter, setPaymentStatusFilter] = useState('all');
  const [paymentFlightFilter, setPaymentFlightFilter] = useState('all');
  // Smart receipt upload state
  const [receiptUploading, setReceiptUploading] = useState(false);
  const [parsedReceipt, setParsedReceipt] = useState(null);
  const [receiptItems, setReceiptItems] = useState([]);
  const [receiptHistory, setReceiptHistory] = useState([]);
  const [confirming, setConfirming] = useState(false);

  const [formData, setFormData] = useState({
    category: '',
    subcategory: '',
    item_name: '',
    estimated: '',
    actual: '',
    notes: '',
    vendor: '',
    item_type: 'expense',
    payment_status: 'pending'
  });

  // Budget categories from 2026 TNWG Encampment Budget structure
  const budgetCategories = [
    // Income Sources
    'Participant Fees',
    'NHQ Allocations',
    'Donations',
    // Expense Categories
    'Facility',
    'DFAC Budget',
    'Graduation Budget',
    'Commandants Budget',
    'Deputy Commander Support',
    'Advanced Training School',
    'Public Affairs',
    'Logistics',
    'Health Services',
    'Awards & Recognition',
    'T-Shirts & Merchandise',
    'Refunds',
    'Other'
  ];

  const COLORS = ['#00205B', '#BF0D3E', '#10B981', '#F59E0B', '#6366F1', '#EC4899', '#14B8A6', '#8B5CF6'];

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [budgetItems, budgetSummary] = await Promise.all([
        getBudget(),
        getBudgetSummary()
      ]);
      setItems(budgetItems);
      setSummary(budgetSummary);
      setAccessDenied(false);
    } catch (error) {
      if (error.response?.status === 403) {
        setAccessDenied(true);
      } else {
        toast.error('Failed to load budget data');
      }
    } finally {
      setLoading(false);
    }
  };

  const loadPaymentData = async () => {
    setPaymentLoading(true);
    try {
      const [summary, history] = await Promise.all([
        getPaymentSummary(),
        getPaymentImportHistory()
      ]);
      setPaymentSummary(summary);
      setPaymentHistory(history);
    } catch (error) {
      if (error.response?.status !== 403) {
        console.error('Failed to load payment data:', error);
      }
    } finally {
      setPaymentLoading(false);
    }
  };

  const handlePaymentUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setPaymentUploading(true);
    try {
      const result = await importPaymentReport(file);
      toast.success(result.message);
      loadPaymentData();
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to import payment report');
    } finally {
      setPaymentUploading(false);
      e.target.value = '';
    }
  };

  const handleSmartReceiptUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setReceiptUploading(true);
    setParsedReceipt(null);
    setReceiptItems([]);
    try {
      const result = await smartReceiptUpload(file);
      setParsedReceipt(result);
      setReceiptItems(
        (result.line_items || []).map((item, i) => ({
          ...item,
          category: item.suggested_category,
          include: true,
          key: i,
        }))
      );
      toast.success(`Receipt parsed: ${result.line_items?.length || 0} items found`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to process receipt');
    } finally {
      setReceiptUploading(false);
      e.target.value = '';
    }
  };

  const handleConfirmReceipt = async () => {
    if (!parsedReceipt) return;
    const itemsToConfirm = receiptItems
      .filter(item => item.include)
      .map(item => ({
        description: item.description,
        amount: item.amount,
        category: item.category,
        vendor: parsedReceipt.vendor,
      }));
    
    if (itemsToConfirm.length === 0) {
      toast.error('Select at least one item to add');
      return;
    }
    
    setConfirming(true);
    try {
      const result = await confirmReceiptItems(parsedReceipt.receipt_id, itemsToConfirm);
      toast.success(result.message);
      setParsedReceipt(null);
      setReceiptItems([]);
      loadData();
      loadReceiptHistory();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to confirm receipt items');
    } finally {
      setConfirming(false);
    }
  };

  const loadReceiptHistory = async () => {
    try {
      const data = await getReceiptUploads();
      setReceiptHistory(data);
    } catch (error) {
      console.error('Failed to load receipt history:', error);
    }
  };

  // Calculate totals with detailed variance tracking
  const totals = useMemo(() => {
    // Income totals
    const incomeItems = items.filter(i => i.item_type === 'income' || i.category?.includes('Fees') || i.category?.includes('Allocations') || i.category?.includes('Donations'));
    const estimatedIncome = incomeItems.reduce((sum, i) => sum + (i.estimated || 0), 0);
    const actualIncome = incomeItems.reduce((sum, i) => sum + (i.actual || 0), 0);
    
    // Expense totals
    const expenseItems = items.filter(i => i.item_type !== 'income' && !i.category?.includes('Fees') && !i.category?.includes('Allocations') && !i.category?.includes('Donations'));
    const estimatedExpenses = expenseItems.reduce((sum, i) => sum + (i.estimated || 0), 0);
    const actualExpenses = expenseItems.reduce((sum, i) => sum + (i.actual || 0), 0);

    // Payment tracking
    const paidItems = items.filter(i => i.payment_status === 'paid');
    const pendingItems = items.filter(i => i.payment_status === 'pending');
    
    return {
      // Income metrics
      estimatedIncome,
      actualIncome,
      incomeVariance: actualIncome - estimatedIncome,
      incomeCollectionRate: estimatedIncome > 0 ? (actualIncome / estimatedIncome * 100) : 0,
      
      // Expense metrics
      estimatedExpenses,
      actualExpenses,
      expenseVariance: estimatedExpenses - actualExpenses, // Positive = under budget
      budgetUtilization: estimatedExpenses > 0 ? (actualExpenses / estimatedExpenses * 100) : 0,
      
      // Balance metrics
      projectedBalance: estimatedIncome - estimatedExpenses,
      currentBalance: actualIncome - actualExpenses,
      
      // Payment tracking
      paidCount: paidItems.length,
      pendingCount: pendingItems.length,
      totalItems: items.length
    };
  }, [items]);

  const filteredItems = useMemo(() => {
    let filtered = items;
    if (categoryFilter !== 'all') {
      filtered = filtered.filter(i => i.category === categoryFilter);
    }
    if (typeFilter !== 'all') {
      if (typeFilter === 'income') {
        filtered = filtered.filter(i => i.item_type === 'income' || i.category?.includes('Fees') || i.category?.includes('Allocations') || i.category?.includes('Donations'));
      } else {
        filtered = filtered.filter(i => i.item_type !== 'income' && !i.category?.includes('Fees') && !i.category?.includes('Allocations') && !i.category?.includes('Donations'));
      }
    }
    if (statusFilter !== 'all') {
      filtered = filtered.filter(i => i.payment_status === statusFilter);
    }
    return filtered;
  }, [items, categoryFilter, typeFilter, statusFilter]);

  const chartData = useMemo(() => {
    if (!summary?.by_category) return [];
    return Object.entries(summary.by_category)
      .filter(([cat]) => !cat.includes('Fees') && !cat.includes('Allocations') && !cat.includes('Donations'))
      .map(([category, data]) => ({
        name: category.length > 12 ? category.substring(0, 12) + '...' : category,
        Estimated: data.estimated,
        Actual: data.actual
      }));
  }, [summary]);

  const pieData = useMemo(() => {
    if (!summary?.by_category) return [];
    return Object.entries(summary.by_category)
      .filter(([cat]) => cat !== 'Income')
      .map(([category, data]) => ({
        name: category,
        value: data.actual || data.estimated
      }))
      .filter(d => d.value > 0);
  }, [summary]);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value || 0);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const dataToSubmit = {
        ...formData,
        estimated: parseFloat(formData.estimated) || 0,
        actual: parseFloat(formData.actual) || 0
      };

      if (editingItem) {
        await updateBudgetItem(editingItem.id, dataToSubmit);
        toast.success('Budget item updated');
      } else {
        await createBudgetItem(dataToSubmit);
        toast.success('Budget item added');
      }
      setIsModalOpen(false);
      resetForm();
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Operation failed');
    }
  };

  const handleEdit = (item) => {
    setEditingItem(item);
    setFormData({
      category: item.category,
      subcategory: item.subcategory || '',
      item_name: item.item_name,
      estimated: item.estimated.toString(),
      actual: item.actual.toString(),
      notes: item.notes || '',
      vendor: item.vendor || '',
      item_type: item.item_type || 'expense',
      payment_status: item.payment_status || 'pending'
    });
    setIsModalOpen(true);
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this budget item?')) {
      try {
        await deleteBudgetItem(id);
        toast.success('Budget item deleted');
        loadData();
      } catch (error) {
        toast.error('Failed to delete budget item');
      }
    }
  };

  const handleImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const result = await importBudget(file);
      toast.success(result.message);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Import failed');
    }
    e.target.value = '';
  };

  const handleReceiptUpload = async (itemId, e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingReceipt(itemId);
    try {
      await uploadReceipt(itemId, file);
      toast.success('Receipt uploaded');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload receipt');
    } finally {
      setUploadingReceipt(null);
    }
    e.target.value = '';
  };

  const handleReceiptDelete = async (itemId) => {
    if (window.confirm('Delete this receipt?')) {
      try {
        await deleteReceipt(itemId);
        toast.success('Receipt deleted');
        loadData();
      } catch (error) {
        toast.error('Failed to delete receipt');
      }
    }
  };

  // Inline actual value editing
  const handleStartEditActual = (item) => {
    setEditingActual(item.id);
    setEditingActualValue(item.actual?.toString() || '0');
  };

  const handleSaveActual = async (itemId) => {
    try {
      const actualValue = parseFloat(editingActualValue) || 0;
      await updateBudgetActual(itemId, actualValue);
      toast.success('Actual value updated');
      setEditingActual(null);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update');
    }
  };

  const handleCancelEditActual = () => {
    setEditingActual(null);
    setEditingActualValue('');
  };

  // Mark as paid quick action
  const handleMarkPaid = async (itemId) => {
    try {
      await markBudgetItemPaid(itemId);
      toast.success('Marked as paid');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to mark as paid');
    }
  };

  const handleLoadTemplate = async () => {
    if (items.length > 0) {
      if (!window.confirm('Loading the TNWG template will require clearing existing items first. This cannot be undone. Continue?')) {
        return;
      }
    }
    
    setLoadingTemplate(true);
    try {
      const result = await seedTNWGBudgetTemplate();
      toast.success(result.message);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to load template');
    } finally {
      setLoadingTemplate(false);
    }
  };

  const resetForm = () => {
    setEditingItem(null);
    setFormData({
      category: '',
      subcategory: '',
      item_name: '',
      estimated: '',
      actual: '',
      notes: '',
      vendor: '',
      item_type: 'expense',
      payment_status: 'pending'
    });
  };

  // Get all items with receipts
  const itemsWithReceipts = useMemo(() => {
    return items.filter(item => item.receipt_url);
  }, [items]);

  // Filter receipts by search
  const filteredReceipts = useMemo(() => {
    if (!receiptSearch) return itemsWithReceipts;
    const search = receiptSearch.toLowerCase();
    return itemsWithReceipts.filter(item => 
      item.item_name?.toLowerCase().includes(search) ||
      item.category?.toLowerCase().includes(search) ||
      item.vendor?.toLowerCase().includes(search) ||
      item.receipt_filename?.toLowerCase().includes(search)
    );
  }, [itemsWithReceipts, receiptSearch]);

  if (loading) {
    return (
      <div className="p-6 lg:p-8 animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-400">Loading budget data...</div>
        </div>
      </div>
    );
  }

  // Access denied view for non-finance users
  if (accessDenied) {
    return (
      <div className="p-6 lg:p-8 animate-fade-in">
        <div className="flex flex-col items-center justify-center h-[60vh]">
          <div className="bg-slate-100 p-6 rounded-full mb-6">
            <Lock className="w-12 h-12 text-slate-400" />
          </div>
          <h2 className="text-2xl font-bold text-slate-700 mb-2">Access Restricted</h2>
          <p className="text-slate-500 text-center max-w-md">
            The Financial Tracker is only accessible to users with <strong>Commander</strong> or <strong>Finance</strong> roles.
          </p>
          <p className="text-slate-400 text-sm mt-4">
            Contact your Commander if you need access to financial data.
          </p>
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
            Financial Tracker
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            {items.length} budget items | Restricted Access
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {items.length === 0 && (
            <Button 
              variant="outline" 
              className="rounded-sm border-amber-600 text-amber-600 hover:bg-amber-50"
              onClick={handleLoadTemplate}
              disabled={loadingTemplate}
              data-testid="load-template-btn"
            >
              <FileSpreadsheet className="w-4 h-4 mr-2" />
              {loadingTemplate ? 'Loading...' : 'TNWG Template'}
            </Button>
          )}

          <label className="cursor-pointer">
            <input
              type="file"
              accept=".xlsx,.xls"
              onChange={handleImport}
              className="hidden"
              data-testid="import-budget-input"
            />
            <Button variant="outline" className="rounded-sm border-[#00205B] text-[#00205B] hover:bg-[#00205B]/10" asChild>
              <span>
                <Upload className="w-4 h-4 mr-2" />
                Import
              </span>
            </Button>
          </label>

          <Dialog open={isModalOpen} onOpenChange={(open) => {
            setIsModalOpen(open);
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button className="bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="add-budget-item-btn">
                <Plus className="w-4 h-4 mr-2" />
                Add Item
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="text-[#00205B] uppercase font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                  {editingItem ? 'Edit Budget Item' : 'Add Budget Item'}
                </DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4 mt-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs uppercase tracking-wide text-slate-600">Type *</Label>
                    <Select
                      value={formData.item_type}
                      onValueChange={(value) => setFormData({ ...formData, item_type: value })}
                    >
                      <SelectTrigger className="mt-1 rounded-sm" data-testid="budget-type-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="expense">Expense</SelectItem>
                        <SelectItem value="income">Income</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs uppercase tracking-wide text-slate-600">Status</Label>
                    <Select
                      value={formData.payment_status}
                      onValueChange={(value) => setFormData({ ...formData, payment_status: value })}
                    >
                      <SelectTrigger className="mt-1 rounded-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="pending">Pending</SelectItem>
                        <SelectItem value="paid">Paid</SelectItem>
                        <SelectItem value="cancelled">Cancelled</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div>
                  <Label className="text-xs uppercase tracking-wide text-slate-600">Category *</Label>
                  <Select
                    value={formData.category}
                    onValueChange={(value) => setFormData({ ...formData, category: value })}
                  >
                    <SelectTrigger className="mt-1 rounded-sm" data-testid="budget-category-select">
                      <SelectValue placeholder="Select category" />
                    </SelectTrigger>
                    <SelectContent>
                      {budgetCategories.map(cat => (
                        <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs uppercase tracking-wide text-slate-600">Item Name *</Label>
                    <Input
                      value={formData.item_name}
                      onChange={(e) => setFormData({ ...formData, item_name: e.target.value })}
                      required
                      className="mt-1 rounded-sm"
                      placeholder="DFAC Supplies"
                      data-testid="budget-item-name-input"
                    />
                  </div>
                  <div>
                    <Label className="text-xs uppercase tracking-wide text-slate-600">Vendor</Label>
                    <Input
                      value={formData.vendor}
                      onChange={(e) => setFormData({ ...formData, vendor: e.target.value })}
                      className="mt-1 rounded-sm"
                      placeholder="Vendor name"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs uppercase tracking-wide text-slate-600">Estimated ($)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={formData.estimated}
                      onChange={(e) => setFormData({ ...formData, estimated: e.target.value })}
                      className="mt-1 rounded-sm font-mono"
                      placeholder="0.00"
                      data-testid="budget-estimated-input"
                    />
                  </div>
                  <div>
                    <Label className="text-xs uppercase tracking-wide text-slate-600">Actual ($)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={formData.actual}
                      onChange={(e) => setFormData({ ...formData, actual: e.target.value })}
                      className="mt-1 rounded-sm font-mono"
                      placeholder="0.00"
                      data-testid="budget-actual-input"
                    />
                  </div>
                </div>
                <div>
                  <Label className="text-xs uppercase tracking-wide text-slate-600">Notes</Label>
                  <Textarea
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    className="mt-1 rounded-sm"
                    rows={2}
                  />
                </div>
                <div className="flex justify-end gap-2 pt-4">
                  <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)} className="rounded-sm">
                    Cancel
                  </Button>
                  <Button type="submit" className="bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="save-budget-item-btn">
                    {editingItem ? 'Update' : 'Add'} Item
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-slate-200">
        <button
          onClick={() => setActiveTab('budget')}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-2 ${
            activeTab === 'budget'
              ? 'border-[#00205B] text-[#00205B]'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
          data-testid="tab-budget"
        >
          <DollarSign className="w-4 h-4" />
          Budget Items
        </button>
        <button
          onClick={() => setActiveTab('receipts')}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-2 ${
            activeTab === 'receipts'
              ? 'border-[#00205B] text-[#00205B]'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
          data-testid="tab-receipts"
        >
          <Receipt className="w-4 h-4" />
          Receipt Repository
          {itemsWithReceipts.length > 0 && (
            <span className="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-slate-100">{itemsWithReceipts.length}</span>
          )}
        </button>
        <button
          onClick={() => { setActiveTab('payments'); if (!paymentSummary) loadPaymentData(); }}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-2 ${
            activeTab === 'payments'
              ? 'border-[#00205B] text-[#00205B]'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
          data-testid="tab-payments"
        >
          <Users className="w-4 h-4" />
          Payment Reports
        </button>
        <button
          onClick={() => { setActiveTab('smart-receipts'); if (receiptHistory.length === 0) loadReceiptHistory(); }}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-2 ${
            activeTab === 'smart-receipts'
              ? 'border-[#00205B] text-[#00205B]'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
          data-testid="tab-smart-receipts"
        >
          <Receipt className="w-4 h-4" />
          Smart Receipts
        </button>
      </div>

      {/* Budget Tab Content */}
      {activeTab === 'budget' && (
        <>
      {/* Live Budget Summary Dashboard */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4 mb-6">
        {/* Income Section */}
        <div className="bg-white border border-emerald-200 rounded-sm p-4" data-testid="budget-income-estimated">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">Est. Income</p>
              <p className="text-lg lg:text-xl font-bold text-slate-600 font-mono">{formatCurrency(totals.estimatedIncome)}</p>
            </div>
            <div className="p-2 bg-emerald-100 rounded-sm">
              <Target className="w-4 h-4 text-emerald-600" />
            </div>
          </div>
        </div>

        <div className="bg-white border border-emerald-200 rounded-sm p-4" data-testid="budget-income-actual">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">Actual Income</p>
              <p className="text-lg lg:text-xl font-bold text-emerald-600 font-mono">{formatCurrency(totals.actualIncome)}</p>
              <p className={`text-xs font-mono mt-1 ${totals.incomeVariance >= 0 ? 'text-emerald-600' : 'text-[#BF0D3E]'}`}>
                {totals.incomeVariance >= 0 ? '+' : ''}{formatCurrency(totals.incomeVariance)} variance
              </p>
            </div>
            <div className="p-2 bg-emerald-100 rounded-sm">
              <Banknote className="w-4 h-4 text-emerald-600" />
            </div>
          </div>
        </div>

        {/* Expense Section */}
        <div className="bg-white border border-slate-200 rounded-sm p-4" data-testid="budget-expense-estimated">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">Est. Expenses</p>
              <p className="text-lg lg:text-xl font-bold text-slate-600 font-mono">{formatCurrency(totals.estimatedExpenses)}</p>
            </div>
            <div className="p-2 bg-[#00205B]/10 rounded-sm">
              <Target className="w-4 h-4 text-[#00205B]" />
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-sm p-4" data-testid="budget-expense-actual">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">Actual Expenses</p>
              <p className="text-lg lg:text-xl font-bold text-[#BF0D3E] font-mono">{formatCurrency(totals.actualExpenses)}</p>
              <p className={`text-xs font-mono mt-1 ${totals.expenseVariance >= 0 ? 'text-emerald-600' : 'text-[#BF0D3E]'}`}>
                {totals.expenseVariance >= 0 ? '+' : ''}{formatCurrency(totals.expenseVariance)} {totals.expenseVariance >= 0 ? 'under' : 'over'}
              </p>
            </div>
            <div className="p-2 bg-red-100 rounded-sm">
              <TrendingDown className="w-4 h-4 text-[#BF0D3E]" />
            </div>
          </div>
        </div>

        {/* Balance Section */}
        <div className="bg-white border border-slate-200 rounded-sm p-4" data-testid="budget-balance">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">Current Balance</p>
              <p className={`text-lg lg:text-xl font-bold font-mono ${totals.currentBalance >= 0 ? 'text-emerald-600' : 'text-[#BF0D3E]'}`}>
                {formatCurrency(totals.currentBalance)}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                Proj: {formatCurrency(totals.projectedBalance)}
              </p>
            </div>
            <div className={`p-2 rounded-sm ${totals.currentBalance >= 0 ? 'bg-emerald-100' : 'bg-red-100'}`}>
              <DollarSign className={`w-4 h-4 ${totals.currentBalance >= 0 ? 'text-emerald-600' : 'text-[#BF0D3E]'}`} />
            </div>
          </div>
        </div>

        {/* Payment Progress */}
        <div className="bg-white border border-slate-200 rounded-sm p-4" data-testid="budget-progress">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">Payment Status</p>
              <p className="text-lg lg:text-xl font-bold text-[#00205B] font-mono">
                {totals.paidCount}/{totals.totalItems}
              </p>
              <div className="w-full bg-slate-200 rounded-full h-1.5 mt-2">
                <div 
                  className="bg-emerald-500 h-1.5 rounded-full transition-all" 
                  style={{ width: `${totals.totalItems > 0 ? (totals.paidCount / totals.totalItems * 100) : 0}%` }}
                />
              </div>
            </div>
            <div className="p-2 bg-[#00205B]/10 rounded-sm">
              <CheckCircle className="w-4 h-4 text-[#00205B]" />
            </div>
          </div>
        </div>
      </div>

      {/* Income vs Expenses Overview + Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Income vs Expenses Card */}
        <div className="bg-white border border-slate-200 rounded-sm">
          <div className="border-b border-slate-100 p-4">
            <h2 className="font-bold uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Income vs Expenses
            </h2>
          </div>
          <div className="p-5 space-y-5">
            {/* Net Position */}
            <div className="text-center py-3">
              <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">Net Position</p>
              <p className={`text-3xl font-bold font-mono ${totals.currentBalance >= 0 ? 'text-emerald-600' : 'text-[#BF0D3E]'}`}>
                {formatCurrency(totals.currentBalance)}
              </p>
              <p className="text-xs text-slate-400 mt-1">Projected: {formatCurrency(totals.projectedBalance)}</p>
            </div>

            {/* Income Bar */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-emerald-700 uppercase tracking-wide">Income</span>
                <span className="text-sm font-mono font-bold text-emerald-600">{formatCurrency(totals.actualIncome)}</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-4 overflow-hidden">
                <div className="bg-emerald-500 h-4 rounded-full transition-all relative" style={{ width: `${Math.min(100, (totals.actualIncome / Math.max(totals.estimatedIncome, 1)) * 100)}%` }}>
                  <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-white">
                    {Math.round((totals.actualIncome / Math.max(totals.estimatedIncome, 1)) * 100)}%
                  </span>
                </div>
              </div>
              <p className="text-[10px] text-slate-400 mt-0.5">of {formatCurrency(totals.estimatedIncome)} estimated</p>
            </div>

            {/* Expenses Bar */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-[#BF0D3E] uppercase tracking-wide">Expenses</span>
                <span className="text-sm font-mono font-bold text-[#BF0D3E]">{formatCurrency(totals.actualExpenses)}</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-4 overflow-hidden">
                <div className="bg-[#BF0D3E] h-4 rounded-full transition-all relative" style={{ width: `${Math.min(100, (totals.actualExpenses / Math.max(totals.estimatedExpenses, 1)) * 100)}%` }}>
                  <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-white">
                    {Math.round((totals.actualExpenses / Math.max(totals.estimatedExpenses, 1)) * 100)}%
                  </span>
                </div>
              </div>
              <p className="text-[10px] text-slate-400 mt-0.5">of {formatCurrency(totals.estimatedExpenses)} estimated</p>
            </div>

            {/* Breakdown */}
            <div className="border-t border-slate-100 pt-3 space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-slate-500">Paid Items</span>
                <span className="font-mono font-semibold text-[#00205B]">{totals.paidCount} / {totals.totalItems}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500">Income Variance</span>
                <span className={`font-mono font-semibold ${totals.incomeVariance >= 0 ? 'text-emerald-600' : 'text-[#BF0D3E]'}`}>
                  {totals.incomeVariance >= 0 ? '+' : ''}{formatCurrency(totals.incomeVariance)}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500">Expense Variance</span>
                <span className={`font-mono font-semibold ${totals.expenseVariance >= 0 ? 'text-emerald-600' : 'text-[#BF0D3E]'}`}>
                  {totals.expenseVariance >= 0 ? '' : '+'}{formatCurrency(Math.abs(totals.expenseVariance))} {totals.expenseVariance >= 0 ? 'under' : 'over'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Budget by Category - Fixed labels */}
        {chartData.length > 0 && (
          <div className="bg-white border border-slate-200 rounded-sm">
            <div className="border-b border-slate-100 p-4">
              <h2 className="font-bold uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
                Budget by Category
              </h2>
            </div>
            <div className="p-4">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={chartData} margin={{ bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 9, fill: '#64748B' }}
                    axisLine={{ stroke: '#E2E8F0' }}
                    angle={-35}
                    textAnchor="end"
                    height={80}
                    interval={0}
                    tickFormatter={(value) => value.length > 14 ? value.substring(0, 14) + '...' : value}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: '#64748B' }}
                    axisLine={{ stroke: '#E2E8F0' }}
                    tickFormatter={(value) => `$${value.toLocaleString()}`}
                    width={65}
                  />
                  <Tooltip
                    formatter={(value, name) => [formatCurrency(value), name]}
                    labelFormatter={(label) => label}
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #E2E8F0',
                      borderRadius: '2px',
                      fontSize: '12px'
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                  <Bar dataKey="Estimated" fill="#00205B" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="Actual" fill="#BF0D3E" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Expense Distribution - Fixed with legend instead of inline labels */}
        {pieData.length > 0 && (
          <div className="bg-white border border-slate-200 rounded-sm">
            <div className="border-b border-slate-100 p-4">
              <h2 className="font-bold uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
                Expense Distribution
              </h2>
            </div>
            <div className="p-4">
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={70}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${entry.name}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => formatCurrency(value)} contentStyle={{ fontSize: '12px' }} />
                </PieChart>
              </ResponsiveContainer>
              {/* Legend below chart */}
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 mt-2 max-h-[110px] overflow-y-auto">
                {pieData.map((entry, index) => {
                  const total = pieData.reduce((s, e) => s + e.value, 0);
                  const pct = total > 0 ? Math.round(entry.value / total * 100) : 0;
                  return (
                    <div key={entry.name} className="flex items-center gap-1.5 text-[10px] leading-tight py-0.5">
                      <div className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                      <span className="text-slate-600 truncate" title={entry.name}>{entry.name}</span>
                      <span className="font-mono text-slate-400 flex-shrink-0 ml-auto">{pct}%</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="bg-white border border-slate-200 rounded-sm p-4 mb-6">
        <div className="flex flex-wrap items-center gap-4">
          <Filter className="w-4 h-4 text-slate-400" />
          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger className="w-48 rounded-sm" data-testid="budget-category-filter">
              <SelectValue placeholder="Filter by category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {budgetCategories.map(cat => (
                <SelectItem key={cat} value={cat}>{cat}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-40 rounded-sm" data-testid="budget-type-filter">
              <SelectValue placeholder="Filter by type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="expense">Expenses</SelectItem>
              <SelectItem value="income">Income</SelectItem>
            </SelectContent>
          </Select>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-40 rounded-sm" data-testid="budget-status-filter">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="paid">Paid</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
          {/* Quick stats */}
          <div className="ml-auto text-sm text-slate-500">
            Showing {filteredItems.length} of {items.length} items
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-slate-200 rounded-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full cap-table" data-testid="budget-table">
            <thead>
              <tr>
                <th className="text-left">Category</th>
                <th className="text-left">Item</th>
                <th className="text-left">Vendor</th>
                <th className="text-right">Estimated</th>
                <th className="text-right">Actual</th>
                <th className="text-center">Variance</th>
                <th className="text-center">Receipt</th>
                <th className="text-center">Status</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={9} className="text-center py-8 text-slate-400">
                    No budget items yet. Add your first item or import from Excel.
                  </td>
                </tr>
              ) : (
                filteredItems.map((item) => {
                  const isIncome = item.item_type === 'income' || item.category?.includes('Fees') || item.category?.includes('Allocations') || item.category?.includes('Donations');
                  const variance = (item.estimated || 0) - (item.actual || 0);
                  const isOverBudget = !isIncome && variance < 0;
                  const isUnderBudget = !isIncome && variance > 0 && item.actual > 0;
                  
                  return (
                    <tr key={item.id} className={`hover:bg-slate-50 ${isIncome ? 'bg-emerald-50/30' : ''} ${item.payment_status === 'paid' ? 'opacity-75' : ''}`} data-testid={`budget-row-${item.id}`}>
                      <td>
                        <div className="flex items-center gap-2">
                          {isIncome && <TrendingUp className="w-3 h-3 text-emerald-600" />}
                          <span className="text-xs uppercase tracking-wide text-slate-500">{item.category}</span>
                        </div>
                      </td>
                      <td className="font-medium">
                        {item.item_name}
                        {item.payment_date && (
                          <span className="block text-xs text-slate-400">Paid: {item.payment_date}</span>
                        )}
                      </td>
                      <td className="text-sm text-slate-500">{item.vendor || '-'}</td>
                      <td className="text-right font-mono text-slate-600">{formatCurrency(item.estimated)}</td>
                      
                      {/* Inline editable actual value */}
                      <td className="text-right">
                        {editingActual === item.id ? (
                          <div className="flex items-center justify-end gap-1">
                            <Input
                              type="number"
                              step="0.01"
                              value={editingActualValue}
                              onChange={(e) => setEditingActualValue(e.target.value)}
                              className="w-24 h-7 text-right font-mono text-sm rounded-sm"
                              autoFocus
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') handleSaveActual(item.id);
                                if (e.key === 'Escape') handleCancelEditActual();
                              }}
                            />
                            <button onClick={() => handleSaveActual(item.id)} className="text-emerald-600 hover:text-emerald-700">
                              <Check className="w-4 h-4" />
                            </button>
                            <button onClick={handleCancelEditActual} className="text-slate-400 hover:text-slate-600">
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => handleStartEditActual(item)}
                            className={`font-mono font-medium hover:underline cursor-pointer ${isIncome ? 'text-emerald-600' : 'text-slate-900'}`}
                            title="Click to edit"
                          >
                            {formatCurrency(item.actual)}
                          </button>
                        )}
                      </td>
                      
                      {/* Variance column */}
                      <td className="text-center">
                        {item.actual > 0 || item.estimated > 0 ? (
                          <span className={`text-xs font-mono px-2 py-0.5 rounded ${
                            isIncome 
                              ? (item.actual >= item.estimated ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700')
                              : isOverBudget 
                                ? 'bg-red-100 text-red-700' 
                                : isUnderBudget 
                                  ? 'bg-emerald-100 text-emerald-700'
                                  : 'bg-slate-100 text-slate-600'
                          }`}>
                            {isIncome 
                              ? (item.actual >= item.estimated ? 'Collected' : `${Math.round((item.actual / item.estimated) * 100)}%`)
                              : variance === 0 
                                ? 'On Budget'
                                : `${variance > 0 ? '+' : ''}${formatCurrency(variance)}`
                            }
                          </span>
                        ) : (
                          <span className="text-xs text-slate-300">-</span>
                        )}
                      </td>
                      
                      <td className="text-center">
                        {item.receipt_url ? (
                          <div className="flex items-center justify-center gap-1">
                            <button
                              onClick={() => setReceiptPreview(item)}
                              className="text-emerald-600 hover:text-emerald-700"
                              title="View receipt"
                            >
                              <FileImage className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleReceiptDelete(item.id)}
                              className="text-red-500 hover:text-red-600"
                              title="Delete receipt"
                            >
                              <X className="w-3 h-3" />
                            </button>
                          </div>
                        ) : (
                          <label className="cursor-pointer">
                            <input
                              type="file"
                              accept="image/*,.pdf"
                              onChange={(e) => handleReceiptUpload(item.id, e)}
                              className="hidden"
                            />
                            <Receipt className={`w-4 h-4 mx-auto ${uploadingReceipt === item.id ? 'animate-pulse text-amber-500' : 'text-slate-300 hover:text-slate-500'}`} />
                          </label>
                        )}
                      </td>
                      <td className="text-center">
                        <span className={`text-xs px-2 py-1 rounded ${
                          item.payment_status === 'paid' ? 'bg-emerald-100 text-emerald-700' :
                          item.payment_status === 'cancelled' ? 'bg-red-100 text-red-700' :
                          'bg-amber-100 text-amber-700'
                        }`}>
                          {item.payment_status || 'pending'}
                        </span>
                      </td>
                      <td className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          {/* Quick Mark as Paid button */}
                          {item.payment_status !== 'paid' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleMarkPaid(item.id)}
                              className="h-8 w-8 p-0 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50"
                              title="Mark as paid"
                              data-testid={`mark-paid-${item.id}`}
                            >
                              <CheckCircle className="w-4 h-4" />
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEdit(item)}
                            className="h-8 w-8 p-0"
                            data-testid={`edit-budget-${item.id}`}
                          >
                            <Edit2 className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(item.id)}
                            className="h-8 w-8 p-0 text-[#BF0D3E] hover:text-[#BF0D3E] hover:bg-red-50"
                            data-testid={`delete-budget-${item.id}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
        </>
      )}

      {/* Receipt Repository Tab */}
      {activeTab === 'receipts' && (
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

          {/* Search and Filters */}
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
                  {/* Receipt Preview */}
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
                  
                  {/* Receipt Info */}
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
      )}

      {/* Receipt Preview Modal */}
      {/* Payment Reports Tab */}
      {activeTab === 'payments' && (
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
      )}

      {/* Smart Receipts Tab */}
      {activeTab === 'smart-receipts' && (
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
              
              <Button variant="outline" size="sm" onClick={() => { setParsedReceipt(null); setReceiptItems([]); }} className="rounded-sm">
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
      )}

      {(receiptPreview || selectedReceipt) && (
        <Dialog open={!!(receiptPreview || selectedReceipt)} onOpenChange={() => { setReceiptPreview(null); setSelectedReceipt(null); }}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle className="text-[#00205B]">
                Receipt: {(receiptPreview || selectedReceipt)?.item_name}
              </DialogTitle>
            </DialogHeader>
            <div className="mt-4">
              {(receiptPreview || selectedReceipt)?.receipt_url?.startsWith('data:application/pdf') ? (
                <div className="bg-slate-100 p-8 text-center rounded">
                  <FileImage className="w-12 h-12 mx-auto text-slate-400 mb-2" />
                  <p className="text-slate-600">PDF Receipt</p>
                  <a 
                    href={(receiptPreview || selectedReceipt)?.receipt_url} 
                    download={(receiptPreview || selectedReceipt)?.receipt_filename || 'receipt.pdf'}
                    className="text-[#00205B] underline text-sm"
                  >
                    Download PDF
                  </a>
                </div>
              ) : (
                <img 
                  src={(receiptPreview || selectedReceipt)?.receipt_url} 
                  alt="Receipt" 
                  className="max-w-full max-h-[60vh] mx-auto rounded border"
                />
              )}
              <div className="mt-4 p-4 bg-slate-50 rounded">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-slate-500">Category</p>
                    <p className="font-medium">{(receiptPreview || selectedReceipt)?.category}</p>
                  </div>
                  <div>
                    <p className="text-slate-500">Amount</p>
                    <p className="font-medium">{formatCurrency((receiptPreview || selectedReceipt)?.actual || 0)}</p>
                  </div>
                  {(receiptPreview || selectedReceipt)?.vendor && (
                    <div>
                      <p className="text-slate-500">Vendor</p>
                      <p className="font-medium">{(receiptPreview || selectedReceipt)?.vendor}</p>
                    </div>
                  )}
                  <div>
                    <p className="text-slate-500">Filename</p>
                    <p className="font-medium truncate">{(receiptPreview || selectedReceipt)?.receipt_filename}</p>
                  </div>
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

export default BudgetPage;
