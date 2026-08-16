import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./lib/store/auth.ts";
import { AuthPage } from "./routes/AuthPage.tsx";
import { DashboardPage } from "./routes/DashboardPage.tsx";
import { EditorPage } from "./routes/EditorPage.tsx";
import { MarketplacePage } from "./routes/MarketplacePage.tsx";
import { MarketplaceDetail } from "./routes/MarketplaceDetail.tsx";
import { Navbar } from "./components/ui/Navbar.tsx";

export default function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-zinc-500">Loading...</div>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/auth" element={user ? <Navigate to="/dashboard" /> : <AuthPage />} />

      {user ? (
        <>
          <Route path="/*" element={<Navbar />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/editor/:projectId" element={<EditorPage />} />
        </>
      ) : (
        <Route path="/*" element={<Navigate to="/auth" />} />
      )}

      <Route path="/marketplace" element={<MarketplacePage />} />
      <Route path="/marketplace/:id" element={<MarketplaceDetail />} />
    </Routes>
  );
}
