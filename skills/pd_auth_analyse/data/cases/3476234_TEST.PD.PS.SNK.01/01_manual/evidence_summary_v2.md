# Bug 3476234 — 证据收集报告

> Bug 3476234 (SPCSS01684954) · UMS9230H · HUAQIN_BD2 · vivo PD2577F · 1-Critical
> 测试项：TEST.PD.PS.SNK.01 (PDO Transitions As Sink)
> 报告日期：2026-07-10
> 本报告只做证据收集与汇总，不做根因定性。

---

## 一、测试项背景

### 1.1 测试项测什么

**TEST.PD.PS.SNK.1（PDO Transitions As Sink）** 是 USB PD3 CTS（Q4 2024 + SNK1 ECN）下"电源特定测试"中的 Sink 侧 PDO 切换测试。测试在 LeCroy Voyager M310e Compliance Suite 上执行，Tester 扮演 Source，UUT（被测手机）扮演 Sink。

核心验证目标：**当 Tester 依次下发不同 PDO 组合的 Source_Capabilities 时，UUT 作为 Sink 能否正确对每一组新的 Source_Capabilities 回 Request 消息，并在允许的 PDO 范围内完成协商。** 测试包含 16 个子检查项 #1–#16，在两种 PD Spec Revision 条件下分别运行：
- **Rev2Snk**：PD Spec Rev 2.0 条件
- **Rev3ChkdSnk**：PD Spec Rev 3.0/3.1 条件（Checked Snk，即带协议校验的 PD3 Sink 行为）

### 1.2 通过/失败判定标准

- **整体判定**：Repeat_0X 下，Rev2Snk 与 Rev3ChkdSnk 两个条件的全部 #1–#16 检查项均须 PASS，该项才算 PASS。
- **关键子检查语义**（与本次失败直接相关）：
  - **#2**：UUT 在收到新的 Source_Capabilities 后，应发送 Request 消息。失败码 `Error(0x00000003): The tester did not send Source_Capabilities message. | The UUT did not send a Request message.`
  - **#7**：验证 UUT 发送的 Request 消息合规。失败码 `Error(0x00000157): The UUT did not send a Request message.`
  - **#12**：所请求的 PDO 落在 VIF 声明的 Sink PDO 范围内。
- **包级 Common Check（CTS 通用校验，源自 .usb.xml 解码）**：
  - `COMMON.CHECK.PD.5.2`：UUT 不得在不允许时发送 Hard_Reset。
  - `COMMON.CHECK.PD.5.5`：UUT 不得执行非预期 Error Recovery。
  - `COMMON.CHECK.PD.12.1`：UUT 发出的 Sink_Capabilities 的 Data Object 数量与 supply 类型须与 VIF 一致。

### 1.3 失败可能原因（可能性列举，非定性）

1. **PD 时序阻塞**：UUT 在处理 Source_Capabilities → 构造 Request 的路径上，被同步阻塞操作卡住，导致 Request 未在 PD 时序窗口内发出，进而触发 Tester 超时 / UUT 自发 Hard_Reset / Error Recovery。
2. **PD 协议栈状态机缺陷**：Sprd_TcpM 在收到新 Source_Capabilities 后的状态转换异常，未进入 Send_Request 路径。
3. **限流/充电 IC 路径阻塞**：构造 Request 时同步调用 `POWER_SUPPLY_SET_PROPERTY(...PD_REQ_CUR...)`，该调用经 charger driver 同步下发 I2C，阻塞 PD 收发上下文。
4. **BC1.2 / APSD 干扰**：`mdelay` / `msleep` 在 PD 通信窗口内占用，或 apsd_detect 误触发影响 Sink 行为。
5. **VIF 与实际 Sink_Capabilities 不一致**：配置层 PDO 数量/类型与 VIF 声明不符（独立于时序的合规问题）。
6. **PD2/PD3 适配差异**：失败仅出现在 PD3（Rev3ChkdSnk），PD2（Rev2Snk）全过，提示 PD3 协议路径有额外校验被触发。

