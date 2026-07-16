#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unisoc PPT Template Inventory Tool

Usage:
    python inventory_template.py <path_to_pptx>

Prints a complete inventory of a PPTX file:
- Slide dimensions and aspect ratio
- All slide layouts with placeholder details
- All slides with shape types, names, positions, sizes
- Text content with font/size/color per run
- Tables and images
"""

import sys, io, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from pptx import Presentation
    from pptx.util import Emu, Pt
except ImportError:
    print("ERROR: python-pptx not installed. Run: pip install python-pptx")
    sys.exit(1)

def emu_to_cm(emu):
    return round(emu / 360000, 1) if emu else 0

def emu_to_pt(emu):
    return round(emu / 12700, 1) if emu else 0

def safe_color(font):
    """Extract color safely, handling theme/preset colors."""
    try:
        return str(font.color.rgb)
    except AttributeError:
        try:
            return f"theme({font.color.theme_color})"
        except:
            return "inherit"

def inventory_pptx(path):
    prs = Presentation(path)

    print("=" * 70)
    print(f"PRESENTATION: {os.path.basename(path)}")
    print(f"Dimensions: {emu_to_cm(prs.slide_width)}cm x {emu_to_cm(prs.slide_height)}cm "
          f"({emu_to_cm(prs.slide_width)/emu_to_cm(prs.slide_height):.2f}:1)")
    print(f"Layouts: {len(prs.slide_layouts)}")
    print(f"Slides: {len(prs.slides)}")

    # ── Layouts ──
    print("\n" + "=" * 70)
    print("LAYOUTS")
    print("=" * 70)
    for i, layout in enumerate(prs.slide_layouts):
        print(f"\nLayout {i}: \"{layout.name}\"")
        if layout.placeholders:
            for ph in layout.placeholders:
                pt_name = str(ph.placeholder_format.type)
                print(f"  [{pt_name}] idx={ph.placeholder_format.idx} \"{ph.name}\" "
                      f"pos=({emu_to_cm(ph.left)},{emu_to_cm(ph.top)})cm "
                      f"size=({emu_to_cm(ph.width)},{emu_to_cm(ph.height)})cm "
                      f"id={ph.shape_id}")
        else:
            print("  (no placeholders)")

    # ── Slides ──
    print("\n" + "=" * 70)
    print("SLIDES")
    print("=" * 70)
    for i, slide in enumerate(prs.slides):
        print(f"\n── Slide {i+1} [Layout: \"{slide.slide_layout.name}\"] ──")
        for shape in slide.shapes:
            stype = str(shape.shape_type)
            has_text = "📝" if shape.has_text_frame else ""
            has_img = "🖼" if hasattr(shape, 'image') else ""

            print(f"  [{stype}] \"{shape.name}\" "
                  f"pos=({emu_to_cm(shape.left)},{emu_to_cm(shape.top)})cm "
                  f"size=({emu_to_cm(shape.width)},{emu_to_cm(shape.height)})cm "
                  f"{has_text}{has_img}")

            if shape.has_text_frame:
                for j, para in enumerate(shape.text_frame.paragraphs):
                    text = para.text.strip()
                    if not text:
                        continue
                    run_info = ""
                    for run in para.runs:
                        c = safe_color(run.font)
                        s = emu_to_pt(run.font.size)
                        run_info = f"font={run.font.name} size={s}pt bold={run.font.bold} color=#{c}"
                        break
                    if run_info:
                        print(f"    P{j}: \"{text[:100]}\" [{run_info}]")
                    else:
                        print(f"    P{j}: \"{text[:100]}\"")

            if hasattr(shape, 'table') and shape.has_table:
                t = shape.table
                print(f"    Table: {len(t.rows)}r x {len(t.columns)}c")
                for r in range(min(len(t.rows), 5)):  # cap at 5 rows
                    cells = [t.cell(r, c).text.strip()[:40].replace('\n', ' ')
                             for c in range(len(t.columns))]
                    print(f"    Row{r}: {cells}")
                if len(t.rows) > 5:
                    print(f"    ... ({len(t.rows) - 5} more rows)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default to template if no arg
        default = r"D:\06_Project\open-slide\unisocppt\紫光展锐企业PPT模板（中文）-2506.pptx"
        if os.path.exists(default):
            path = default
        else:
            print("Usage: python inventory_template.py <path_to_pptx>")
            print(f"Default template not found at: {default}")
            sys.exit(1)
    else:
        path = sys.argv[1]

    if not os.path.exists(path):
        print(f"ERROR: File not found: {path}")
        sys.exit(1)

    inventory_pptx(path)
