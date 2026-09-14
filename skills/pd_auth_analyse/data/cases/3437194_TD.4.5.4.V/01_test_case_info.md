# Bug 3437194 — 信息摘要

## 结论

- **Bug 类型判定**：`pd_auth_cert`
  - 判定依据：命中 PD 认证强信号: ['TD\\.4\\.']
- **提取到的 TEST_ID**：`TD.4.5.4.V`
- **失败现象关键句**：
  - 14    Fail    The PUT does not respond to Discover ID with well-formed messages
  - TD.4.5.4.V.14    Fail    The PUT does not respond to Discover ID with well-formed messages.    fail 概率 3/3
  - 第一次TD 4.5.4 DRP Connect DRP Test FAIL，都是PD通信异常：
  - TD.4.5.4.V.14 fail
  - Error(0x00000064): The PUT does not respond to Discover ID with well-formed messages.
- **附件清单（分类）**：
  - 类型 `unknown`：1 项
    - unitrans_attachment (unitrans) https://unitrans.unisoc.com/share/23fa77da-7599-4774-b760-99a9ede2eeae
  - 类型 `.usb`：2 项
    - Type-C\TD.4.10.3\Repeat_03\04_TD.4.10.3_USB2_Step14_FAIL.usb (comment) 
    - 64900000.usb (comment) 

## 基本信息

- **Summary**：[UMS9230H][HUAQIN_BD2][PD2577F][16849][手持-智能手机]欧盟认证：TD.4.5.4.V.14    Fail    The PUT does not respond to Discover ID with well-formed messages.
- **Status**：Closed
- **Resolution**：NON-REPRODUCE
- **Severity**：1-Critical
- **Product**：SPCSS_UMS9230H
- **Component**：01-BSP-Charge
- **Creation Time**：2026-06-02T09:34:25Z

## 评论（前 5 条）

### huaqin_BD2@huaqin.com

SPCSS ID: SPCSS01670383
SubmitDT: 2026-06-02 17:31:22

Description: 
步骤：

现象：
TD.4.5.4.V.14    Fail    The PUT does not respond to Discover ID with well-formed messages.    fail 概率 3/3

分析：
 

[客户项目信息 请至以下路径查询]: 
https://isupport.unisoc.com/isu-project/projectDetail?id=16849 

[该Case 客户端提交人信息] 
Contacts: 马壮 
CUSPhone: 15151865732 
Emails  : mazhuang@huaqin.com 

 
AttachmentFile download: 
请至Uni-Trans系统https://unitrans.unisoc.com下载附件: huaqin_BD2/2026-6/SPCSS01670383

或使用快捷链接下载（此链接仅提供下载功能，仅供展锐员工在公司网络进行下载操作）: 
https://unitrans.unisoc.com/share/23fa77da-7599-4774-b760-99a9ede2eeae
 
如Unisoc 员工需对外进行交付，请使用Uni-Patch进行对外交付: 
http://uni-patch.unisoc.com/ 
如Unisoc 员工需对外进行提供，请使用Uni-Samplecode进行对外提供: 
http://uni-patch.unisoc.com/add-samplecode

### Alex.Lv@unisoc.com

请charge同事看一下
感谢

第一次TD 4.5.4 DRP Connect DRP Test FAIL，都是PD通信异常：

TD.4.5.4.V.14 fail
	Error(0x00000064): The PUT does not respond to Discover ID with well-formed messages.
	Verification Result: FAILED
	
	
第二次TD 4.5.4 DRP Connect DRP Test FAIL， 也都是PD通信异常：

TD.4.5.4.V.13 fail
	Error(0x0000007A): The PUT does not respond with valid GoodCRC messages.
	Verification Result: FAILED

TD.4.5.4.V.14 fail
	Error(0x00000064): The PUT does not respond to Discover ID with well-formed messages.
	Verification Result: FAILED

第三次TD 4.5.4 DRP Connect DRP Test FAIL，也都是PD通信异常：
TD.4.5.4.V.14 fail
	Error(0x00000064): The PUT does not respond to Discover ID with well-formed messages.
	Verification Result: FAILED

### Alex.Lv@unisoc.com

欧盟typec认证问题
改task

### Yongqing.Wang@unisoc.com

[模块名称]
充电
[当前进展]
TD.4.5.4.V.14    Fail    The PUT does not respond to Discover ID with well-formed messages.
异常的流程，没有立刻处理Discover ID，
正常的流程，立刻处理了
[后续计划]
请研发帮忙分析。

