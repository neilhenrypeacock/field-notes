# Field Notes: East Anglia — Complete Brand & Design Reference

> This document is the single source of truth for the Field Notes visual identity. Use it to generate new illustrations, design new components, or recreate any part of the brand without needing to read the source files.

---

## 1. Brand Identity

| | |
|---|---|
| **Full name** | Field Notes: East Anglia |
| **Tagline** | Weekly farming intelligence for East Anglia |
| **Hero headline** | "Field Notes" (line 1) / "East Anglia" (line 2, gold) |
| **Hero subline** | "Everything East Anglian agriculture needs to know. Every Monday morning." |
| **Meta line** | "Free · 5 minutes · 10+ sources · Every Monday lunchtime" |
| **Target audience** | Farmers, agronomists, land managers, contractors, rural trades — Norfolk, Suffolk, Cambridgeshire |
| **Domain** | fieldnoteseastanglia.co.uk |
| **Email** | hello@fieldnoteseastanglia.co.uk |

### Tone of voice
- Professional, direct, no hedging
- Lead with the number (£/t, p/kg, %, dates)
- Farming-specific language: ex-farm, delivered, p/kg dwt, NVZ, SFI, FETF
- No marketing fluff — every sentence must earn its place
- Source everything inline

---

## 2. Colour Palette

### Primary colours

| Name | Hex | Usage |
|---|---|---|
| **Dark Green** | `#1b3a2d` | Hero bg, section badge backgrounds, table headers, link colour, CTA buttons, body background |
| **Mid Green** | `#263f32` | About/legend strip, forward banner, web footer |
| **Gold** | `#d4a853` | Margin Watch badge, One Good Read badge, hero "East Anglia" subtitle, From the Soil divider, CTA buttons, "Free Weekly Briefing" label, forward banner Playfair text |

### Backgrounds