---

## 二、需要什么证据

基于测试项特点（Sink 侧"收 SourceCap → 回 Request"时序敏感、且失败仅限 PD3），需要以下证据，按优先级排序：

| 优先级 | 证据类型 | 获取方式 | 用途 |
|--------|----------|----------|------|
| P0 | **FAIL/PASS 合规测试日志（per-check pass/fail）** | LeCroy 导出的 `USB_ComplianceTestLog.html` | 锁定到底是哪几个 check 失败、哪个 Revision 条件失败 |
| P0 | **FAIL 包级解码结果（Common Check 错误码）** | `.usb.xml`（trace 的解码校验报告） | 锁定包级行为异常（Hard_Reset/Error Recovery/Sink_Cap 与 VIF 比对） |
| P0 | **修复 patch** | `Attachements/13f31c6.diff` | 提取开发者自述的修改原因/解决方法，定位代码路径 |
| P1 | **VIF 关键字段** | trace 同目录 VIF xml（嵌入合规日志） | 对照 #12 / COMMON.CHECK.PD.12.1 的 PDO 声明 |
| P1 | **PASS run 对照** | PASS trace 的合规日志 + .usb.xml | 差分确认：通过态下同样的 check 全 PASS，佐证失败是真实可复现且 PD3 专属 |
| P2 | **kernel log 中 patch 行为标记** | `mobilelog/APLog_*/kernel_log_*` | 确认 `power_supply set done` / `em_authorized` / `sprd_tcpm_ic_limit_worker` 线程是否在实际运行、运行时机 |
| P2 | **FAIL/PAS trace 差分时序** | `.usb` 二进制（需 Lecroy 工具解码） | 精确 Request 缺失时刻 vs Source_Capabilities 下发时刻 |

> 说明：`.usb` 为 LeCroy 二进制，Windows bash 无 `strings` 可用；但同目录 `.usb.xml`（解码校验报告）与 `USB_ComplianceTestLog.html`（per-check 日志）已包含解码后的检查结论与错误码，足以替代原始包解码用于"是否发 Request / 是否发 Hard_Reset"的判定。

---

## 三、证据检索结果

### 3.1 证据 A：FAIL run 合规测试日志（per-check pass/fail）

- **来源**：`…\3FILL0PASS 357766\20260706_210703\…\TEST.PD.PS.SNK.1\Repeat_01\USB_ComplianceTestLog.html`
- **工具**：Read（HTML 文本读取）
- **关键发现**：
  - TEST.PD.PS.SNK.01 整体 **FAIL**。
  - **Rev2Snk（PD2 条件）：全部检查 PASS。**
  - **Rev3ChkdSnk（PD3 条件）：#2 FAIL、#7 FAIL；其余 #1/#12/#13/#14/#3–#6/#15/#16/#8–#11 均 PASS。**
  - #2 失败码：`Error(0x00000003): The tester did not send Source_Capabilities message. | The UUT did not send a Request message.`
  - #7 失败码：`Error(0x00000157): The UUT did not send a Request message.`
  - Tester：Voyager #27255，BoardID=161，BoardRev=9。
  - VIF（V2606/0319）关键字段：PD_Spec_Rev=3.1 v1.8；Num_Snk_PDOs=2；Snk_PDO1=10V/3A；Snk_PDO2=18V/1.6A；PD_Power_As_Sink=15W；Num_Src_PDOs=1；Src_PDO1=10V/1.2A；PD_Power_As_Source=6W；Accepts_PR_Swap=YES；EPR_Supported=NO。
- **证据结论**：失败精确锁在 PD3/Rev3ChkdSnk 条件下的 #2 与 #7，二者均报告"UUT 未发送 Request 消息"；PD2 全过。说明问题与 PD3 协议路径强相关，且表现为"收到新 Source_Capabilities 后未（及时）回 Request"。

### 3.2 证据 B：FAIL run 包级解码（Common Check 错误码）

