# Requirements Document

## Introduction

本文件定義「餐廳訂位留資表單」功能的需求規格。此功能讓高齡使用者透過 AI 智慧生活服務管家 App，以對話式「一次一問」的方式完成餐廳訂位流程。系統支援兩種模式：串接第三方訂位系統（如 EZTable）即時確認訂位，或建立諮詢單由客服人工媒合。訂位完成後，系統自動管理訂單狀態生命週期，包含排程 Job 自動推進狀態。

## Glossary

- **Reservation_Agent**: 負責引導使用者完成餐廳訂位流程的 AI 對話代理，遵循「一次一問」模式逐步收集訂位資訊
- **Reservation_Form**: 餐廳訂位留資表單系統，包含前端 UI 元件與後端資料處理邏輯
- **Order_Service**: 後端訂單管理服務，負責建立、更新與查詢 mms_order_record 中的訂位紀錄
- **Third_Party_Booking_API**: 第三方訂位系統（如 EZTable）提供的即時訂位介面
- **Status_Scheduler**: 排程批次任務，負責根據用餐時間自動推進訂單狀態
- **mms_order_record**: 系統既有的訂單資料表，用於儲存所有服務訂單紀錄
- **order_type_02**: mms_order_record 中代表「餐廳訂位」的訂單類型編碼
- **order_status**: 訂單狀態碼，包含 02（待確認）、03（已確認）、04（進行中）、70（已完成）、80（核銷完成）
- **vendor_data**: 訂單中儲存第三方系統回傳資訊的 JSON 欄位
- **service_time**: 訂單中儲存實際用餐時間的欄位，格式為標準 ISO 8601 timestamp
- **is_premium**: 布林值旗標，標記該訂位是否為指定餐廳或高級訂位服務

## Requirements

### Requirement 1: 餐廳訂位服務註冊

**User Story:** 身為高齡使用者，我希望在 AI 管家的服務清單中看到「餐廳訂位」選項，以便我可以透過熟悉的管家介面完成訂位。

#### Acceptance Criteria

1. THE Reservation_Form SHALL 在系統服務清單中註冊為一項可選服務，service_id 為 "restaurant_reservation"，order_type 為 "02"，顯示名稱為「餐廳訂位」
2. WHEN 使用者選擇「餐廳訂位」服務, THE Reservation_Agent SHALL 於 3 秒內啟動對話式訂位流程，以「一次一問」模式引導使用者，首先進入餐廳選擇步驟
3. IF Reservation_Agent 無法啟動訂位流程（如服務暫時不可用）, THEN THE Reservation_Form SHALL 顯示提示訊息告知使用者服務暫時無法使用，並建議稍後再試

### Requirement 2: 餐廳選擇

**User Story:** 身為高齡使用者，我希望能輕鬆選擇想去的餐廳，以便系統為我處理後續訂位。

#### Acceptance Criteria

1. WHEN 訂位流程開始, THE Reservation_Agent SHALL 顯示至多 6 張「熱門餐廳精選卡片」供使用者選擇，並同時提供「留下需求，客服協助媒合」選項
2. WHEN 使用者選擇一間餐廳, THE Reservation_Form SHALL 記錄 restaurant_name 與 restaurant_id，並以視覺反白標示已選取的卡片
3. WHEN 使用者選擇「客服協助媒合」, THE Reservation_Form SHALL 顯示文字輸入欄位，允許使用者以最多 200 字描述餐廳偏好需求
4. WHILE 餐廳卡片列表顯示中, THE Reservation_Form SHALL 於每張卡片中呈現餐廳名稱、地址與電話資訊，字級不小於 14px，觸控區域不小於 44px
5. IF 系統無法載入餐廳清單或清單為空, THEN THE Reservation_Form SHALL 顯示提示訊息引導使用者改用「客服協助媒合」選項，確保流程不中斷

### Requirement 3: 日期與時段選擇

**User Story:** 身為高齡使用者，我希望能選擇用餐日期和時段，以便餐廳為我保留座位。

