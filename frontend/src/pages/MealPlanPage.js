import React, { useState, useEffect, useCallback } from 'react';
import { getMealPlans, createMealPlan, updateMealPlan, deleteMealPlan } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import {
  Plus, Edit2, Trash2, UtensilsCrossed,
  Loader2, Coffee, Sun, Sunset, Cookie, Users, AlertCircle
} from 'lucide-react';

const MEAL_TYPES = [
  { value: 'breakfast', label: 'Breakfast', icon: Coffee, color: 'bg-amber-50 border-amber-200 text-amber-800', time: '0700' },
  { value: 'lunch', label: 'Lunch', icon: Sun, color: 'bg-sky-50 border-sky-200 text-sky-800', time: '1200' },
  { value: 'dinner', label: 'Dinner', icon: Sunset, color: 'bg-indigo-50 border-indigo-200 text-indigo-800', time: '1800' },
  { value: 'snack', label: 'Snack', icon: Cookie, color: 'bg-green-50 border-green-200 text-green-800', time: '' }
];

const PERIODS = [
  {
    id: 'training',
    label: 'Cadre & Staff Training Weekend',
    shortLabel: 'Training Weekend',
    dates: ['2026-05-29', '2026-05-30'],
    description: 'May 29 - 30, 2026'
  },
  {
    id: 'encampment',
    label: 'Encampment',
    shortLabel: 'Encampment',
    dates: ['2026-07-17', '2026-07-18', '2026-07-19', '2026-07-20', '2026-07-21', '2026-07-22', '2026-07-23', '2026-07-24'],
    description: 'July 17 - 24, 2026'
  }
];

const getMealInfo = (type) => MEAL_TYPES.find(m => m.value === type) || MEAL_TYPES[0];

const formatDayHeader = (dateStr) => {
  const d = new Date(dateStr + 'T12:00:00');
  return {
    dayName: d.toLocaleDateString('en-US', { weekday: 'short' }),
    dayNum: d.getDate(),
    monthDay: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  };
};