- **来源**：`…\Repeat_01\02_TEST.PD.PS.SNK.1_Rev3ChkdSnk.usb.xml`
- **工具**：Read（XML 解码校验报告）
- **关键发现**：
  - `COMMON.CHECK.PD.5.2` **3/3 FAIL**：`Err#0x02A8: The UUT was not allowed to send Hard_Reset signal.` —— UUT 共 3 次发送了本不应发送的 Hard_Reset。
  - `COMMON.CHECK.PD.5.5` **1 FAIL**：`Err#0x0525: The UUT unexpectedly performs an Error Recovery.` —— UUT 执行了一次非预期 Error Recovery。
  - `COMMON.CHECK.PD.12.1` **1/1 FAIL**：`Err#0x00FD: Number of Data Objects did not match vendor value` + `Err#0x01CD: supply types in Sink Capabilities did not match VIF` —— UUT 发出的 Sink_Capabilities 与 VIF 声明（Num_Snk_PDOs=2）不一致。
  - `COMMON.PROC.PD.10.1`（UUT Sent Request）：6 次出现，0 失败 —— UUT 全程确实发过 6 条 Request 且格式合规。
  - `COMMON.CHECK.PD.8`（Check Request Message）：6 次，0 失败 —— 已发的 Request 均合规。
  - 所有 EPR 相关检查：0 次出现（非 EPR 场景）。
- **证据结论**：UUT 并非完全不会发 Request（有 6 条合规 Request），而是**在特定 Source_Capabilities 切换点上未发 Request**，转而触发 Hard_Reset（3 次）与 Error Recovery（1 次）；同时 Sink_Capabilities 本身与 VIF 存在结构不一致。这与 #2/#7"在某一 PDO 切换点未回 Request"互为印证。

### 3.3 证据 C：修复 patch（开发者自述根因 + 代码改动）

- **来源**：`Attachements/13f31c6.diff`
- **工具**：Read（全量读取 diff）
- **关键发现**：
  - Commit message（开发者自述）：
    - 修改原因：**POWER_SUPPLY_SET_PROPERTY 时间超时**
    - 解决方法：**使用 work 进行规避**
    - 关联 BPM：欧盟认证相关测试报 fail（B260506-84526）
  - `drivers/usb/typec/tcpm/sprd_tcpm.c`：
    - 新增 `sprd_tcpm_ic_limit_work_handler()`（kthread_work），在其中执行 `POWER_SUPPLY_SET_PROPERTY(batt_psy, POWER_SUPPLY_PROP_PD_REQ_CUR, …)`，并打印 `pr_info("… power_supply set done")`。
    - `sprd_tcpm_set_cm_ic_limit_current()` 签名由全局改为 `port` 入参，函数体改为**只填字段 + `kthread_queue_work(&port->ic_limit_kworker, &port->ic_limit_work)`**，并注释 `/* Async power_supply operation to avoid blocking PD timing */`。
    - 三处调用点更新为传 `port`：`sprd_tcpm_pd_ctrl_request`、`sprd_tcpm_pd_build_request`、`sprd_tcpm_reset_port`。其中 `sprd_tcpm_pd_build_request` 正是构造 Request 的路径。
    - `sprd_tcpm_register_port` 新建 `ic_limit_kworker`/`ic_limit_task`（线程名 `sprd_tcpm_ic_limit_worker`）并 `kthread_init_work(ic_limit_work)`；error path 与 `unregister_port` 中 `kthread_flush_worker`+`kthread_stop`。
  - `include/linux/usb/sprd_tcpm.h`：`sprd_tcpm_port` 新增 `ic_limit_kworker/ic_limit_task/ic_limit_work/ic_limit_pdo_type/ic_limit_req_vol/ic_limit_req_cur/ic_limit_enable_limit`。
  - `drivers/power/supply/vchg/vivo-sgm41512_charger.c`：
    - 删除 `sc8960x_set_dp` / `sc8960x_set_dm` 中的 3 处 `mdelay(5)`。
    - `sgm41512_apsd_detect_work` 增加 `extern unsigned int em_authorized;`，并将条件改为 `if (chip->is_sc89601d && !chip->direct_charger_enable && em_authorized)`。
