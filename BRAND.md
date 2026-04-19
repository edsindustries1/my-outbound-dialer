# Open Humana — Brand & Design System Reference

This file is the canonical brand reference for **Open Humana** (openhumana.com), a product of **Everyday Digital Solutions** (Founder: Shushant Bangar). Upload it to Claude (or any other design tool) so generated designs match the live site.

---

## Fonts

The product uses two web fonts, both served from Google Fonts. Use the exact `@import` / `<link>` lines below in any generated HTML/CSS so the typography matches.

### Primary font — Inter
Used for **all body text, UI, buttons, and most headings**.

- Family: `Inter`
- Weights used: `300, 400, 500, 600, 700, 800, 900`
- Source: Google Fonts
- CDN link tags:
  ```html
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
  ```
- CSS `@import`:
  ```css
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
  ```
- Fallback stack:
  ```css
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  ```

### Secondary font — DM Serif Display
Used for **editorial / hero headings only** (About page hero, section titles, CTA blocks). Often set in *italic* at weight 400.

- Family: `DM Serif Display`
- Weights used: `400` (regular and italic)
- Source: Google Fonts
- CDN link tag (combined with Inter on the About page):
  ```html
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet">
  ```
- Fallback stack:
  ```css
  font-family: 'DM Serif Display', Georgia, serif;
  ```

### Typography rules of thumb

| Use case | Font | Weight | Notes |
|---|---|---|---|
| Body text | Inter | 400 | line-height 1.6 |
| UI buttons / labels | Inter | 600–700 | letter-spacing slightly tightened |
| Section headings (utility pages) | Inter | 700–800 | tight letter-spacing (`-0.01em`) |
| Hero / editorial headings | DM Serif Display | 400 italic | `clamp(36px, 5.5vw, 58px)` |
| Eyebrow labels | Inter | 600 uppercase | `letter-spacing: 2.5px` |
| Monospace (numbers, IDs) | system monospace | 400 | `font-family: monospace` |

---

## Color Palette

The product uses a clean, near-monochrome palette with a single dark accent. Marketing surfaces are light; the app shell and admin pages are dark.

### Core (light surfaces — pricing, landing, billing)
| Token | Hex | Use |
|---|---|---|
| `--bg` | `#ffffff` | Page background |
| `--bg-subtle` | `#f8f9fa` | Section background, table headers |
| `--text` | `#111827` | Primary text |
| `--text-muted` | rgba(17,24,39,0.6) | Secondary text |
| `--accent` | `#1a1a1a` | Buttons, primary CTAs, focus borders |
| `--accent-hover` | `#000000` | CTA hover state |
| `--accent-light` | rgba(26,26,26,0.06) | CTA hover background, pill backgrounds |
| `--border` | `#e5e7eb` | Card and input borders |

### Dark surfaces (app shell, super admin)
| Token | Hex | Use |
|---|---|---|
| Background | `#0a0a0a` | Page background |
| Surface | rgba(255,255,255,0.04) | Cards, inputs |
| Surface border | rgba(255,255,255,0.08–0.10) | Card borders |
| Text | `#ffffff` | Primary |
| Text muted | rgba(255,255,255,0.55–0.65) | Secondary |

### Status / accent colors (used for pills, badges, status descriptions)
| Status | Hex | Tinted background |
|---|---|---|
| Green (success) | `#10b981` / `#059669` | `rgba(16,185,129,0.15)` |
| Yellow (warning) | `#f59e0b` | `rgba(245,158,11,0.15)` |
| Red (error) | `#ef4444` | `rgba(239,68,68,0.15)` |
| Blue (info) | `#3b82f6` | `rgba(59,130,246,0.15)` |
| Purple (premium) | `#a78bfa` / `#8b5cf6` | `rgba(139,92,246,0.20)` |

---

## Shape & Spacing

| Token | Value | Use |
|---|---|---|
| `--radius` | `8px` | Inputs, small buttons |
| `--radius-lg` | `16px` | Cards, modals |
| Pill radius | `99px` / `50px` | Badges, toggle buttons |
| Card padding | `36–40px` | Pricing cards |
| Button padding | `8–12px × 18–22px` | Primary CTAs |
| Box shadow (cards) | `0 4px 24px rgba(0,0,0,0.04)` | Light surfaces |
| Box shadow (CTA hover) | `0 4px 16px var(--accent-glow)` | Lift effect |

---

## Voice & Brand Notes

- **Product name:** Open Humana (always two words, both capitalized)
- **Parent company:** Everyday Digital Solutions
- **Tagline themes:** AI digital employee, voicemail drop, outbound call automation
- **Lead persona:** "Alex" — the AI digital employee
- **Tone:** Plain-spoken, confident, slightly editorial on marketing pages (hence DM Serif Display for hero)

---

## Quick copy-paste starter for Claude designs

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:#ffffff; --bg-subtle:#f8f9fa;
    --text:#111827; --text-muted:rgba(17,24,39,0.6);
    --accent:#1a1a1a; --accent-hover:#000000;
    --accent-light:rgba(26,26,26,0.06);
    --border:#e5e7eb;
    --font:'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --font-display:'DM Serif Display', Georgia, serif;
    --radius:8px; --radius-lg:16px;
  }
  body { font-family: var(--font); background: var(--bg); color: var(--text); line-height: 1.6; }
  h1.hero { font-family: var(--font-display); font-weight: 400; font-style: italic; letter-spacing: -0.01em; }
</style>
```
