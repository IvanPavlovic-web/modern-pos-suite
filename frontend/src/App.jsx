import { Routes, Route, Navigate, Link, useLocation } from "react-router-dom";
import { useAuth } from "./auth";
import Login from "./pages/Login";
import POS from "./pages/POS";
import Admin from "./pages/Admin";
import Reports from "./pages/Reports";
import Refunds from "./pages/Refunds";
import AuditLog from "./pages/AuditLog";
import ReceiptSettings from "./pages/ReceiptSettings";
import DailyReportPage from "./pages/DailyReportPage";
import PeriodicReportPage from "./pages/PeriodicReportPage";

function PrivateRoute({ children, roles }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading">Učitavanje...</div>;
  if (!user) return <Navigate to="/login" />;
  if (roles && !roles.some((r) => user.groups.includes(r))) {
    return <Navigate to="/pos" />;
  }
  return children;
}

function Nav() {
  const { user, logout } = useAuth();
  const location = useLocation();
  if (!user) return null;

  const isManager =
    user.groups.includes("manager") || user.groups.includes("admin");

  return (
    <nav className="nav">
      <div className="nav-brand">POS Sistem</div>
      <div className="nav-links">
        <Link
          className={location.pathname === "/pos" ? "active" : ""}
          to="/pos"
        >
          Kasa
        </Link>
        {isManager && (
          <>
            <Link
              className={location.pathname === "/admin" ? "active" : ""}
              to="/admin"
            >
              Admin
            </Link>
            <Link
              className={location.pathname === "/reports" ? "active" : ""}
              to="/reports"
            >
              Izvještaji
            </Link>
            <Link
              className={location.pathname === "/refunds" ? "active" : ""}
              to="/refunds"
            >
              Refundacije
            </Link>
            <Link
              className={location.pathname === "/audit" ? "active" : ""}
              to="/audit"
            >
              Audit log
            </Link>
            <Link
              className={
                location.pathname.startsWith("/settings") ? "active" : ""
              }
              to="/settings/receipt"
            >
              Podešavanja
            </Link>
          </>
        )}
      </div>
      <div className="nav-user">
        <span>
          {user.username} ({user.groups.join(", ")})
        </span>
        <button onClick={logout}>Odjava</button>
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <>
      <Nav />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/pos"
          element={
            <PrivateRoute>
              <POS />
            </PrivateRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <PrivateRoute roles={["manager", "admin"]}>
              <Admin />
            </PrivateRoute>
          }
        />
        <Route
          path="/reports"
          element={
            <PrivateRoute roles={["manager", "admin"]}>
              <Reports />
            </PrivateRoute>
          }
        />
        <Route
          path="/reports/daily"
          element={
            <PrivateRoute roles={["manager", "admin"]}>
              <DailyReportPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/reports/periodic"
          element={
            <PrivateRoute roles={["manager", "admin"]}>
              <PeriodicReportPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/refunds"
          element={
            <PrivateRoute roles={["manager", "admin"]}>
              <Refunds />
            </PrivateRoute>
          }
        />
        <Route
          path="/audit"
          element={
            <PrivateRoute roles={["manager", "admin"]}>
              <AuditLog />
            </PrivateRoute>
          }
        />
        <Route
          path="/settings/receipt"
          element={
            <PrivateRoute roles={["manager", "admin"]}>
              <ReceiptSettings />
            </PrivateRoute>
          }
        />
        <Route path="*" element={<Navigate to="/pos" />} />
      </Routes>
    </>
  );
}