[分析过程]
SPCSS01670383\20260601_86322XXXXX09847_87111_343945\delay_Time20260601_212943_core\mobilelog\APLog_2026_0601_211240__3\kernel_log_8__2026_0601_212649.utc 
---异常流程---	
	>>收到Discover Identity
`	Line 1852: [2026-06-01 21:27:16.945658],6,452660,1722184967,-,caller=T455@C5;[1421 / 1426] [ 1722.157472] [sprd_pd_log] header = 0x176f, msg header = 0x176f
	>>又收到一次 Discover Identity
	Line 1904: [2026-06-01 21:27:16.973672],6,452712,1722212981,-,caller=T455@C2;[1429 / 1562] [ 1722.189123] [sprd_pd_log] header = 0x196f, msg header = 0x196f
	>>只处理后面一次
	Line 1916: [2026-06-01 21:27:16.973718],6,452724,1722213027,-,caller=T455@C2;[1441 / 1562] [ 1722.194132] [sprd_tcpm_log] PD TX, header: 0x124f
	
--正常流程--	
	>>收到Discover Identity
	Line 2091: [2026-06-01 21:27:17.001767],6,452899,1722241076,-,caller=T455@C2;[1587 / 1756] [ 1722.217121] [sprd_pd_log] header = 0x176f, msg header = 0x176f
	>>正常应答
	Line 2098: [2026-06-01 21:27:17.001791],6,452906,1722241100,-,caller=T455@C2;[1594 / 1756] [ 1722.217302] [sprd_tcpm_log] PD TX, header: 0x104f
	>>又收到一次 Discover Identity
	Line 2113: [2026-06-01 21:27:17.001841],6,452921,1722241150,-,caller=T455@C2;[1609 / 1756] [ 1722.220458] [sprd_pd_log] header = 0x196f, msg header = 0x196f
	>>正常应答
	Line 2120: [2026-06-01 21:27:17.001866],6,452928,1722241175,-,caller=T455@C2;[1616 / 1756] [ 1722.22...(截断)

### Xianjun.Zeng@unisoc.com

Dear Customer:


从log来看sprd_tcpm_ic_limit_work_handler刚好阻塞了30ms pd发送指令，当前的线程是kthread吗，之前上传的文件是work，麻烦用kthread，并且新起一个，不要和tcpm的放在同一个队列

6,276543,739221236,-,caller=T455@C1;[530 / 538] [  739.195107] [sprd_pd_log] pd irq: start handle irq, irq = 84
6,276544,739221244,-,caller=T455@C1;[531 / 538] [  739.195132] [sprd_pd_log] pd irq: int sts = 0x10
6,276545,739221251,-,caller=T455@C1;[532 / 538] [  739.195163] [sprd_pd_log] pd irq: delay 500 us
6,276546,739221259,-,caller=T455@C1;[533 / 538] [  739.195759] [sprd_pd_log] header = 0x176f, msg header = 0x176f
6,276547,739221266,-,caller=T455@C1;[534 / 538] [  739.195778] [sprd_pd_log] sc27xx_pd_check_message_packages, reg_val = 0x4, rx fifo data num = 4
6,276548,739221275,-,caller=T455@C1;[535 / 538] [  739.195857] [sprd_pd_log] sc27xx_pd_rx_flush:line821: start rx flush
6,276549,739221283,-,caller=T455@C1;[536 / 538] [  739.195898] [sprd_pd_log] sc27xx_pd_rx_flush:line824: rx flush done
6,276550,739221291,-,caller=T455@C1;[537 / 538] [  739.195905] [sprd_pd_log] pd irq: IRQ_HANDLED
3,276551,739221845,-,caller=T11921@C4;leds sc27xx:blue: Setting an LED's brightness failed (-524)
 SUBSYSTEM=leds
 DEVICE=+leds:sc27xx:blue
3,276552,739223209,-,caller=T671@C4;vfcs-cms: vfcs_cms_charge_get_chg_up_limit_keep_soc: keep_soc[1:60], ret=0
3,276553,739224421,-,caller=T671@C4;vusb dbg: SGM41512: get_mcu_psy: direct_charger_enable:0
3,276554,739224439,-,caller=T671@C4;vfcs-cms: batt_last_mode_flag_show: batt_last_mode_flag_show: val 0
3,276555,73...(截断)
