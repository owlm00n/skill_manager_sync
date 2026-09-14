# Bug 3442513 — 信息摘要

## 结论

- **Bug 类型判定**：`pd_auth_cert`
  - 判定依据：命中 PD 认证强信号: ['TD\\.4\\.', 'USB_PD_Applicability']
- **提取到的 TEST_ID**：`TD.4.10.3.V`
- **失败现象关键句**：
  - 18 fail
  - TD.4.10.3.V.18 fail
  - Check_Class::Verify()::Check if any Bring-up has failed.
  - Error(0x000000FA): The PUT draws power greater than 25 mW.
  - Verification Result: FAILED
- **附件清单（分类）**：
  - 类型 `unknown`：1 项
    - unitrans_attachment (unitrans) https://unitrans.unisoc.com/share/764d200c-8fed-4b87-bd20-5348e2c65e9a
  - 类型 `.usb`：2 项
    - Type-C\TD.4.10.3\Repeat_03\04_TD.4.10.3_USB2_Step14_FAIL.usb (comment) 
    - 04_TD.4.10.3_USB2_Step14_FAIL.usb (comment) 

## 基本信息

- **Summary**：[UMS9230H][HUAQIN_BD2][PD2577F][16849][手持-智能手机]TD.4.10.3.V.18 fail,The PUT draws power greater than 25 mW.
- **Status**：Closed
- **Resolution**：NON-REPRODUCE
- **Severity**：1-Critical
- **Product**：SPCSS_UMS9230H
- **Component**：11-HW-BB-Power
- **Creation Time**：2026-06-08T01:31:10Z

## 评论（前 5 条）

### huaqin_BD2@huaqin.com

SPCSS ID: SPCSS01672238
SubmitDT: 2026-06-08 09:30:48

Description: 
步骤：

现象：

分析：
TD.4.10.3.V.18 fail
Relevant CVS found on item 17
Check_Class::Verify()::Check if any Bring-up has failed.
Check_Class::Verify()::Executing Check_USB_PD_Applicability
Error(0x000000FA): The PUT draws power greater than 25 mW.
Verification Result: FAILED
F:\PD2577_0513\vivo Mobile Communication Co., Ltd.-V2606-0000\20260606_132831\USB Type-C\TD.4.10.3\Repeat_03\04_TD.4.10.3_USB2_Step14_FAIL.usb: Saving trace file
Trace captured.
Running ProcessResult:
Test_Class::DisconnectFromBoards()
Board_Class::CloseConnection()::AutomationObj.SetAnalyzerParameters(1,0)
Board_Class::CloseConnection() Successfully for CVS_0 to #27255
 

[客户项目信息 请至以下路径查询]: 
https://isupport.unisoc.com/isu-project/projectDetail?id=16849 

[该Case 客户端提交人信息] 
Contacts: 马壮 
CUSPhone: 15151865732 
Emails  : mazhuang@huaqin.com 

 
AttachmentFile download: 
请至Uni-Trans系统https://unitrans.unisoc.com下载附件: huaqin_BD2/2026-6/SPCSS01672238

或使用快捷链接下载（此链接仅提供下载功能，仅供展锐员工在公司网络进行下载操作）: 
https://unitrans.unisoc.com/share/764d200c-8fed-4b87-bd20-5348e2c65e9a
 
如Unisoc 员工需对外进行交付，请使用Uni-Patch进行对外交付: 
http://uni-patch.unisoc.com/ 
如Unisoc 员工需对外进行提供，请使用Uni-Samplecode进行对外提供: 
http://uni-patch.unisoc.com/add-samplecode

### huaqin_BD2@huaqin.com

TheNotesSyncFromCustomerSupportSystem2TheBug:
Submitted by: huaqin_BD2 on 08 June 2026 09:35:25 ====

Hi 展锐
相关log 已经上传至附件
请辛苦帮忙分析
Zhuang

### huaqin_BD2@huaqin.com

TheNotesSyncFromCustomerSupportSystem2TheBug:
Submitted by: huaqin_BD2 on 08 June 2026 09:38:00 ====

Hi 展锐
本地驱动文件也已经上传
Zhuang

### Yongqing.Wang@unisoc.com

正在分析中

### svc.uLogSys@unisoc.com

******日志分析系统自动分析结果(分析结果有效时期截止2026-06-22)******
[1.分析工具]:    ABPS 
[2.分析详情链接]:  http://datastoreanal.unisoc.com:8888/#/task-result?id=544872  
[3.分析结果下载链接]:  http://10.29.57.212:8181/job/analy_log_linux_job/62162/artifact/62162/ABPS_result/ABPS_result.zip 
[4.Log路径]:    /huaqin_BD2/2026-6/SPCSS01672238/vivo-sgm41512_charger_new.c.zip 
[5.分析结果]:

[分析器]:ABPS
[分析结论]:无法从问题描述中识别出明确的异常类型，因此未能进行定向故障分析。
当前问题描述为：「[UMS9230H][HUAQIN_BD2][PD2577F][16849][手持-智能手机]TD.4.10.3.V.18 fail,The PUT draws power greater than 25 mW.」
可能的原因如下：
  1. 问题描述中未包含分析器可识别的异常关键字（如"ANR"、"重启"、"关机"、"无响应"等）。
  2. 问题描述使用了非标准或不常见的表述方式，建议参考上述关键字重新描述。
  3. 该异常类型可能暂不在分析器的支持范围内。
建议：请尝试在问题描述中补充具体的异常现象关键字，或查阅详细分析报告确认是否存在其他类型的异常。

当前日志中未扫描到任何已知异常，请确认日志文件是否完整、是否覆盖了问题复现的时间段。
[详细信息]:无
[故障树]:无
