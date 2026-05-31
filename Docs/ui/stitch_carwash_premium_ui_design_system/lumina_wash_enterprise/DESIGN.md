---
name: Lumina Wash Enterprise
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#424754'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#727785'
  outline-variant: '#c2c6d6'
  surface-tint: '#005ac2'
  primary: '#0058be'
  on-primary: '#ffffff'
  primary-container: '#2170e4'
  on-primary-container: '#fefcff'
  inverse-primary: '#adc6ff'
  secondary: '#00687a'
  on-secondary: '#ffffff'
  secondary-container: '#57dffe'
  on-secondary-container: '#006172'
  tertiary: '#6b38d4'
  on-tertiary: '#ffffff'
  tertiary-container: '#8455ef'
  on-tertiary-container: '#fffbff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#004395'
  secondary-fixed: '#acedff'
  secondary-fixed-dim: '#4cd7f6'
  on-secondary-fixed: '#001f26'
  on-secondary-fixed-variant: '#004e5c'
  tertiary-fixed: '#e9ddff'
  tertiary-fixed-dim: '#d0bcff'
  on-tertiary-fixed: '#23005c'
  on-tertiary-fixed-variant: '#5516be'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-mono:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.05em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  container-padding-desktop: 32px
  container-padding-mobile: 16px
  gutter: 24px
  card-gap: 20px
---

## Brand & Style

The design system is engineered to evoke a sense of clinical precision, freshness, and high-end hospitality. It targets carwash facility managers and staff who require a tool that feels as clean and polished as the vehicles they service. 

The aesthetic is **Corporate Modern** with a **Glassmorphic** touch. It leverages a light, airy environment where depth is created through soft shadows and subtle translucent layers rather than heavy borders. The tone is professional and trustworthy, emphasizing efficiency through a clear visual hierarchy and a calming, water-inspired color palette.

## Colors
The palette is built on a foundation of "Fresh Water" blues and "Clean Slate" neutrals. 

- **Primary Action:** A vibrant Blue (#3B82F6) often paired with a Cyan (#06B6D4) gradient to represent water and movement.
- **Backgrounds:** The main application background uses #F8FAFC to reduce eye strain, while active surfaces and cards use pure #FFFFFF to "pop" against the canvas.
- **Status Semantic System:** A robust color coding system is used for vehicle lifecycle tracking. Use these colors at low opacity (10-15%) for badge backgrounds and 100% opacity for text and indicator icons.
- **Gradients:** Use a linear gradient (135deg) from Primary Blue to Secondary Cyan for high-impact elements like primary buttons or active state indicators.

## Typography
The typography system prioritizes legibility and technical clarity. 

- **Inter** is the workhorse for all UI elements, providing a neutral and modern feel. 
- **JetBrains Mono** is reserved strictly for technical data: vehicle license plates, transaction IDs, timestamps, and currency amounts. This creates a functional "data" layer that is instantly recognizable.
- For Persian localization, **Vazirmatn** should be used as the primary typeface, maintaining the same weight and scale ratios defined for Inter.
- **Headlines** utilize tighter letter spacing to maintain a premium "editorial" look in large sizes.

## Layout & Spacing
This design system employs a **Fluid Grid** with generous white space to reflect the "cleanliness" of the brand.

- **Grid:** A 12-column grid for desktop with 24px gutters. 
- **Margins:** Large outer margins (32px on desktop) keep content centered and focused.
- **Rhythm:** Spacing follows an 8px base unit. Component internal padding should lean towards the larger side (e.g., 24px or 32px for card padding) to evoke a premium, un-crowded feel.
- **Adaptation:** On mobile, grids collapse to a single column, and container padding reduces to 16px to maximize real estate while maintaining the signature soft-shadow depth.

## Elevation & Depth
Depth is the primary driver of hierarchy in this design system. 

- **Surfaces:** Main background is flat. Cards and Modals use "Floating Elevation."
- **Shadow-MD:** Use a soft, diffused shadow for standard cards (0px 10px 25px -5px rgba(15, 23, 42, 0.05)).
- **Shadow-Glow:** Reserved for Primary buttons and active status indicators. This uses the primary color hex with 20% opacity (0px 8px 20px rgba(59, 130, 246, 0.25)).
- **Glassmorphism:** Use backdrop blur (12px) on sticky navigation headers and modal overlays to maintain a sense of environmental continuity.

## Shapes
Shapes are intentionally soft to feel approachable and modern.

- **Cards:** Use a large 20px radius. This "squircle" influence feels more premium and custom than standard web defaults.
- **Interactive Elements:** Buttons use a 12px radius, and Input fields use a 14px radius, creating a distinct visual difference between clickable actions and data entry points.
- **Badges/Chips:** Always use a full pill shape (rounded-full) to signify status and categories.

## Components

- **Buttons:** 
  - **Primary:** Linear gradient (Blue to Cyan), 12px radius, shadow-glow. Text is white, semi-bold.
  - **Secondary:** White background with a subtle 1px border (#E2E8F0) and Primary Blue text.
- **Cards:** 
  - Pure white background, 20px radius, shadow-md. No borders unless used for state (e.g., a 2px blue border for a "selected" car wash package).
- **Inputs:** 
  - 14px radius, #F1F5F9 background. On focus, use a 2px solid primary blue ring with a subtle outer glow.
- **Badges:** 
  - Use the status colors at 12% opacity for the background and 100% opacity for the text. Font should be Inter Bold, Uppercase, 12px.
- **Lists:** 
  - For vehicle queues, use "Quiet Rows" with no horizontal borders; instead, use a 1px #F1F5F9 divider that doesn't span the full width of the container.
- **License Plate Display:**
  - A specialized component using JetBrains Mono. High-contrast (Dark Navy background, White text) or stylized to look like a physical plate, enclosed in a card with 8px radius.