# Bug 2912824 — 信息摘要

## 结论

- **Bug ID**: 2912824 (SPCSS01467901)
- **分类**: PD 认证类
- **TEST_ID**: `TEST.PD.PROT.SRC.10`
- **状态**: Closed / FIXED
- **产品**: SPCSS_UMS9230E
- **组件**: 01-BSP-Charge
- **客户**: SPROCOMM / blade-A56-u
- **问题**: PR_Swap 时 PSSourceOnTimer 超时，Error Recovery 在 tPSSourceOn min 前被检测到

## 失败现象

- TEST.PD.PROT.SRC.10#3 Fail
- Error Recovery State was detected before tPSSourceOn min.
- Rev2Src Fail
- Rev3ChkdSrc Fail
- PR_Swap - PSSourceOnTimer Timeout

## 附件来源

- FTP: `ftp://ftp.unisoc.com/FTPDATA/2025-2/SPCSS01467901`
- UNC: `\\10.0.0.165\FtpData\FAE\sprocomm\FTPDATA\2025-2\SPCSS01467901`
- SampleCode: `\\10.0.0.165\FtpData\FAE\sprocomm\FTPDATA\2025-2\SPCSS01467901\SampleCodeForCUS`