# PlantGuard AI Frontend Graph

## Overview
This document describes the frontend architecture of PlantGuard AI, including component hierarchy, state management, data flow, and UI/UX patterns.

## Technology Stack
- **Framework**: React 18.3.1
- **Build Tool**: Vite 8.1.5
- **Language**: TypeScript 7.0.2
- **Styling**: Tailwind CSS 4.3.3
- **UI Library**: Radix UI primitives
- **State Management**: React Query (tanstack/query) 5.101.4
- **Forms**: React Hook Form 7.82.0
- **Routing**: React Router DOM 6.30.1
- **Charts**: Recharts 3.10.0
- **Animations**: Framer Motion 12.42.2

## Component Architecture
```
+------------------+
|     App Root     |
|  (App.tsx)       |
+------------------+
        |
        v
+------------------+     +------------------+     +------------------+
|  ThemeProvider   |     |   Router         |     |   Global Styles  |
|  (next-themes)   |     |  (react-router)  |     |  (global.css)    |
+------------------+     +------------------+     +------------------+
        |                         |
        |                         v
        |              +------------------+
        |              |   AppShell       |
        |              |  (Layout)        |
        |              +------------------+
        |                         |
        |        +------------------+------------------+
        |        |                  |                  |
        v        v                  v                  v
+------------------+  +------------------+  +------------------+
|   Sidebar        |  |   AppHeader      |  |   Outlet         |
|  (navigation)    |  |  (header/toolbar)|  |  (page content)  |
+------------------+  +------------------+  +------------------+
        |                         |                         |
        |                         |        +------------------+------------------+
        |                         |        |                  |                  |
        |                         v        v                  v                  v
        |              +------------------+  +------------------+  +------------------+
        |              |   MobileNav      |  |   Pages          |  |   MoreSheet      |
        |              |  (bottom nav)    |  |  (route views)   |  |  (mobile menu)   |
        |              +------------------+  +------------------+  +------------------+
        |                         |
        |              +------------------+
        +<-------------|   Toaster/Sonner |
                       |  (notifications) |
                       +------------------+
```

## Page Structure
The application uses React Router for client-side routing with the following pages:

### Index Page (`/`)
- **Component**: `Index.tsx` (in `client/pages/`)
- **Purpose**: Landing page/dashboard overview
- **Current State**: Shows welcome message and navigation to main features
- **Planned Features**: 
  - Plant collection overview
  - Recent scan summaries
  - Quick actions (scan new plant, view recommendations)
  - Weather snapshot for user's location

### Plants Page (`/plants`)
- **Component**: `PlantsPage.tsx` (in `client/pages/`)
- **Purpose**: Manage user's plant collection
- **Current State**: 
  - Displays plant cards in grid/list view
  - Search and filter functionality
  - Basic plant information (name, species, location, health score, status)
  - Add plant button
- **Components Used**:
  - `PlantCard` (reusable component within PlantsPage)
  - Search input with clear button
  - Filter buttons (All plants, Healthy, Needs attention)
  - Grid/List view toggle
- **Planned Features**:
  - Plant detail modal/page
  - Edit plant information
  - Remove plant from collection
  - Scan history for each plant
  - Care reminders and notifications

### Scan Page (`/scan`)
- **Component**: `PlaceholderPage` (in `App.tsx` routes)
- **Purpose**: Upload and analyze plant leaf images
- **Current State**: Placeholder page indicating future implementation
- **Planned Components**:
  - Image upload area (drag & drop or click to upload)
  - Camera capture option (for mobile)
  - Image preview with crop/resize functionality
  - Scan button to initiate analysis
  - Loading state with progress indicator
  - Results display with:
    - Top prediction (disease/health status)
    - Confidence score
    - Alternative predictions (top 3-5)
    - Recommended actions/treatment
    - Similar images from knowledge base
    - Save to plant collection option

