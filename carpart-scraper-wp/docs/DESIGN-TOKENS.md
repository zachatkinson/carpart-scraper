# Design Tokens

Every colour, radius, and spacing decision in the plugin's CSS goes through a
`--csf-*` custom property. Component stylesheets never reference Kadence's
`--global-palette*` directly; the inheritance happens once, in
`public/css/csf-color-system.css`.

## Precedence (later wins)

1. `csf-color-system.css` — plugin defaults, inheriting Kadence slots.
2. `csf-color-system-dark.css` — dark values, gated by the **Color Scheme** setting.
3. **Design** settings inline CSS — preset values plus per-token overrides.
4. Block-level attributes — per-instance CSS from `render.php`.

## Kadence slot semantics

Kadence's own layout, not a custom mapping. Sites keep this layout even when
they change the colours, so a token must only inherit a slot with the same
meaning.

| Slot | Meaning | Inherited by |
|------|---------|--------------|
| 1 | Accent | `--csf-primary` |
| 2 | Accent hover / secondary | `--csf-secondary` |
| 3 | Text, darkest | `--csf-text` |
| 4 | Text secondary | `--csf-text-secondary` |
| 5 | Text muted | `--csf-text-muted` |
| 6 | Text, lightest | nothing |
| 7 | Background alt | `--csf-bg-alt` |
| 8 | Background | `--csf-bg` |
| 9 | Surface, lightest | `--csf-surface` |
| 10+ | Site-specific | nothing |

Never use slots 3 to 6 as a background. That mistake put slate-grey panels on
the part pages in 1.8.x.

## Tokens

| Token | Role | Default (light) |
|-------|------|-----------------|
| `--csf-primary` | Buttons, links, highlights | slot 1, `#C41C10` |
| `--csf-primary-hover` | Derived: primary mixed 18% black | computed |
| `--csf-on-primary` | Text on a primary background | `#FFFFFF` |
| `--csf-secondary` | Pagination, tabs, badges, focus | slot 2, `#0099CC` |
| `--csf-secondary-hover` | Derived | computed |
| `--csf-on-secondary` | Text on a secondary background | `#FFFFFF` |
| `--csf-accent` | Notices: possible match, engine confirm | `#D97706` |
| `--csf-on-accent` | Text on an accent background | `#1A202C` |
| `--csf-text` / `-secondary` / `-muted` | Copy hierarchy | slots 3 / 4 / 5 |
| `--csf-bg` / `--csf-bg-alt` / `--csf-surface` | Page / panel / card surfaces | slots 8 / 7 / 9 |
| `--csf-inverse-bg` / `--csf-inverse-text` | Dark panel on a light page | `#2D3748` / `#FCFCFC` |
| `--csf-border` / `--csf-border-hover` | Borders | `#E7E5E4` / `#D6D3D1` |
| `--csf-success` / `--csf-warning` / `--csf-error` | Status | plugin-owned |
| `--csf-focus-ring`, `--csf-glow-*` | Derived from secondary | computed |
| `--csf-shadow-sm` … `-xl` | Elevation scale | see stylesheet |
| `--csf-spacing-xs` … `-xl` | 8 / 12 / 16 / 24 / 32 px in rem | see stylesheet |
| `--csf-font-heading` / `--csf-font-body` | Inherit Kadence typography | theme vars |

### Radius

Two layers. The **scale** is what the Design page edits; the **roles** are what
component CSS uses, so changing one scale value updates every element with
that role.

| Scale | Default | Roles using it |
|-------|---------|----------------|
| `--csf-radius-sm` | 4px | `--csf-radius-control`: buttons, inputs, selects, small notices |
| `--csf-radius-md` | 8px | corner badges (`.csf-part-card__badge`) |
| `--csf-radius-lg` | 16px | `--csf-radius-card`: cards, panels, gallery, sections |
| `--csf-radius-pill` | 9999px | `--csf-radius-badge`: year, category, status pills |

`--csf-radius-media` is derived: `max(sm, card − 8px)`. A thumbnail
inset 8px inside a 16px card gets 8px, so the inner and outer curves stay
concentric. `--csf-radius` is an alias of `--csf-radius-card` kept for older
rules.

## Presets

Defined in `includes/class-csf-parts-design.php`. `kadence` applies nothing
(the base stylesheet already inherits the theme). `csf-red` matches the About
and Contact pages: CSF red `#CF2E2E`, navy `#2D3748` for secondary and inverse
panels, `#F7FAFC` page, `#FCFCFC` cards, 16px cards, 3px buttons.

Overrides for brand tokens (`primary`, `secondary`, `accent`, the `on-*` trio)
and the radius scale apply in both light and dark mode. Other overrides apply
to light mode only; dark keeps the preset or stylesheet value.

## Block-level options

Both blocks use WordPress core block supports for the wrapper: background,
text and link colour, padding and margin, font size and line height (the
Single Product block also gets border and shadow). Core renders those through
`get_block_wrapper_attributes()`, so they need no plugin code and preview in
the editor for free.

Card styling in the Product Catalog block stays plugin-specific because it
targets the inner cards, not the wrapper. `CSF_Parts_Block_Styles` maps the
attributes to custom properties on the wrapper (`--csf-card-radius`,
`--csf-card-border-width`, `--csf-card-border-color`, `--csf-card-shadow`)
and the stylesheet reads them with the design token as fallback:

```css
border-radius: var(--csf-card-radius, var(--csf-radius-card));
```

An attribute left unset therefore inherits the Design page, which inherits
the theme. Hover effects, scroll animations, card colour schemes and
responsive visibility are wrapper classes (`csf-hover-*`, `csf-anim-*`,
`csf-card-scheme-*`, `csf-hide-*`) with rules in the stylesheet; the only
per-instance CSS left is the responsive grid and image aspect ratio.

The pre-1.10 `blockPadding` / `blockMargin` attributes are still read when a
block has no core spacing set, so existing content keeps its layout until it
is re-saved with the Dimensions panel.

## Adding a token

1. Define it in `csf-color-system.css` (and a dark value if it is a colour).
2. If administrators should edit it, add it to `CSF_Parts_Design::tokens()`
   and give each preset a value.
3. Use it in component CSS. Never write a hex literal or a Kadence slot there.
