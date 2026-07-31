import type { HTMLAttributes, ReactNode } from "react";

interface Props extends HTMLAttributes<HTMLDivElement> {
  children?: ReactNode;
}

/**
 * 玻璃擬態容器：統一封裝 index.css 的 `.glass-panel`（半透明背景 + backdrop-blur + 細邊框），
 * Light/Dark 兩套參數與 `@supports` fallback 全由 CSS 負責，元件本身不持有色值。
 * 僅供 Hero／摘要／overlay 等重點卡片使用；清單與表單等資料密集區塊維持不透明實色卡片。
 */
export function GlassPanel({ className, children, ...rest }: Props) {
  const classes = className ? `glass-panel ${className}` : "glass-panel";
  return (
    <div className={classes} {...rest}>
      {children}
    </div>
  );
}