#### Acceptance Criteria

1. WHEN 餐廳已選定, THE Reservation_Agent SHALL 以對話方式請使用者選擇用餐日期，並顯示日期選擇器供使用者點選
2. THE Reservation_Form SHALL 限制日期選擇器僅能選擇今日（含）起算 60 天內的日期，今日以前與 60 天以後的日期不可點選
3. WHEN 使用者選定日期, THE Reservation_Agent SHALL 以對話方式請使用者選擇用餐時段，並顯示午餐與晚餐兩個時段選項
4. THE Reservation_Form SHALL 提供「午餐」（11:00–14:00）與「晚餐」（17:00–21:00）兩個時段選項，使用者選擇時段後可進一步以 30 分鐘為間隔指定用餐時間
5. IF 使用者選擇過去的日期或已過的時間, THEN THE Reservation_Form SHALL 顯示提示訊息「請選擇未來的日期與時段」並阻止提交
6. IF 使用者選擇當天日期且該時段的所有可選時間皆已過, THEN THE Reservation_Form SHALL 將該時段設為不可選取，僅顯示尚有可選時間的時段

### Requirement 4: 用餐人數選擇

**User Story:** 身為高齡使用者，我希望能指定用餐人數，以便餐廳安排合適的座位。

#### Acceptance Criteria

1. WHEN 時段已選定, THE Reservation_Agent SHALL 以「一次一問」模式詢問使用者用餐人數，並顯示人數選擇元件
2. THE Reservation_Form SHALL 提供「+」與「−」按鈕供使用者調整用餐人數，預設值為 2 人，有效範圍為 1 至 20 人，每次點擊增減 1 人，按鈕觸控區域不小於 44px
3. IF 用餐人數已達下限（1 人）, THEN THE Reservation_Form SHALL 將「−」按鈕設為不可點擊狀態，防止數值低於 1
4. IF 用餐人數已達上限（20 人）, THEN THE Reservation_Form SHALL 將「+」按鈕設為不可點擊狀態，防止數值超過 20
5. IF 使用者以其他方式輸入非正整數或空白值, THEN THE Reservation_Form SHALL 顯示提示訊息「用餐人數請填寫 1 至 20 人」並阻止進入下一步

### Requirement 5: 聯絡資料填寫

**User Story:** 身為高齡使用者，我希望能填寫我的聯絡資訊，以便餐廳或客服能聯繫我確認訂位。

#### Acceptance Criteria

1. WHEN 人數已填寫, THE Reservation_Agent SHALL 引導使用者填寫聯絡人姓名與手機號碼，姓名長度限制為 1 至 50 個字元
2. IF 使用者帳號已有聯絡人姓名或手機號碼資料, THEN THE Reservation_Form SHALL 自動帶入既有資料作為預設值，並允許使用者修改
3. THE Reservation_Form SHALL 驗證手機號碼格式為台灣手機號碼（09 開頭，共 10 碼純數字，不含空格或符號）
4. IF 使用者輸入格式不正確的手機號碼, THEN THE Reservation_Form SHALL 顯示提示訊息「請輸入正確的手機號碼格式（09 開頭，共 10 碼）」
5. IF 聯絡人姓名或手機號碼任一欄位為空白, THEN THE Reservation_Form SHALL 顯示提示訊息指出該欄位為必填，並阻止流程進入下一步
6. IF 聯絡人姓名超過 50 個字元, THEN THE Reservation_Form SHALL 顯示提示訊息「姓名請勿超過 50 個字」並阻止提交

### Requirement 6: 訂位確認摘要

**User Story:** 身為高齡使用者，我希望在送出訂位前能看到所有填寫內容的摘要，以便我確認資訊無誤或返回修改。

#### Acceptance Criteria