const MealPlanPage = () => {
  const { canEditMealPlan } = useAuth();
  const [meals, setMeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingMeal, setEditingMeal] = useState(null);
  const [activePeriod, setActivePeriod] = useState('encampment');

  const [formData, setFormData] = useState({
    date: '', meal_type: 'breakfast', menu_items: '',
    location: '', time: '', notes: '', headcount: '', dietary_notes: ''
  });

  const currentPeriod = PERIODS.find(p => p.id === activePeriod);

  const loadMeals = useCallback(async () => {
    try {
      const data = await getMealPlans();
      setMeals(data);
    } catch {
      toast.error('Failed to load meal plans');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadMeals(); }, [loadMeals]);

  const getMealsForDate = (date) => {
    return meals
      .filter(m => m.date === date)
      .sort((a, b) => {
        const order = { breakfast: 0, lunch: 1, dinner: 2, snack: 3 };
        return (order[a.meal_type] || 99) - (order[b.meal_type] || 99);
      });
  };

  const periodMealCount = currentPeriod.dates.reduce((acc, d) => acc + getMealsForDate(d).length, 0);

  const openAdd = (date, mealType) => {
    const mealInfo = getMealInfo(mealType);
    setEditingMeal(null);
    setFormData({
      date, meal_type: mealType, menu_items: '',
      location: 'Dining Facility', time: mealInfo.time,
      notes: '', headcount: '', dietary_notes: ''
    });
    setIsFormOpen(true);
  };

  const openEdit = (meal) => {
    setEditingMeal(meal);
    setFormData({
      date: meal.date, meal_type: meal.meal_type, menu_items: meal.menu_items,
      location: meal.location || '', time: meal.time || '',
      notes: meal.notes || '', headcount: meal.headcount || '',
      dietary_notes: meal.dietary_notes || ''
    });
    setIsFormOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.menu_items.trim()) { toast.error('Menu items are required'); return; }

    const payload = {
      ...formData,
      headcount: formData.headcount ? parseInt(formData.headcount) : null,
      dietary_notes: formData.dietary_notes || null,
      notes: formData.notes || null,
      location: formData.location || null,
      time: formData.time || null
    };

    try {
      if (editingMeal) {
        await updateMealPlan(editingMeal.id, payload);
        toast.success('Meal plan updated');
      } else {
        await createMealPlan(payload);
        toast.success('Meal plan added');
      }
      setIsFormOpen(false);
      loadMeals();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save meal plan');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this meal plan entry?')) return;
    try {
      await deleteMealPlan(id);
      toast.success('Meal plan deleted');
      loadMeals();
    } catch {
      toast.error('Failed to delete');
    }
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-6 h-6 animate-spin text-[#00205B]" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-3 sm:p-6 lg:p-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl sm:text-2xl lg:text-3xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Meal Plan Schedule
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            {periodMealCount} meal{periodMealCount !== 1 ? 's' : ''} planned for {currentPeriod.shortLabel}
          </p>
        </div>
        {canEditMealPlan() && (
          <Button
            onClick={() => {
              openAdd(currentPeriod.dates[0], 'breakfast');
            }}
            className="bg-[#00205B] hover:bg-[#001540] rounded-sm"
            data-testid="add-meal-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Meal
          </Button>
        )}
      </div>

      {/* Period Selector */}
      <div className="bg-white border border-slate-200 rounded-sm mb-6 overflow-hidden" data-testid="period-selector">
        <div className="flex">
          {PERIODS.map(period => (
            <button
              key={period.id}
              onClick={() => setActivePeriod(period.id)}
              className={`flex-1 px-4 py-3 text-center transition-colors border-b-2 ${
                activePeriod === period.id
                  ? 'bg-[#00205B] text-white border-[#00205B]'
                  : 'bg-white text-slate-600 hover:bg-slate-50 border-transparent'
              }`}
              data-testid={`period-${period.id}`}
            >
              <div className="font-bold text-xs sm:text-sm uppercase tracking-tight">{period.shortLabel}</div>
              <div className={`text-[10px] sm:text-xs mt-0.5 ${activePeriod === period.id ? 'text-blue-200' : 'text-slate-400'}`}>
                {period.description}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Date Grid */}
      <div className={`grid gap-3 ${
        currentPeriod.id === 'training'
          ? 'grid-cols-1 sm:grid-cols-2'
          : 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8'
      }`}>
        {currentPeriod.dates.map(date => {
          const dateMeals = getMealsForDate(date);
          const { dayName, dayNum, monthDay } = formatDayHeader(date);
          const isToday = date === new Date().toISOString().split('T')[0];

          return (
            <div
              key={date}
              className={`bg-white border rounded-sm ${isToday ? 'border-[#00205B] ring-1 ring-[#00205B]/20' : 'border-slate-200'}`}
              data-testid={`day-column-${date}`}
            >
              {/* Day Header */}
              <div className={`px-3 py-2 border-b text-center ${isToday ? 'bg-[#00205B] text-white border-[#00205B]' : 'bg-slate-50 border-slate-200'}`}>
                <div className="text-[10px] uppercase tracking-wider font-bold">{dayName}</div>
                <div className="text-lg font-bold">{dayNum}</div>
                <div className={`text-[10px] ${isToday ? 'text-blue-200' : 'text-slate-400'}`}>{monthDay}</div>
              </div>

              {/* Meals */}
              <div className="p-2 space-y-2 min-h-[200px]">
                {dateMeals.length === 0 ? (
                  <div className="text-center py-6">
                    <UtensilsCrossed className="w-5 h-5 mx-auto mb-1 text-slate-300" />
                    <p className="text-[10px] text-slate-400">No meals</p>
                    {canEditMealPlan() && (
                      <button
                        onClick={() => openAdd(date, 'breakfast')}
                        className="mt-2 text-[10px] text-[#00205B] hover:underline font-medium"
                        data-testid={`add-meal-day-${date}`}
                      >
                        + Add
                      </button>
                    )}
                  </div>
                ) : (
                  <>
                    {dateMeals.map(meal => {
                      const info = getMealInfo(meal.meal_type);
                      const MealIcon = info.icon;
                      return (
                        <div
                          key={meal.id}
                          className={`border rounded-sm p-2 ${info.color} group relative`}
                          data-testid={`meal-card-${meal.id}`}
                        >
                          <div className="flex items-center gap-1.5 mb-1">
                            <MealIcon className="w-3 h-3 flex-shrink-0" />
                            <span className="text-[10px] font-bold uppercase tracking-wider">{info.label}</span>
                            {meal.time && (
                              <span className="text-[10px] opacity-70 ml-auto">{meal.time}</span>
                            )}
                          </div>
                          <p className="text-xs leading-tight line-clamp-3">{meal.menu_items}</p>
                          {meal.dietary_notes && (
                            <div className="mt-1 flex items-start gap-1">
                              <AlertCircle className="w-2.5 h-2.5 mt-0.5 flex-shrink-0 opacity-60" />
                              <p className="text-[10px] opacity-70 line-clamp-1">{meal.dietary_notes}</p>
                            </div>
                          )}
                          {meal.headcount && (
                            <div className="mt-1 flex items-center gap-1">
                              <Users className="w-2.5 h-2.5 opacity-60" />
                              <span className="text-[10px] opacity-70">{meal.headcount}</span>
                            </div>
                          )}
                          {canEditMealPlan() && (
                            <div className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity flex gap-0.5">
                              <button onClick={() => openEdit(meal)} className="p-0.5 rounded hover:bg-black/10" data-testid={`edit-meal-${meal.id}`}>
                                <Edit2 className="w-3 h-3" />
                              </button>
                              <button onClick={() => handleDelete(meal.id)} className="p-0.5 rounded hover:bg-black/10 text-red-600" data-testid={`delete-meal-${meal.id}`}>
                                <Trash2 className="w-3 h-3" />
                              </button>
                            </div>
                          )}
                        </div>
                      );
                    })}
                    {canEditMealPlan() && (
                      <button
                        onClick={() => openAdd(date, 'breakfast')}
                        className="w-full text-center text-[10px] text-slate-400 hover:text-[#00205B] py-1 border border-dashed border-slate-200 rounded-sm hover:border-[#00205B]/30 transition-colors"
                        data-testid={`add-more-meal-${date}`}
                      >
                        + Add meal
                      </button>
                    )}
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Add/Edit Modal */}
      <Dialog open={isFormOpen} onOpenChange={setIsFormOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-[#00205B] uppercase font-bold" style={{ fontFamily: 'Chivo, sans-serif' }}>
              {editingMeal ? 'Edit Meal' : 'Add Meal'}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4 mt-2">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-600">Date *</Label>
                <Select value={formData.date} onValueChange={(v) => setFormData(p => ({ ...p, date: v }))}>
                  <SelectTrigger className="mt-1 rounded-sm" data-testid="meal-date-input">
                    <SelectValue placeholder="Select date" />
                  </SelectTrigger>
                  <SelectContent>
                    {PERIODS.flatMap(period =>
                      period.dates.map(d => {
                        const fd = formatDayHeader(d);
                        return (
                          <SelectItem key={d} value={d}>
                            {fd.dayName} {fd.monthDay} ({period.shortLabel})
                          </SelectItem>
                        );
                      })
                    )}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-600">Meal Type *</Label>
                <Select value={formData.meal_type} onValueChange={(v) => {
                  const info = getMealInfo(v);
                  setFormData(p => ({ ...p, meal_type: v, time: p.time || info.time }));
                }}>
                  <SelectTrigger className="mt-1 rounded-sm" data-testid="meal-type-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {MEAL_TYPES.map(t => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-600">Menu Items *</Label>
              <Textarea
                value={formData.menu_items}
                onChange={(e) => setFormData(p => ({ ...p, menu_items: e.target.value }))}
                required
                className="mt-1 rounded-sm text-sm"
                rows={3}
                placeholder="e.g. Scrambled eggs, bacon, toast, fruit, juice, coffee"
                data-testid="meal-menu-input"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-600">Time</Label>
                <Input
                  value={formData.time}
                  onChange={(e) => setFormData(p => ({ ...p, time: e.target.value }))}
                  className="mt-1 rounded-sm"
                  placeholder="e.g. 0700"
                  data-testid="meal-time-input"
                />
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wide text-slate-600">Headcount</Label>
                <Input
                  type="number"
                  value={formData.headcount}
                  onChange={(e) => setFormData(p => ({ ...p, headcount: e.target.value }))}
                  className="mt-1 rounded-sm"
                  placeholder="Expected #"
                  data-testid="meal-headcount-input"
                />
              </div>
            </div>

            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-600">Location</Label>
              <Input
                value={formData.location}
                onChange={(e) => setFormData(p => ({ ...p, location: e.target.value }))}
                className="mt-1 rounded-sm"
                placeholder="e.g. Dining Facility"
              />
            </div>

            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-600">Dietary Notes</Label>
              <Input
                value={formData.dietary_notes}
                onChange={(e) => setFormData(p => ({ ...p, dietary_notes: e.target.value }))}
                className="mt-1 rounded-sm"
                placeholder="e.g. Vegetarian option: veggie scramble"
                data-testid="meal-dietary-input"
              />
            </div>

            <div>
              <Label className="text-xs uppercase tracking-wide text-slate-600">Notes</Label>
              <Input
                value={formData.notes}
                onChange={(e) => setFormData(p => ({ ...p, notes: e.target.value }))}
                className="mt-1 rounded-sm"
                placeholder="Additional notes"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => setIsFormOpen(false)} className="rounded-sm">
                Cancel
              </Button>
              <Button type="submit" className="bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="submit-meal-btn">
                {editingMeal ? 'Save Changes' : 'Add Meal'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MealPlanPage;
