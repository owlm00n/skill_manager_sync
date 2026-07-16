#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unisoc PPT Generator

Builds a Unisoc-branded deck from a JSON outline or markdown file.

Usage:
    python gen_unisoc_ppt.py outline.json output.pptx
    python gen_unisoc_ppt.py outline.md output.pptx

JSON outline format:
{
    "title": "演示标题",
    "subtitle": "副标题",
    "presenter": "演讲者",
    "date": "2026-06-25",
    "classification": "内部",
    "slides": [
        {"type": "toc", "items": ["章节1", "章节2", "章节3"]},
        {"type": "section", "number": "01", "title": "章节标题", "desc": "章节描述"},
        {"type": "content", "title": "页面标题", "body": ["要点1", "要点2", "要点3"]},
        {"type": "content", "title": "另一页面", "body": "单段文字内容..."},
        {"type": "closing"}
    ]
}
"""

import sys, io, os, json, re, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from pptx import Presentation
    from pptx.util import Emu, Pt, Cm
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.enum.shapes import MSO_SHAPE
except ImportError:
    print("ERROR: python-pptx not installed. Run: pip install python-pptx")
    sys.exit(1)

# ─── Config ─────────────────────────────────────────────────────────
TEMPLATE_PATH = r"D:\06_Project\open-slide\unisocppt\紫光展锐企业PPT模板（中文）-2506.pptx"

FONT = "微软雅黑"
PURPLE = RGBColor(0x92, 0x07, 0x84)
DARK_TITLE = RGBColor(0x26, 0x26, 0x26)
BODY_GRAY = RGBColor(0x40, 0x40, 0x40)
NEAR_BLACK = RGBColor(0x13, 0x00, 0x00)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

# Layout indexes (from official template)
LAYOUT_COVER = 0
LAYOUT_TRANSITION_1 = 1  # First of 6 transition layouts (1-6)
LAYOUT_TOC = 8
LAYOUT_CONTENT = 7
LAYOUT_CLOSING = 9

# Chapter theme colors — 8-color gradient, each chapter gets a distinct color
CHAPTER_COLORS = [
    RGBColor(0x89, 0x16, 0x7B),  # deep purple
    RGBColor(0x9B, 0x69, 0xFF),  # violet
    RGBColor(0x00, 0x7A, 0xFF),  # blue
    RGBColor(0x09, 0xD3, 0x94),  # green
    RGBColor(0xFF, 0x6B, 0x35),  # orange
    RGBColor(0xE9, 0x1E, 0x63),  # rose
    RGBColor(0x00, 0xBC, 0xD4),  # teal
    RGBColor(0x8B, 0xC3, 0x4A),  # lime
]

# ─── Font helpers ────────────────────────────────────────────────────

def set_font(run, name=FONT, size=None, bold=None, color=None):
    """Apply font settings to a run."""
    run.font.name = name
    if size is not None:
        run.font.size = size
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color

def add_textbox(slide, left, top, width, height, texts, font_size=Pt(20),
                color=BODY_GRAY, bold=False, alignment=PP_ALIGN.LEFT):
    """Add a text box with one or more paragraphs."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True

    if isinstance(texts, str):
        texts = [texts]

    for i, text in enumerate(texts):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        run = p.add_run()
        run.text = text
        set_font(run, size=font_size, bold=bold, color=color)
        p.alignment = alignment
        p.space_after = Pt(6)
    return txBox

def add_content_line(tf, text, font_size=Pt(22), color=BODY_GRAY, bold=False, bullet="", indent_level=0):
    """Add a single formatted line to an existing text frame."""
    p = tf.add_paragraph()
    p.alignment = PP_ALIGN.LEFT
    if indent_level > 0:
        p.level = indent_level
    run = p.add_run()
    prefix = f"{bullet} " if bullet else ""
    run.text = f"{prefix}{text}"
    set_font(run, size=font_size, bold=bold, color=color)
    return p

# ─── Slide builders ─────────────────────────────────────────────────

