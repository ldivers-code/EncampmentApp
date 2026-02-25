import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  getMyFlightInfo, getFlightRoster, getSquadronRoster, 
  getFlightDocuments, getDocuments, createDocument, deleteDocument,
  getScoreCategories, recordMeritDemerit, getMeritDemerits, getIndividualLeaderboard,
  getFlightLeaderboard, getCumulativeStandings
} from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { toast } from 'sonner';
import { 
  Users, 
  FileText, 
  BookOpen, 
  ChevronRight,
  Plus,
  Minus,
  Trash2,
  ExternalLink,
  Shield,
  Star,
  User,
  Folder,
  GraduationCap,
  Upload,
  Filter,
  RefreshCw,
  Trophy,
  TrendingUp,
  Award
} from 'lucide-react';

const CATEGORY_LABELS = {
  tlp: 'Training Lesson Plans (TLPs)',
  pocket_class: 'Pocket Classes',
  handbook: 'Handbooks',
  sop: 'SOPs',
  form: 'Forms',
  checklist: 'Checklists',
  reference: 'Reference Materials',
  other: 'Other'
};

const CATEGORY_ICONS = {
  tlp: GraduationCap,
  pocket_class: BookOpen,
  handbook: BookOpen,
  sop: FileText,
  form: FileText,
  checklist: FileText,
  reference: Folder,
  other: FileText
};

