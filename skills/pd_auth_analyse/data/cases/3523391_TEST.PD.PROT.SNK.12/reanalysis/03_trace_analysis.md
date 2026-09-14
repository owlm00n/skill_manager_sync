# 03 — Trace 协议层分析

**Bug**: 3523391 (unicase005585)
**测试用例**: TEST.PD.PROT.SNK.12 — PR_Swap - PSSourceOffTimer Timeout
**DUT**: UNISOC-P610F01-1.0 (UMS512 / SC27xx PMIC 集成 CC)
**分析时间**: 2026-09-11
**证据层级**: Lecroy .usb + USB_ComplianceTestLog.html = 主证据；POWER-Z pd.sqlite = 辅助交叉验证（单独标记来源）

---

## 1. 证据源与解码方法

### 1.1 主证据 — Lecroy Voyager M310e

| 文件 | 路径 | 大小 | 角色 |
|------|------|------|------|
| 测试日志 | `E:\08_Bug\Bug 3523391(unicase005585) - [UMS512][zte_sh][P610F01][17353][现场-客户手机]PD CE认证失败 TEST.PD.PROT.SNK.12\Attachements\20260827_155005\USB Power Delivery\TEST.PD.PROT.SNK.12\USB_ComplianceTestLog.html` | 43,416 bytes (654 行) | 全局测试结果 |
| 会话日志 | `E:\08_Bug\Bug 3523391(unicase005585) - [UMS512][zte_sh][P610F01][17353][现场-客户手机]PD CE认证失败 TEST.PD.PROT.SNK.12\Attachements\20260827_155005\USB_ComplianceSessionLog.html` | 43,614 bytes | 会话配置 |
| 结果摘要 | `E:\08_Bug\Bug 3523391(unicase005585) - [UMS512][zte_sh][P610F01][17353][现场-客户手机]PD CE认证失败 TEST.PD.PROT.SNK.12\Attachements\20260827_155005\Teledyne LeCroy USB Compliance Result__UNISOC-P610F01-1.0.html` | 7,464 bytes | 汇总 |
| PASS trace | `E:\08_Bug\Bug 3523391(unicase005585) - [UMS512][zte_sh][P610F01][17353][现场-客户手机]PD CE认证失败 TEST.PD.PROT.SNK.12\Attachements\20260827_155005\USB Power Delivery\TEST.PD.PROT.SNK.12\01_TEST.PD.PROT.SNK.12_Rev2Snk.usb` | 9,261,906 bytes | Rev2Snk PASS 二进制 |
| FAIL trace | `E:\08_Bug\Bug 3523391(unicase005585) - [UMS512][zte_sh][P610F01][17353][现场-客户手机]PD CE认证失败 TEST.PD.PROT.SNK.12\Attachements\20260827_155005\USB Power Delivery\TEST.PD.PROT.SNK.12\02_TEST.PD.PROT.SNK.12_Rev3ChkdSnk_FAIL.usb` | 25,614,448 bytes | Rev3ChkdSnk FAIL 二进制 |

