# open-slide — PPT Skill Framework

Custom Claude Code skills for generating templated PowerPoint decks. Currently focused on 紫光展锐 (Unisoc) corporate presentations.

## Project Layout

```
open-slide/
  .claude/skills/unisoc-ppt/     # Claude Code skill definition
    SKILL.md                      # Skill entry point (frontmatter + rules)
    scripts/
      inventory_template.py       # Slide-by-slide template analysis tool
      gen_unisoc_ppt.py           # Deck generator (JSON or Markdown → PPTX)
    references/
      template-layouts.md         # Full layout catalog + positioning guide
  unisocppt/
    紫光展锐企业PPT模板（中文）-2506.pptx  # Official Unisoc corporate template
  referenceppt/                   # Screenshots from reference skill tutorials
```

## Available Skills

- **Unisoc-PPT** — Generate Unisoc-branded decks from structured markdown/JSON outlines using the official corporate template.

## Using the Generator

```bash
python .claude/skills/unisoc-ppt/scripts/gen_unisoc_ppt.py outline.md output.pptx
```

Markdown outline format:
```markdown
# 演示标题
## 章节一
### 内容页标题
- 要点1
- 要点2
## 章节二
### 另一内容页
- 要点A
- 要点B
```

## Dependencies

```bash
pip install python-pptx>=0.6.21
```