- **证据结论**：patch 自述根因落在"在 PD 处理路径同步调用 `POWER_SUPPLY_SET_PROPERTY` 导致超时"，规避方式为**将限流相关 power_supply 同步调用改为独立 kthread worker 异步执行**，并移除 charger 侧 `mdelay(5)`、给 apsd_detect 加 `em_authorized` 守卫。改动点覆盖了构造 Request（`pd_build_request`）路径，与 #2/#7"未发 Request"在代码路径上吻合。

### 3.4 证据 D：PASS run 合规日志（差分对照）

- **来源**：`…\3pass 360579\20260707_170346\…\TEST.PD.PS.SNK.1\Repeat_01\USB_ComplianceTestLog.html`
- **工具**：Read
- **关键发现**：
  - 同一测试项、同一 VIF（V2606-0000）、同一 Tester（#27255）下，**TEST.PD.PS.SNK.1 整体 PASS**。
  - **Rev2Snk pass、Rev3ChkdSnk pass**；#1–#16 全 PASS，其中 **#2 pass**（line 807）、**#7 pass**（line 887）。
- **证据结论**：PASS run 下 PD3/Rev3ChkdSnk 的 #2/#7 均 PASS，证实失败真实存在且可复现，差分点正是 FAIL run 中失败的 #2/#7。结合两 run 时间（FAIL=0706 21:07，PASS=0707 17:03）与 patch 存在，PASS run 具备"patch 已生效"的时间窗——但需 kernel log 佐证（见 §5）。

### 3.5 证据 E：VIF 关键字段（对照 #12 / 12.1）

- **来源**：嵌入 FAIL run 合规日志的 VIF（V2606/0319）字段
- **工具**：Read（同 3.1 一次读取获得）
- **关键发现**：Num_Snk_PDOs=2、Snk_PDO1=10V/3A、Snk_PDO2=18V/1.6A、PD_Power_As_Sink=15W；EPR_Supported=NO；Accepts_PR_Swap=YES。
- **证据结论**：VIF 声明 2 个 Fixed Sink PDO、SPR（非 EPR）。`COMMON.CHECK.PD.12.1` 报"Data Object 数量/supply 类型与 VIF 不符"，提示**实际发出的 Sink_Capabilities 在某次发送时结构异常**（非时序问题，是合规层独立异常），需结合 trace 时序确认是否与 Hard_Reset/Error Recovery 同源。

### 3.6 证据 F：kernel log 行为标记（部分命中 — 存在缺口）

- **来源/工具**：Grep FAIL/PASS run 的 `mobilelog/APLog_*/kernel_log_*`
- **关键发现**：两 run 均只命中 `em_authorized: 0`；patch 新增的 `pr_info("…power_supply set done")` 与线程名 `sprd_tcpm_ic_limit_worker` **未在所抓 kernel_log 中出现**。
- **证据结论**：无法从现有 kernel_log 直接证实"patch 的异步 worker 在测试窗口内实际执行"。这是一个**证据缺口**，见 §5。

---

## 四、证据汇总

