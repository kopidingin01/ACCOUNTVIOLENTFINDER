import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider } from "./hooks/useAuth";
import AccountFinder from "./pages/AccountFinder";
import AuditLogs from "./pages/AuditLogs";
import CaseDetail from "./pages/CaseDetail";
import Cases from "./pages/Cases";
import Dashboard from "./pages/Dashboard";
import EvidencePage from "./pages/Evidence";
import Login from "./pages/Login";
import Platforms from "./pages/Platforms";
import Policies from "./pages/Policies";
import Reports from "./pages/Reports";
import ReviewQueue from "./pages/ReviewQueue";
import Settings from "./pages/Settings";
import Targets from "./pages/Targets";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/account-finder" element={<ProtectedRoute roles={["ADMIN", "ANALYST"]}><AccountFinder /></ProtectedRoute>} />
        <Route path="/cases" element={<ProtectedRoute><Cases /></ProtectedRoute>} />
        <Route path="/cases/:id" element={<ProtectedRoute><CaseDetail /></ProtectedRoute>} />
        <Route path="/evidence" element={<ProtectedRoute><EvidencePage /></ProtectedRoute>} />
        <Route path="/targets" element={<ProtectedRoute><Targets /></ProtectedRoute>} />
        <Route path="/policies" element={<ProtectedRoute><Policies /></ProtectedRoute>} />
        <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
        <Route path="/reviews" element={<ProtectedRoute roles={["ADMIN", "REVIEWER", "AUDITOR", "ANALYST"]}><ReviewQueue /></ProtectedRoute>} />
        <Route path="/platforms" element={<ProtectedRoute><Platforms /></ProtectedRoute>} />
        <Route path="/audit" element={<ProtectedRoute roles={["ADMIN", "AUDITOR"]}><AuditLogs /></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