| Name | Hex | Usage |
|---|---|---|
| **Parchment** | `#f2f0eb` | Outer email wrapper, landing page body (What's Inside, Sources, Map Strip) |
| **Cream** | `#faf8f4` | Markets/Costs/Margin Watch cluster; From the Soil cluster; Community cluster |
| **Off-white** | `#f7f5f0` | Diamond divider background, Data Sources strip, Reader Submission CTA box |
| **White** | `#ffffff` | Opening cluster (At a Glance + Weather), Livestock cluster, Closing cluster (One Good Read) |

### Text colours

| Name | Hex | Usage |
|---|---|---|
| **Body text** | `#333333` | Main copy everywhere |
| **Dark copy** | `#4a4a4a` | Margin Watch body, One Good Read body |
| **Muted text** | `#9a8e7d` | Source lines, captions, footnotes |
| **Link/source text** | `#8a7e6d` | Source links, "Source:" label |
| **Sage text** | `#c8d6c0` | Hero date/issue text, about strip italic text |
| **Green copy** | `#2e5c3a` | Share strip text |
| **Green caption** | `#7db88a` | Footer body copy |
| **Green links** | `#5a8a65` | Footer small links |
| **Grey muted** | `#666` | No-change price indicator, From the Soil italic |

### Data / state colours

| Name | Hex | Usage |
|---|---|---|
| **Up arrow** | `#2e7d32` | Price increase ▲ |
| **Down arrow** | `#c62828` | Price decrease ▼ |
| **No change** | `#666666` | No price change |
| **Weather green bg** | `#f0f7f2` | Weather row < 30% rain; Share strip background |
| **Weather gold bg** | `#fdf8ee` | Weather row 30–60% rain; Margin Watch card bg; One Good Read card bg |
| **Weather red bg** | `#fdf2f2` | Weather row ≥ 60% rain |

### Border / rule colours

| Name | Hex | Usage |
|---|---|---|
| **Table border** | `#e8e2d6` | Price table border, thin HR rules |
| **Divider rule** | `#e0dbd0` | Flanking rules on diamond dividers |
| **Tan diamond** | `#c4b99a` | ◆ ◆ ◆ diamond colour |
| **Warm border** | `#e8dcc4` | Margin Watch / One Good Read card border |
| **Share strip border** | `#d4e8d9` | Bottom border of share strip |
| **Gold divider** | `#d4a853` | From the Soil top border, About strip bottom border |

### Illustration-only colours

| Name | Hex | Typical opacity | Usage in illustrations |
|---|---|---|---|
| **Sky blue** | `#9BBFDF` | 0.25–0.40 | Clouds, sky wash, outer circles |
| **Pale sky** | `#C5DCF0` | 0.25–0.45 | Cloud mass, inner sky circles |
| **Sage green** | `#8FBF96` | 0.28–0.42 | Crops, fields, livestock, schemes |
| **Light sage** | `#B5D4B8` | 0.22–0.35 | Inner sage shapes, hills |
| **Gold warm** | `#D4A843` | 0.35–0.50 | Wheat, markets, primary gold shapes |
| **Gold pale** | `#E8CC7A` | 0.30–0.50 | Inner gold shapes, background wash |
| **Terracotta** | `#C4886B` | 0.20–0.45 | Livestock, farmhouse roof, town dots |
| **Terracotta dark** | `#D4956A` | 0.22 | Inner livestock shapes |
| **Earth brown** | `#B8956A` | 0.18–0.45 | Ground lines, book spine, map Cambridgeshire |
| **Earth dark** | `#A08060` | 0.20–0.25 | Earth shadow lines |

---

## 3. Typography

### Google Fonts import

```
https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Source+Sans+3:wght@400;600;700&family=Source+Serif+4:ital,wght@0,400;0,600;1,400&display=swap
```

### Font 1: Playfair Display

**Role:** Editorial masthead, premium section badges, forward banner

| Context | Size | Weight | Colour | Other |
|---|---|---|---|---|
| Email hero "Field Notes" | 38px | 900 | `#ffffff` | letter-spacing: -0.5px, line-height: 1.15 |
| Email hero "East Anglia" | 22px | 700 | `#d4a853` | letter-spacing: 0.5px, line-height: 1.3 |
| Landing hero h1 "Field Notes" | clamp(44px, 8vw, 64px) | 700 | `#ffffff` | line-height: 1.0 |
| Landing hero h1 span "East Anglia" | (same) | 700 | `#d4a853` | display: block |
| Margin Watch card heading | 16px | 700 | `#1b3a2d` | line-height: 1.3 |
| Forward banner "Or subscribe here →" | 18px | 700 | `#d4a853` | — |
| Email footer "Field Notes: East Anglia" | 16px | 700 | `#d4a853` | — |
| Landing "For You" heading | clamp(22px, 3.5vw, 28px) | 700 | `#ffffff` | — |
| Landing CTA h2 | clamp(24px, 4vw, 32px) | 700 | `#ffffff` | — |
| Fallbacks | — | — | — | Georgia, 'Times New Roman', serif |

### Font 2: Source Sans 3

**Role:** Everything functional — labels, badges, body UI, captions, navigation

| Context | Size | Weight | Colour | Other |
|---|---|---|---|---|
| Section badge labels | 12px | 700 | `#ffffff` (or `#1b3a2d` for gold badges) | letter-spacing: 1.5px, uppercase |
| Hero eyebrow label | 11px | 700 | `#d4a853` | letter-spacing: 3px, uppercase |
| At a Glance body | 14px | 400 | `#333333` | line-height: 1.7 |
| Source/caption lines | 11px | 400 | `#9a8e7d` | line-height: 1.5 |
| "Source:" label | 11px | 700 | `#8a7e6d` | — |
| Share strip | 13px | 400 | `#2e5c3a` | — |
| Hero date/issue | 13px | 400 | `#c8d6c0` | date bold white |
| Hero tagline | 11px | 700 | `#d4a853` | letter-spacing: 3px, uppercase |
| Fieldwork Verdict label | 10px | 700 | varies | letter-spacing: 2px, uppercase |
| Fieldwork Verdict value | 15px | 700 | `#333333` | line-height: 1.5 |
| Reader CTA italic | 12px | 400 | `#8a7e6d` | italic |
| Landing chip | 11px | 600 | rgba(255,255,255,0.40) | letter-spacing: 0.5px |
| Landing icon label | 11px | 700 | `#1b3a2d` | letter-spacing: 1.5px, uppercase |
| Landing icon desc | 13px | 400 | `#777` | line-height: 1.45 |
| Landing sources link | 13px | 400 | `#5a6e60` | — |
| Reply CTA | 13px | 400 | `#9a8e7d` | — |
| "From the Soil" label | 10px | 700 | `#d4a853` | letter-spacing: 2px, uppercase |
| Fallbacks | — | — | — | Arial, Helvetica, sans-serif |

### Font 3: Source Serif 4

**Role:** Editorial prose sections — gives weight and warmth to substantive content

| Context | Size | Weight | Style | Colour |
|---|---|---|---|---|
| About/legend strip | 14px | 400 | italic | `#c8d6c0` |
| Markets summary | 14px | 400 | normal | `#333333` |
| Costs summary | 14px | 400 | normal | `#333333` |
| Margin Watch body | 14px | 400 | normal | `#4a4a4a` |
| Livestock summary | 14px | 400 | normal | `#333333` |
| Schemes summary | 14px | 400 | normal | `#333333` |
| One Good Read body | 14px | 400 | normal | `#4a4a4a` |
| From the Soil | 13px | 400 | italic | `#666` |
| Line height (all body) | — | — | — | 1.75 |
| Fallbacks | — | — | — | Georgia, serif |

---

## 4. Layout System

### Email template

| Property | Value |
|---|---|
| Outer wrapper background | `#f2f0eb` |
| Outer padding | 20px top/bottom, 12px left/right |
| Inner container width | 640px max-width, 100% responsive |
| Content horizontal padding | 44px left/right (all sections) |
| Hero top border-radius | 12px 12px 0 0 |
| Footer bottom border-radius | 0 0 12px 12px |
| Section top padding | 28–32px |
| Section bottom padding | 36px |
| Between-section HR | 24px spacer above, 1px `#e8e2d6` rule |

### Spacing scale (common values)

| Usage | Value |
|---|---|
| Hero inner padding | 36px top/bottom, 44px left |
| Between badge and body | 18px |
| Between sections in same cluster | 24px spacer + 1px rule |
| Diamond divider | 10px top/bottom padding |
| About strip | 20px top/bottom, 44px left/right |
| Share strip | 12px top/bottom, 44px left/right |
| Margin Watch / One Good Read card | 20–22px padding |
| Footer | 28px top/bottom, 44px left/right |
| Data Sources strip | 20px top/bottom, 44px left/right |
| Forward banner | 26px top/bottom, 44px left/right |

### Border radius values

| Element | Value |
|---|---|
| Hero top corners | 12px 12px 0 0 |
| Footer bottom corners | 0 0 12px 12px |
| Section badges | 4px |
| Margin Watch card (right side only) | 0 6px 6px 0 |
| One Good Read card | 6px |
| Price tables | 6px |
| Fieldwork Verdict card | 6px |
| JustFarm CTA box | 6px |
| Hero date box | 6px |
| Buttons / inputs | 6px |
| Topic chips | 20px (pill) |
| "Free, every Monday" pill | 20px |

---

## 5. Components

### Section badge (standard — dark green)

```
background-color: #1b3a2d
border-radius: 4px
padding: 14px 20px 14px 12px

Icon: 36×36px SVG illustration (display:block)
Icon margin-right: 8px
Label: Source Sans 3, 12px, weight 700, #ffffff, letter-spacing 1.5px, uppercase
```

### Section badge (gold — Margin Watch and One Good Read)

```
background-color: #d4a853
border-radius: 4px
padding: 14px 20px 14px 12px

Icon: 36×36px SVG illustration
Label: Source Sans 3, 12px, weight 700, #1b3a2d (dark text on gold)
```

### Diamond divider

```
Background: #f7f5f0
Border-top: 1px solid #e0dbd0
Border-bottom: 1px solid #e0dbd0
Padding: 10px 0
Text: ◆  ◆  ◆  (HTML: &#9670;&nbsp;&nbsp;&#9670;&nbsp;&nbsp;&#9670;)
Font: Source Sans 3, 10px, weight 700, #c4b99a, letter-spacing 4px, uppercase, centered
```

Landing page version (light):
```
.divider--light background: #f7f5f0
Rule color: #e0dbd0
Diamond color: #c4b99a
```

Landing page version (dark):
```
.divider--dark background: #1b3a2d
Rule color: rgba(255,255,255,0.09)
Diamond color: rgba(255,255,255,0.18)
```

### Price table

```
Border: 1px solid #e8e2d6
Border-radius: 6px
Overflow: hidden

Header row:
  background-color: #1b3a2d
  color: #ffffff
  font-size: 11px
  font-weight: 700
  letter-spacing: 0.5px
  text-transform: uppercase
  padding: 10px 12px

Alternating data rows:
  Odd: background #ffffff
  Even: background #faf8f4
  padding: 9px 12px
  font-size: 13px
  color: #333333

Change column:
  ▲ color: #2e7d32 (green)
  ▼ color: #c62828 (red)
  — color: #666666 (grey)
```

### Margin Watch card

```
Background: #fdf8ee
Border: 1px solid #e8dcc4
Border-left: 4px solid #d4a853
Border-radius: 0 6px 6px 0
Padding: 20px 22px

Title: Playfair Display, 16px, weight 700, #1b3a2d
  Dot: 10×10px circle, border-radius 50%, colour = $margin_dot_color, margin-right 8px
Body: Source Serif 4, 14px, line-height 1.75, #4a4a4a
Source line: Source Sans 3, 11px, #9a8e7d
```

### One Good Read card

```
Background: #fdf8ee
Border: 1px solid #e8dcc4
Border-radius: 6px
Padding: 22px 24px
Font: Source Serif 4, 14px, line-height 1.7, #4a4a4a
```

### From the Soil

```
Border-top: 2px solid #d4a853
Padding-top: 20px

Label: Source Sans 3, 10px, weight 700, #d4a853, letter-spacing 2px, uppercase
Body: Source Serif 4, 13px, italic, line-height 1.7, #666
```

### About / legend strip

```
Background: #263f32
Border-bottom: 3px solid #d4a853
Padding: 20px 44px
Font: Source Serif 4, 14px, italic, line-height 1.65, #c8d6c0
```

### Share strip

```
Background: #f0f7f2
Border-bottom: 1px solid #d4e8d9
Padding: 12px 44px
Font: Source Sans 3, 13px, #2e5c3a
Links: color #1b3a2d, font-weight 700, text-decoration underline
```

### Weather table rows (colour by rain probability)

```
< 30% rain:  background #f0f7f2  (light green)
30–60% rain: background #fdf8ee  (light gold)
≥ 60% rain:  background #fdf2f2  (light red)
```

### Reader Submission CTA

```
Padding: 18px 20px
Border-left: 4px solid #1b3a2d
Background: #f7f5f0

Title: Source Sans 3, 14px, weight 700, #1b3a2d
Body: Source Sans 3, 13px, line-height 1.6, #4a4a4a
Link: color #1b3a2d, font-weight 600, text-decoration underline
```

### Forward banner

```
Background: #263f32
Padding: 26px 44px
Text-align: center

Sub-text: Source Sans 3, 14px, #c8d6c0
CTA line: Playfair Display, 18px, weight 700, #d4a853
Link: color #d4a853, text-decoration underline
```

### Email footer

```
Background: #1b3a2d
Border-radius: 0 0 12px 12px
Padding: 28px 44px

Logotype: Playfair Display, 16px, weight 700, #d4a853
Descriptor: Source Sans 3, 12px, line-height 1.7, #7db88a
Divider: border-top 1px solid rgba(255,255,255,0.15), padding-top 14px
Links: Source Sans 3, 11px, #5a8a65; link color #7db88a
```

### Landing page: topic chips

```
Font: Source Sans 3, 11px, weight 600, letter-spacing 0.5px
Color: rgba(255,255,255,0.40)
Background: rgba(255,255,255,0.06)
Border: 1px solid rgba(255,255,255,0.10)
Border-radius: 20px
Padding: 4px 12px
```

### Landing page: signup button

```
Background: #d4a853
Color: #1b3a2d
Border-radius: 6px
Padding: 14px 26px
Font: Source Sans 3, 15px, weight 700
Hover: background #c49543
Transition: 0.15s
```

### Landing page: email input

```
Background: #ffffff
Color: #222
Border: none
Border-radius: 6px
Padding: 14px 18px
Font: Source Sans 3, 15px
Focus: box-shadow 0 0 0 3px rgba(212,168,83,0.45)
```

### Data Sources strip (email)

```
Background: #f7f5f0
Border-top: 1px solid #e8e2d6
Padding: 20px 44px
Font: Source Sans 3, 12px, line-height 1.7, #8a7e6d
"Sources:" label: weight bold, color #1b3a2d
Link: color #8a7e6d, text-decoration underline
```

---

## 6. Illustration System

### Overview

All 15 illustrations use an **abstract watercolour circle technique**: simple geometric shapes (circles, ellipses, rectangles with high border-radius) layered with transparency to create an impression of the subject without literal iconography. This gives a soft, painterly, premium editorial feel.

### Standard dimensions

```
viewBox="0 0 140 80"
width="140" height="80"
```

Used at **36×36px** in section badges, **22×22px** in the hero eyebrow, and **54×54px** on the landing page icon grid.

### Layer structure (applies to every illustration)

1. **Background wash** — large low-opacity ellipse, usually `#E8CC7A` (gold) at opacity 0.08–0.15
2. **Large primary shapes** — 2–4 large circles/ellipses at opacity 0.30–0.45, establishing the subject's palette
3. **Inner highlight shapes** — slightly smaller, lighter or paler version of the primary shapes at opacity 0.22–0.35
4. **Ground line** (where applicable) — thin flat ellipse at bottom, `#B8956A` or `#B5D4B8`, opacity 0.18–0.30
5. **Accent/glow** — small central circle or overlapping element at opacity 0.20–0.25

### Illustration colour palette (with standard opacities)

| Shape type | Primary fill | Opacity range | Inner fill | Opacity range |
|---|---|---|---|---|
| Sky / cloud | `#9BBFDF` | 0.35–0.40 | `#C5DCF0` | 0.25–0.45 |
| Gold / wheat / markets | `#D4A843` | 0.38–0.50 | `#E8CC7A` | 0.30–0.50 |
| Sage / fields / schemes | `#8FBF96` | 0.28–0.42 | `#B5D4B8` | 0.22–0.35 |
| Livestock / terracotta | `#C4886B` | 0.30–0.45 | `#D4956A` | 0.22 |
| Earth / ground | `#B8956A` | 0.18–0.30 | `#A08060` | 0.20–0.25 |
| Background wash | `#E8CC7A` | 0.08–0.15 | — | — |
| Centre glow | `#E8CC7A` | 0.20–0.25 | — | — |

### Illustration inventory

#### `fn_illustration_01_at_a_glance.svg` — At a Glance
Three overlapping circles (sky blue left, gold centre, sage right) with a centre glow. Suggests breadth of coverage — sky, harvest, land.
```
Background wash: ellipse #E8CC7A 0.12
Sky blue left:   circle cx=42 r=24 #9BBFDF 0.35 / inner r=18 #C5DCF0 0.30
Gold centre:     circle cx=70 r=26 #D4A843 0.40 / inner r=19 #E8CC7A 0.35
Sage right:      circle cx=96 r=22 #8FBF96 0.38 / inner r=16 #B5D4B8 0.30
Centre glow:     circle cx=68 r=10 #E8CC7A 0.20
```

#### `fn_illustration_02_markets.svg` — Markets / What You're Selling
Five wheat stems (vertical ellipses + round heads) with an earth ground line. Clear agricultural commodity reference.
```
Background wash: ellipse #E8CC7A 0.10
Ground line:     two ellipses #B8956A 0.30 / #A08060 0.20
5 stems:         vertical ellipses #D4A843 / #E8CC7A, staggered heights cx=32,52,70,88,106
Stem heads:      circles at top of each stem #D4A843 + #E8CC7A inner
```

#### `fn_illustration_03_input_costs.svg` — Costs / What You're Paying
Abstract overlapping circles in muted gold and sage. Neutral/functional palette suggests inputs/costs.
*(Not read in full — follows same circle technique with gold/sage palette)*

#### `fn_illustration_04_margin_watch.svg` — Margin Watch
Two pill-shaped rectangles (revenue left = gold, costs right = sage) with a thin gold sliver between them representing the margin gap. A pressure indicator ellipse in terracotta at centre.
```
Background: ellipse #E8CC7A 0.08
Revenue band: rect x=12 w=52 h=28 rx=14 #D4A843 0.45 / inner rx=10 #E8CC7A 0.30
Costs band:   rect x=76 w=52 h=28 rx=14 #8FBF96 0.42 / inner rx=10 #B5D4B8 0.30
Margin sliver: rect x=63 w=14 h=36 rx=7 #D4A843 0.20 / inner #E8CC7A 0.25
Pressure:     ellipse cx=70 r=4x12 #C4886B 0.20
```

#### `fn_illustration_04b_livestock.svg` — Livestock & Dairy
Three overlapping circles: terracotta left (animal body suggestion), sage green centre, gold right. Small accent circle top-left. Ground line at base.
```
Background wash: ellipse #C4886B 0.07
Terracotta:  circle cx=46 r=24 #C4886B 0.32 / inner r=16 #D4956A 0.22
Sage:        circle cx=72 r=22 #8FBF96 0.35 / inner r=14 #A8D4AC 0.22
Gold:        circle cx=96 r=18 #D4A843 0.38 / inner r=11 #E8CC7A 0.25
Accent top:  circle cx=30 cy=26 r=9 #C4886B 0.20
Ground:      ellipse cy=70 #B8956A 0.18
```

#### `fn_illustration_05_schemes.svg` — Schemes & Grants
A document/scroll shape (rectangles) in sage green with a gold seal (concentric circles) at bottom-right. Text line suggestions as thin rectangles.
```
Background: ellipse #B5D4B8 0.10
Scroll:     rect 38,10 w=64 h=60 rx=8 #8FBF96 0.30
            rect 42,14 w=56 h=52 rx=6 #B5D4B8 0.35
            rect 46,18 w=48 h=44 rx=4 #8FBF96 0.15
Text lines: 3 thin rects #8FBF96 0.20–0.30
Seal:       circle r=12 #D4A843 0.50 / r=8 #E8CC7A 0.40 / r=4 #D4A843 0.30
```

#### `fn_illustration_06_weather.svg` — Weather
Cloud mass (overlapping blue circles) with sun arc (gold circle) behind, and rain drop ellipses below. Ground wash at base.
```
Sun arc:    circle cx=100 r=22 #E8CC7A 0.30 / inner r=16 #D4A843 0.20
Clouds:     5 circles cx=46,56,66,74,84 sizes r=12–22 #9BBFDF 0.25–0.40 / #C5DCF0 0.30–0.45
Rain drops: 4 vertical ellipses cx=48,60,72,84 rx=2.5–3 ry=8–11 #9BBFDF/#C5DCF0 0.25–0.35
Ground:     ellipse cy=70 #C5DCF0 0.12
```

#### `fn_illustration_07_land.svg` — Land & Property
Landscape: sky wash, layered hill ellipses (sage), a farmhouse (terracotta rect body + triangle roof), small window (gold rectangle).
```
Sky:        ellipse cy=20 #C5DCF0 0.20
Far hills:  ellipses cx=40,105 #B5D4B8 0.25–0.30
Near hills: ellipses cx=60,95 #8FBF96 0.30–0.35
Ground:     ellipse cy=70 #B5D4B8 0.25
Farmhouse:  rect 62,42 w=18 h=14 rx=2 #B8956A 0.40
Roof:       path triangle #C4886B 0.45 / inner #C4886B 0.25
Window:     rect 67,46 w=5 h=5 rx=1 #E8CC7A 0.35
```

#### `fn_illustration_08_jobs.svg` — Jobs
*(Follows same technique — likely figures/shapes suggesting people or documents)*

#### `fn_illustration_09_machinery.svg` — Machinery
*(Follows same technique — likely circles/ellipses suggesting wheels or equipment)*

#### `fn_illustration_10_regulatory.svg` — Regulatory & Health
*(Follows same technique — likely document/shield shapes in sage/gold)*

#### `fn_illustration_11_events.svg` — Community & Events
*(Follows same technique — likely circles suggesting gathering/community)*

#### `fn_illustration_12_one_good_read.svg` — One Good Read
Open book: two rotated rectangles (pages) with a central spine rectangle. Subtle text line suggestions. Gold palette throughout.
```
Background: ellipse cy=46 #E8CC7A 0.10
Left page:  rect 22,16 w=46 h=52 rx=4 #D4A843 0.35, rotate(-4) / inner #E8CC7A 0.30
Right page: rect 72,16 w=46 h=52 rx=4 #D4A843 0.38, rotate(4) / inner #E8CC7A 0.30
Spine:      rect 66,14 w=8 h=56 rx=4 #B8956A 0.45 / inner #A08060 0.25
Text lines: 3 thin rects per page #D4A843 0.15–0.20, matching rotation
```

#### `fn_illustration_12b_tech_watch.svg` — Tech Watch
*(Follows same technique — likely circuit/gear shapes in sage/sky blue)*

---

## 7. Map Asset: `fn_map_east_anglia_banner.svg`

### Dimensions
```
viewBox="70 10 310 250"
width="200" height="161"
Internal scale: translate(40,-10) scale(0.55)
```

### County colours

| County | Fill | Opacity | Stroke | Stroke opacity |
|---|---|---|---|---|
| **Cambridgeshire** | `#B8956A` | 0.30 | `#A08060` | 0.30, width 0.6 |
| **Norfolk** | `#D4A843` | 0.35 | `#D4A843` | 0.35, width 0.6 |
| **Suffolk** | `#8FBF96` | 0.28 | `#8FBF96` | 0.30, width 0.6 |

### Water features
```
North Sea (east coast): 3 soft blue ellipses #9BBFDF opacity 0.08–0.12
The Wash (north):       ellipse #9BBFDF opacity 0.08
```

### Town dots
```
Shape: circle, radius 1.8–3px
Fill: #C4886B, opacity 0.30–0.50
5 dots at approximate Norwich, Cambridge, Ipswich, King's Lynn, Ely positions
```

### Usage in email
```
width="200" height="161"
style="display:block;opacity:0.75;"
Position: bottom-right of hero, valign="bottom" align="right"
Padding: 0 36px 36px 20px
```

### Usage in landing page
```
width="min(320px, 80vw)"
opacity: 0.88
In hero: position absolute, inset 0, width 100%, height 100%, object-fit cover
  filter: brightness(1.6), opacity: 0.20
In map strip: centred, display block, margin auto
```

---

## 8. Background Cluster System

The email is divided into visual clusters by alternating background colours:

| Cluster | Background | Sections contained |
|---|---|---|
| Opening cluster | `#ffffff` white | At a Glance, Fieldwork Verdict, Weather |
| Money cluster | `#faf8f4` cream | Markets, Costs, Margin Watch |
| Livestock cluster | `#ffffff` white | Livestock & Dairy |
| From the Soil cluster | `#faf8f4` cream | From the Soil |
| Policy cluster | `#ffffff` white | Schemes & Grants, Regulatory |
| Community cluster | `#faf8f4` cream | Events, Land, Jobs, Machinery, Tech Watch |
| Closing cluster | `#ffffff` white | One Good Read |
| Data strip | `#f7f5f0` off-white | Data Sources |
| Forward banner | `#263f32` mid-green | Forward CTA |
| Footer | `#1b3a2d` dark-green | Footer |

---

## 9. Landing Page Structure

```
1. Hero           — #1b3a2d full-viewport, map SVG ghosted (opacity 0.20, brightness 1.6)
2. Light divider  — ◆ ◆ ◆ on #f7f5f0
3. What's Inside  — #f2f0eb, 3×2 icon grid (54px icons)
4. Sources        — #f2f0eb, inline source links
5. Map strip      — #f2f0eb, county map at 320px, opacity 0.88
6. Dark divider   — ◆ ◆ ◆ on #1b3a2d
7. For You        — #1b3a2d, Playfair heading, target audience copy
8. Repeat CTA     — #1b3a2d, second signup form
9. Footer         — #263f32
```

### Responsive breakpoints

```css
/* Icon grid */
default: grid-template-columns: repeat(3, 1fr); gap: 40px 28px
@media (max-width: 540px): grid-template-columns: repeat(2, 1fr); gap: 32px 20px

/* Hero h1 */
font-size: clamp(44px, 8vw, 64px)

/* For You heading */
font-size: clamp(22px, 3.5vw, 28px)

/* CTA h2 */
font-size: clamp(24px, 4vw, 32px)

/* Hero tagline */
font-size: clamp(16px, 2.5vw, 19px)
```

---

## 10. AI Image Generation Prompts

Use these prompts to generate new images that match the Field Notes aesthetic.

### Style description (use in any prompt)

> Abstract watercolour-style illustration using only simple geometric shapes: overlapping semi-transparent circles and ellipses. No outlines. No literal iconography. Soft, painterly, editorial feel. Colour palette: muted gold (#D4A843, #E8CC7A), sage green (#8FBF96, #B5D4B8), sky blue (#9BBFDF, #C5DCF0), terracotta (#C4886B), earth brown (#B8956A). All shapes at 20–50% opacity, layered to create blended colour transitions. Rectangular canvas 140×80, landscape orientation. Background: very faint gold ellipse wash.

### Prompt template for a new section illustration

> Create an abstract watercolour SVG illustration for "[SECTION NAME]". Style: overlapping translucent circles and ellipses only — no outlines, no literal objects, no text. Colour palette restricted to: gold (#D4A843, #E8CC7A), sage green (#8FBF96, #B5D4B8), sky blue (#9BBFDF, #C5DCF0), terracotta (#C4886B), earth brown (#B8956A). Opacity range 0.20–0.50 per shape. 3–6 shapes total. Canvas 140×80px. The dominant colour should suggest [PRIMARY COLOUR FOR SECTION].

### Section → dominant colour mapping

| Section | Dominant colour suggestion |
|---|---|
| At a Glance | Balanced gold + sage + sky |
| Markets / Grain | Gold (#D4A843) |
| Costs / Fertiliser | Muted sage + gold |
| Margin Watch | Gold left half, sage right half |
| Livestock & Dairy | Terracotta (#C4886B) |
| Schemes & Grants | Sage green (#8FBF96) |
| Weather | Sky blue (#9BBFDF, #C5DCF0) |
| Land & Property | Sage green with earth brown farmhouse |
| Jobs | Sage + gold balanced |
| Machinery | Earth brown + gold |
| Tech Watch | Sky blue + sage |
| Regulatory | Sage green |
| One Good Read | Gold (open book) |
| Events / Community | Gold + sage balanced |

### Prompt for a social media post image

> Flat editorial design image for Field Notes: East Anglia farming newsletter. Dark green background (#1b3a2d). White text "Field Notes" in Playfair Display serif, gold text "East Anglia" below it. Small abstract watercolour circles (gold, sage, sky blue) in the background at low opacity. Clean, professional, agricultural press aesthetic. No photographs.

### Prompt for a banner / header image

> Wide editorial banner for a farming newsletter. Background: deep forest green (#1b3a2d). Right side: faint abstract map outline of Norfolk, Suffolk, and Cambridgeshire counties filled in muted gold, sage green, and warm brown at 25% opacity. Left side: "Field Notes" in large Playfair Display serif (white, weight 900), "East Anglia" beneath in gold (#d4a853). Bottom: very small abstract watercolour circles suggesting farmland. Horizontal format, approximately 4:1 ratio.

---

## 11. SVG Illustration Quick-Reference Card

When writing a new SVG illustration from scratch, use this skeleton:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 140 80" width="140" height="80">

  <!-- 1. Background wash — always first -->
  <ellipse cx="70" cy="45" rx="60" ry="30" fill="#E8CC7A" opacity="0.10"/>

  <!-- 2. Primary shapes (2–4 large circles/ellipses) -->
  <circle cx="[LEFT]"   cy="[Y]" r="[R]" fill="[PRIMARY_COLOR]"  opacity="0.38"/>
  <circle cx="[CENTRE]" cy="[Y]" r="[R]" fill="[PRIMARY_COLOR]"  opacity="0.42"/>
  <circle cx="[RIGHT]"  cy="[Y]" r="[R]" fill="[ACCENT_COLOR]"   opacity="0.35"/>

  <!-- 3. Inner highlights (same centre, ~75% radius) -->
  <circle cx="[LEFT]"   cy="[Y]" r="[0.75R]" fill="[LIGHTER_VERSION]" opacity="0.28"/>
  <circle cx="[CENTRE]" cy="[Y]" r="[0.75R]" fill="[LIGHTER_VERSION]" opacity="0.30"/>

  <!-- 4. Ground line (optional) -->
  <ellipse cx="70" cy="70" rx="52" ry="5" fill="#B8956A" opacity="0.20"/>

  <!-- 5. Centre glow (optional) -->
  <circle cx="70" cy="40" r="10" fill="#E8CC7A" opacity="0.22"/>

</svg>
```

**Rules:**
- No `stroke` attributes (shapes only, no outlines)
- No `<text>` elements
- No gradients or filters
- All fills from the palette above
- Opacity always between 0.08 and 0.50
- Maximum 8–10 shape elements per illustration
- Keep it abstract — suggest, don't depict

---

*Last updated: 24 March 2026*
*Source files: `/Users/neilpeacock/farm/field-notes/newsletter/template.html`, `web/index.html`, `newsletter/assets/*.svg`*
