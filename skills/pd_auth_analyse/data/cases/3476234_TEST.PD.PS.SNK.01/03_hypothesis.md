# Bug 3476234 — 根因假设 & 排查地图

## 结论

- **TEST_ID**：`TEST.PD.PS.SNK.01`
- **失败现象**：
  - TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail
- **keyword-vault 推荐关键字**：`TEST.PD.PS.SNK.01`, `PDO`, `Transitions`, `Sink`, `fail`

## Top-3 候选根因

### #1. CC检测与PD通信时序配合  （置信度 80%）

**支持证据**：
- 'PDO' 命中 → TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail
- 'Sink' 命中 → TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail

**Log 搜索关键字**（供 Step 4）：
```
sc27xx-typec DRP state event tTypeCSendSourceCap tCCDebounce PDO Sink
```

**代码定位函数**（供 Step 6）：
- `sc27xx_typec_state_machine`
- `typec_send_source_cap`
- `cc_detect_debounce`

**判定理由**：基于失败现象 + TEST_ID(TEST.PD.PS.SNK.01) + keyword-vault 推荐关键字综合打分

### #2. PD协议栈状态机实现缺陷  （置信度 60%）

**支持证据**：
- 'PDO' 命中 → TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail

**Log 搜索关键字**（供 Step 4）：
```
sprd_tcpm pd_notify PR_SWAP DR_SWAP tPSSourceOn tPSSourceOff PDO SourceCap
```

**代码定位函数**（供 Step 6）：
- `sprd_tcpm_pd_swap`
- `sprd_tcpm_dr_swap`
- `pe_src_send_swap`
- `pd_state_machine`

**判定理由**：基于失败现象 + TEST_ID(TEST.PD.PS.SNK.01) + keyword-vault 推荐关键字综合打分

## 排查地图

按以下顺序排查，每步产物保存后进入下一步：

1. 假设 **CC检测与PD通信时序配合** → 用关键字 ['sc27xx-typec', 'DRP', 'state'] 在 log 中搜索 → 定位函数 ['sc27xx_typec_state_machine', 'typec_send_source_cap']
2. 假设 **PD协议栈状态机实现缺陷** → 用关键字 ['sprd_tcpm', 'pd_notify', 'PR_SWAP'] 在 log 中搜索 → 定位函数 ['sprd_tcpm_pd_swap', 'sprd_tcpm_dr_swap']
