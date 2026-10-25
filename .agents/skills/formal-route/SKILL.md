---
name: formal-route
description: 評估測試是否保護獨立產品契約，選擇必要的形式化方法與 Lab 證據，支持保留、改寫、合併或刪除的工程判斷。
---

# Formal route

本 Lab 是通用方法與互動契約的唯一來源。任何 Repo 都可使用，不需依賴 Soodles、Noodle、原 Owner 或原 Session。Session 負責工程判斷，原 Repo 的測試與驗收入口保留執行及交付責任。

先讀 [測試價值與方法](../../../docs/FORMAL-ROUTE.md)。原 Goal、Measurement、Effort 與有效續行沿用；只有新的可反駁前提才重新思考，不增加固定回合、測項數或決策數門檻。

分類或統計測項時引用 [測試分類契約](../../../docs/TEST-CATALOG.md)：方法、執行環境、受保護的行為模組、保留裁決與需求條件分開。CI 是環境，必要性依具體觸發判定；多標籤按原 ID 去重並分粒度計數。用唯讀 `catalog` 查詢 caller 自有資料，不由標籤新增選測、跳過或 gate；欄位齊全不證明價值，未知必要數不能填零。

完整跨 Repo 資料流與工具責任引用 [交互契約](../../../docs/ROUTE-INTERACTION.md)，來源定位品質引用 [映射量測契約](../../../docs/SOURCE-MAPPING.md)。本入口保留方法與工程判斷；機械欄位、拒絕、讀回與度量交原程式。文件不因移動而變成可執行流程，>99% 只適用實際量測的固定母體，不延伸為語義或價值保證。

先問測試是否驗證產品需求，而非替目前實作背書。逐項核對獨立 Oracle、外部契約／不變量、具體失效判別、替代覆蓋、實際觸發與成本。必要與按需測試都接受同一評估。優先處理 Implementation-Coupled Testing、Self-Verification 與 Oracle Problem；另一個 Agent、綠燈、coverage、測項數或模型一致都不自動解決它們。

若是明確重複或脆弱實作預期，先用原契約與具體正／負例判斷。有限替代覆蓋問題使用 [互動契約](../../../docs/TEST-RETENTION-INTERACTION.md)，保持原 fixture、entrypoint、來源與觀測界限。若未決點是狀態、並發、重試、UNKNOWN 效果或純函式性質，再按方法文件選 Quint／Apalache、歸納、P4 或實際 trace conformance。不要為了使用 formal-route 強迫所有測試跑 solver 或新增永久 formal job。

獨立預期來源不明時繼續補證，不認定該測試已值得保留，也不把缺證據當成可刪。修改預期前，說明哪條獨立契約改變；不得由新實作輸出反向生成驗收答案。合併／刪除前核對原故障與合法鄰例都由已驗證替代保護。新增形式化測試本身也要證明保留價值。

原 Repo Test Manager 選定實際控制並執行。現有 Schema／feedback 工具只傳遞原來源與結果；可用時沿其原契約消費，不新增 Manager 或平行狀態。Carrier、Hook、Cron、Provider 或 CI 各需其原觸發與授權，不因這個 route 自動執行。一般 Repo 測試不以 Lab 可用性為前置條件。

保存實際方法、來源／工具版本、命令、界限、退出、正負控制、反例、UNKNOWN 與成本。重用仍有效的既有證據，不重跑未變模型。Lab 只讀選定資料，模型 PASS／有限 coverage PASS 都不批准刪測、效果、重試或 merge；最後由 Session 依獨立產品契約裁決並更新原 handoff。

新／變更 route 的分層、thinking route 交互與去留判斷，必須依方法文件的 [行為 eval](../../../docs/FORMAL-ROUTE.md#required-route-behavior-evaluation) 使用實際 eval skills 與 fresh consumer 證據驗證。Unit、CI、模型、實際 trace 與 Agent 行為各有不同已知／未知界限，不能互代。已知事實直接讀回；真正新語義未決才回 thinking route。不能用文件關鍵字、schema PASS 或另一個 Agent 評分取代真實行為，也不為每個測項強制另跑一輪 eval。新缺口只限制其依賴的主張。
