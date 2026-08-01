import { useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { FormAgentProvider } from "./hooks/useFormAgent";
import { useAuth } from "./hooks/useAuth";
import { useVendorAuth } from "./hooks/useVendorAuth";
import { CalendarPage } from "./pages/CalendarPage";
import { HomePage } from "./pages/HomePage";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { MyServicesPage } from "./pages/MyServicesPage";
import { NewRequestPage } from "./pages/NewRequestPage";
import { RequestDetailPage } from "./pages/RequestDetailPage";
import { ReservationFlowPage } from "./pages/ReservationFlowPage";
import { DeliveryFlowPage } from "./pages/DeliveryFlowPage";
import { ShopFlowPage } from "./pages/ShopFlowPage";
import { HealthRecommendationPage } from "./pages/HealthRecommendationPage";
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

/**
 * React Router 換頁預設不會重設捲動位置：從一個捲得很下面的長頁面（例如 HomePage）
 * 切到另一個固定 `h-dvh` 單一畫面高度的頁面（例如 AI 管家聊天室 `/new`）時，瀏覽器仍
 * 停在舊頁面的捲動位置，導致新頁面的頂部（含返回鈕）被捲到畫面外，看起來像整個
 * 視窗「跳」上去、按不到返回。每次路徑變化都強制捲回頂部即可修正。
 */
function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

export default function App() {
  return (
    // FormAgentProvider 包在路由外層：AI 代操表單的動作佇列要撐過「導頁到表單頁」
    // 以及「關閉管家面板」兩件事（見 useFormAgent.tsx）。
    <FormAgentProvider>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/home" element={<Protected><HomePage /></Protected>} />
        <Route path="/calendar" element={<Protected><CalendarPage /></Protected>} />
        <Route path="/my-services" element={<Protected><MyServicesPage /></Protected>} />
        <Route
          path="/services/restaurant_reservation"
          element={<Protected><ReservationFlowPage /></Protected>}
        />
        <Route
          path="/services/food_delivery"
          element={<Protected><DeliveryFlowPage /></Protected>}
        />
        <Route
          path="/services/health_product_recommendation"
          element={<Protected><HealthRecommendationPage /></Protected>}
        />
        <Route
          path="/services/shop_purchase"
          element={<Protected><ShopFlowPage /></Protected>}
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
    </FormAgentProvider>
  );
}
