interface Props {
  open: boolean;
  text: string;
  confirmLabel: string;
  cancelLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}

/** 二次確認彈窗（取消案件／取消申請等破壞性操作用）。 */
export function ConfirmModal({ open, text, confirmLabel, cancelLabel, onConfirm, onCancel }: Props) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(10,25,40,0.45)] p-6">
      <div className="w-full max-w-sm rounded-2xl bg-white p-7 shadow-xl">
        <p className="mb-6 text-lg font-bold leading-relaxed text-ink">{text}</p>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 rounded-xl border-2 border-gray-200 px-4 py-3 font-bold text-gray-500"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="flex-1 rounded-xl bg-danger px-4 py-3 font-bold text-white"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
