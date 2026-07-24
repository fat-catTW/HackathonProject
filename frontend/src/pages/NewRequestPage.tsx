import { useLocation } from "react-router-dom";
import { ButlerPanel } from "../components/ButlerPanel";

export function NewRequestPage() {
  const location = useLocation();
  const autoMessage = (location.state as { autoMessage?: string } | null)?.autoMessage;

  return <ButlerPanel autoMessage={autoMessage} currentPageId="assistant" />;
}
