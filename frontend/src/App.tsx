import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import Layout from "./components/Layout";
import { LoadingBlock } from "./components/ui";
import ChartsPage from "./pages/ChartsPage";
import ComparePage from "./pages/ComparePage";
import DashboardPage from "./pages/DashboardPage";
import ImportPage from "./pages/ImportPage";
import InsightsPage from "./pages/InsightsPage";
import PertPage from "./pages/PertPage";
import LoginPage from "./pages/LoginPage";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import ProjectsPage from "./pages/ProjectsPage";
import RegisterPage from "./pages/RegisterPage";
import ReportsPage from "./pages/ReportsPage";
import SecurityPage from "./pages/SecurityPage";
import SettingsPage from "./pages/SettingsPage";

function Protected() {
  const { user, ready } = useAuth();
  if (!ready) return <LoadingBlock label="Checking session" />;
  if (!user) return <Navigate to="/login" replace />;
  return <Layout />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<Protected />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
        <Route path="/import" element={<ImportPage />} />
        <Route path="/charts" element={<ChartsPage />} />
        <Route path="/pert" element={<PertPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/insights" element={<InsightsPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/security" element={<SecurityPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