### History Page (`/history`)
- **Component**: `PlaceholderPage` (in `App.tsx` routes)
- **Purpose**: View scan history and trends
- **Current State**: Placeholder page
- **Planned Features**:
  - Timeline view of all scans
  - Filter by plant, date range, prediction type
  - Scan detail view with image and results
  - Compare scans of same plant over time
  - Export history option
  - Delete individual scans

### Recommendations Page (`/recommendations`)
- **Component**: `PlaceholderPage` (in `App.tsx` routes)
- **Purpose**: Personalized care recommendations
- **Current State**: Placeholder page
- **Planned Features**:
  - AI-generated care tips based on plant types and scan history
  - Seasonal recommendations
  - Weather-based advice (e.g., "Increase watering due to high temperatures")
  - Product suggestions (fertilizers, treatments)
  - Community tips and tricks
  - Mark recommendations as completed/dismissed

### Weather Page (`/weather`)
- **Component**: `PlaceholderPage` (in `App.tsx` routes)
- **Purpose**: Local weather insights for plant care
- **Current State**: Placeholder page
- **Planned Features**:
  - Current weather conditions
  - Hourly and daily forecast
  - Plant-specific weather insights (e.g., frost warning, humidity alerts)
  - Watering recommendations based on evaporation
  - Disease risk forecasts (fungal risk in high humidity)
  - Location setting/manual override

### Chat Page (`/chat`)
- **Component**: `PlaceholderPage` (in `App.tsx` routes)
- **Purpose**: AI assistant for plant care questions
- **Current State**: Placeholder page
- **Planned Features**:
  - Chat interface with message input
  - Message history display
  - AI responses with typing indicators
  - Image upload for plant identification/questions
  - Quick suggestion buttons
  - Conversation reset/clear history
  - Feedback on response helpfulness
  - Source citations for factual information

### Profile Page (`/profile`)
- **Component**: `PlaceholderPage` (in `App.tsx` routes)
- **Purpose**: User profile and settings
- **Current State**: Placeholder page
- **Planned Features**:
  - User information (name, email, avatar)
  - Plant collection statistics
  - Notification preferences
  - Units preference (metric/imperial)
  - Language selection
  - Account management (logout, delete account)

### Settings Page (`/settings`)
- **Component**: `PlaceholderPage` (in `App.tsx` routes)
- **Purpose**: Application settings
- **Current State**: Placeholder page
- **Planned Features**:
  - General app settings
  - Notification configuration
  - Data export/import
  - Cache management
  - About version information
  - Terms of service and privacy policy

### Not Found Page (`/*`)
- **Component**: `NotFound.tsx` (in `client/pages/`)
- **Purpose**: 404 error page
- **Current State**: Simple "Page not found" message with link back to dashboard

## Key UI Components

### Layout Components
- **Sidebar**: Collapsible navigation drawer with brand, primary/secondary navigation, user info
- **AppHeader**: Sticky header with title, notifications, theme toggle, scan button, profile avatar
- **MobileNav**: Bottom navigation for mobile devices
- **MoreSheet**: Slide-up menu for additional options on mobile

### UI Primitives (from `@/components/ui/*`)
The application uses Radix UI primitives styled with Tailwind CSS:
- **Buttons**: Various sizes and variants (primary, secondary, etc.)
- **Forms**: Inputs, labels, checkboxes, radio groups, toggles, sliders
- **Overlays**: Dialogs, popovers, dropdown menus, tooltips
- **Navigation**: Accordion, breadcrumbs, navigation menu, tabs
- **Data Display**: Avatars, badges, cards, calendars, carousels
- **Feedback**: Alerts, progress, sonner (toast), skeleton loaders
- **Layout**: Aspect ratio, separator, scroll area, resizable panels

### Custom Components
- **ThemeProvider**: Wraps application with next-themes for dark/light/system theme support
- **useToast hook**: Custom hook for displaying notifications (sonner-based)
- **useMobile hook**: Detects mobile viewport for responsive layouts

## State Management

### React Query (tanstack/query)
**Used For**:
- Server state caching (API responses)
- Automatic refetching and background updates
- Pagination and infinite scrolling
- Mutation optimization (optimistic updates)
- Request deduplication

