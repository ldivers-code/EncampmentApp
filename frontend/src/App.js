import "@/App.css";
import "./styles/print.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Toaster } from "./components/ui/sonner";
import Sidebar from "./components/Sidebar";
import LoginPage from "./pages/LoginPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import DashboardPage from "./pages/DashboardPage";
import RosterPage from "./pages/RosterPage";
import OrgChartPage from "./pages/OrgChartPage";
import SchedulePage from "./pages/SchedulePage";
import MealPlanPage from "./pages/MealPlanPage";
import BudgetPage from "./pages/BudgetPage";
import HandbooksPage from "./pages/HandbooksPage";
import DocumentsPage from "./pages/DocumentsPage";
import AdminPage from "./pages/AdminPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import ProfilePage from "./pages/ProfilePage";
import PointsPage from "./pages/PointsPage";
import MyFlightPage from "./pages/MyFlightPage";
import HealthServicesDashboard from "./pages/HealthServicesDashboard";
import TrainingOfficerPage from "./pages/TrainingOfficerPage";
import LogisticsPage from "./pages/LogisticsPage";
import StatusBoardControl from "./pages/StatusBoardControl";
import StatusBoardDisplay from "./pages/StatusBoardDisplay";
import CheckInPage from "./pages/CheckInPage";
import BarracksPage from "./pages/BarracksPage";
import MyCadetPage from "./pages/MyCadetPage";
import AssignmentsPage from "./pages/AssignmentsPage";

const ProtectedRoute = ({ children, allowedRoles }) => {
  const { isAuthenticated, loading, user } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-slate-400">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Parents can only access /my-cadet
  if (user?.role === 'parent' && allowedRoles && !allowedRoles.includes('parent')) {
    return <Navigate to="/my-cadet" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user?.role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Sidebar>{children}</Sidebar>;
};

const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading, user } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-slate-400">Loading...</div>
      </div>
    );
  }

  if (isAuthenticated) {
    // Parents always go to My Cadet page
    return <Navigate to={user?.role === 'parent' ? "/my-cadet" : "/dashboard"} replace />;
  }

  return children;
};

function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        }
      />
      <Route
        path="/forgot-password"
        element={
          <PublicRoute>
            <ForgotPasswordPage />
          </PublicRoute>
        }
      />
      <Route
        path="/reset-password"
        element={
          <PublicRoute>
            <ResetPasswordPage />
          </PublicRoute>
        }
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/my-flight"
        element={
          <ProtectedRoute>
            <MyFlightPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/my-cadet"
        element={
          <ProtectedRoute allowedRoles={['parent']}>
            <MyCadetPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/assignments"
        element={
          <ProtectedRoute>
            <AssignmentsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/roster"
        element={
          <ProtectedRoute>
            <RosterPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/org-chart"
        element={
          <ProtectedRoute>
            <OrgChartPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/schedule"
        element={
          <ProtectedRoute>
            <SchedulePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/meal-plan"
        element={
          <ProtectedRoute>
            <MealPlanPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/budget"
        element={
          <ProtectedRoute>
            <BudgetPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/handbooks"
        element={
          <ProtectedRoute>
            <HandbooksPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/documents"
        element={
          <ProtectedRoute>
            <DocumentsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/analytics"
        element={
          <ProtectedRoute allowedRoles={['dcp', 'commander', 'executive_staff', 'staff', 'finance', 'support_pa']}>
            <AnalyticsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/points"
        element={
          <ProtectedRoute>
            <PointsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute allowedRoles={['dcp', 'commander', 'executive_staff', 'exec_cadre']}>
            <AdminPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/health"
        element={
          <ProtectedRoute allowedRoles={['dcp', 'commander', 'executive_staff', 'health_services', 'staff', 'support_health', 'squadron_commander']}>
            <HealthServicesDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/training"
        element={
          <ProtectedRoute allowedRoles={['dcp', 'commander', 'executive_staff', 'training_officer', 'staff']}>
            <TrainingOfficerPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/logistics"
        element={
          <ProtectedRoute allowedRoles={['dcp', 'commander', 'executive_staff', 'logistics', 'staff', 'cadre', 'exec_cadre', 'training_officer', 'finance', 'plans_programs', 'health_services', 'support_logistics']}>
            <LogisticsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/check-in"
        element={
          <ProtectedRoute allowedRoles={['dcp', 'commander', 'executive_staff', 'plans_programs', 'logistics', 'support_logistics', 'squadron_commander']}>
            <CheckInPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/barracks"
        element={
          <ProtectedRoute allowedRoles={['dcp', 'commander', 'executive_staff', 'plans_programs', 'logistics', 'support_logistics', 'squadron_commander']}>
            <BarracksPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/status-control"
        element={
          <ProtectedRoute>
            <StatusBoardControl />
          </ProtectedRoute>
        }
      />
      <Route
        path="/status-display"
        element={<StatusBoardDisplay />}
      />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
        <Toaster position="top-right" richColors />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