1. WHEN 所有必填欄位皆已收集完成, THE Reservation_Agent SHALL 顯示訂位確認摘要卡片，包含餐廳名稱、日期、時段、人數、聯絡人與手機號碼，每項資訊以獨立欄位標籤搭配對應值逐行呈現
2. THE Reservation_Form SHALL 在確認摘要中提供「確認送出」與「返回修改」兩個操作按鈕，「確認送出」使用深海藍主要行動按鈕樣式，「返回修改」使用次要按鈕樣式
3. WHEN 使用者點選「返回修改」, THE Reservation_Form SHALL 保留所有已填寫的欄位資料，並允許使用者選擇回到任一欄位進行修改
4. WHEN 使用者於返回修改後完成欄位變更, THE Reservation_Form SHALL 重新顯示更新後的訂位確認摘要卡片，供使用者再次確認
5. THE Reservation_Form SHALL 在確認摘要卡片中以不小於 16px 字級呈現所有訂位資訊，每項欄位標籤與欄位值分行顯示且標籤使用粗體區隔

### Requirement 7: 訂位送出與訂單建立

**User Story:** 身為高齡使用者，我希望確認送出後系統能為我建立訂位，以便我不需要自己打電話給餐廳。

#### Acceptance Criteria

1. WHEN 使用者點選「確認送出」, THE Order_Service SHALL 建立一筆 mms_order_record 紀錄，order_type 為 "02"，order_status 初始值為 "02"（待確認）
2. WHEN 訂位紀錄建立時, THE Order_Service SHALL 將訂位資訊寫入 order_items 欄位，包含 restaurant_name、people、is_premium、reservedDate、restaurantPhone、restaurantAddress
3. WHEN 訂位紀錄建立時, THE Order_Service SHALL 將 service_time 欄位以 ISO 8601 格式含時區資訊儲存（例如 "2025-06-25T12:30:00+08:00"），時區預設為 Asia/Taipei（UTC+08:00）
4. WHEN 訂位紀錄建立成功, THE Reservation_Form SHALL 顯示「訂位已送出」成功訊息給使用者
5. IF 訂位紀錄建立過程中發生錯誤（資料庫寫入失敗或服務異常）, THEN THE Reservation_Form SHALL 顯示錯誤訊息告知使用者訂位未成功，並保留已填寫的表單資料供使用者重新嘗試送出
6. IF 訂位紀錄建立失敗, THEN THE Order_Service SHALL 於 10 秒內回應失敗結果，不得讓使用者無限期等待

### Requirement 8: 第三方訂位系統串接

**User Story:** 身為高齡使用者，我希望系統能幫我向餐廳即時確認訂位，以便我能馬上知道是否訂位成功。

#### Acceptance Criteria

1. WHEN 訂單建立成功且該餐廳支援第三方訂位系統, THE Order_Service SHALL 於 30 秒逾時限制內呼叫 Third_Party_Booking_API 發送訂位請求
2. WHEN Third_Party_Booking_API 回覆確認成功, THE Order_Service SHALL 將 order_status 設為 "03"（已確認），並將 shareReservationUrl 存入 vendor_data
3. WHEN Third_Party_Booking_API 回覆確認成功, THE Reservation_Form SHALL 顯示「訂位確認連結」供使用者查看訂位詳情
4. WHEN Third_Party_Booking_API 回覆需人工確認, THE Order_Service SHALL 將 order_status 設為 "02"（待確認），並由 Reservation_Form 顯示訊息告知使用者訂位已送出、目前待餐廳確認中
5. WHEN 餐廳不支援第三方訂位系統, THE Order_Service SHALL 將 order_status 設為 "02"（待確認），並由 Reservation_Form 顯示訊息告知使用者訂位已送出、將由客服人員協助確認
6. WHEN Third_Party_Booking_API 以非同步方式回傳確認結果, THE Order_Service SHALL 更新對應訂單之 order_status 與 vendor_data，並透過系統通知告知使用者最新訂位狀態

### Requirement 9: 第三方 API 異常處理

**User Story:** 身為高齡使用者，我希望在系統發生異常時訂位不會遺失，以便我不需要重新填寫所有資訊。

#### Acceptance Criteria

