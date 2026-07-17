# DESIGN.md — Đặc Sản Phố

## Brand Identity

| Thuộc tính | Giá trị |
|-----------|---------|
| **Tên** | Đặc Sản Phố |
| **Tagline** | Món ngon đường phố |
| **Lĩnh vực** | Ẩm thực đường phố Việt Nam |
| **Tính cách** | Gần gũi • Dân dã • Ấm áp • Đậm chất Việt • Ngon miệng |
| **Cảm hứng** | Gánh hàng rong, chợ phiên, phố cổ, đêm Sài Gòn/Hà Nội |

## Color Palette

### Primary — Đỏ ớt / Tương ớt
| Token | Hex | Dùng cho |
|-------|-----|----------|
| `--color-primary` | `#E53935` | CTA, nút chính, accent |
| `--color-primary-dark` | `#C62828` | Hover, active |
| `--color-primary-light` | `#FFEBEE` | Background nhạt |

### Secondary — Vàng nghệ
| Token | Hex | Dùng cho |
|-------|-----|----------|
| `--color-secondary` | `#F9A825` | Stars, badges, highlight |
| `--color-secondary-dark` | `#F57F17` | Hover |
| `--color-secondary-light` | `#FFF8E1` | Background quán gốc |

### Accent — Xanh lá rau thơm
| Token | Hex | Dùng cho |
|-------|-----|----------|
| `--color-accent` | `#43A047` | Tags, success, organic |
| `--color-accent-light` | `#E8F5E9` | Background tags |

### Neutral
| Token | Hex | Dùng cho |
|-------|-----|----------|
| `--color-bg` | `#FAFAFA` | Background chính |
| `--color-surface` | `#FFFFFF` | Card, section |
| `--color-text` | `#1A1A1A` | Text chính |
| `--color-text-secondary` | `#757575` | Text phụ |
| `--color-text-muted` | `#BDBDBD` | Text mờ |
| `--color-border` | `#E0E0E0` | Border |

### Footer
| Token | Hex |
|-------|-----|
| `--color-footer-bg` | `#1B1B1B` |
| `--color-footer-text` | `#9E9E9E` |

## Typography

| Token | Font | Weight | Size | Use |
|-------|------|--------|------|-----|
| `--font-display` | `'Be Vietnam Pro', sans-serif` | 700/800 | 2rem+ | Hero title |
| `--font-heading` | `'Be Vietnam Pro', sans-serif` | 600/700 | 1.1-1.5rem | Section headings |
| `--font-body` | `'Inter', -apple-system, sans-serif` | 400/500 | 14-16px | Body text |
| `--font-mono` | `'JetBrains Mono', monospace` | 400 | 13px | Code, data |

## Design System

### Border Radius
| Token | Value | Use |
|-------|-------|-----|
| `--radius-sm` | `6px` | Tags, chips |
| `--radius-md` | `10px` | Cards, inputs |
| `--radius-lg` | `16px` | Large cards, modals |
| `--radius-full` | `9999px` | Pills, avatars |

### Shadows
| Token | Value |
|-------|-------|
| `--shadow-sm` | `0 1px 3px rgba(0,0,0,0.06)` |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,0.08)` |
| `--shadow-lg` | `0 8px 30px rgba(0,0,0,0.12)` |
| `--shadow-xl` | `0 20px 60px rgba(0,0,0,0.15)` |

### Spacing (8px grid)
| Token | Value |
|-------|-------|
| `--space-xs` | `4px` |
| `--space-sm` | `8px` |
| `--space-md` | `16px` |
| `--space-lg` | `24px` |
| `--space-xl` | `32px` |
| `--space-2xl` | `48px` |

## Components

### Buttons
- Primary: `background: var(--color-primary)`, rounded, shadow-sm, hover scale 1.02
- Secondary: outlined, border `--color-primary`
- Ghost: transparent, hover background `--color-primary-light`

### Cards
- White background, rounded-md, shadow-sm
- Hover: translateY(-4px), shadow-lg, border highlight
- Image: 200px height, object-fit cover, gradient overlay bottom

### Tags/Chips
- Rounded-full, 8-12px padding
- Default: bg `--color-bg`, border
- Active: bg `--color-primary`, white text
- Food category: icon + text

### Hero
- Gradient: `linear-gradient(135deg, #C62828 0%, #E53935 50%, #FF6F00 100%)`
- White text, centered
- Search box: white, rounded-lg, shadow

## Iconography
- Emoji-based (no icon library needed for static site)
- Food categories: 🍜🥖🍨🦐🥢🔥🍚🥤🍲🍿🏆🥬
- UI: 🏙️⭐📍💰🕐📂🗺️📸📋✅🔍
