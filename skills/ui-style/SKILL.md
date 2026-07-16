---
name: ui-style
slug: ui-style
version: 1.0.0
description: "Apply the house UI style when building or modifying frontend interfaces. Triggers when the user asks to create UI, build a page, style a component, or make an interface — applies the progetto glassmorphism + gradient-accent + dark-mode-first design system."
metadata: {"clawdbot":{"emoji":"🎨","requires":{"bins":[]},"os":["linux","darwin","win32"]}}
---

## When to Use

This skill activates when the user asks you to:
- Create a new page, form, dashboard, tool UI, or web interface
- Style or redesign an existing component
- Build frontend for a new feature
- "Make it look like our style" / "follow the house style"

## Reference Project

The canonical design reference is `D:\05_Code\MobaXterm-Keygen`. When in doubt about a visual decision, read the source files in that project — especially `index.html`, `css/style.css`, and `css/fire.css`.

## Tech Stack Defaults

- **CSS framework**: Tailwind CSS (CDN or build), with a custom Tailwind config for the primary palette, font, and keyframes
- **Base reset**: Pure CSS or modern-normalize
- **Reactive layer**: Vue 3 (Composition API, `<script setup>`) — upgrade from the reference's Vue 2
- **Font**: Outfit (Google Fonts), weights 300/400/500/600/700/800/900
- **Icons**: Inline SVG, Heroicons outline style (24x24, stroke-width 2, fill="none", stroke="currentColor")
- **No component library** — everything is hand-built with Tailwind utility classes

## Design System: "Neumorphic Glassmorphism + Gradient Accents"

### 1. Color Palette

#### Primary (Indigo/Blue-Purple)

| Token | Hex | Usage |
|---|---|---|
| primary-50 | `#eef2ff` | Info box backgrounds, subtle badges |
| primary-100 | `#e0e7ff` | Badge backgrounds (light mode) |
| primary-200 | `#c3dafe` | Light borders |
| primary-300 | `#a3bffa` | Dark-mode text accents, active tab text |
| primary-400 | `#7f9cf5` | Focus rings (dark mode), active borders |
| primary-500 | `#667eea` | **Core primary** — button base, focus rings, indicators |
| primary-600 | `#5a67d8` | Tab active text (light), link hover |
| primary-700 | `#4c51bf` | Badge text (light) |
| primary-800 | `#434190` | Dark badge borders |
| primary-900 | `#3c366b` | Dark badge backgrounds |

#### Neutral / Slate

| Token | Light Mode | Dark Mode |
|---|---|---|
| Page background | `#f8fafc` (slate-50) | `#000000` (black) |
| Panel background | `rgba(255,255,255,0.85)` | `rgba(15,23,42,0.75)` |
| Body text | `#1e293b` (slate-800) | `#f8fafc` (slate-50) |
| Muted text | `#64748b` (slate-500) | `#94a3b8` (slate-400) |
| Label text | `#334155` (slate-700) | `#cbd5e1` (slate-300) |
| Input border | `rgba(209,213,219,0.6)` | `rgba(71,85,105,0.6)` |

#### Accent Gradients

- **Button gradient**: `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`
- **Title text gradient**: `#1e40af` → `#ec4899` → `#4f46e5`
- **Tab underline gradient**: `#667eea` to `#ed64a6`
- **Background blobs**: purple-400, blue-400, pink-400 at opacity-20
- **Aurora stripes** (animated bg): `#60a5fa`, `#e879f9`, `#5eead4`

#### Semantic

- Error: `red-500` (`#ef4444`), backgrounds `red-50`/`red-900`
- Success: `green-50`/`green-900` bg, `green-700` text
- Pulse indicator: `red-500`

### 2. Glass Panel (Core Card)

The `.glass-panel` class is the single most important visual element:

```css
.glass-panel {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(40px);
  -webkit-backdrop-filter: blur(40px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.4);
  border-radius: 24px; /* rounded-3xl */
}

.dark .glass-panel {
  background: rgba(15, 23, 42, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.1);
}
```

With a subtle shimmer overlay: `bg-gradient-to-tr from-white/5 to-white/0`.

### 3. Buttons

#### Primary Action (`.btn-gradient`)

