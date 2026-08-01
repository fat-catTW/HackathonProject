import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { FormAction, FormContext as FormContextPayload } from "../types/request";

/** 表單頁註冊給 AI 管家的操作介面（由 ServiceFormPage 實作）。 */
export interface FormAgentController {
  serviceId: string;
  /** 這張表單目前有沒有這一格（含 visibleWhen 隱藏的欄位）。 */
  hasField: (fieldId: string) => boolean;
  /** 把該欄位捲進畫面，準備高亮。 */
  focusField: (fieldId: string) => void;
  /** 真正把值寫進欄位；回傳 false 代表這一格填不進去（例如下拉沒有這個選項）。 */
  fillField: (fieldId: string, value: string) => boolean;
  /** 表單目前畫面上的值，送給 Agent 當作判斷依據。 */
  getValues: () => Record<string, string>;
}

export interface FormAgentState {
  /** 是否正在逐格代填。 */
  running: boolean;
  /** 正在填的欄位（高亮用）。 */
  activeFieldId: string | null;
  /** 這一輪真的填進去的欄位（顯示「AI 已填」標記）。 */
  filledFieldIds: string[];
  /** 這一輪填不進去、需要使用者自己補的欄位標籤。 */
  skippedLabels: string[];
  /** 這一輪總共要填幾格。 */
  total: number;
  /** 每一格的資料來源說明，例如「沿用你上次填的資料」。 */
  notes: Record<string, string>;
}

interface FormAgentContextValue {
  state: FormAgentState;
  register: (controller: FormAgentController) => () => void;
  run: (actions: FormAction[], serviceId: string | null) => Promise<number>;
  /** 使用者喊停：立刻停在目前這一格，已填的不動。 */
  cancel: () => void;
  getFormContext: () => FormContextPayload | null;
}

const IDLE_STATE: FormAgentState = {
  running: false,
  activeFieldId: null,
  filledFieldIds: [],
  skippedLabels: [],
  total: 0,
  notes: {},
};

/** 高亮停留多久才真的把值寫進去（讓使用者看得到「AI 正在填這一格」）。 */
const HIGHLIGHT_MS = 480;
/** 填完一格後停多久再換下一格。 */
const STEP_MS = 320;
/** 導頁後等表單頁掛載並註冊的上限。 */
const CONTROLLER_WAIT_MS = 5000;
/** 送給後端的表單值單格長度上限；太長的值截斷即可，Agent 只需要知道「這格有東西」。 */
const MAX_VALUE_LENGTH = 200;

const NOOP_CONTEXT: FormAgentContextValue = {
  state: IDLE_STATE,
  register: () => () => {},
  run: async () => 0,
  cancel: () => {},
  getFormContext: () => null,
};

const FormAgentContext = createContext<FormAgentContextValue>(NOOP_CONTEXT);

function sleep(ms: number) {
  if (ms <= 0) return Promise.resolve();
  return new Promise<void>((resolve) => setTimeout(resolve, ms));
}

interface ProviderProps {
  children: ReactNode;
  /** 測試可以把節奏調成 0，避免等動畫。 */
  stepDelayMs?: number;
  /** 等表單頁掛載的上限；測試可調短。 */
  controllerWaitMs?: number;
}

/**
 * AI 代操表單的中樞：接住 Agent 回傳的 form_actions，逐格高亮後寫進目前註冊的表單。
 *
 * 放在路由外層（App）而不是表單頁裡面，有兩個原因：
 * 1. 使用者在別的頁面說「幫我填冷氣清洗」時，Agent 會回 redirect_path，導頁後才有表單可以填，
 *    動作佇列必須撐過這次換頁。
 * 2. 執行動作的期間 AI 管家面板會關閉（否則整張表單被蓋住看不到），面板卸載不能中斷代填。
 */
