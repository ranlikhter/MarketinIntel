# MarketinIntel UI/UX Redesign: Wireframes and Component Specifications

This document details the wireframes and component specifications for the MarketinIntel UI/UX redesign, adhering to the "glassy, light, and techy" aesthetic. The focus is on creating a highly usable, flexible, and visually appealing interface.

## 1. General Layout and Navigation

The overall layout will feature a persistent left-hand navigation sidebar and a main content area. The top bar will include global actions, search, and user profile information.

### 1.1. Left Navigation Sidebar

*   **Appearance:** Glassmorphic background (light, blurred, semi-transparent) with subtle border. Collapsible to provide more screen real estate.
*   **Items:** Based on `NAV_ITEMS` from `Layout.js`, with clear icons and text labels. Active item will have a distinct highlight (e.g., amber accent, subtle glow).
*   **Interaction:** Smooth collapse/expand animation. Tooltips on collapsed icons.

### 1.2. Top Bar

*   **Appearance:** Glassmorphic background, subtle shadow.
*   **Elements:**
    *   **Logo/Brand:** Top-left.
    *   **Global Search:** Prominent search bar with a glassy input field.
    *   **Notifications:** Bell icon with badge for unread alerts.
    *   **User Profile:** Avatar/name with dropdown for settings, logout, etc.

## 2. Key Screen Wireframes and Components

### 2.1. Dashboard (Overview)

**Purpose:** Provide a high-level overview of key metrics, alerts, and recent activity. Highly customizable.

**Layout:** Grid-based layout allowing users to add, remove, and rearrange widgets.

**Components:**

*   **Page Header:** `PageHeader` component with a clear title (e.g., "Dashboard") and a subtitle (e.g., "Your personalized overview"). Action button for "Customize Dashboard".
*   **Stat Cards:** `StatCard` components displaying key performance indicators (KPIs) like "Total Products Monitored", "New Alerts", "Competitor Activity".
    *   **Appearance:** Glassmorphic `Card` background, amber-accented values, subtle trend indicators (up/down arrows with `signal` colors).
*   **Activity Feed Card:** A `Card` displaying recent system activities or user actions.
    *   **Appearance:** Glassmorphic `Card` background. List items with icons and timestamps.
*   **Chart Widgets:** Embed `PriceChart.js`, `TrendlineChart.js`, or other custom charts within `Card` components.
    *   **Appearance:** Charts will have transparent backgrounds, techy grid lines, and amber/signal colors for data representation.
*   **Empty State:** `EmptyState` component for areas with no data or unconfigured widgets, prompting user action.

**Example Dashboard Widget (Stat Card):**

```markdown
<Card hover={true}>
  <StatCard label="New Alerts" value="12" color="#EF4444" sub="Last 24 hours" />
</Card>
```

### 2.2. Product Detailed View

**Purpose:** Display comprehensive information about a single product, including its performance, competitor analysis, and related alerts.

**Layout:** Multi-column layout with sections for product details, charts, and related data tables.

**Components:**

*   **Page Header:** Product name as title, SKU/ID as subtitle. Action buttons for "Edit Product", "View Competitors", "Add Alert".
*   **Product Info Card:** A `Card` displaying static product details (image, description, categories).
*   **Performance Charts:** Multiple `Card` components embedding `PriceChart.js` and `TrendlineChart.js` for price history, sales trends, etc.
    *   **Interaction:** Time range selectors (e.g., 7 days, 30 days, 90 days) with glassy `Btn` components.
*   **Competitor Overview Table:** A `Card` containing a `DataTable.js` component showing key metrics for competitors of this product.
    *   **Appearance:** Table with glassy header, subtle row dividers, and amber highlights on interactive elements.
*   **Related Alerts Card:** A `Card` listing alerts specific to this product.
    *   **Appearance:** `Alert` components within the card, using appropriate `type` (e.g., `error`, `warning`, `info`).

## 3. Core UI Components (Glassy & Techy Treatment)

### 3.1. Buttons (`Btn`)

*   **Primary Button:** `variant="primary"` (amber background, dark text). Will have a subtle glow effect on hover and active states, mimicking a light source behind glass.
*   **Secondary/Outline Buttons:** `variant="secondary"` or `outline` (transparent background, amber/ink text, subtle amber border). On hover, a light glassy background fill will appear.
*   **Icon Buttons:** Used for actions within cards or tables, with a minimalist glassy appearance.

### 3.2. Inputs (`Input`, `Textarea`, `Select`)

*   **Appearance:** Transparent background, subtle light border (e.g., `rgba(255,255,255,0.2)`), and a soft inner shadow. Focus state will show a distinct amber glow around the input field.
*   **Placeholders:** Light, semi-transparent text.
*   **Labels:** `Label` component with `textMuted` color, uppercase, and `IBM Plex Mono` font for a techy feel.

### 3.3. Cards (`Card`)

*   **Appearance:** The primary element for glassmorphism. `background: rgba(255, 255, 255, 0.15);` with `backdrop-filter: blur(10px);`. Border `1px solid rgba(255, 255, 255, 0.2);`. Existing `glass` and `glass-lg` shadows will be used.
*   **Hover Effect:** `hover={true}` will trigger a slightly more pronounced border and shadow, or a subtle background shift.

### 3.4. Badges (`Badge`)

*   **Appearance:** Semi-transparent background with a subtle border, using `signal` colors for context (success, danger, info).

### 3.5. Data Tables (`DataTable.js`)

*   **Header:** Glassmorphic background, bold `text` color.
*   **Rows:** Alternating subtle background shades or hover effects for readability. Amber highlight on selected rows.
*   **Pagination/Sorting Controls:** Glassy buttons and input fields.

## 4. Data Visualization Guidelines

*   **Color Palette:** Primarily use the `amber` palette for primary data series, with `signal` colors for status or comparison. Avoid overly saturated colors.
*   **Grids and Axes:** Minimalist, light gray grid lines. `IBM Plex Mono` for axis labels.
*   **Tooltips:** Glassmorphic tooltip backgrounds with clear data display.
*   **Interactivity:** Smooth transitions and animations on hover or data updates.

## 5. Customization Options

*   **Dashboard Layout:** Drag-and-drop functionality for widgets.
*   **Theme Toggle:** While the primary request is for a "light" theme, a future consideration could be a toggle between light and dark glassmorphism.
*   **Data Display Preferences:** Options for date formats, currency symbols, and default chart types.

## 6. Future Considerations

*   **Micro-interactions:** Subtle animations on button clicks, form submissions, and data loading to enhance the techy feel.
*   **Accessibility:** Ensure all glassy effects and color contrasts meet WCAG guidelines.

## 7. Next Steps

Proceed to building a full interactive UI prototype based on these specifications.