1. IF Third_Party_Booking_API 呼叫超過 10 秒未回應或回傳 HTTP 錯誤, THEN THE Order_Service SHALL 將訂單以 order_status "02"（待確認）狀態保存，確保訂單不遺失
2. IF Third_Party_Booking_API 呼叫失敗, THEN THE Reservation_Form SHALL 於 3 秒內顯示訊息「訂位已送出，目前待確認中，客服將盡快為您處理」，避免使用者誤以為訂位失敗
3. IF Third_Party_Booking_API 呼叫失敗, THEN THE Order_Service SHALL 將該筆訂單標記為「待重試」狀態，由後台重試機制自動處理
4. THE Order_Service SHALL 對標記為「待重試」的訂單，以每 5 分鐘間隔自動重新呼叫 Third_Party_Booking_API，最多重試 3 次
5. IF 訂單已達最大重試次數（3 次）仍未成功, THEN THE Order_Service SHALL 將該筆訂單標記為「需人工介入」，由客服人員手動處理
6. WHEN 後台重試成功且 Third_Party_Booking_API 回覆確認, THEN THE Order_Service SHALL 將 order_status 更新為 "03"（已確認），並透過系統通知使用者訂位已確認

### Requirement 10: 訂位時段額滿處理

**User Story:** 身為高齡使用者，我希望在時段已滿時能即時得知並選擇其他時段，以便我不會白等。

#### Acceptance Criteria

1. WHEN Third_Party_Booking_API 回覆該時段已無空位, THE Reservation_Form SHALL 於 2 秒內顯示訊息「該時段已無空位，建議選擇其他時段」，訊息持續顯示直到使用者進行下一步操作
2. WHEN 時段已滿的訊息顯示後, THE Reservation_Agent SHALL 引導使用者重新選擇日期或時段，並保留使用者已填寫的餐廳選擇、用餐人數、聯絡人姓名與手機號碼，無需重新填寫
3. IF 系統無法即時查詢空位狀態（Third_Party_Booking_API 回應時間超過 10 秒或連線不可用）, THEN THE Order_Service SHALL 在訂單建立後 30 分鐘內以 App 推播通知方式告知使用者訂位結果
4. IF 使用者重新選擇時段後 Third_Party_Booking_API 仍回覆無空位且已連續嘗試 3 次, THEN THE Reservation_Agent SHALL 顯示訊息建議使用者改由客服協助媒合，並提供「轉客服處理」選項

### Requirement 11: 訂單狀態自動推進

**User Story:** 身為系統管理員，我希望訂單狀態能在用餐時間過後自動推進，以便減少人工操作並維持資料正確性。

#### Acceptance Criteria

1. WHEN 訂單 order_status 為 "03"（已確認）且當前時間等於或超過 service_time, THE Status_Scheduler SHALL 將 order_status 更新為 "04"（進行中）
2. WHEN 訂單 order_status 為 "04"（進行中）且當前時間超過 service_time 達 3 小時, THE Status_Scheduler SHALL 將 order_status 更新為 "70"（已完成）
3. IF 訂單 order_status 為 "70"（已完成）且該餐廳於系統設定中啟用核銷機制旗標，且當前時間超過進入 "70" 狀態的時間達 7 天, THEN THE Status_Scheduler SHALL 將 order_status 更新為 "80"（核銷完成）
4. THE Status_Scheduler SHALL 以批次排程 Job 方式執行，執行頻率不低於每 15 分鐘一次，獨立於主要 API 服務之外運行
5. IF 訂單 order_status 為已取消（"90"）或已退款狀態, THEN THE Status_Scheduler SHALL 跳過該筆訂單，不進行任何狀態推進
6. IF Status_Scheduler 執行過程中發生錯誤導致單筆訂單狀態更新失敗, THEN THE Status_Scheduler SHALL 記錄該筆失敗紀錄並繼續處理其餘訂單，不中斷整批作業
7. THE Status_Scheduler SHALL 於每次執行時僅處理符合推進條件的訂單，每批次處理上限為 500 筆

