interface Props {
  open: boolean;
  text: string;
  confirmLabel: string;
  cancelLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * 二次確認彈窗（取消案件／取消申請等破壞性操作用）。
 *
 * 配色一律引用語意色 Token（Requirement 6.6），因此 Light/Dark 兩模式共用同一份 className：
 * - 遮罩用 `--color-scrim`（兩模式各為 50% / 60% 深色，足以隔離前景內容，Requirement 16.7）
 * - 卡片用 `--color-surface` + `--color-border` 明確邊界，內文用 `--color-foreground`
 * - 破壞性主按鈕的標籤色用 `--color-on-primary`（Light 為白、Dark 為近黑），避免 Dark 模式
 *   提亮後的 `--color-danger` 配白字對比不足（僅 2.77:1）
 */
export function ConfirmModal({ open, text, confirmLabel, cancelLabel, onConfirm, onCancel }: Props) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--color-scrim)] p-6">
      <div className="w-full max-w-sm rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-7 shadow-xl">
        <p className="mb-6 text-lg font-bold leading-relaxed text-[var(--color-foreground)]">
          {text}
        </p>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 rounded-xl border-2 border-[var(--color-border)] px-4 py-3 font-bold text-[var(--color-muted-foreground)]"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="flex-1 rounded-xl bg-[var(--color-danger)] px-4 py-3 font-bold text-[var(--color-on-primary)]"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
