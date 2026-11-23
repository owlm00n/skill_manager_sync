import os
import sys

# ⚠️ 此脚本为一次性分析脚本，实际生产环境应使用 common.report_utils.generate_report_filename_from_bug()
# 标准命名格式: {bug_id}_{type}_{keyword}__{YYYYMMDD}.md
# 示例: 3528294_analysis_patch_eval__20260831.md
base = r'E:\08_Bug'
ws = [os.path.join(base, d) for d in os.listdir(base) if '3528294' in d][0]

# 使用标准化命名替代硬编码 analysis_report.md
try:
    _skills = os.path.dirname(os.path.abspath(__file__))
    if _skills not in sys.path:
        sys.path.insert(0, _skills)
    from bug_core import generate_report_filename
    report_name = generate_report_filename(
        bug_id="3528294",
        report_type="analysis",
        keyword="patch_eval",
        date_str="20260831"
    )
except Exception:
    # fallback: 保持旧命名以防导入失败
    report_name = "3528294_analysis_patch_eval__20260831.md"
report_path = os.path.join(ws, report_name)

content = """# Bug SPCSS01698559 分析报告

## Bug 基本信息

| 字段 | 值 |
|------|-----|
| **Bug ID** | SPCSS01698559 (内部ID: 3528294) |
| **标题** | [UMS9230E][LONGCHEER_BU2][Santiago_A][17369] 帮忙评估平台释放的patch影响 |
| **状态** | Assigned |
| **优先级/严重度** | 1-Resolve Immediately / 1-Critical |
| **产品/模块** | SPCSS_UMS9230E / BSP_Power_Deep/Light/DVFS |
| **Base On Version** | SPRDROID17_SYS_TRUNK_W26.19.3 + SPRDROID17_VND_TRUNK_W26.19.3 + SPRDLINUX6.18_KERNEL_TRUNK_W26.18.6 |
| **Assignee** | Xianjun.Zeng@unisoc.com |
| **创建时间** | 2026-08-26 |
| **URL** | https://bugzilla.unisoc.com/bugzilla/show_bug.cgi?id=SPCSS01698559 |

---

## 客户问题

平台释放了两笔patch，需要导入p0.1试产，帮忙评估：

1. 修改内容是什么？影响模块有哪些？
2. 修改的具体影响是什么？
3. 需要做哪些测试以及压力测试？
4. 该项目和SomaliaA项目共线，是否影响老的项目？如果影响需要做哪些测试？

---

## 涉及 Patch 清单

| Patch ID | 关联 Bug | 仓库 | 修改文件 | 作者 |
|----------|---------|------|---------|------|
| PATCH20012527 | Bug 3478769 | bsp/bootloader/edk2 | SprdPkg/Library/PmicLib/regulator/Regulator2730.c | Jiansheng Wu |
| PATCH20012528 | Bug 3471497 | kernel6.18/unisoc-ext-modules/audio | src/asoc/codec/sc2730/sprd-codec.c | Jinbo Yang |

---

## 一、PATCH20012527 -- Bootloader PMIC Regulator 修改

### 1.1 修改内容

PATCH20012527 包含两个子 patch，均修改 Regulator2730.c：

#### 0001 -- efuse 接口替换 + shft bug 修复

**变更1：头文件 & API 接口替换**
- 头文件：`PmicEfuseLib.h` -> `PmicEfuseApiLib.h`
- API：`Pmic_Efuse_Por_Read()` -> `EfiPmicEfuseRead()`（efuse EFI 接口统一迁移）
- 函数签名一致（reg_val, efuse_block_id, PMICID 参数不变），功能等价

**变更2：shft 变量重算 Bug 修复（关键修复）**
- **问题**：第一个 for 循环（id 0-9，DCDC ZCD 校准）中，原代码复用了上一个循环的 shft 值，没有为每个 DCDC 通道重新计算 `shft = __ffs(dcdc_zcd_cfg[i].pmic_regs_mask)`
- **修复**：在 for 循环体内添加 `shft = __ffs(dcdc_zcd_cfg[i].pmic_regs_mask)`，确保每个 DCDC 通道使用各自正确的 bit 偏移写入 ZCD 校准值
- **影响**：原 bug 导致 DCDC 通道 id=0 到 id=9 的 ZCD 校准值写入到错误的寄存器 bit 位置

**变更3：代码格式**
- 第一个 for 循环加大括号 `{}`
- 删除一行空行（无功能影响）

#### 0002 -- OCP Level 修改（tps510g vendor 适配）

**新增 `pmic_oc_level_reinit()` 函数：**
- 从 efuse block 23 读取 bit[6:5] 作为 vendor ID
- 若 vendor ID == 0x02（tps510g），修改 CPU DCDC 过流保护 level：
  - 写入 `ANA_REG_GLB_DCDC_CPU_REG1`
  - 值 `BITS_DCDC_CPU_CL_CTRL(0x2)`，mask `BITS_DCDC_CPU_CL_CTRL(0x3)`
- 非 tps510g 版本不做任何修改

**调用位置**：`RegulatorPmicInit()` 末尾，`reset_cbank_value()` 之后

### 1.2 影响模块

| 影响范围 | 说明 |
|----------|------|
| SC2730 PMIC regulator 初始化 | RegulatorPmicInit() 启动流程 |
| DCDC ZCD 校准（10路） | DCDC_CPU/GPU/CORE/MODEM/MEM/MEMQ/GEN0/GEN1/WPA/SRAM_ZCD |
| LDO_DCXO_LP 校准 | id=10，使用相同 efuse 接口但不受 shft 修复影响 |
| CPU DCDC OCP Level | 仅 tps510g 版本芯片生效 |
| Bootloader 上电流程 | edk2 阶段 PMIC 初始化 |

### 1.3 具体影响

| 子 Patch | 风险等级 | 影响说明 |
|----------|:--------:|----------|
| 0001 shft 修复 | 中 | ZCD 校准值写入到正确的寄存器 bit 位，修正前可能写入错误位置导致 DCDC 过零检测精度偏差，影响电源稳定性 |
| 0001 API 替换 | 低 | 等价接口替换，功能无变化 |
| 0002 OCP level | 中 | tps510g 版本 CPU DCDC 过流保护阈值变更，需验证高负载场景下不会误触发保护 |

---

## 二、PATCH20012528 -- Kernel Audio Codec 修改

### 2.1 修改内容

修改文件：`src/asoc/codec/sc2730/sprd-codec.c`

**变更1：枚举定义**
- 新增 CODEC_PRODUCT_SMIC = 0
- CODEC_PRODUCT_TSMC 显式赋值为 CODEC_PRODUCT_SMIC（=0）
- SMIC 和 TSMC 在数值上等价（均为 0）
- JINGHE_PHASE1 和 JINGHE_PHASE3 值后移

**变更2：产品识别逻辑**
- 在 `sprd_codec_product_info_get()` 中新增 0x40 匹配分支，识别 SMIC 圆晶版本
- 分支顺序：0x00(TSMC) -> 0x40(SMIC, 新增) -> 0x20(JINGHE_PHASE1) -> 0x60(JINGHE_PHASE3)

### 2.2 影响模块

| 影响范围 | 说明 |
|----------|------|
| SC2730 audio codec 产品型号识别 | sprd_codec_product_info_get() kcontrol |
| HAL 层音频配置 | 通过 kcontrol 读取 codec 产品信息，配置不同圆晶版本的音频参数 |
| 仅影响 audio 模块 | 不影响其他子系统 |

### 2.3 具体影响

| 风险等级 | 影响说明 |
|:--------:|----------|
| 低 | 纯粹增加一个产品识别分支，不影响原有 TSMC/JINGHE 分支逻辑 |
| | SMIC 和 TSMC 枚举值相同(=0)，在 HAL 层通过 kcontrol 值区分产品类型 |
| | 不影响 DAPM/音频通路的其他逻辑 |

---

## 三、测试建议

### 3.1 功能测试（必须）

| 测试项 | 说明 | 优先级 |
|--------|------|:------:|
| PMIC 上电验证 | 多次开关机，确认各路 DCDC 输出电压在规格范围内（重点 vddcore/vddcpu/vddgpu） | 高 |
| ZCD 校准验证 | 对比 patch 前后 DCDC 通道 ZCD 寄存器值，确认 shft 修复后写入正确 bit 位 | 高 |
| OCP 保护验证 | 确认 tps510g 版本 CPU DCDC 过流保护阈值修改生效（读取寄存器确认） | 中 |
| 非 tps510g 版本验证 | 确认非 tps510g 版本不受 OCP level 修改影响 | 中 |
| Audio codec 产品识别 | 验证 SMIC/TSMC/JINGHE 各版本 codec_product_info kcontrol 返回值正确 | 中 |
| 音频基本功能 | 播放/录音/通话/铃声，确认音频通路正常 | 高 |

### 3.2 压力测试

| 测试项 | 说明 | 建议次数/时长 |
|--------|------|:------:|
| 反复开关机 | 验证 bootloader PMIC 初始化稳定性 | 100+ 次 |
| CPU 高负载压力测试 | Geekbench/Antutu 循环跑分，验证 OCP level 修改后不会误触发 | 连续 2 小时 |
| 视频长时间播放 | 确认 codec 产品识别不影响音频通路 | 连续 2 小时 |
| 全场景音频 | 播放/录音/通话/蓝牙/耳机全场景轮换 | 每场景 30 分钟 |

### 3.3 回归测试

| 测试项 | 说明 |
|--------|------|
| 整机休眠/唤醒 | 验证 PMIC regulator 休眠唤醒流程 |
| 充电/放电 | PMIC regulator 供电切换场景 |
| 音频全场景回归 | 播放/录音/通话/铃声/通知 |

---

## 四、SomaliaA 共线影响评估

### 4.1 PATCH20012527（bootloader PMIC）影响

| 场景 | 影响评估 |
|------|----------|
| SomaliaA 使用相同 SC2730 PMIC 芯片 | efuse 接口替换和 shft 修复同样生效，修正 ZCD 校准值写入位置 |
| SomaliaA 使用 tps510g 版本 PMIC | OCP level 修改也会生效，CPU DCDC 过流保护阈值变更 |
| SomaliaA 使用非 tps510g 版本 PMIC | OCP level 修改不生效（vendor_id != 0x02），仅 efuse 接口替换和 shft 修复生效 |

**建议**：确认 SomaliaA 项目 PMIC 芯片版本，若是 tps510g 版本需额外验证 OCP 保护行为。

### 4.2 PATCH20012528（audio codec）影响

| 场景 | 影响评估 |
|------|----------|
| SomaliaA 使用相同 SC2730 codec | 仅增加 SMIC 产品识别分支，不影响原有 TSMC/JINGHE 逻辑 |
| 枚举值变化 | CODEC_PRODUCT_SMIC 和 CODEC_PRODUCT_TSMC 值相同(=0)，不影响数值比较 |

**建议**：SomaliaA 项目仅需音频功能回归测试。

### 4.3 SomaliaA 测试建议

| 测试项 | 说明 |
|--------|------|
| 基本功能验证 | 开关机、充电、休眠唤醒 |
| 音频功能回归 | 播放/录音/通话/铃声 |
| PMIC 电压确认 | 对比 patch 前后 DCDC 电压值 |
| （若 tps510g）CPU 压力测试 | 高负载场景验证 OCP 保护 |

---

## 五、总结

| 评估维度 | PATCH20012527 | PATCH20012528 |
|----------|:------------:|:------------:|
| 修改内容 | efuse API 迁移 + shft bug 修复 + tps510g OCP level | 新增 SMIC codec 产品识别 |
| 影响模块 | Bootloader PMIC regulator | Kernel audio codec |
| 风险等级 | 中（shft 修复影响 DCDC 校准精度） | 低（纯新增分支） |
| SomaliaA 影响 | 有影响（efuse 接口+shft 修复均生效；OCP 仅 tps510g 生效） | 无实质影响 |
| 建议 | 导入前完成 PMIC 功能验证 + 压力测试 | 导入后音频功能回归即可 |

---

## 六、来源记录

| 数据来源 | 说明 |
|----------|------|
| Bugzilla REST API | Bug 3528294 基本信息 |
| Bugzilla REST API | 评论列表（共 6 条评论） |
| Patch 文件 | 0001-Bug3478769.patch, 0002-Bug3478769.patch, 0001-Bug3471497.patch（来自 FTP 附件） |
| 附件路径 | longcheer_bu2/2026-8/SPCSS01698559（Unitrans FTP） |
| 工作区 | E:\\08_Bug\\Bug 3528294(SPCSS01698559)...\\ |
"""

with open(report_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Report written to:', report_path)
print('Size:', len(content), 'bytes')