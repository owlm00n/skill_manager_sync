# Bug 2912824 — 根因假设 & 排查地图

## 结论

- **TEST_ID**：`TEST.PD.PROT.SRC.10`
- **失败现象**：
  - TEST.PD.PROT.SRC.10#3 Fail
  - Error Recovery State was detected before tPSSourceOn min.
  - Rev2Src Fail
  - Rev3ChkdSrc Fail
  - PR_Swap - PSSourceOnTimer Timeout
- **keyword-vault 推荐关键字**：`TEST.PD.PROT.SRC.10`, `Fail`

## Top-3 候选根因

### #1. PD协议栈状态机实现缺陷  （置信度 30%）

**支持证据**：
- 'PR_SWAP' 命中 → PR_Swap - PSSourceOnTimer Timeout
- 'tPSSourceOn' 命中 → Error Recovery State was detected before tPSSourceOn min.

**Log 搜索关键字**（供 Step 4）：
```
sprd_tcpm pd_notify PR_SWAP DR_SWAP tPSSourceOn tPSSourceOff
```

**代码定位函数**（供 Step 6）：
- `sprd_tcpm_pd_swap`
- `sprd_tcpm_dr_swap`
- `pe_src_send_swap`
- `pd_state_machine`

**判定理由**：基于失败现象 + TEST_ID(TEST.PD.PROT.SRC.10) + keyword-vault 推荐关键字综合打分

### #2. CC检测与PD通信时序配合  （置信度 15%）

**支持证据**：
- 'state' 命中 → Error Recovery State was detected before tPSSourceOn min.

**Log 搜索关键字**（供 Step 4）：
```
sc27xx-typec DRP state event tTypeCSendSourceCap tCCDebounce
```

**代码定位函数**（供 Step 6）：
- `sc27xx_typec_state_machine`
- `typec_send_source_cap`
- `cc_detect_debounce`

**判定理由**：基于失败现象 + TEST_ID(TEST.PD.PROT.SRC.10) + keyword-vault 推荐关键字综合打分

## 排查地图

按以下顺序排查，每步产物保存后进入下一步：

1. 假设 **PD协议栈状态机实现缺陷** → 用关键字 ['sprd_tcpm', 'pd_notify', 'PR_SWAP'] 在 log 中搜索 → 定位函数 ['sprd_tcpm_pd_swap', 'sprd_tcpm_dr_swap']
2. 假设 **CC检测与PD通信时序配合** → 用关键字 ['sc27xx-typec', 'DRP', 'state'] 在 log 中搜索 → 定位函数 ['sc27xx_typec_state_machine', 'typec_send_source_cap']