```css
.btn-gradient {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  background-size: 200% 200%;
  color: white;
  transition: all 0.5s ease;
}
.btn-gradient:hover {
  background-position: right center;
  box-shadow: 0 10px 25px -5px rgba(102, 126, 234, 0.4);
  transform: translateY(-2px);
}
.btn-gradient:active {
  transform: translateY(1px);
  box-shadow: 0 4px 6px -1px rgba(102, 126, 234, 0.2);
}
.btn-gradient:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}
```

Default sizing: `w-full py-4 px-6 rounded-xl text-lg font-bold uppercase tracking-wider`.
Focus ring: `focus:ring-4 focus:ring-primary-500/50 focus:outline-none`.

### 4. Inputs (`.input-modern`)

```css
.input-modern {
  width: 100%;
  padding: 14px 16px 14px 44px; /* pl-11 pr-4 py-3.5 */
  border-radius: 12px; /* rounded-xl */
  background: rgba(255, 255, 255, 0.7);
  border: 2px solid rgba(209, 213, 219, 0.6);
  color: #1f2937;
  transition: all 0.3s ease;
  outline: none;
}
.input-modern:focus {
  background: #ffffff;
  border-color: #667eea;
  box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.2);
}

.dark .input-modern {
  background: rgba(15, 23, 42, 0.7);
  border-color: rgba(71, 85, 105, 0.6);
  color: #f8fafc;
}
.dark .input-modern:focus {
  background: rgba(15, 23, 42, 0.95);
  border-color: #7f9cf5;
  box-shadow: 0 0 0 4px rgba(127, 156, 245, 0.2);
}
```

**Input icon pattern**: Wrap input in `relative` container. Icon is absolutely positioned left (`left-3.5 top-1/2 -translate-y-1/2`), colored `text-slate-400`, and transitions to `text-primary-500` on `group-focus-within`.

**Select dropdowns**: Same `.input-modern` base + `appearance-none` + custom chevron SVG overlay on the right. `cursor-pointer`.

```css
/* Required for native form controls to respect dark/light mode */
:root { color-scheme: dark; }
body.light { color-scheme: light; }

.select-field {
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%2394a3b8' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 32px;
}

.select-field option {
  background: #1e293b;
  color: #f1f5f9;
}

body.light .select-field option {
  background: #ffffff;
  color: #0f172a;
}
```

Without `color-scheme` and explicit `option` styling, browser-native `<select>` popups render with the OS default theme (typically white bg), ignoring the page's dark mode.

### 5. Tabs

```html
<!-- Tab container -->
<div class="bg-slate-200/60 dark:bg-slate-800/60 p-1.5 rounded-2xl shadow-inner max-w-sm mx-auto">
  <button class="py-2.5 px-6 text-sm sm:text-base font-bold rounded-xl tracking-wide transition-all duration-300"
          :class="active ? 'bg-white dark:bg-slate-700 shadow-sm text-primary-600 dark:text-primary-400' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'">
    Tab Label
  </button>
</div>
```

Active tab gets a gradient underline via `::after` pseudo-element (3px height, `#667eea` → `#ed64a6`, animated in with `@keyframes tabSlide`).

### 6. Layout Pattern

- **Single centered card**: `max-w-2xl mx-auto min-h-screen flex flex-col items-center justify-center`
- **Page padding**: `px-4 sm:px-6 py-12 lg:py-24`
- **Card padding**: `p-8 md:p-12`
- **Form grid**: `grid grid-cols-1 md:grid-cols-2 gap-8`, full-width elements use `col-span-1 md:col-span-2`
- **Section gaps**: `space-y-6` for sections, `space-y-3` for compact groups, `mb-10` between major sections

### 7. Typography Scale

| Element | Size | Weight | Tracking |
|---|---|---|---|
| Page title (h1) | `text-4xl` → `md:text-6xl` | `font-extrabold` | `tracking-tight` |
| Subtitle | `text-sm` → `text-base` | normal | — |
| Section heading | `text-lg` | `font-semibold` | — |
| Labels | `text-sm` | `font-medium` | — |
| Body text | `text-sm` → `text-base` | normal | — |
| Button text | `text-lg` | `font-bold` | `uppercase tracking-wider` |
| Tab text | `text-sm sm:text-base` | `font-bold` | `tracking-wide` |
| Small hint | `text-xs` | normal | — |
| Footer | `text-xs` → `text-[11px]` | normal | — |
| Code (inline) | `text-xs` | normal | `font-mono` |

### 8. Border Radius Scale

