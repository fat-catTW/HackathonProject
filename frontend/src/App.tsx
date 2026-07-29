import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./hooks/useAuth";
import { HomePage } from "./pages/HomePage";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { MyServicesPage } from "./pages/MyServicesPage";
import { NewRequestPage } from "./pages/NewRequestPage";
import { RequestDetailPage } from "./pages/RequestDetailPage";
import { ReservationFlowPage } from "./pages/ReservationFlowPage";
import { DeliveryFlowPage } from "./pages/DeliveryFlowPage";
import { ServiceFormPage } from "./pages/ServiceFormPage";

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
      <Route path="/my-services" element={<Protected><MyServicesPage /></Protected>} />
      <Route
        path="/services/restaurant_reservation"
        element={<Protected><ReservationFlowPage /></Protected>}
      />
      <Route
        path="/services/food_delivery"
        element={<Protected><DeliveryFlowPage /></Protected>}
      />
      <Route path="/services/:serviceId" element={<Protected><ServiceFormPage /></Protected>} />
      <Route path="/new" element={<Protected><NewRequestPage /></Protected>} />
      <Route
        path="/requests/:requestId"
        element={<Protected><RequestDetailPage /></Protected>}
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