const MyFlightPage = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [flightInfo, setFlightInfo] = useState(null);
  const [selectedFlight, setSelectedFlight] = useState('');
  const [viewMode, setViewMode] = useState('flight'); // flight or squadron
  const [roster, setRoster] = useState(null);
  const [documents, setDocuments] = useState({});
  const [activeTab, setActiveTab] = useState('roster');
  const [selectedCategory, setSelectedCategory] = useState('all');
  
  // Document upload form
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadForm, setUploadForm] = useState({
    title: '',
    description: '',
    doc_type: 'tlp',
    category: 'tlp',
    content: '',
    file_url: '',
    scope: 'flight',
    flight: '',
    squadron: ''
  });

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

  useEffect(() => {
    loadFlightInfo();
  }, []);

  useEffect(() => {
    if (selectedFlight) {
      loadRoster();
      loadDocuments();
    }
  }, [selectedFlight, viewMode]);

  const loadFlightInfo = async () => {
    try {
      const info = await getMyFlightInfo();
      setFlightInfo(info);
      
      // Set default selected flight
      if (info.user_flight) {
        setSelectedFlight(info.user_flight);
      } else if (info.accessible_flights.length > 0) {
        setSelectedFlight(info.accessible_flights[0]);
      }
    } catch (error) {
      toast.error('Failed to load flight information');
    } finally {
      setLoading(false);
    }
  };

  const loadRoster = async () => {
    try {
      if (viewMode === 'flight') {
        const data = await getFlightRoster(selectedFlight);
        setRoster(data);
      } else {
        const flight = allFlights.find(f => f.value === selectedFlight);
        if (flight) {
          const data = await getSquadronRoster(flight.squadron);
          setRoster(data);
        }
      }
    } catch (error) {
      console.error('Failed to load roster:', error);
    }
  };

  const loadDocuments = async () => {
    try {
      const data = await getFlightDocuments(selectedFlight);
      setDocuments(data.documents || {});
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  };

  const handleUploadDocument = async (e) => {
    e.preventDefault();
    if (!uploadForm.title) {
      toast.error('Title is required');
      return;
    }

    try {
      const docData = {
        ...uploadForm,
        flight: uploadForm.scope === 'flight' ? selectedFlight : null,
        squadron: uploadForm.scope === 'squadron' ? (allFlights.find(f => f.value === selectedFlight)?.squadron || null) : null
      };
      
      await createDocument(docData);
      toast.success('Document uploaded successfully');
      setIsUploadModalOpen(false);
      setUploadForm({
        title: '',
        description: '',
        doc_type: 'tlp',
        category: 'tlp',
        content: '',
        file_url: '',
        scope: 'flight',
        flight: '',
        squadron: ''
      });
      loadDocuments();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload document');
    }
  };

  const handleDeleteDocument = async (docId) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    
    try {
      await deleteDocument(docId);
      toast.success('Document deleted');
      loadDocuments();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete document');
    }
  };

  const getAccessibleFlights = () => {
    if (!flightInfo) return [];
    return allFlights.filter(f => flightInfo.accessible_flights.includes(f.value));
  };

  const getFlightLabel = (flightValue) => {
    return allFlights.find(f => f.value === flightValue)?.label || flightValue;
  };

  const getDocumentCount = () => {
    return Object.values(documents).reduce((sum, docs) => sum + docs.length, 0);
  };

  const getFilteredDocuments = () => {
    if (selectedCategory === 'all') {
      return documents;
    }
    return { [selectedCategory]: documents[selectedCategory] || [] };
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-400">Loading flight information...</div>
        </div>
      </div>
    );
  }

  if (!flightInfo || flightInfo.accessible_flights.length === 0) {
    return (
      <div className="p-6 lg:p-8 animate-fade-in">
        <div className="bg-amber-50 border border-amber-200 rounded-sm p-8 text-center">
          <Users className="w-12 h-12 mx-auto mb-4 text-amber-500" />
          <h2 className="text-xl font-bold text-amber-800 mb-2">No Flight Assigned</h2>
          <p className="text-amber-600">
            You haven't been assigned to a flight yet. Please contact your commander for flight assignment.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <Shield className="w-8 h-8 text-[#00205B]" />
          <div>
            <h1 className="text-2xl lg:text-3xl font-black uppercase tracking-tight text-[#00205B]" style={{ fontFamily: 'Chivo, sans-serif' }}>
              My Flight
            </h1>
            <p className="text-slate-500 text-sm">
              {flightInfo.has_full_access ? 'Full Access - All Flights' : `Assigned to ${getFlightLabel(flightInfo.user_flight)}`}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3 flex-wrap">
          {/* Flight Selector */}
          {getAccessibleFlights().length > 1 && (
            <Select value={selectedFlight} onValueChange={setSelectedFlight}>
              <SelectTrigger className="w-48 rounded-sm" data-testid="flight-selector">
                <SelectValue placeholder="Select Flight" />
              </SelectTrigger>
              <SelectContent>
                {getAccessibleFlights().map(f => (
                  <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          
          {/* View Mode Toggle */}
          {flightInfo.has_full_access && (
            <div className="flex rounded-sm border border-slate-200 overflow-hidden">
              <button
                onClick={() => setViewMode('flight')}
                className={`px-3 py-2 text-sm font-medium transition-colors ${
                  viewMode === 'flight' 
                    ? 'bg-[#00205B] text-white' 
                    : 'bg-white text-slate-600 hover:bg-slate-50'
                }`}
              >
                Flight
              </button>
              <button
                onClick={() => setViewMode('squadron')}
                className={`px-3 py-2 text-sm font-medium transition-colors ${
                  viewMode === 'squadron' 
                    ? 'bg-[#00205B] text-white' 
                    : 'bg-white text-slate-600 hover:bg-slate-50'
                }`}
              >
                Squadron
              </button>
            </div>
          )}
          
          <Button variant="outline" onClick={() => { loadRoster(); loadDocuments(); }} className="rounded-sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-slate-200">
        {[
          { id: 'roster', label: 'Roster', icon: Users },
          { id: 'documents', label: 'Documents', icon: FileText, count: getDocumentCount() }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-2 ${
              activeTab === tab.id
                ? 'border-[#00205B] text-[#00205B]'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
            data-testid={`tab-${tab.id}`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
            {tab.count !== undefined && (
              <span className="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-slate-100">{tab.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* Roster Tab */}
      {activeTab === 'roster' && roster && (
        <div className="bg-white border border-slate-200 rounded-sm">
          <div className="border-b border-slate-100 p-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5 text-[#00205B]" />
              <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm">
                {viewMode === 'flight' ? getFlightLabel(selectedFlight) : `Squadron ${roster.squadron?.replace('sq', '')}`} Roster
              </h2>
            </div>
            <div className="flex gap-4 text-sm text-slate-500">
              {viewMode === 'flight' && roster.cadre_count !== undefined && (
                <>
                  <span>{roster.cadre_count} Cadre</span>
                  <span>{roster.cadet_count} Cadets</span>
                </>
              )}
              <span className="font-medium text-[#00205B]">
                {viewMode === 'flight' ? roster.count : roster.total_count} Total
              </span>
            </div>
          </div>
          
          <div className="divide-y divide-slate-100">
            {viewMode === 'flight' ? (
              // Flight roster view
              roster.roster?.length === 0 ? (
                <div className="p-8 text-center text-slate-400">
                  <Users className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>No members in this flight</p>
                </div>
              ) : (
                roster.roster?.map((member) => (
                  <div 
                    key={member.id} 
                    className="p-4 hover:bg-slate-50 transition-colors flex items-center gap-4"
                  >
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                      member.is_student ? 'bg-blue-100 text-blue-600' : 'bg-emerald-100 text-emerald-600'
                    }`}>
                      {member.is_student ? <Star className="w-5 h-5" /> : <User className="w-5 h-5" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-slate-900 truncate">{member.name}</p>
                      {member.position && (
                        <p className="text-sm text-slate-500">{member.position}</p>
                      )}
                    </div>
                    <div className="text-right">
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        member.is_student 
                          ? 'bg-blue-50 text-blue-700' 
                          : 'bg-emerald-50 text-emerald-700'
                      }`}>
                        {member.is_student ? 'Cadet' : 'Cadre'}
                      </span>
                    </div>
                  </div>
                ))
              )
            ) : (
              // Squadron roster view (grouped by flight)
              Object.entries(roster.flights || {}).map(([flight, members]) => (
                <div key={flight} className="p-4">
                  <h3 className="font-bold text-[#00205B] uppercase text-sm mb-3 flex items-center gap-2">
                    <Shield className="w-4 h-4" />
                    {getFlightLabel(flight)}
                    <span className="font-normal text-slate-400 ml-2">{members.length} members</span>
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {members.map((member) => (
                      <div 
                        key={member.id}
                        className="p-2 bg-slate-50 rounded-sm flex items-center gap-2"
                      >
                        <span className={`w-2 h-2 rounded-full ${member.is_student ? 'bg-blue-500' : 'bg-emerald-500'}`} />
                        <span className="text-sm truncate">{member.name}</span>
                        {member.position && (
                          <span className="text-xs text-slate-400 ml-auto truncate">{member.position}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Documents Tab */}
      {activeTab === 'documents' && (
        <div className="space-y-6">
          {/* Documents Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-3">
              <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                <SelectTrigger className="w-56 rounded-sm">
                  <Filter className="w-4 h-4 mr-2 text-slate-400" />
                  <SelectValue placeholder="Filter by category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
                    <SelectItem key={key} value={key}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            {user?.role === 'commander' && (
              <Dialog open={isUploadModalOpen} onOpenChange={setIsUploadModalOpen}>
                <DialogTrigger asChild>
                  <Button className="bg-[#00205B] hover:bg-[#001540] rounded-sm" data-testid="upload-document-btn">
                    <Upload className="w-4 h-4 mr-2" />
                    Upload Document
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-lg">
                  <DialogHeader>
                    <DialogTitle className="text-[#00205B] uppercase font-bold">Upload Document</DialogTitle>
                  </DialogHeader>
                  <form onSubmit={handleUploadDocument} className="space-y-4 mt-4">
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Title *</Label>
                      <Input
                        value={uploadForm.title}
                        onChange={(e) => setUploadForm({...uploadForm, title: e.target.value})}
                        required
                        className="mt-1 rounded-sm"
                        placeholder="Document title"
                      />
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Category *</Label>
                      <Select
                        value={uploadForm.category}
                        onValueChange={(v) => setUploadForm({...uploadForm, category: v, doc_type: v})}
                      >
                        <SelectTrigger className="mt-1 rounded-sm">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
                            <SelectItem key={key} value={key}>{label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Scope *</Label>
                      <Select
                        value={uploadForm.scope}
                        onValueChange={(v) => setUploadForm({...uploadForm, scope: v})}
                      >
                        <SelectTrigger className="mt-1 rounded-sm">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="flight">This Flight Only</SelectItem>
                          <SelectItem value="squadron">Entire Squadron</SelectItem>
                          <SelectItem value="global">All Flights (Global)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Description</Label>
                      <Input
                        value={uploadForm.description}
                        onChange={(e) => setUploadForm({...uploadForm, description: e.target.value})}
                        className="mt-1 rounded-sm"
                        placeholder="Brief description"
                      />
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">External Link (PDF, Google Doc, etc.)</Label>
                      <Input
                        type="url"
                        value={uploadForm.file_url}
                        onChange={(e) => setUploadForm({...uploadForm, file_url: e.target.value})}
                        className="mt-1 rounded-sm"
                        placeholder="https://..."
                      />
                    </div>
                    <div>
                      <Label className="text-xs uppercase tracking-wide text-slate-600">Content (Optional)</Label>
                      <Textarea
                        value={uploadForm.content}
                        onChange={(e) => setUploadForm({...uploadForm, content: e.target.value})}
                        className="mt-1 rounded-sm"
                        rows={4}
                        placeholder="Enter document content or notes..."
                      />
                    </div>
                    <div className="flex justify-end gap-2 pt-2">
                      <Button type="button" variant="outline" onClick={() => setIsUploadModalOpen(false)}>Cancel</Button>
                      <Button type="submit" className="bg-[#00205B]">Upload Document</Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>
            )}
          </div>

          {/* Documents Grid */}
          {getDocumentCount() === 0 ? (
            <div className="bg-white border border-slate-200 rounded-sm p-12 text-center">
              <FileText className="w-16 h-16 mx-auto mb-4 text-slate-300" />
              <p className="text-lg text-slate-500">No documents available</p>
              <p className="text-sm text-slate-400 mt-2">Documents uploaded for this flight will appear here</p>
            </div>
          ) : (
            <div className="space-y-6">
              {Object.entries(getFilteredDocuments()).map(([category, docs]) => {
                if (!docs || docs.length === 0) return null;
                const CategoryIcon = CATEGORY_ICONS[category] || FileText;
                
                return (
                  <div key={category} className="bg-white border border-slate-200 rounded-sm">
                    <div className="border-b border-slate-100 p-4 flex items-center gap-2">
                      <CategoryIcon className="w-5 h-5 text-[#00205B]" />
                      <h2 className="font-bold uppercase tracking-tight text-[#00205B] text-sm">
                        {CATEGORY_LABELS[category] || category}
                      </h2>
                      <span className="ml-auto text-xs text-slate-400">{docs.length} documents</span>
                    </div>
                    <div className="divide-y divide-slate-100">
                      {docs.map((doc) => (
                        <div 
                          key={doc.id}
                          className="p-4 hover:bg-slate-50 transition-colors flex items-start gap-4 group"
                        >
                          <div className="w-10 h-10 bg-slate-100 rounded-sm flex items-center justify-center flex-shrink-0">
                            <FileText className="w-5 h-5 text-slate-500" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-slate-900">{doc.title}</p>
                            {doc.description && (
                              <p className="text-sm text-slate-500 mt-0.5 line-clamp-2">{doc.description}</p>
                            )}
                            <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
                              {doc.scope && doc.scope !== 'global' && (
                                <span className="px-2 py-0.5 bg-slate-100 rounded-full">
                                  {doc.scope === 'flight' ? doc.flight?.toUpperCase() : doc.squadron?.toUpperCase()}
                                </span>
                              )}
                              {doc.scope === 'global' && (
                                <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">Global</span>
                              )}
                              {doc.version > 1 && (
                                <span>v{doc.version}</span>
                              )}
                              {doc.uploaded_by && (
                                <span>by {doc.uploaded_by}</span>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {doc.file_url && (
                              <a
                                href={doc.file_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="p-2 text-[#00205B] hover:bg-[#00205B]/10 rounded-sm transition-colors"
                              >
                                <ExternalLink className="w-4 h-4" />
                              </a>
                            )}
                            {user?.role === 'commander' && (
                              <button
                                onClick={() => handleDeleteDocument(doc.id)}
                                className="p-2 text-red-500 hover:bg-red-50 rounded-sm transition-colors opacity-0 group-hover:opacity-100"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default MyFlightPage;