def make_cover(prs, title, subtitle="", presenter="", date="", classification="内部"):
    """Build cover slide from Layout 0."""
    slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_COVER])

    # Title placeholder (idx=0)
    ph_title = slide.placeholders[0]
    tf = ph_title.text_frame
    tf.clear()

    lines = title.split("\n") if "\n" in title else [title]
    for i, line in enumerate(lines[:2]):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        run = p.add_run()
        run.text = line
        set_font(run, size=Pt(46), bold=True, color=PURPLE)

    # Subtitle placeholder (idx=10) — date, location, URL, classification
    ph_sub = slide.placeholders[10]
    tf = ph_sub.text_frame
    tf.clear()

    info_lines = []
    if subtitle:
        info_lines.append(subtitle)
    info_lines.append("中国 · 上海")
    info_lines.append("www.unisoc.com")
    if presenter:
        info_lines.append(f"演讲者: {presenter}")
    if date:
        info_lines.append(date)
    info_lines.append(classification)

    for i, line in enumerate(info_lines):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        run = p.add_run()
        run.text = line
        set_font(run, size=Pt(16), color=NEAR_BLACK)

    return slide

def make_toc(prs, items):
    """Build TOC with colored chapter squares matching the template style."""
    slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_TOC])

    add_textbox(slide, Cm(3.2), Cm(4.8), Cm(11.3), Cm(2),
                "目  录", font_size=Pt(40), bold=True, color=DARK_TITLE)

    n = len(items)
    max_per_row = 4

    if n <= 4:
        # Single row — matches template slide 10 exactly
        square_size = Cm(6.3)
        x_positions = [Cm(3.4), Cm(10.3), Cm(17.2), Cm(24.0)]
        y_square = Cm(7.7)
        num_size = Pt(60)
        title_size = Pt(14)
        num_y_off = Cm(3.5)
        title_y_off = Cm(0.7)
        rows_data = [(0, items)]
    else:
        # Two rows — scaled colored squares, centered per row
        sq_cm = 5.0
        square_size = Cm(sq_cm)
        gap = Cm(0.8)
        num_size = Pt(44)
        title_size = Pt(12)
        num_y_off = Cm(2.7)
        title_y_off = Cm(0.5)
        y1 = Cm(7.0)
        y2 = Cm(13.2)
        mid = min(max_per_row, n)
        rows_data = [(0, items[:mid]), (1, items[mid:])]

    for row_idx, row_items in rows_data:
        n_in_row = len(row_items)

        if n <= 4:
            row_x = x_positions
            y_square_emu = y_square
        else:
            # Center each row horizontally
            row_total_w = n_in_row * square_size + (n_in_row - 1) * gap
            start_x = int((prs.slide_width - row_total_w) / 2)
            row_x = [start_x + i * int(square_size + gap) for i in range(n_in_row)]
            y_square_emu = y1 if row_idx == 0 else y2

        for i, item in enumerate(row_items):
            x = row_x[i]
            global_idx = (row_idx * max_per_row) + i
            color = CHAPTER_COLORS[global_idx % len(CHAPTER_COLORS)]

            # Colored square
            rect = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, x, y_square_emu, square_size, square_size
            )
            rect.fill.solid()
            rect.fill.fore_color.rgb = color
            rect.line.fill.background()

            # Number — lower portion of square (matches template layout)
            add_textbox(slide, x, y_square_emu + num_y_off,
                        square_size, Cm(2.5),
                        f"0{global_idx + 1}", font_size=num_size, bold=False,
                        color=WHITE, alignment=PP_ALIGN.CENTER)

            # Chapter title — upper portion of square
            add_textbox(slide, x, y_square_emu + title_y_off,
                        square_size, Cm(0.9),
                        item, font_size=title_size, bold=True,
                        color=WHITE, alignment=PP_ALIGN.CENTER)

    return slide

def make_section(prs, number, title, desc="", chapter_index=0):
    """Build section divider slide using Layout 1 (过渡页1)."""
    slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_TRANSITION_1])
    theme_color = CHAPTER_COLORS[chapter_index % len(CHAPTER_COLORS)]

    # Large chapter number — right side, 120pt, bold, chapter-themed color
    add_textbox(slide, Cm(17.6), Cm(5.8), Cm(11.3), Cm(5.4),
                number, font_size=Pt(120), bold=True, color=theme_color)

    # Section title
    add_textbox(slide, Cm(17.5), Cm(9.2), Cm(11.3), Cm(2.0),
                title, font_size=Pt(36), bold=True, color=DARK_TITLE)

    if desc:
        add_textbox(slide, Cm(17.3), Cm(11.9), Cm(11.5), Cm(2.6),
                    desc, font_size=Pt(18), color=BODY_GRAY)

    return slide

