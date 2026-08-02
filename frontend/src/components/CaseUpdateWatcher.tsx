import { useCaseUpdates } from "../hooks/useCaseUpdates";
import { useDailyGreeting } from "../hooks/useDailyGreeting";
import { useOnboarding } from "../hooks/useOnboarding";
import { CaseUpdateModal } from "./CaseUpdateModal";

/**
 * 掛在住戶端每個登入後的頁面上，負責在案件有進度時把通知卡送到眼前。
 *
 * 新手導引與每日問候卡也是整頁的卡片，同時跳出來會疊成一團、使用者不知道該先看
 * 哪一張。這裡讓案件通知禮讓那兩張：通知留在佇列裡不會消失，等前面那張關掉之後
 * 才接著跳。
 */
export function CaseUpdateWatcher() {
  const { update, dismiss } = useCaseUpdates();
  const { shouldShow: onboardingOpen } = useOnboarding();
  const { shouldShow: greetingOpen } = useDailyGreeting();

  if (!update || onboardingOpen || greetingOpen) return null;
  return <CaseUpdateModal update={update} onDismiss={dismiss} />;
}