export function FormAgentProvider({ children, stepDelayMs, controllerWaitMs }: ProviderProps) {
  const [state, setState] = useState<FormAgentState>(IDLE_STATE);
  const controllerRef = useRef<FormAgentController | null>(null);
  const runIdRef = useRef(0);

  const highlightMs = stepDelayMs ?? HIGHLIGHT_MS;
  const stepMs = stepDelayMs ?? STEP_MS;
  const waitMs = controllerWaitMs ?? CONTROLLER_WAIT_MS;

  const register = useCallback((controller: FormAgentController) => {
    controllerRef.current = controller;
    return () => {
      // 只解除自己的註冊，不中止進行中的佇列：React StrictMode 會 mount → cleanup → mount，
      // 導頁後剛掛載的表單頁如果在這裡把 runId 加一，剛送出的代填就會整批被取消。
      // 真的離開表單頁時，下面的迴圈會等不到 controller 而自行結束。
      if (controllerRef.current === controller) {
        controllerRef.current = null;
      }
    };
  }, []);

  const waitForController = useCallback(
    async (serviceId: string | null, runId: number) => {
      const deadline = Date.now() + waitMs;
      for (;;) {
        const controller = controllerRef.current;
        if (controller && (!serviceId || controller.serviceId === serviceId)) return controller;
        if (Date.now() >= deadline || runIdRef.current !== runId) return null;
        await sleep(Math.min(80, waitMs));
      }
    },
    [waitMs],
  );

  const cancel = useCallback(() => {
    runIdRef.current += 1;
    setState((prev) => ({ ...prev, running: false, activeFieldId: null }));
  }, []);

  const run = useCallback(
    async (actions: FormAction[], serviceId: string | null) => {
      const runnable = (actions ?? []).filter((action) => action.field_id);
      if (runnable.length === 0) return 0;

      runIdRef.current += 1;
      const runId = runIdRef.current;
      setState({
        running: true,
        activeFieldId: null,
        filledFieldIds: [],
        skippedLabels: [],
        total: runnable.length,
        notes: Object.fromEntries(
          runnable.filter((action) => action.note).map((action) => [action.field_id, action.note!]),
        ),
      });

      let applied = 0;
      for (const action of runnable) {
        // 每一格都重新確認表單還在（換頁後就等不到了，代填自然結束）。
        const controller = await waitForController(serviceId, runId);
        if (!controller || runIdRef.current !== runId) break;
        if (!controller.hasField(action.field_id)) continue;

        controller.focusField(action.field_id);
        setState((prev) => ({ ...prev, activeFieldId: action.field_id }));
        await sleep(highlightMs);
        if (runIdRef.current !== runId) break;

        const written = controller.fillField(
          action.field_id,
          action.type === "clear" ? "" : action.value,
        );
        // 填不進去的欄位不能標成「AI 已填」，否則畫面在說謊。
        setState((prev) =>
          written
            ? {
                ...prev,
                filledFieldIds: prev.filledFieldIds.includes(action.field_id)
                  ? prev.filledFieldIds
                  : [...prev.filledFieldIds, action.field_id],
              }
            : { ...prev, skippedLabels: [...prev.skippedLabels, action.label || action.field_id] },
        );
        if (written) applied += 1;
        await sleep(stepMs);
      }

      if (runIdRef.current === runId) {
        // 保留 filledFieldIds，讓「AI 已填」標記在代填結束後仍留在畫面上。
        setState((prev) => ({ ...prev, running: false, activeFieldId: null }));
      }
      return applied;
    },
    [highlightMs, stepMs, waitForController],
  );

  const getFormContext = useCallback((): FormContextPayload | null => {
    const controller = controllerRef.current;
    if (!controller) return null;

    const values: Record<string, string> = {};
    for (const [fieldId, rawValue] of Object.entries(controller.getValues())) {
      const value = (rawValue ?? "").trim();
      // 照片是 data URL，送出去只會撐爆請求；略過的 key 代表「這格不要動」。
      if (value.startsWith("data:")) continue;
      // 空字串要照送：Agent 靠它知道使用者把某一格清掉了。
      values[fieldId] = value.length > MAX_VALUE_LENGTH ? value.slice(0, MAX_VALUE_LENGTH) : value;
    }
    return { service_id: controller.serviceId, values };
  }, []);

  const value = useMemo(
    () => ({ state, register, run, cancel, getFormContext }),
    [state, register, run, cancel, getFormContext],
  );

  return <FormAgentContext.Provider value={value}>{children}</FormAgentContext.Provider>;
}

/** 沒有 Provider 時回傳無動作的預設值，讓單獨渲染的頁面（含既有測試）照常運作。 */
export function useFormAgent() {
  return useContext(FormAgentContext);
}
