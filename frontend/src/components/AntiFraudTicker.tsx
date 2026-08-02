import { ServiceIcon } from "./ServiceIcon";

/*
 * 防詐提醒的內容刻意只寫「這個 App 真的會／不會做的事」，而不是抄一般的宣導標語。
 * 使用者能對照的是自己剛剛在這裡下的單（維修、訂位、付款通知），一旦有人用電話或
 * 簡訊冒名要求別的動作，這幾句就是他當下可以拿來比對的依據。最後一則留下 165，
 * 讓已經半信半疑的人有一個離開 App 也能求證的出口。
 */
const FRAUD_TIPS = [
  "管家不會私訊你，要求先把訂金匯到個人帳戶",
  "師傅到府的費用一律走 App 內帳單，別掃來路不明的收款 QR Code",
  "自稱客服說「訂單設定錯誤」要你到 ATM 操作，一律是詐騙",
  "我們不會跟你索取信用卡末三碼或簡訊驗證碼",
  "訂位改期只會在 App 內通知，不會打電話要你重刷一次卡",
  "覺得怪就先掛掉，撥 165 反詐騙專線，或回 App 找客服確認",
] as const;

/**
 * 首頁防詐跑馬燈。
 *
 * 放在問候標題與 AI 管家入口之間：使用者往下滑要去找管家時一定會經過這一條，
 * 但它只佔一行高度，不會擋住主要動線。橫向捲動用 CSS 動畫（見 index.css 的
 * .ticker-track），滑鼠移入或鍵盤 focus 進來會暫停，讓人有機會把整句讀完。
 */
export function AntiFraudTicker() {
  return (
    <section
      aria-label="防詐騙提醒"
      className="mt-5 flex items-center gap-2 overflow-hidden rounded-full border border-accent/25 bg-accent-soft py-2 pl-2 pr-1"
    >
      <span className="flex shrink-0 items-center gap-1 rounded-full bg-[var(--color-warning)] px-2.5 py-1 text-[11px] font-black text-[var(--color-surface)]">
        <ServiceIcon type="warning" size={12} />
        防詐提醒
      </span>

      {/*
        兩份完全一樣的清單接在一起，動畫從 0 跑到 -50%（剛好是第一份的寬度）後瞬間
        回頭，接縫處看起來就是連續不斷的。第二份只是為了補畫面、不該被讀螢幕再念
        一次，所以標成 aria-hidden。
      */}
      <div className="ticker-viewport min-w-0 flex-1">
        <div className="ticker-track flex w-max">
          {[0, 1].map((copy) => (
            <ul
              key={copy}
              // 用 undefined 而不是 false，第一份才不會多出一個沒有意義的 aria-hidden="false"。
              aria-hidden={copy === 1 || undefined}
              className="flex shrink-0 items-center"
            >
              {FRAUD_TIPS.map((tip) => (
                <li
                  key={tip}
                  className="flex items-center gap-3 whitespace-nowrap pr-3 text-xs font-bold text-[var(--color-warning)]"
                >
                  {tip}
                  {/*
                    透明度走色票別名（accent = --color-warning），不要寫成
                    `text-[var(--color-warning)]/45`——直接對 var() 加透明度是產不出
                    CSS 的，理由見 tailwind.config.js 的 withAlpha。
                  */}
                  <span aria-hidden className="text-accent/45">
                    ◆
                  </span>
                </li>
              ))}
            </ul>
          ))}
        </div>
      </div>
    </section>
  );
}