**Planned Queries**:
- `usePlants()`: Fetch user's plant collection
- `usePlant(plantId)`: Fetch specific plant details
- `useScans()`: Fetch scan history with filters
- `useRecommendations()`: Get personalized care tips
- `useWeather(location)`: Get weather data
- `useChatHistory()`: Fetch chat message history

**Planned Mutations**:
- `addPlant()`: Create new plant
- `updatePlant()`: Modify plant information
- `removePlant()`: Delete plant from collection
- `uploadScan()`: Submit image for analysis
- `logCareActivity()`: Record watering, fertilizing, etc.
- `sendMessage()`: Chat with AI assistant

### Local State (useState/useReducer)
**Used For**:
- UI state (sidebar collapsed, modal open, form inputs)
- Temporary data (uploaded image preview, search query)
- Client-only interactions (toggles, animations)

### Context API
**Currently Used**:
- Theme context (via next-themes)
- Potential future use for:
  - User authentication context
  - Plant collection context (to avoid prop drilling)
  - Scan session context

## Data Flow

### Data Loading Pattern
1. **Route Change**: React Router matches URL to page component
2. **Data Fetching**: Page component uses React Query hooks to fetch data
3. **Loading State**: Show skeleton loaders or placeholders while fetching
4. **Error State**: Display error message with retry option
5. **Success State**: Render data with UI components
6. **Background Updates**: React Query refetches stale data automatically

### Mutation Pattern
1. **User Action**: User clicks button or submits form
2. **Optimistic Update**: UI updates immediately assuming success
3. **API Call**: Mutation function sends request to backend
4. **Success**: React Query invalidates related queries to refetch
5. **Error**: Rollback optimistic update, show error message
6. **Retry**: User can retry failed mutations

### Form Handling
- **Library**: React Hook Form
- **Validation**: Zod schemas (via `@hookform/resolvers`)
- **Submission**: Handle loading states, errors, and success messages
- **Reset**: Form resets after successful submission

## Asset Management

### Images
- **Plant Images**: Stored in `public/` folder or via external URLs (Unsplash currently used in demo)
- **Icons**: Lucide React icons (imported individually for tree-shaking)
- **Logos/Branding**: SVG files in `public/` folder
- **Uploaded User Images**: To be stored via backend API (likely cloud storage)

### Styles
- **Global Styles**: `global.css` for base styles and CSS variables
- **Tailwind Configuration**: `tailwind.config.ts` for custom colors, fonts, breakpoints
- **PostCSS Configuration**: `postcss.config.js` for Tailwind processing
- **Component Styles**: Utility-first Tailwind classes in JSX

## Performance Optimizations

### Code Splitting
- **Route-based**: Each page lazy-loaded via React Router
- **Component-based**: Heavy components (charts, maps) lazy-loaded when needed
- **Vendor Splitting**: Separate bundles for dependencies

### Asset Optimization
- **Image Optimization**: 
  - Plant cards use optimized Unsplash images with query parameters
  - Future: Serve images via CDN with responsive sizes
  - Uploaded images: Client-side resize/compression before upload
- **Font Optimization**: System fonts to avoid external requests
- **Icon Optimization**: Tree-shaking to include only used Lucide icons

### Caching Strategies
- **React Query**: 
  - Stale-while-revalidate caching
  - Garbage collection of unused data
  - Manual invalidation for mutations
- **HTTP Caching**: 
  - Static assets served with appropriate Cache-Control headers
  - API responses with proper ETag/Last-Modified headers
- **Service Workers**: 
  - Planned for offline capabilities and faster repeat visits
  - Currently not implemented (Vite PWA plugin could be used)

### Rendering Optimizations
- **Memoization**: `useMemo` and `useCallback` for expensive calculations
- **Virtual Scrolling**: Planned for large lists (plant collections, scan history)
- **Windowing**: For chat message history
- **Debouncing**: Search inputs and resize handlers

## Accessibility Features

