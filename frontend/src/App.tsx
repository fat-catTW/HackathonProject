import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./hooks/useAuth";
import { useVendorAuth } from "./hooks/useVendorAuth";
import { HomePage } from "./pages/HomePage";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { MyServicesPage } from "./pages/MyServicesPage";
import { NewRequestPage } from "./pages/NewRequestPage";
import { RequestDetailPage } from "./pages/RequestDetailPage";
import { ReservationFlowPage } from "./pages/ReservationFlowPage";
import { DeliveryFlowPage } from "./pages/DeliveryFlowPage";
import { ServiceFormPage } from "./pages/ServiceFormPage";
import { VendorLoginPage } from "./pages/VendorLoginPage";
import { VendorRequestDetailPage } from "./pages/VendorRequestDetailPage";
import { VendorRequestsPage } from "./pages/VendorRequestsPage";

function Protected({ children }: { children: JSX.Element }) {
  const { isLoggedIn } = useAuth();
  return isLoggedIn ? children : <Navigate to="/login" replace />;
}

function VendorProtected({ children }: { children: JSX.Element }) {
  const { isLoggedIn } = useVendorAuth();
  return isLoggedIn ? children : <Navigate to="/vendor/login" replace />;
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
      <Route path="/vendor" element={<Navigate to="/vendor/requests" replace />} />
      <Route path="/vendor/login" element={<VendorLoginPage />} />
      <Route
        path="/vendor/requests"
        element={<VendorProtected><VendorRequestsPage /></VendorProtected>}
      />
      <Route
        path="/vendor/requests/:requestId"
        element={<VendorProtected><VendorRequestDetailPage /></VendorProtected>}
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
