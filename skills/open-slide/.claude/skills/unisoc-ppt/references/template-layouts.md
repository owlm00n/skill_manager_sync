# Unisoc Template Layout Reference

Complete catalog of all layouts and slides in `紫光展锐企业PPT模板（中文）-2506.pptx`.

## Layouts

### Layout 0 — 封面页 (Cover Page)

**Placeholders:**
| idx | Name | Type | Position (EMU) | Size (EMU) | Purpose |
|-----|------|------|----------------|------------|---------|
| 0 | 标题 38 | TITLE (1) | left=947918, top=1520119 | w=5094742, h=1804105 | Main title (company name + tagline) |
| 10 | 文本占位符 5 | BODY (2) | left=948635, top=4860803 | w=2447925, h=701675 | Subtitle (date, location, URL, classification) |

**Template slide example (Slide 1):**
- Title area (custom text box, not placeholder): "紫光展锐" / "用 芯 成就美好世界" (font: 微软雅黑, size: 46pt, bold, color: #920784)
- Address: "中国 · 上海" / "www.unisoc.com" (font: 微软雅黑, size: 16pt, color: #130000)
- Classification: "密级" (font: 微软雅黑, size: 10pt)
- Decorative shape on right side

**Code pattern:**
```python
slide = prs.slides.add_slide(prs.slide_layouts[0])
title_ph = slide.placeholders[0]  # idx=0
title_ph.text = "演示标题"
subtitle_ph = slide.placeholders[10]  # idx=10
subtitle_ph.text = "中国 · 上海\nwww.unisoc.com\n内部"
```

### Layout 1 — 过渡页1 (Section Transition 1)

No placeholders. Pure decorative background layout for section dividers.

**Template slide example (Slide 12):**
- Large "01" section number
- Section title text box
- Subtitle text box

**Code pattern:**
```python
slide = prs.slides.add_slide(prs.slide_layouts[1])
# Manually add text boxes for section number and title
left = Emu(950000)
top = Emu(2500000)
txBox = slide.shapes.add_textbox(left, top, Emu(10000000), Emu(2000000))
tf = txBox.text_frame
tf.text = "01"
run = tf.paragraphs[0].runs[0]
run.font.name = '微软雅黑'
run.font.size = Pt(72)
run.font.bold = True
run.font.color.rgb = RGBColor(0x92, 0x07, 0x84)
```

### Layout 2–6 — 过渡页2 to 过渡页6 (Section Transitions)

Same placeholder structure, different background art:

| idx | Name | Type | Position | Size | Purpose |
|-----|------|------|----------|------|---------|
| 10 | 文本占位符 29 | BODY (2) | left=6311900, top=3300730 | w=4065588, h=708025 | Section tag/eyebrow |
| 12 | 文本占位符 18 | BODY (2) | left=6232525, top=4273868 | w=4144963, h=941388 | Section description |

**Code pattern:**
```python
slide = prs.slides.add_slide(prs.slide_layouts[2])  # or 3,4,5,6
slide.placeholders[10].text = "SECTION TAG"
slide.placeholders[12].text = "Section description text here"
```

### Layout 7 — 标题居中页 (Centered Title Content)

| idx | Name | Type | Position | Size | Purpose |
|-----|------|------|----------|------|---------|
| 0 | 标题 1 | TITLE (1) | left=142875, top=980440 | w=12049760, h=477520 | Slide heading |

**Note:** This layout only has a title placeholder. All body content must be added as manual text boxes, tables, or images.

**This is the primary layout for all content slides.** Approximately 20 of the 29 template slides use this layout.

**Code pattern:**
```python
slide = prs.slides.add_slide(prs.slide_layouts[7])
slide.placeholders[0].text = "页面标题"

# Add body text as a manual text box
txBox = slide.shapes.add_textbox(
    Emu(950000), Emu(1800000), Emu(10200000), Emu(4500000)
)
tf = txBox.text_frame
tf.word_wrap = True
```

### Layout 8 — 目录页 (Table of Contents)

No placeholders. Branded background with decorative elements.
Used for agenda/TOC slides. Content placed manually.

**Template slide examples (Slides 10–11):**
- Slide 10: "目 录" title + "01" / "02" section numbers
- Slide 11: "目 录" title + chapter listing with descriptions

### Layout 9 — 1_标题居中页 (Closing/Ending Slide)

No placeholders. Branded background with chip motif.
Used for closing slides or thank-you pages.

**Template slide examples (Slides 27–29):**
- "用芯成就美好世界" tagline
- Legal disclaimer text
- Company branding elements

## Font Specifications

| Element | Font | Size (Pt) | Weight | Color |
|---------|------|-----------|--------|-------|
| Cover title (company name) | 微软雅黑 | 46 | Bold | #920784 |
| Cover subtitle (date/location) | 微软雅黑 | 16 | Regular | #130000 |
| Classification label | 微软雅黑 | 10 | Regular | #130000 |
| Section number | 微软雅黑 | 72+ | Bold | #920784 or #4472C4 |
| Section title | 微软雅黑 | 44-48 | Bold | #262626 |
| Slide heading | 微软雅黑 | 36-44 | Bold | #262626 |
| Body text | 微软雅黑 | 18-24 | Regular | #404040 |
| Footer/notes | 微软雅黑 | 12-14 | Regular | #A5A5A5 |

## Color Palette

| Color Name | Hex | Usage |
|------------|-----|-------|
| Unisoc Purple | #920784 | Brand identity, cover title, section numbers, accent elements |
| Dark Text | #262626 | Titles, headings |
| Body Gray | #404040 | Body paragraphs |
| Near Black | #130000 | Footer info, secondary text |
| Theme Blue | #4472C4 | Alternative accent |
| Theme Orange | #ED7D31 | Alternative accent |
| Theme Light | #E7E6E6 | Background elements |
| Theme Dark | #44546A | Borders, lines |

## Slide Inventory (All 29 Template Slides)

### Slide 1 — Cover
- Layout: 封面页 (0)
- Content: "紫光展锐" / "用 芯 成就美好世界", "中国 · 上海", "www.unisoc.com", "密级"
- Shapes: 文本框 7 (title), 文本框 1 (address), 图片 82 (decorative), 文本框 4 (classification)

### Slide 2 — Color Spec
- Layout: 标题居中页 (7)
- Content: "颜色搭配及使用规范"
- Color swatches in template

### Slide 3 — Font Spec
- Layout: 标题居中页 (7)
- Content: "字体、字号使用规范" + sample texts

### Slide 4 — Products
- Layout: 标题居中页 (7)
- Content: "智能机", "功能机", "平板" — three product categories

### Slide 5 — LOGO (Single)
- Layout: 标题居中页 (7)
- Content: "LOGO品牌标志—中/英文" + logo placements

### Slide 6 — LOGO (Joint)
- Layout: 标题居中页 (7)
- Content: "新紫光集团+紫光展锐联合LOGO品牌标志"

### Slide 7 — Chip Graphics
- Layout: 标题居中页 (7)
- Content: "芯片模板-线稿/立体图" + chip diagrams

### Slide 8 — Image Materials (Tech)
- Layout: 标题居中页 (7)
- Content: "图片素材", "人工智能及未来科技", "智慧城市及数字世界"

### Slide 9 — Image Materials (Team)
- Layout: 标题居中页 (7)
- Content: "图片素材", "团队合作共赢", "芯片设计技术创新"

### Slide 10 — TOC (Simple)
- Layout: 目录页 (8)
- Content: "目 录", "01", "02"

### Slide 11 — TOC (Detailed)
- Layout: 目录页 (8)
- Content: "目 录", "01", chapter title + description

### Slide 12 — Section Divider
- Layout: 过渡页1 (1)
- Content: "01", section title, section description

### Slides 13–26 — Content Examples
- Layout: 标题居中页 (7)
- Various content arrangements: 1-col text, 2-col, 3-col, image+text, table, diagram
- Most contain placeholder text ("单击此处编辑...")

### Slides 27–29 — Closing
- Layout: 1_标题居中页 (9)
- Content: "用芯成就美好世界" tagline, legal disclaimers

## Shape Positioning Guide

Refer to these approximate positions in centimeters (EMU = cm × 360000).

### Content slides (Layout 7):
- Title placeholder: left ~0.4cm, top ~2.7cm, width ~33.5cm (nearly full-width bar at top)
- Content area below title: top ~5cm, left ~3cm, width ~27cm

### Cover slide (Layout 0):
- Title placeholder: left ~2.6cm, top ~4.2cm, width ~14.2cm
- Subtitle placeholder: left ~2.6cm, top ~13.5cm
- Decorative shape on right half of slide

Use `scripts/inventory_template.py <file.pptx>` for exact per-slide measurements.

## Markdown → Slide Mapping

When converting markdown to slides:

| Markdown Element | Slide Layout | Notes |
|-----------------|--------------|-------|
| `# Title` (H1) | 封面页 (0) | First H1 becomes cover title |
| `## Section` (H2) | 过渡页 (1-6) or 标题居中页 (7) | Use 过渡页 for major sections, 标题居中页 for sub-sections |
| `### Topic` (H3) | 标题居中页 (7) | Content slide with H3 as heading |
| Bullet list (`- item`) | Text boxes on 标题居中页 | Each bullet becomes a text paragraph |
| `![image]()` | Picture shape on 标题居中页 | Place image in content area, wrap text around |
| Numbered list | Text boxes on 标题居中页 | Ordered list formatting |
| Code block | Skipped (manual review) | PPT is not ideal for code; suggest summary instead |
| Table | Table shape on 标题居中页 | Use python-pptx table API |
