---
name: Unisoc-PPT
slug: unisoc-ppt
version: 1.0.0
description: "Generate Unisoc (紫光展锐) branded PowerPoint presentations from the official corporate template. Use when the user asks for Unisoc/紫光展锐 PPTs, presentation slides with corporate branding, or template-driven slide generation from structured content outlines."
metadata: {"emoji":"📊","requires":{"bins":["python"],"python_packages":["python-pptx>=0.6.21"]},"os":["linux","darwin","win32"]}
---

## When to Use

Use when the user asks to create a PPT/PPTX deck for 紫光展锐 (Unisoc), or when they describe slide content ("make a 5-slide presentation about chip design", "generate a Unisoc project status deck"). Also use when the user provides a structured outline and wants it turned into templated slides.

**Skip** when the task is pure text extraction from an existing deck, general PPT editing, or when no Unisoc branding is needed — use the general `Powerpoint-PPTX` skill instead.

## Template Overview

The official Unisoc template lives at `unisocppt/紫光展锐企业PPT模板（中文）-2506.pptx` relative to the project root (`D:\06_Project\open-slide`).

### Key specs
- **Aspect ratio**: 16:9 (960cm × 540cm, 12192000 × 6858000 EMU)
- **Primary font**: 微软雅黑 (Microsoft YaHei) — used on all slides
- **Theme font**: 等线 / 等线 Light (used in theme definitions, overridden by 微软雅黑 on slides)
- **Brand purple**: `#920784` — used for company name and key branding elements
- **Dark text**: `#130000` (near-black), `#262626` (titles), `#404040` (body)
- **Theme accent**: `#4472C4` (blue), `#ED7D31` (orange)

### Available layouts (10 layouts, 0–9)

| Index | Name | Purpose | Key Placeholders |
|-------|------|---------|------------------|
| 0 | 封面页 | Title/cover slide | `idx=0` Title, `idx=10` Subtitle/Body |
| 1 | 过渡页1 | Section transition (style 1) | None (decorative background) |
| 2 | 过渡页2 | Section transition (style 2) | `idx=10` Tag line, `idx=12` Body text |
| 3 | 过渡页3 | Section transition (style 3) | `idx=10` Tag line, `idx=12` Body text |
| 4 | 过渡页4 | Section transition (style 4) | `idx=10` Tag line, `idx=12` Body text |
| 5 | 过渡页5 | Section transition (style 5) | `idx=10` Tag line, `idx=12` Body text |
| 6 | 过渡页6 | Section transition (style 6) | `idx=10` Tag line, `idx=12` Body text |
| 7 | 标题居中页 | Centered title slide (content) | `idx=0` Title |
| 8 | 目录页 | Table of contents | Decorative, manual content placement |
| 9 | 1_标题居中页 | Ending/closing slide | Empty, branded background |

### Template slides inventory (29 slides)

| Slide | Layout | Content Type |
|-------|--------|-------------|
| 1 | 封面页 | Cover: company name, tagline, address, website, classification |
| 2 | 标题居中页 | Color specification guide |
| 3 | 标题居中页 | Font specification guide |
| 4 | 标题居中页 | Product categories (智能机/功能机/平板) |
| 5 | 标题居中页 | Logo brand marks |
| 6 | 标题居中页 | Joint logo (新紫光+紫光展锐) |
| 7 | 标题居中页 | Chip template line/solid diagram |
| 8-9 | 标题居中页 | Image material samples |
| 10-11 | 目录页 | Table of contents examples |
| 12 | 过渡页1 | Section divider example |
| 13-26 | 标题居中页 | Various content layout examples |
| 27-29 | 1_标题居中页 | Closing slides with tagline |

**Read `references/template-layouts.md` for the full slide-by-slide catalog with shape positions and sample text.**

## Core Rules

### 1. Always clone the template — never build from scratch

- Copy the template file to the output path before adding slides. The template's theme, masters, and layouts carry the brand identity.
- The template path is `D:\06_Project\open-slide\unisocppt\紫光展锐企业PPT模板（中文）-2506.pptx`.
- Never use `Presentation()` with a blank deck — always start from the template.
- After cloning, delete all existing template slides (keep only the layouts/masters) before building the content deck.

### 2. Map content structure to layouts before writing code