def make_content(prs, title, body, chapter_index=0):
    """Build a content slide from Layout 7 with chapter-themed accent."""
    slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_CONTENT])

    # Title placeholder
    ph_title = slide.placeholders[0]
    tf = ph_title.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = title
    set_font(run, size=Pt(40), bold=True, color=DARK_TITLE)

    # Chapter-themed color bar (left accent strip)
    theme_color = CHAPTER_COLORS[chapter_index % len(CHAPTER_COLORS)]
    accent = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Cm(2.0), Cm(5.0), Cm(0.3), Cm(12.5)
    )
    accent.fill.solid()
    accent.fill.fore_color.rgb = theme_color
    accent.line.fill.background()

    # Normalize body
    if isinstance(body, str):
        body = [body]

    # Content body
    body_y = Cm(5.0)
    body_x = Cm(3.0)
    body_w = Cm(27.5)
    body_h = Cm(12.5)

    if len(body) == 0:
        return slide

    if len(body) == 1 and len(body[0]) > 100:
        # Long single paragraph — smaller font, full width
        add_textbox(slide, body_x, body_y, body_w, Cm(11),
                    body[0], font_size=Pt(20), color=BODY_GRAY)
    elif len(body) <= 4:
        # Few bullet points — large text, generous spacing
        txBox = slide.shapes.add_textbox(body_x, body_y, Cm(28.5), Cm(12))
        tf = txBox.text_frame
        tf.word_wrap = True
        for i, item in enumerate(body):
            if i == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()
            p.space_after = Pt(12)
            run = p.add_run()
            run.text = f"• {item}"
            set_font(run, size=Pt(24), color=BODY_GRAY)
    else:
        # Many items — two-column layout
        mid = (len(body) + 1) // 2
        col_w = Cm(13)
        gap = Cm(1.5)
        x1 = Cm(3.0)
        x2 = x1 + col_w + gap

        for col_idx, items in enumerate([body[:mid], body[mid:]]):
            x = x1 if col_idx == 0 else x2
            txBox = slide.shapes.add_textbox(x, body_y, col_w, Cm(12))
            tf = txBox.text_frame
            tf.word_wrap = True
            for i, item in enumerate(items):
                if i == 0:
                    p = tf.paragraphs[0]
                else:
                    p = tf.add_paragraph()
                p.space_after = Pt(8)
                run = p.add_run()
                run.text = f"• {item}"
                set_font(run, size=Pt(18), color=BODY_GRAY)

    return slide

def make_closing(prs, kept_slide):
    """Update the preserved template closing slide with content."""
    slide = kept_slide

    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        tf = shape.text_frame
        name = shape.name

        # Clear ALL placeholder text first
        for para in tf.paragraphs:
            for run in para.runs:
                if "单击此处编辑" in (run.text or ""):
                    run.text = ""

        if "文本占位符 13" in name or ("占位符" in name and "13" in name):
            tf.clear()
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            run = p.add_run()
            run.text = "用 芯 成就美好世界"
            set_font(run, size=Pt(44), bold=True, color=PURPLE)
        elif "文本占位符 19" in name or ("占位符" in name and "19" in name):
            tf.clear()
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            run = p.add_run()
            run.text = "www.unisoc.com"
            set_font(run, size=Pt(16), color=NEAR_BLACK)
        elif "文本占位符 4" in name or ("占位符" in name and "4" in name):
            tf.clear()
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            run = p.add_run()
            run.text = "中国 · 上海"
            set_font(run, size=Pt(14), color=BODY_GRAY)

    return slide

# ─── Outline parsing ────────────────────────────────────────────────

def parse_markdown_outline(md_path):
    """Convert a markdown file into the outline JSON format."""
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    outline = {
        "title": "",
        "subtitle": "",
        "presenter": "",
        "date": "",
        "classification": "内部",
        "slides": []
    }

    lines = content.strip().split('\n')
    current_slide = None

    for line in lines:
        line = line.rstrip()

        if line.startswith('# ') and not outline["title"]:
            outline["title"] = line[2:].strip()
            continue

        if line.startswith('## '):
            if current_slide:
                outline["slides"].append(current_slide)
            sec_num = len([s for s in outline['slides'] if s['type'] == 'section']) + 1
            current_slide = {
                "type": "section",
                "number": f"0{sec_num}",
                "title": line[3:].strip(),
                "desc": ""
            }
            continue

        if line.startswith('### '):
            if current_slide:
                outline["slides"].append(current_slide)
            current_slide = {
                "type": "content",
                "title": line[4:].strip(),
                "body": []
            }
            continue

        if line.strip().startswith(('- ', '* ', '+ ')) or re.match(r'^\d+[\.\)] ', line.strip()):
            text = re.sub(r'^[\d\-\*\+\.\)]+\s*', '', line.strip())
            if current_slide and current_slide["type"] == "content":
                current_slide["body"].append(text)
            continue

        if line.strip() and current_slide and current_slide["type"] == "content":
            if current_slide["body"]:
                current_slide["body"][-1] += " " + line.strip()
            else:
                current_slide["body"].append(line.strip())

    if current_slide:
        outline["slides"].append(current_slide)

    if not outline["title"]:
        outline["title"] = os.path.splitext(os.path.basename(md_path))[0]

    sections = [s for s in outline['slides'] if s['type'] == 'section']
    if sections:
        toc_items = [s['title'] for s in sections]
        outline['slides'].insert(0, {"type": "toc", "items": toc_items})
    outline['slides'].append({"type": "closing"})

    return outline

