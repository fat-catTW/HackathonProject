import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./hooks/useAuth";
import { HomePage } from "./pages/HomePage";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { NewRequestPage } from "./pages/NewRequestPage";
import { RequestDetailPage } from "./pages/RequestDetailPage";

function Protected({ children }: { children: JSX.Element }) {
  const { isLoggedIn } = useAuth();
  return isLoggedIn ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/home" element={<Protected><HomePage /></Protected>} />
      <Route path="/new" element={<Protected><NewRequestPage /></Protected>} />
      <Route
        path="/requests/:requestId"
        element={<Protected><RequestDetailPage /></Protected>}
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