### Semantic HTML
- Proper use of landmarks (header, nav, main, section, aside)
- Button elements for interactive actions
- Label elements associated with form inputs
- Heading hierarchy (h1-h6) for content structure

### Keyboard Navigation
- All interactive elements accessible via Tab key
- Visible focus outlines
- Escape key closes modals and dropdowns
- Arrow keys navigate menus, tabs, radio groups

### Screen Reader Support
- ARIA labels for icons and buttons
- Live regions for dynamic content (toasts, loading states)
- Descriptive alt text for images
- Skip navigation links (planned)

### Color Contrast
- Tailwind color palette meets WCAG AA contrast ratios
- Dark mode colors carefully selected for readability
- Focus indicators visible on both light and dark themes

### Responsive Design
- Mobile-first approach with Tailwind breakpoints
- Touch-friendly minimum target sizes (44x44px)
- Layout adapts from single column (mobile) to multi-column (desktop)

## Internationalization (Planned)
Currently not implemented, but planned for future:
- **Framework**: react-i18next or similar
- **Storage**: JSON files per language in `locales/` directory
- **Components**: Translated strings via `useTranslation` hook
- **Routing**: Language prefix in URLs (`/en/plants`, `/es/plants`)
- **Date/Formatting**: Localized dates, numbers, and units
- **RTL Support**: Layout mirroring for right-to-left languages

## Testing Strategy

### Unit Testing
- **Framework**: Vitest 4.1.10
- **Rendering**: React Testing Library
- **Mocking**: MSW (Mock Service Worker) for API calls
- **Coverage**: Components, hooks, utilities

### End-to-End Testing
- **Framework**: Playwright or Cypress (planned)
- **Scenarios**: User journeys (add plant, scan leaf, view results)
- **Environments**: Test against staging backend

### Visual Regression
- **Tool**: Chromatic or Percy (planned)
- **Purpose**: Detect unintended UI changes
- **Frequency**: On each pull request

## Current Limitations and Placeholders

### Missing Functionality
1. **API Integration**: No actual API calls to backend; all data is mock/hardcoded
2. **Image Upload**: No image handling or upload functionality
3. **Persistent State**: No connection to backend for data persistence
4. **Authentication**: No user login/system; all data is ephemeral
5. **Real Data**: Plant data is hardcoded array in PlantsPage.tsx
6. **Notifications**: Toaster/Sonner present but not connected to real events
7. **Theme Persistence**: Theme selection not persisted across sessions (missing implementation)

### Technical Debt
1. **Type Safety**: Some components may lack complete TypeScript definitions
2. **Error Boundaries**: No error boundaries for graceful degradation
3. **Loading States**: Inconsistent loading UI across components
4. **Accessibility Gaps**: Some ARIA labels and keyboard navigation may be incomplete
5. **Performance**: No code splitting for route-based components yet

## Planned Enhancements

### Short-term
1. Connect frontend to backend API endpoints
2. Implement image upload and preview functionality
3. Add authentication flow (login/register)
4. Implement persistent state management via React Query
5. Add proper error handling and loading states
6. Enhance accessibility compliance

### Medium-term
1. Implement offline capabilities with service workers
2. Add data visualization components (charts, graphs)
3. Implement augmented reality features for plant measurement
4. Add social features (plant sharing, community tips)
5. Implement advanced filtering and sorting

### Long-term
1. Progressive Web App (PWA) features
2. Machine learning model confidence visualization
3. Integration with IoT sensors (soil moisture, light meters)
4. Voice command interface
5. Multi-language support

## Related Documents
- [ARCHITECTURE.md](01_ARCHITECTURE.md) - System architecture
- [API_CONTRACTS.md](05_API_CONTRACTS.md) - Backend endpoints frontend will consume
- [MODEL_REGISTRY.md](04_MODEL_REGISTRY.md) - ML model used for scan functionality
- [RAG_GRAPH.md](06_RAG_GRAPH.md) - Knowledge base used by AI assistant
- [AGENT_GRAPH.md](07_AGENT_GRAPH.md) - Agent system that may power advanced features