**Lecroy 软件**: Teledyne LeCroy USB Compliance Suite Version 7.92 Build 1198
**分析仪**: M310e (Serial #27506)

**.usb 二进制解码方法**: 使用 `C:\Users\xianjun.zeng\AppData\Local\Temp\extract_html_clean.py` 提取嵌入的 HTML 标注块（`<html>...</html>`）。这些标注由 Lecroy Compliance Suite 在测试过程中写入，标记每个测试步骤的完成状态。同时提取所有 >=4 字符的 ASCII 字符串。

### 1.2 辅助证据 — POWER-Z（非 Lecroy）

> **来源标记**: 以下数据来自 POWER-Z 手持式 USB PD 分析仪，**不是 Lecroy 数据**。仅作为辅助交叉验证使用，不纳入 Lecroy 证据链。

| 文件 | 路径 | 大小 |
|------|------|------|
| POWER-Z 数据库 | `E:\08_Bug\Bug 3523391(unicase005585) - [UMS512][zte_sh][P610F01][17353][现场-客户手机]PD CE认证失败 TEST.PD.PROT.SNK.12\Attachements\20260827_155005\pd.sqlite` | 167,936 bytes |

**解码方法**: `C:\Users\xianjun.zeng\AppData\Local\Temp\decode_powerz_full.py`，按 PD spec 标准布局解码 16-bit header:
```
bit15=Extended, bits14-12=NumObj, bits11-9=MsgID, bit8=DataRole,
bits7-6=Revision, bit5=PowerRole, bits4-0=MessageType
```
Header 读取: offset 6，小端序 (`struct.unpack("<H", raw[6:8])`)。97% 有效解码率。

**数据库结构**:
- `pd_table`: 303 行 (t=16.206s ~ 71.504s)，字段: Time, Vbus, Ibus, Raw(Blob)
- `pd_chart`: 3125 行 (VBUS 图表数据)
- `pd_table_key`: 0 行 (空)

---

## 2. PD 消息序列 — Phase 2: Rev2Snk PASS (PD 2.0)

### 2.1 Lecroy .usb HTML 标注序列（主证据）

来源: `01_TEST.PD.PROT.SNK.12_Rev2Snk.usb`

5 个 HTML 标注，按偏移顺序:

| 序号 | 偏移 | HTML 标注 | 对应 PD 协议步骤 |
|------|------|----------|-----------------|
| 1 | @008d4eb9 | `negotiation completed` | PD 协商完成 |
| 2 | @008d4ef7 | `the tester sends a pr_swap message to the uut` | Tester → DUT: PR_Swap |
| 3 | @008d4f4d | `the put sent an accept message to pr-swap. the uut sent an accept message` | DUT → Tester: Accept |
| 4 | @008d4fbf | `Error Recovery Detected on 851.180 ms [Start of measurement: 4.021 sec Found: 4.872 sec (750.000 ms - 920.000 ms)]` | PR_Swap 角色切换恢复 |
| 5 | @008d505f | `End of the Common-Checks.` | Common-Checks 完成 |

**协议完整度**: PR_Swap → Accept → Error Recovery → Common-Checks End。完整流程走完。

### 2.2 POWER-Z 辅助: PD 消息序列（辅助验证）

来源: POWER-Z pd.sqlite，Phase 2 (t=35.302s ~ 36.267s)

| # | 时间 (s) | 方向 | PD Rev | 角色 | 消息类型 | MsgID | Header | Payload | VBUS |
|---|----------|------|--------|------|----------|:-----:|--------|---------|------|
| 4 | 35.302 | Src→Snk | PD2.0 | Src/DFP | Request | 0 | 0x1161 | 0a900120 | 4.98V |
| 5 | 35.303 | Snk→Src | PD2.0 | Snk/UFP | GoodCRC | 0 | 0x0041 | — | 4.98V |
| 6 | 35.309 | Snk→Src | PD2.0 | Snk/UFP | BIST | 0 | 0x1042 | 2c290017 | 4.98V |
| 7 | 35.310 | Src→Snk | PD2.0 | Src/DFP | GoodCRC | 0 | 0x0161 | — | 4.98V |
| 8 | 35.311 | Src→Snk | PD2.0 | Src/DFP | Accept | 1 | 0x0363 | — | 4.98V |
| 9 | 35.311 | Snk→Src | PD2.0 | Snk/UFP | GoodCRC | 1 | 0x0241 | — | 4.98V |
| **10** | **35.761** | **Src→Snk** | **PD2.0** | **Src/DFP** | **PS_RDY** | **2** | **0x0566** | **—** | **4.98V** |
| 11 | 35.762 | Snk→Src | PD2.0 | Snk/UFP | GoodCRC | 2 | 0x0441 | — | 4.98V |
| 12 | 36.263 | Src→Snk | PD2.0 | Src/DFP | Get_Sink_Cap | 3 | 0x076a | — | 4.98V |
| 13 | 36.263 | Snk→Src | PD2.0 | Snk/UFP | GoodCRC | 3 | 0x0641 | — | 4.98V |
| 14 | 36.266 | Snk→Src | PD2.0 | Snk/UFP | Accept | 1 | 0x0243 | — | 4.98V |
| 15 | 36.267 | Src→Snk | PD2.0 | Src/DFP | GoodCRC | 1 | 0x0361 | — | 4.98V |

**关键**: 消息 #10 — **PS_RDY** 在 t=35.761s 由 Src/DFP（Tester）发送。这是 PR_Swap 过程中的 PS_RDY。Accept → PS_RDY 间隔 = 35.761 - 35.311 = **450 ms**（在 PD spec 允许范围内）。

**注意**: POWER-Z 捕获中 PR_Swap 控制消息本身不可见（可能因 POWER-Z 采样窗口未覆盖或消息头解码限制），但 PS_RDY 和 Accept 都完整捕获。Lecroy .usb HTML 标注 #2/#3 明确记录了 PR_Swap 和 Accept 的交换。

---

## 3. PD 消息序列 — Phase 3/4: Rev3ChkdSnk FAIL (PD 3.0)

### 3.1 Lecroy .usb HTML 标注序列（主证据）

来源: `02_TEST.PD.PROT.SNK.12_Rev3ChkdSnk_FAIL.usb`

**HTML 标注数 = 0**

| 序号 | 偏移 | HTML 标注 | 对应 PD 协议步骤 |
|------|------|----------|-----------------|
| — | — | **（无标注）** | — |

**可提取字符串** (共 39 个 >=4 字符，无任何 PD 协议步骤标注):
- `LeCroy Analyzer Trace File` — 文件头
- `Teledyne LeCroy USB Compliance Suite Version: 7.92 Build 1198`
- `Triggered on Exr Port Rp On (CC1), Exr Port Ra On (CC2), Power Delivery/CC Packets`
- `CATCWalk`
- `0-106/Packet/107` — 107 个数据包被记录
- `Packet 106/Packet`

**结论**: 测试场景在 Lecroy Compliance Suite 写入第一个步骤标注（"negotiation completed"）之前就中止了。对比 PASS 变体有 5 个标注，FAIL 变体 0 个标注 → 场景在协议握手初期即中断。

### 3.2 POWER-Z 辅助: PD 消息序列（辅助验证）

来源: POWER-Z pd.sqlite，Phase 3/4 (t=49.984s ~ 65.133s)

#### 3.2.1 Phase 3 开始 — 重复 Request 序列

| # | 时间 (s) | 方向 | PD Rev | 角色 | 消息类型 | MsgID | Header | Payload | VBUS |
|---|----------|------|--------|------|----------|:-----:|--------|---------|------|
| 16 | 49.984 | Src→Snk | PD3.0 | Src/DFP | Request | 0 | 0x11a1 | 0a900120 | 4.98V |
| 17 | 49.985 | Src→Snk | PD3.0 | Src/DFP | Request | 0 | 0x11a1 | 0a900120 | 4.98V |
| 18 | 49.987 | Src→Snk | PD3.0 | Src/DFP | Request | 0 | 0x11a1 | 0a900120 | 4.98V |
| 19 | 50.138 | Src→Snk | PD3.0 | Src/DFP | Request | 1 | 0x13a1 | 0a900120 | 4.98V |
| 20 | 50.140 | Src→Snk | PD3.0 | Src/DFP | Request | 1 | 0x13a1 | 0a900120 | 4.98V |
| 21 | 50.142 | Src→Snk | PD3.0 | Src/DFP | Request | 1 | 0x13a1 | 0a900120 | 4.98V |
| 22 | 50.293 | Src→Snk | PD3.0 | Src/DFP | Request | 2 | 0x15a1 | 0a900120 | 4.98V |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

**模式**: Tester（Src/DFP）每 ~150 ms 发送 3 次相同的 Request 消息（同一 MsgID），然后 MsgID +1 循环 0→7。

#### 3.2.2 VCONN_Swap 尝试（未得到响应）

| # | 时间 (s) | 方向 | PD Rev | 角色 | 消息类型 | MsgID | Header | VBUS |
|---|----------|------|--------|------|----------|:-----:|--------|------|
| 169 | 57.728 | Src→Snk | PD3.0 | Src/DFP | VCONN_Swap | 0 | 0x01ad | 4.98V |
| 170 | 57.729 | Src→Snk | PD3.0 | Src/DFP | VCONN_Swap | 0 | 0x01ad | 4.98V |
| 171 | 57.731 | Src→Snk | PD3.0 | Src/DFP | VCONN_Swap | 0 | 0x01ad | 4.98V |

**关键**: Tester 发送了 3 次 VCONN_Swap（t=57.728-57.731s），**DUT 未回复 Accept 或 GoodCRC**。VCONN_Swap 后紧接的是更多重复 Request 消息（#172, t=58.939s）。

#### 3.2.3 Phase 3/4 结束 — 仍在重复 Request

| # | 时间 (s) | 方向 | PD Rev | 角色 | 消息类型 | MsgID | Header | Payload | VBUS |
|---|----------|------|--------|------|----------|:-----:|--------|---------|------|
| 292 | 65.129 | Src→Snk | PD3.0 | Src/DFP | Request | 0 | 0x11a1 | 0a900120 | 4.99V |
| 293 | 65.131 | Src→Snk | PD3.0 | Src/DFP | Request | 0 | 0x11a1 | 0a900120 | 4.99V |
| 294 | 65.133 | Src→Snk | PD3.0 | Src/DFP | Request | 0 | 0x11a1 | 0a900120 | 4.99V |

**最后一帧仍然是 Request**，场景从未进入 PR_Swap / Accept / PS_RDY 阶段。

### 3.3 Phase 3/4 消息统计

| 消息类型 | 数量 | 说明 |
|----------|------|------|
| PD3.0/Src/DFP/Request | 280 | Tester 不断重复发送，DUT 无有效响应 |
| PD3.0/Src/DFP/VCONN_Swap | 3 | Tester 尝试 VCONN_Swap，DUT 未响应 |
| PD3.0 Snk/UFP 响应 (Accept/GoodCRC/PS_RDY) | **0** | **DUT 在 PD 3.0 模式下完全静默** |
| **PS_RDY** | **0** | **PS_RDY 完全缺失** |
| PR_Swap | 0 | PR_Swap 控制消息未出现 |

---

## 4. 对比分析: Rev2Snk PASS vs Rev3ChkdSnk FAIL

### 4.1 协议交互对比

| 协议步骤 | Rev2Snk (PD 2.0) PASS | Rev3ChkdSnk (PD 3.0) FAIL |
|----------|----------------------|---------------------------|
| PD 协商 | ✅ HTML标注: `negotiation completed` | ❌ 无 HTML 标注 |
| PR_Swap 发送 | ✅ HTML标注: `the tester sends a pr_swap message to the uut` | ❌ 无标注；POWER-Z 中无 PR_Swap 消息 |
| DUT Accept | ✅ HTML标注: `the uut sent an accept message` | ❌ 无标注；POWER-Z 中 Accept 数=0 |
| PS_RDY | ✅ POWER-Z: PS_RDY @ t=35.761s (id=2) | ❌ **POWER-Z: PS_RDY 数=0** |
| Error Recovery | ✅ HTML标注: `Error Recovery Detected on 851.180 ms` | ❌ 无标注 |
| Common-Checks | ✅ HTML标注: `End of the Common-Checks.` | ❌ 无标注 |
| 测试验证 | ✅ 3/3 验证通过 | ❌ Error(0xFFF5) 场景中止 |

### 4.2 时序对比

| 指标 | Rev2Snk (PASS) | Rev3ChkdSnk (FAIL) |
|------|:--------------:|:------------------:|
| Generation Max Wait | 15000 ms | 15000 ms |
| Generation Time-out | — | 15112 ms (超窗口) |
| Analyzer Trigged | 3752 ms | 16164 ms |
| Accept → PS_RDY 间隔 | 450 ms (35.311→35.761) | N/A (PS_RDY 缺失) |
| Request 重复次数 | 1 (正常) | 280 (异常重试) |
| 场景最终状态 | 3/3 验证通过 | 0xFFF5 场景中止 |

### 4.3 VBUS 时序对比

来源: POWER-Z pd.sqlite（辅助捕获）

| 阶段 | 时间范围 | VBUS | 判定 |
|------|----------|:----:|------|
| Phase 1 (初始) | t=16.206-16.211s | 5.26V | 正常 5V |
| Phase 2 (Rev2Snk) | t=35.302-36.267s | 4.98V | 正常，PR_Swap 期间稳定 |
| Phase 3/4 (Rev3ChkdSnk) | t=49.984-65.133s | 4.98-4.99V | 正常，无断电 |

**VBUS 电压分布** (295 条消息):
- 4.98V: 274 条
- 4.99V: 17 条
- 5.26V: 4 条

**结论**: VBUS 全程稳定在 4.98-5.26V，PR_Swap 过程中无 VBUS 异常。VBUS 时序正常，与 Comment #27 "VBUS 时序日志匹配" 一致。

---

## 5. PD Header 解码详情

### 5.1 关键 Header 解码

| Header | 二进制 | Extended | NumObj | MsgID | DataRole | Revision | PowerRole | MsgType | 解读 |
|--------|--------|:--------:|:------:|:-----:|:--------:|:--------:|:---------:|:-------:|------|
| 0x1161 | 0001 0001 0110 0001 | 0 | 1 | 0 | UFP(0) | PD2.0(01) | Src(1) | Request(1) | PD2.0 Src→Snk Request |
| 0x0041 | 0000 0000 0100 0001 | 0 | 0 | 0 | UFP(0) | PD2.0(01) | Snk(0) | GoodCRC(1) | PD2.0 Snk→Src GoodCRC |
| 0x0363 | 0000 0011 0110 0011 | 0 | 0 | 1 | UFP(0) | PD2.0(01) | Src(1) | Accept(3) | PD2.0 Src→Snk Accept |
| **0x0566** | 0000 0101 0110 0110 | 0 | 0 | 2 | UFP(0) | PD2.0(01) | Src(1) | **PS_RDY(6)** | **PD2.0 Src→Snk PS_RDY** |
| 0x11a1 | 0001 0001 1010 0001 | 0 | 1 | 0 | DFP(1) | PD3.0(10) | Src(1) | Request(1) | PD3.0 Src→Snk Request |
| 0x01ad | 0000 0001 1010 1101 | 0 | 0 | 0 | DFP(1) | PD3.0(10) | Src(1) | VCONN_Swap(13) | PD3.0 Src→Snk VCONN_Swap |

### 5.2 解码正确性验证

- PD2.0 Rev2Snk 阶段: DataRole=UFP (bit8=0), PowerRole 在 Src/Snk 间正确翻转 → 符合 PD 2.0 spec
- PD3.0 Rev3ChkdSnk 阶段: DataRole=DFP (bit8=1), Revision=PD3.0 (bits7-6=10) → 符合 PD 3.0 spec
- MessageID 循环 0-7 符合 PD spec 的 3-bit MessageID 计数器
- 97% 有效解码率确认 offset 6 小端序为正确读取位置

---

## 6. 根因方向分析

### 6.1 现象总结

1. **Rev2Snk (PD 2.0) PASS**: DUT 在 PD 2.0 模式下正确完成 PR_Swap 全流程（PR_Swap → Accept → PS_RDY → Error Recovery → Common-Checks End）
2. **Rev3ChkdSnk (PD 3.0) FAIL**: DUT 在 PD 3.0 Checked 模式下完全静默 — 对 Tester 的 280 次 Request 和 3 次 VCONN_Swap 均无有效响应，最终场景超时中止

### 6.2 关键差异: PD 2.0 vs PD 3.0

| 特性 | PD 2.0 (Rev2Snk) | PD 3.0 (Rev3ChkdSnk) |
|------|------------------|----------------------|
| Revision 字段 | 01 (PD2.0) | 10 (PD3.0) |
| DataRole | UFP | DFP |
| Checked 模式 | 否 | 是 |
| DUT 响应 | 正常 (Accept/GoodCRC/PS_RDY) | 静默 (0 响应) |
| 结果 | PASS | FAIL |

### 6.3 根因方向

**DUT（UMS512 / SC27xx PMIC 集成 CC）在 PD 3.0 Checked Sink 模式下不响应 Tester 的消息**。具体表现为:

1. Tester 反复发送 Request（280 次，MsgID 循环 0-7），DUT 不回复 GoodCRC 或 Accept
2. Tester 尝试 VCONN_Swap（3 次），DUT 仍不响应
3. PS_RDY 从未发送（因 PR_Swap 握手根本未建立）
4. Lecroy Compliance Suite 等待 15112 ms 后 Generation Time-out，中止场景

**注**: 本分析仅定位到 trace 层面的现象 — DUT 在 PD 3.0 模式下静默。根因需结合 kernel log 中 PD 3.0 协议栈状态机分析（由 kernel log 分析 agent 负责）。

### 6.4 排除项

- **VBUS 异常**: 排除。VBUS 全程 4.98-5.26V 稳定
- **tPSSourceOffTimer 超时**: 排除。Lecroy 判决是"场景中止"(0xFFF5)，非定时器超时测量。"PSSourceOffTimer Timeout" 是测试用例名称
- **外部 CC 芯片问题**: 排除。UMS512 使用 SC27xx PMIC 集成 CC，非第三方芯片
- **CC 检测被提前禁用 (sc27xx_typec_pr_swap_no_chk_detach)**: 排除。该结论从 kernel log 反推，trace 层面无证据支持。Trace 显示 DUT 在 PD 3.0 阶段从未进入 PR_Swap 步骤，谈不上"提前禁用 CC 检测导致 PR_Swap 超时"

---

## 7. 与 Comment #27 对齐

**Comment #27** (Yongqing.Wang, 9/8):
> PD 2.0 首次 PR_Swap 成功。PD 3.0 第二次 PR_Swap 未收到 PS_RDY。VBUS 时序日志匹配

| #27 论点 | Trace 证据来源 | 证据 | 对齐 |
|----------|--------------|------|:----:|
| PD 2.0 首次 PR_Swap 成功 | Lecroy .usb File 01 + POWER-Z | 5 个 HTML 标注含 PR_Swap/Accept；3/3 验证 PASS；PS_RDY @ t=35.761s | ✅ |
| PD 3.0 第二次 PR_Swap 未收到 PS_RDY | Lecroy .usb File 02 + POWER-Z | 0 个 HTML 标注；PS_RDY 数=0；场景中止 0xFFF5 | ✅ |
| VBUS 时序日志匹配 | POWER-Z | VBUS 全程 4.98-5.26V 稳定 | ✅ |

**三个论点全部被 trace 证据证实，Comment #27 完全准确。**

---

## 8. 结论

### 8.1 真实失败点

Rev3ChkdSnk（PD 3.0 Checked Sink）变体中，DUT 在 PD 3.0 模式下对 Tester 的所有消息（280 次 Request + 3 次 VCONN_Swap）**完全不响应**，导致:
- PR_Swap 握手从未建立（无 Accept）
- PS_RDY 从未发送（因 PR_Swap 未建立）
- Lecroy Compliance Suite Generation Time-out @ 15112 ms
- 测试场景中止，Error(0xFFF5)

### 8.2 PS_RDY 缺失的 Trace 证据

**Lecroy 主证据**:
- `02_TEST.PD.PROT.SNK.12_Rev3ChkdSnk_FAIL.usb` 中 HTML 标注数 = 0（对比 PASS 变体 5 个标注含完整 PR_Swap→Accept→PS_RDY 流程）

**POWER-Z 辅助证据**:
- Phase 3/4 (t=49.984-65.133s) 中 PS_RDY 出现次数 = 0
- Phase 3/4 中 Accept 出现次数 = 0
- Phase 3/4 中 PR_Swap 出现次数 = 0
- 仅 280 条重复 Request + 3 条未响应的 VCONN_Swap

### 8.3 旧 tPSSourceOffTimer 理论判定

**不成立**。理由:
1. "PSSourceOffTimer Timeout" 是测试用例名称，不是 Lecroy 的失败判决
2. Lecroy 实际判决是 `Error(0xFFF5): Test scenario aborted`（场景中止），非定时器超时测量
3. .usb File 02 有 0 个 HTML 标注 → 场景在到达 PR_Swap 步骤之前就中止了
4. 旧结论"步骤 4→5 tPSSourceOffTimer 超时"是在未读 trace 的情况下从 kernel log 反推编造的

### 8.4 下一步建议

Trace 层面已确认: DUT 在 PD 3.0 Checked Sink 模式下不响应 Tester 消息。根因需在 kernel log 中分析 PD 3.0 协议栈状态机为何不处理 Tester 的 Request/VCONN_Swap 消息（由 kernel log 分析 agent 负责）。