| # | 证据 | 来源产物 | 工具 | 关键发现 | 结论指向 |
|---|------|----------|------|----------|----------|
| A | FAIL 合规日志 | `USB_ComplianceTestLog.html`（FAIL run Repeat_01） | Read | PD2 全过；PD3 仅 #2/#7 FAIL（"UUT did not send a Request"） | 失败仅 PD3，表现为"未回 Request" |
| B | FAIL 包级解码 | `02_…_Rev3ChkdSnk.usb.xml` | Read | Hard_Reset 非授权 3/3、Error Recovery 非预期 1、Sink_Cap 与 VIF 不符；Request 全程 6 条且合规 | 缺失 Request 集中于特定切换点，伴随 Hard_Reset/ErrRecovery |
| C | 修复 patch | `13f31c6.diff` | Read | 自述根因：POWER_SUPPLY_SET_PROPERTY 超时；改异步 kthread worker；去 mdelay；加 em_authorized | 代码路径覆盖 `pd_build_request`，与"未发 Request"路径吻合 |
| D | PASS 合规日志 | `USB_ComplianceTestLog.html`（PASS run Repeat_01） | Read | #1–#16 全 PASS，含 #2/#7；Rev2Snk+Rev3ChkdSnk 均 pass | 失败可复现，差分点即 #2/#7 |
| E | VIF 字段 | 合规日志内嵌 VIF | Read | Num_Snk_PDOs=2（10V/3A, 18V/1.6A），SPR，非 EPR | 12.1 失败指向 Sink_Cap 结构异常，独立合规项 |
| F | kernel log 标记 | `APLog_*/kernel_log_*` | Grep | 仅命中 `em_authorized:0`；未命中 `power_supply set done` / worker 线程 | 证据缺口，未能从日志侧坐实 patch 运行 |

---

## 五、待确认事项

1. **kernel log 缺口**：patch 新增的 `pr_info("…power_supply set done")` 与线程 `sprd_tcpm_ic_limit_worker` 未在所抓 kernel_log 中命中。需确认：
   - 所抓 kernel_log 是否覆盖 FAIL/PASS 测试窗口（0706 21:07 / 0707 17:03）？
   - 该 `pr_info` 是否被打入其他 log buffer（如 dmesg / mobile_log_zip）而未被 Grep 命中？
   - 建议补充抓取测试时刻对齐的完整 kernel_log 并按时间窗过滤。

2. **FAIL/PAS 与 patch 时间线关系**：FAIL run=0706、PASS run=0707，patch 提交日期为 2026-06-10（早于两次测试）。需确认两次 run 的镜像是否已合入 patch：若 FAIL run 镜像已含 patch 仍失败、PASS run 镜像含 patch 通过，则失败可能为**时序敏感/flaky**或**依赖运行时状态（em_authorized 取值、充电 IC 状态）**，而非"是否合 patch"的二元关系。需获取两次测试的镜像版本号与 patch 合入状态确认。

3. **Sink_Capabilities 与 VIF 不符的根因归属**：`COMMON.CHECK.PD.12.1`（Err#0x00FD/0x01CD）是独立合规缺陷还是与"未发 Request → Hard_Reset/ErrRecovery"同源（如 Error Recovery 后重发的 Sink_Cap 异常）？需在 `.usb` 二进制中按时间轴定位异常 Sink_Cap 的发送时刻，确认它与 Hard_Reset/ErrRecovery 的先后关系。该步需 LeCroy 工具或支持 PD 包解码的解析器解码原始 `.usb`。

4. **#2 报错语义复核**：#2 失败码同时含"The tester did not send Source_Capabilities message."与"The UUT did not send a Request message."——前者字面为"Tester 没发 Source_Cap"，需确认该报错是 Tester 侧语义（因 UUT 状态导致 Tester 中止 Source_Cap 序列）还是真实 Tester 未发出，建议对照 PASS run 同名 `.usb.xml` 的 `COMMON.CHECK.PD.7`（Source Cap）出现次数做差分。

5. **em_authorized 取值影响**：两 run 均为 `em_authorized: 0`，而 patch 给 apsd_detect 加了 `&& em_authorized` 守卫。需确认 `em_authorized=0` 时 apsd_detect 走哪条分支、是否因此改变了 BC1.2/APSD 时序从而影响 PD3 行为，需结合 charger driver 上下文确认。

6. **PD2/PD3 路径差异点**：失败仅 PD3 出现，需在 `sprd_tcpm.c` 中确认 PD3（Rev3ChkdSnk）相较 PD2 多触发的校验/状态路径（如 extended cap / SPR AVS / chunking 相关），以解释为何同一阻塞只影响 PD3。
