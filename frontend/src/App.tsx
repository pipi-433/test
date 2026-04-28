import { AdminPage } from "./pages/AdminPage";
import { KioskPage } from "./pages/KioskPage";
import { MobileHomePage } from "./pages/MobileHomePage";

export default function App() {
  const path = window.location.pathname;

  if (path.startsWith("/kiosk")) {
    return <KioskPage />;
  }

  if (path.startsWith("/admin")) {
    return <AdminPage />;
  }

  return <MobileHomePage />;
}
