---
name: isupport-downloader
description: isupport DCC文档下载 - 通过文档ID或关键词从isupport.unisoc.com检索并下载PDF/文档，支持批量下载和过滤
version: "1.0"
tags: [isupport, dcc, document, download, unisoc]
---

# isupport DCC 文档下载

从 isupport.unisoc.com 的 DCC（Document Control Center）检索并下载文档。

## 触发条件

- 用户说"下载文档"、"下载isupport文档"、"isupport下载"
- 用户提供文档ID（如"下载ID 105142"）
- 用户提供文档名称关键词（如"搜索UMS512相关文档"）
- 用户说"isupport文档查询"、"DCC下载"

## 前置条件

文档工具位于 `D:\06_Project\isupport_down\`，需要先检查依赖和认证状态。

## 工作流程

### 流程1：按文档ID下载（精确）

1. 用户指定文档ID，如"下载文档ID 105142"
2. 创建目标目录（如 `downloads/`）
3. 调用下载命令：
   ```bash
   cd D:\06_Project\isupport_down
   python src/main.py download --id <文件ID> --dir downloads/<目录名>
   ```
4. 如果认证失效（token过期>72h），先执行 `python src/main.py login` 重新登录
5. 验证下载的文件是否为有效PDF（检查文件头 `%PDF-`）

### 流程2：按关键词搜索并下载

1. 用户提供搜索关键词，如"搜索并下载UMS512相关文档"
2. 调用搜索命令（先查看结果）：
   ```bash
   cd D:\06_Project\isupport_down
   python src/main.py search "<关键词>" --max 20 --chip <芯片型号>
   ```
3. 展示搜索结果（文件名、大小、芯片、作者、关键词标签）
4. 确认后调用下载命令：
   ```bash
   python src/main.py get "<关键词>" --max 5 --dir downloads/<目录名>
   ```

### 流程3：按条件批量下载

1. 用户指定多个过滤条件：关键词、芯片平台、Android版本
2. 先搜索预览结果：
   ```bash
   python src/main.py search "<关键词>" --chip UMS512 --android-version "Android 17 (X)"
   ```
3. 确认搜索结果后执行批量下载

### 流程4：认证刷新

1. 如token过期（提示认证失败），打开浏览器完成SSO登录：
   ```bash
   cd D:\06_Project\isupport_down
   python src/main.py login
   ```
2. 登录后token保存72小时，后续命令无需再次登录

## 命令速查

| 命令 | 用途 |
|------|------|
| `python src/main.py login` | 打开浏览器完成SSO登录 |
| `python src/main.py search "关键词" --max 20` | 搜索文档 |
| `python src/main.py search "关键词" --chip UMS512` | 按芯片过滤搜索 |
| `python src/main.py download --id 105142 --dir downloads/` | 按ID下载 |
| `python src/main.py get "关键词" --max 5 --dir downloads/` | 搜索+下载 |

## 输出

- 文件保存到 `downloads/` 目录下的指定子目录
- 文件名为搜索API返回的原始文件名（含中文）
- 返回下载结果：文件名、大小、路径
- 如需要，可展示文件列表和完整性校验（PDF文件头验证）

## 注意事项

- 工具依赖 Python 3.8+，Playwright 1.40+，requests 2.28+
- 首次使用需执行 `login` 完成SSO认证
- Token有效期72小时，过期后需重新登录
- 中文文件名在浏览器Content-Disposition Header中有编码问题，工具已从API直接获取正确文件名
- 支持的文件类型：PDF（主要）、Excel、Word等（通过同一个previewFile端点）