| Size | Value | Usage |
|---|---|---|
| `rounded-3xl` | 24px | Main glass card |
| `rounded-2xl` | 16px | Tabs, info boxes, file dropzones |
| `rounded-xl` | 12px | Inputs, buttons, small cards |
| `rounded-lg` | 8px | Icon containers, inline code |
| `rounded-full` | 9999px | Badges, indicator dots |

### 9. Animations

**Always use `cubic-bezier(0.16, 1, 0.3, 1)`** as the standard easing curve for entrances, exits, and transitions. This is the house curve.

| Animation | Trigger | Duration | Easing |
|---|---|---|---|
| Content fade-in-up | Page load | 0.8s | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Button hover lift | Hover | 0.5s | ease |
| Input focus glow | Focus | 0.3s | ease |
| Tab underline slide | Tab switch | 0.3s | ease-out |
| Toast slide-in | Show | 0.4s | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Preloader fade-out | Page ready | 0.6s | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Background blobs | Continuous | 7s | infinite |
| Aurora stripes | Continuous | 40s | linear infinite |

**Key rule**: Every visible element that appears on load gets `animate-fade-in-up` (staggered via `animation-delay`). The preloader covers the page until everything is ready, then fades out.

### 10. Animated Background

A premium "aurora" effect behind the glass panel:

- Full-screen fixed overlay, `z-0`, `overflow-hidden`
- Diagonal repeating stripes via `repeating-linear-gradient`
- Rainbow color stops, heavily blurred (`blur-[120px]`)
- `mix-blend-mode: difference` for iridescence
- `@keyframes aurora` scrolls the background position over 40s
- Plus 3 floating blobs (purple, blue, pink) with `animate-blob` at different delays

### 11. Toast Notifications

```css
.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 50;
  border-radius: 12px;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  gap: 12px;
  backdrop-filter: blur(20px);
  transform: translateY(96px);
  opacity: 0;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.toast.show { transform: translateY(0); opacity: 1; }
```

Auto-dismiss after 4 seconds. Success uses green tones, error uses red tones.

### 12. Badges & Indicators

- **Status badge**: `rounded-full px-3 py-1 text-xs font-semibold`, primary color bg/text
- **Ping dot**: A green `animate-ping` dot + static colored dot, absolutely positioned
- **Info box**: `bg-primary-50/80 dark:bg-primary-900/10 border border-primary-100 dark:border-primary-800/30 rounded-2xl p-5`

### 13. Dark Mode

Dark mode is **first-class**, not an afterthought. Every color rule needs a `dark:` counterpart.

```js
// Theme init (inline in <head> to prevent FOUC)
if (localStorage.theme === 'dark' || (!('theme' in localStorage) && matchMedia('(prefers-color-scheme: dark)').matches)) {
  document.documentElement.classList.add('dark');
}
```

Toggle button switches `dark` class on `<html>` and persists to `localStorage.theme`.

### 14. File Upload Dropzone

```css
.dropzone {
  border: 2px dashed; /* border-slate-300 dark:border-slate-600 */
  border-radius: 16px;
  width: 100%;
  height: 128px; /* h-32 */
  background: rgba(255,255,255,0.3);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: background 0.2s;
}
.dropzone:hover {
  background: rgba(255,255,255,0.6);
}
```

Hidden `<input type="file">` triggered by `<label>`. Shows an upload icon, filename, and size hint.

---

## Build Checklist

When delivering a UI, verify every item:

- [ ] Glass panel card with correct backdrop-filter and border-radius-3xl
- [ ] Inline SVG Heroicons (no icon library dependency)
- [ ] Outfit font loaded from Google Fonts
- [ ] Tailwind config extends primary palette + font + keyframes
- [ ] `.btn-gradient` class with hover lift and active press
- [ ] `.input-modern` class with focus glow and icon positioning
- [ ] Dark mode `dark:` variants on every color rule
- [ ] Theme toggle persisted to localStorage
- [ ] Preloader that fades out on page ready
- [ ] `animate-fade-in-up` on content elements
- [ ] Standard easing curve `cubic-bezier(0.16, 1, 0.3, 1)` on all transitions
- [ ] Responsive: grid → stack on mobile, card padding adjusts
- [ ] Toast notification system for success/error feedback
- [ ] Gradient accent on at least one element (button, title, or tab underline)
- [ ] Animated background (blobs or aurora effect) behind the glass panel
- [ ] Single centered column layout, max-w-2xl
- [ ] Tailwind CSS from CDN (dev/prototype) or bundled (production)