def load_outline(path):
    """Load outline from JSON or Markdown."""
    if path.endswith('.json'):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    elif path.endswith('.md'):
        return parse_markdown_outline(path)
    else:
        raise ValueError(f"Unsupported format: {path} (use .json or .md)")

# ─── Main builder ────────────────────────────────────────────────────

def build_deck(outline, output_path):
    """Build a complete Unisoc deck from an outline dict."""
    # Clone template
    shutil.copy2(TEMPLATE_PATH, output_path)
    prs = Presentation(output_path)

    # Preserve closing slide (slide 27, 0-indexed) before stripping
    closing_source = prs.slides[26]  # Slide 27 (0-indexed)

    # Strip all original slides EXCEPT the closing slide (26 = slide 27)
    rIds_to_keep = []
    sldId_to_keep = None
    for i, sld_id in enumerate(prs.slides._sldIdLst):
        if i == 26:
            sldId_to_keep = sld_id
            rId = sld_id.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            rIds_to_keep.append(rId)

    # Remove all slides except the closing one
    for i in range(len(prs.slides._sldIdLst) - 1, -1, -1):
        if i != 26:
            rId = prs.slides._sldIdLst[i].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            prs.part.drop_rel(rId)
            prs.slides._sldIdLst.remove(prs.slides._sldIdLst[i])

    title = outline.get("title", "演示标题")
    subtitle = outline.get("subtitle", "")
    presenter = outline.get("presenter", "")
    date = outline.get("date", "")
    classification = outline.get("classification", "内部")

    # 1. Cover
    make_cover(prs, title, subtitle, presenter, date, classification)

    # 2. Content slides — track section counter for chapter colors
    section_counter = 0
    for slide_def in outline.get("slides", []):
        stype = slide_def.get("type", "content")

        if stype == "toc":
            make_toc(prs, slide_def.get("items", []))

        elif stype == "section":
            section_counter += 1
            chap_idx = section_counter - 1
            make_section(prs,
                        slide_def.get("number", f"0{section_counter}"),
                        slide_def.get("title", ""),
                        slide_def.get("desc", ""),
                        chapter_index=chap_idx)

        elif stype == "content":
            chap_idx = max(0, section_counter - 1)
            make_content(prs,
                        slide_def.get("title", ""),
                        slide_def.get("body", ""),
                        chapter_index=chap_idx)

        # Closing slide handled after the loop (always at index 0)

    # Move the preserved closing slide from index 0 to the end
    sldIdLst = prs.slides._sldIdLst
    if len(sldIdLst) > 1:
        closing_sld_id = sldIdLst[0]
        sldIdLst.remove(closing_sld_id)
        sldIdLst.append(closing_sld_id)
    make_closing(prs, prs.slides[-1])

    prs.save(output_path)
    return len(prs.slides)

# ─── CLI entry ───────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python gen_unisoc_ppt.py outline.md output.pptx")
        print("  python gen_unisoc_ppt.py outline.json output.pptx")
        print()
        print("Create a .md outline like:")
        print("  # 项目汇报")
        print("  ## 项目背景")
        print("  ### 背景概述")
        print("  - 要点1")
        print("  - 要点2")
        sys.exit(1)

    outline_path = sys.argv[1]
    output_path = sys.argv[2]

    if not os.path.exists(outline_path):
        print(f"ERROR: Input file not found: {outline_path}")
        sys.exit(1)

    outline = load_outline(outline_path)
    count = build_deck(outline, output_path)
    print(f"Done: {count} slides → {output_path}")
