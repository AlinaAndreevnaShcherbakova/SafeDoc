import React from "react";
import Container from "react-bootstrap/Container";
import Alert from "react-bootstrap/Alert";
import { Navigate, Route, Routes } from "react-router-dom";

import AppNavbar from "./components/AppNavbar";
import Loader from "./components/Loader";
import { useAuth } from "./context/AuthContext";
import DocumentsPage from "./pages/DocumentsPage";
import LoginPage from "./pages/LoginPage";
import RequestsPage from "./pages/RequestsPage";
import UsersPage from "./pages/UsersPage";

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <Loader />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function SuperadminRoute({ children }) {
  const { user } = useAuth();
  if (!user?.is_superadmin) {
    return <Alert variant="warning">Раздел доступен только суперадмину.</Alert>;
  }
  return children;
}

export default function App() {
  const { isAuthenticated, user, logout, loading } = useAuth();

  if (loading) {
    return <Loader />;
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <>
      <AppNavbar isSuperadmin={Boolean(user?.is_superadmin)} onLogout={logout} />
      <Container className="pb-4">
        <Routes>
          <Route
            path="/documents"
            element={
              <ProtectedRoute>
                <DocumentsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/requests"
            element={
              <ProtectedRoute>
                <RequestsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/users"
            element={
              <ProtectedRoute>
                <SuperadminRoute>
                  <UsersPage />
                </SuperadminRoute>
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/documents" replace />} />
        </Routes>
      </Container>
    </>
  );
}