### Requirement 12: 防重複提交

**User Story:** 身為高齡使用者，我希望系統能防止我在等待期間不小心重複送出訂位，以免造成多筆重複訂位。

#### Acceptance Criteria

1. WHEN 使用者點選「確認送出」後, THE Reservation_Form SHALL 於 100 毫秒內將送出按鈕設為不可點擊狀態，防止重複點擊
2. WHILE 訂單正在建立中, THE Reservation_Form SHALL 顯示包含動態圖示與「訂位處理中，請稍候」文字標籤的載入狀態指示，文字字級不小於 16px
3. IF 使用者在同一個 session 中對相同 user_id、restaurant_id、date 與 time_slot 組合重複送出, THEN THE Order_Service SHALL 阻擋重複訂單的建立，並回傳重複偵測結果給前端
4. IF 訂單建立請求超過 30 秒未收到回應或回傳失敗, THEN THE Reservation_Form SHALL 恢復送出按鈕為可點擊狀態，並顯示提示訊息告知使用者可重新嘗試送出
5. IF 重複提交被後端阻擋, THEN THE Reservation_Form SHALL 顯示提示訊息告知使用者該筆訂位已成功送出、無需重複提交

### Requirement 13: 指定/高級訂位標記

**User Story:** 身為高齡使用者，我希望能標記是否需要指定餐廳或高級訂位服務，以便系統安排合適的處理流程。

#### Acceptance Criteria

1. WHEN 聯絡資料填寫完成後, THE Reservation_Agent SHALL 以「一次一問」模式詢問使用者是否需要指定餐廳或高級訂位服務，並以二選一選項呈現（「是，我要指定/高級訂位」與「否，一般訂位即可」），同時附上簡短說明文字解釋高級訂位代表將由專人為您安排指定餐廳或特殊座位需求
2. WHEN 使用者選擇高級訂位, THE Order_Service SHALL 在 order_items 中將 is_premium 標記為 true
3. WHEN 使用者選擇一般訂位, THE Order_Service SHALL 在 order_items 中將 is_premium 標記為 false
4. IF 訂單之 is_premium 為 true, THEN THE Order_Service SHALL 將 order_status 設為 "02"（待確認）並略過 Third_Party_Booking_API 自動呼叫，改由客服人員人工處理該筆訂單

### Requirement 14: 高齡友善介面規範

**User Story:** 身為高齡使用者，我希望訂位介面簡潔易讀且容易操作，以便我能獨立完成訂位而不需要他人協助。

#### Acceptance Criteria

1. THE Reservation_Form SHALL 所有互動元件的觸控區域不小於 44×44px（寬與高皆須滿足）
2. THE Reservation_Form SHALL 所有文字字級不小於 14px；頁面標題、卡片內服務名稱、金額、確認摘要中的訂位資訊等主要內容字級不小於 16px，行高不小於 1.5
3. THE Reservation_Form SHALL 遵循系統既有的「一次一問」對話模式，每一步驟畫面僅呈現單一待填欄位或單一待選操作，不在同一畫面同時顯示多個待填欄位
4. THE Reservation_Form SHALL 使用系統既有的深海藍品牌色（#0F4C81）作為主要行動按鈕色彩，維持「看到深海藍代表可以按」的一致性，非互動裝飾元素不得使用該色彩
5. THE Reservation_Form SHALL 所有狀態訊息同時使用顏色與文字標籤傳達，不單靠顏色區分狀態
6. THE Reservation_Form SHALL 文字與背景的色彩對比度符合 WCAG 2.1 AA 標準：一般文字（小於 18px 或小於 14px 粗體）對比度不低於 4.5:1，大型文字（18px 以上或 14px 粗體以上）對比度不低於 3:1
7. WHILE 使用者裝置啟用 prefers-reduced-motion 設定, THE Reservation_Form SHALL 停用所有非必要的動畫與轉場效果，僅保留即時狀態切換