For each content chunk the user provides, decide the layout:
- **Title/cover** → Layout 0 (封面页). Set title placeholder to the presentation title, subtitle to presenter/date info.
- **Section start** → Layout 1 (过渡页1). Manually add text boxes for section number (120pt, purple) and title (36pt, dark).
- **Content slide with heading** → Layout 7 (标题居中页). Set `idx=0` (Title) to the slide heading, then add text boxes/shapes for body content.
- **Agenda/TOC** → Layout 8 (目录页). Manual text placement for section numbers and titles.
- **Closing/Thanks** → Layout 9 (1_标题居中页). Add final message or company tagline "用芯成就美好世界".

### 3. Use the slide duplication pattern for content slides

The safest way to add content slides is:
```python
from pptx import Presentation
from copy import deepcopy

prs = Presentation(TEMPLATE_PATH)
# Use a template slide as a "donor" for the layout
layout = prs.slide_layouts[7]  # 标题居中页
slide = prs.slides.add_slide(layout)
```

Then populate shapes by matching `shape.name` or `placeholder_format.idx`.

### 4. Font and color rules

- **Always use 微软雅黑** for all text. Set `run.font.name = '微软雅黑'` on every run.
- **Heading text**: size Pt(44)–Pt(60), bold, color `#262626`
- **Body text**: size Pt(18)–Pt(24), regular, color `#404040`
- **Company name/accent text**: `#920784` (Unisoc purple), bold
- **Cover title**: size Pt(46), bold, `#920784`
- Apply font to both Latin and East Asian runs: `run.font.name = '微软雅黑'`
- Set `rPr` element's `ea` typeface for CJK fallback in the XML.

### 5. Content fitting and overflow prevention

- The title placeholder on Layout 7 is ~1205mm wide × 48mm tall — keep titles under ~30 Chinese characters.
- Body text areas need explicit sizing: if adding text boxes, use widths ≤1100mm to stay within slide margins.
- For multi-point content slides (3-5 bullet points), add text boxes manually at calculated Y positions rather than cramming into one placeholder.
- Check text length: if >100 Chinese chars for a single text area, split across slides.

### 6. Slide structure conventions

A standard Unisoc deck follows this sequence:
1. **Cover** (封面页) — title, subtitle, date, classification
2. **TOC** (目录页) — agenda items
3. **Section dividers** (过渡页) — before each major section
4. **Content slides** (标题居中页) — the main content
5. **Closing** (1_标题居中页) — "用芯成就美好世界" + thank you

### 7. QA checklist before delivery

- [ ] All text uses 微软雅黑 font
- [ ] No placeholder text survived ("单击此处编辑...")
- [ ] Title sizes consistent across content slides
- [ ] Unisoc purple (#920784) used on cover title and branding elements
- [ ] Classification level set on cover (default: 内部)
- [ ] Company tagline "用 芯 成就美好世界" on closing slide
- [ ] Slide count matches user's content outline + cover + TOC + closing

## Common Workflows

### Workflow A: Generate from outline

User says: "Make a 5-slide deck about our Q3 chip roadmap"

Steps:
1. Ask user for: title, presenter name, date, classification level (default: 内部)
2. Plan slide structure: Cover → TOC → content slide per topic → Closing
3. Clone template, delete existing slides
4. Add slides using layouts 0, 8, 7 (×N), 9
5. Populate text, run QA checklist

### Workflow B: Regenerate from markdown outline

User provides a markdown document with `# Title`, `## Section`, bullet points.

Steps:
1. Parse markdown structure
2. `# Title` → Cover slide title
3. `## Section` → Section divider (过渡页) or content slide heading
4. Bullet lists → text boxes on content slides
5. Close with ending slide

### Workflow C: Edit existing Unisoc deck

User has a `.pptx` file in the project and wants content updates.

Steps:
1. Read the existing deck to inventory slides
2. Match each slide to its layout
3. Update text in place, preserving shapes and positions
4. Run font compliance check (ensure 微软雅黑)

## Usage Demo

### Quick Start (3 steps)

**Step 1 — Write an outline.** Create a `.md` file in the project:

```markdown
# Q3芯片项目汇报
## 项目进展
### 总体进度
- 5G芯片T820进入量产验证阶段
- 目标市场：中高端智能手机
- 计划Q3完成首批客户导入

### 关键里程碑
- 3月：架构设计完成
- 5月：前端设计冻结
- 7月：Tape-out
- 9月：首批样片回片

## 风险与应对
### 主要风险
- 先进工艺产能紧张
- IP验证周期较长
- EDA工具license不足

### 应对措施
- 已与TSMC锁定产能窗口
- IP vendor承诺加急交付
- 正在采购额外license
```

**Step 2 — Generate.**

```bash
python .claude/skills/unisoc-ppt/scripts/gen_unisoc_ppt.py outline.md output.pptx
```

**Step 3 — Inspect.**

```bash
python .claude/skills/unisoc-ppt/scripts/inventory_template.py output.pptx
```

### Demo output

The demo file `demo_output.pptx` was generated from `demo_outline.md` (the creation process of this skill itself):

```
 1. [封面页] Unisoc-PPT Skill 创建过程与要点 | 中国·上海 | 内部
 2. [目录页] 目 录 | 01 项目背景 | 02 模板逆向分析 | 03 技能架构设计
 3. [过渡页2] 01 | 项目背景
 4. [标题居中页] 需求分析
 5. [标题居中页] 现有资源盘点
 6. [过渡页3] 02 | 模板逆向分析
 7. [标题居中页] 版式提取
 8. [标题居中页] 品牌规范提取
 9. [标题居中页] 内容结构归纳
10. [过渡页4] 03 | 技能架构设计
11. [标题居中页] 文件结构
12. [标题居中页] 生成器核心函数
13. [标题居中页] 输入格式设计
14. [过渡页5] 04 | 关键技术要点
15. [标题居中页] 模板克隆策略
16. [标题居中页] 字体处理
17. [标题居中页] 版式选择规则
18. [标题居中页] QA检查清单
19. [过渡页6] 05 | 验证结果
20. [标题居中页] 测试用例
21. [标题居中页] 已确认可用的功能
22. [1_标题居中页] 用芯成就美好世界
```

### Markdown → Slide mapping rules

| Markdown | Becomes | Layout |
|----------|---------|--------|
| `# 标题` (first H1) | Cover slide title | Layout 0 (封面页) |
| `## 章节名` | Section divider | Layout 1 (过渡页1) |
| `### 页面名` | Content slide heading | Layout 7 (标题居中页) |
| `- 要点` / `1. 要点` | Body bullet points | Text box on content slide |
| (auto-generated) | TOC after cover | Layout 8 (目录页) |
| (auto-generated) | Closing slide | Layout 9 (1_标题居中页) |

### JSON input format (for programmatic use)

```json
{
  "title": "演示标题",
  "subtitle": "副标题",
  "presenter": "演讲者",
  "date": "2026-06-25",
  "classification": "内部",
  "slides": [
    {"type": "toc", "items": ["章节1", "章节2"]},
    {"type": "section", "number": "01", "title": "第一章", "desc": "章节描述"},
    {"type": "content", "title": "页面标题", "body": ["要点1", "要点2"]},
    {"type": "closing"}
  ]
}
```

```bash
python .claude/skills/unisoc-ppt/scripts/gen_unisoc_ppt.py outline.json output.pptx
```

### Conversational usage (in Claude Code)

Just say:
- "帮我做一个关于XX的紫光展锐PPT"
- "把这份会议纪要转成Unisoc汇报PPT"
- "/unisoc-ppt 生成Q2项目总结"

The skill will guide you through title, sections, and content, then generate the `.pptx` file. Output goes to the project root by default (e.g. `output.pptx`).

## Reference Files

- `references/template-layouts.md` — Complete layout catalog, shape positions, placeholder indexes, and per-slide breakdown of all 29 template slides.
- `scripts/inventory_template.py` — Run this to print a full inventory of any `.pptx` file (shape names, positions, text, fonts, colors).

## Dependencies

```bash
pip install python-pptx>=0.6.21
```

## Traps

- **Do not** use `prs.slide_layouts[0]` for content slides — that's the cover layout. Content slides use layout 7.
- **Do not** write text into placeholders by index alone — verify the placeholder name and type first. Layouts 2–6 share the same placeholder structure but different background art.
- **Do not** assume font inheritance works. Always explicitly set `run.font.name = '微软雅黑'` on every text run.
- The cover slide's subtitle placeholder (idx=10) holds date/location/URL info, not a second title line.
- Adding slides to the template increases file size because the template's 29 slides carry media. Always strip the original slides after cloning.
