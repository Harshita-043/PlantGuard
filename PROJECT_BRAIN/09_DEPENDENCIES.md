# PlantGuard AI Dependencies

## Overview
This document lists all dependencies used in the PlantGuard AI project, including frontend, backend, development tools, and machine learning frameworks. Note that the backend is planned to use FastAPI and PostgreSQL as per user preference.

## Frontend Dependencies
Located in `frontend/package.json`

### Core Framework
- **react**: ^18.3.1 - React library for building user interfaces
- **react-dom**: ^18.3.1 - React DOM for web rendering
- **react-router-dom**: ^6.30.1 - Declarative routing for React applications

### Build & Tooling
- **vite**: ^8.1.5 - Next-generation frontend build tool
- **@vitejs/plugin-react**: ^6.0.4 - Vite plugin for React
- **typescript**: ^7.0.2 - TypeScript compiler
- **tsx**: ^4.23.1 - TypeScript execution engine
- **vitest**: ^4.1.10 - Vite-native unit testing framework

### Styling & UI
- **tailwindcss**: ^4.3.3 - Utility-first CSS framework
- **tailwind-merge**: ^2.6.1 - Utility for conditionally combining Tailwind classes
- **tailwindcss-animate**: ^1.0.7 - Tailwind CSS plugin for animations
- **autoprefixer**: (via tailwindcss) - CSS vendor prefixing
- **postcss**: ^8.5.23 - CSS post-processor
- **postcss.config.js**: PostCSS configuration

### UI Components
- **@radix-ui/react-***: Various Radix UI primitives for accessible components
  - accordion, alert-dialog, aspect-ratio, avatar, checkbox, collapsible, 
  - context-menu, dialog, dropdown-menu, hover-card, label, menubar,
  - navigation-menu, popover, progress, radio-group, scroll-area,
  - select, separator, slider, slot, switch, tabs, toast, toggle, tooltip
- **lucide-react**: ^1.25.0 - Beautiful & consistent icon toolkit
- **class-variance-authority**: ^0.7.1 - Utility for composing CVA classes
- **clsx**: ^2.1.1 - Utility for constructing className strings conditionally
- **cmdk**: ^1.1.1 - Command menu component
- **sonner**: ^2.0.7 - Toast notification component
- **vaul**: ^1.1.2 - Drawer component
- **next-themes**: ^0.4.6 - Theme provider for Next.js (used for system theme detection)
- **date-fns**: ^4.4.0 - Modern JavaScript date utility library
- **react-day-picker**: ^9.8.1 - Flexible date picker for React
- **react-hook-form**: ^7.82.0 - Performant forms library for React
- **react-resizable-panels**: ^3.0.4 - Resizable panels for React
- **recharts**: ^3.10.0 - Redefined chart library built with React and D3
- **framer-motion**: ^12.42.2 - Production-ready motion library for React
- **embla-carousel-react**: ^8.6.0 - Carousel component for React
- **@react-three/fiber**: ^8.18.0 - React renderer for Three.js
- **@react-three/drei**: ^9.122.0 - Useful helpers for React Three.js
- **three**: ^0.185.1 - JavaScript 3D library

### State Management & Data Fetching
- **@tanstack/react-query**: ^5.101.4 - Powerful asynchronous state management
- **@hookform/resolvers**: ^5.4.0 - Resolvers for React Hook Form (Zod integration)

### Utilities
- **zod**: ^4.4.3 - TypeScript-first schema validation with static type inference
- **dotenv**: ^17.4.2 - Loads environment variables from .env file
- **cors**: ^2.8.6 - Express middleware for enabling CORS (used in current backend)
- **express**: ^5.2.1 - Fast, unopinionated, minimalist web framework (current backend)
- **serverless-http**: ^4.0.0 - Wrapper for deploying Express servers to serverless platforms
- **globals**: ^17.7.0 - Global identifiers from different JavaScript environments
- **input-otp**: ^1.4.2 - OTP input component

### Development Dependencies
- **@types/react**: ^18.3.23 - TypeScript definitions for React
- **@types/react-dom**: ^18.3.7 - TypeScript definitions for React DOM
- **@types/node**: ^26.1.1 - TypeScript definitions for Node.js
- **@types/express**: ^5.0.6 - TypeScript definitions for Express
- **@types/cors**: ^2.8.19 - TypeScript definitions for CORS
- **@swc/core**: ^1.15.46 - Super-fast TypeScript/JavaScript compiler
- **prettier**: ^3.9.6 - Opinionated code formatter
- **@tailwindcss/postcss**: ^4.3.3 - Tailwind CSS as PostCSS plugin
- **@tailwindcss/typography**: ^0.5.20 - Tailwind CSS plugin for typography

### Package Management
- **packageManager**: pnpm@10.14.0+sha512.ad27a79641b49c3e481a16a805baa71817a04bbe06a38d17e60e2eaee83f6a146c6a688125f5792e48dd5ba30e7da52a5cda4c3992b9ccf333f9ce223af84748
- **pkg**: Configuration for packaging the application with pkg

## Planned Backend Dependencies (FastAPI + PostgreSQL)
*Note: These are planned dependencies reflecting the user's preference for FastAPI and PostgreSQL*

### Core Framework
- **fastapi**: ^0.110.0 - Modern, fast (high-performance) web framework for building APIs
- **uvicorn**: ^0.29.0 - ASGI server for running FastAPI applications

### Database
- **sqlalchemy**: ^2.0.0 - SQL toolkit and Object-Relational Mapping library
- **alembic**: ^1.13.0 - Database migration tool for SQLAlchemy
- **asyncpg**: ^0.29.0 - Asynchronous PostgreSQL client for Python
- **psycopg2-binary**: ^2.9.0 - PostgreSQL adapter for Python (sync version)

### Validation & Serialization
- **pydantic**: ^2.5.0 - Data validation and settings management using Python type annotations
- **pydantic-settings**: ^2.1.0 - Settings management using Pydantic

### Authentication & Security
- **python-jose**: ^3.3.0 - JavaScript Object Signing and Encryption (JWT) implementation
- **passlib**: ^1.7.4 - Password hashing library
- **python-multipart**: ^0.0.9 - Parsing multipart/form-data for file uploads

### Environment & Configuration
- **python-dotenv**: ^1.0.0 - Loads environment variables from .env file

### API Utilities
- **httpx**: ^0.25.0 - Next-generation HTTP client for Python (sync and async)
- **requests**: ^2.31.0 - Simple, yet elegant HTTP library

### Machine Learning
- **tensorflow**: ^2.15.0 - End-to-end open source machine learning platform
- **keras**: ^3.5.0 - Deep learning API (part of TensorFlow 2.x)
- **numpy**: ^1.26.0 - Fundamental package for scientific computing
- **Pillow**: ^10.1.0 - Python Imaging Library for image processing

### Development Dependencies
- **pytest**: ^8.0.0 - Testing framework
- **pytest-asyncio**: ^0.23.0 - Pytest support for asyncio
- **black**: ^24.1.0 - Code formatter
- **flake8**: ^7.0.0 - Style guide enforcement
- **mypy**: ^1.8.0 - Static type checker
- **isort**: ^5.13.0 - Import sorting utility

## Machine Learning Dependencies
Based on the model files in `ml/models/classification/`:
- **tensorflow**: Version compatible with Keras .keras format (2.x)
- **keras**: High-level neural networks API
- **numpy**: Numerical computing library
- **Pillow/PIL**: Python Imaging Library (used for image processing)

## Development & DevOps Tools

### Code Quality
- **eslint**: JavaScript/TypeScript linter (frontend)
- **@typescript-eslint/parser**: TypeScript parser for ESLint
- **@typescript-eslint/eslint-plugin**: TypeScript-specific ESLint rules
- **prettier**: Code formatter
- **black**: Python code formatter
- **flake8**: Python style guide enforcement
- **mypy**: Python static type checker

### Testing
- **vitest**: Frontend unit testing
- **pytest**: Backend unit testing
- **happy-dom**: DOM implementation for Vitest
- **msw**: Mock Service Worker for API mocking (frontend)
- **pytest-asyncio**: Async testing for backend

### Docker/Containerization
- **docker**: Container platform
- **docker-compose**: Multi-container Docker applications

### Deployment
- **netlify**: Platform for frontend deployment
- **AWS/GCP/Azure**: Planned for backend/ML services (TBD)
- **terraform**: Infrastructure as Code (planned)

## Dependency Analysis

### Bundle Size Considerations
The frontend has a substantial number of UI component dependencies (@radix-ui/*) which provides high-quality, accessible components but increases bundle size. Tree-shaking helps mitigate this.

### Type Safety
Heavy reliance on TypeScript and Zod for frontend validation with static type inference, and Pydantic for backend validation provides excellent type safety across the application.

### State Management
React Query provides excellent server state management with automatic caching, background updates, and deduplication.

### UI Library Choice
Using Radix UI primitives gives maximal control over styling and behavior while ensuring accessibility, paired with Tailwind CSS for rapid UI development.

### Backend Framework Choice
FastAPI provides:
- High performance (comparable to NodeJS/Go)
- Automatic API documentation (Swagger UI, ReDoc)
- Data validation with Pydantic
- Async support built-in
- Excellent developer experience
- Based on Starlette and Pydantic

### Database Choice
PostgreSQL provides:
- Robust, open-source relational database
- Excellent performance and reliability
- Rich feature set (JSONB, GIS, full-text search)
- Strong community and ecosystem
- Good fit for relational data (users, plants, scans)

### ML Framework Choice
TensorFlow/Keras provides industry-standard tools for deep learning with good community support and deployment options.

## Missing Dependencies (Planned Features)
For planned features not yet implemented, these dependencies would likely be needed:

### Payment Processing (if offering premium features)
- **stripe**: For payment processing

### Analytics
- **posthog-js**: For product analytics (frontend)
- **postgresqldb**: For backend analytics queries

### Internationalization
- **react-i18next**: For internationalization framework (frontend)
- **python-i18n**: For backend internationalization

### Monitoring & Error Tracking
- **sentry**: For error tracking and performance monitoring
- **prometheus-client**: For metrics exposure

## Dependency Management Practices

### Version Pinning
Dependencies use semantic versioning ranges appropriate for each ecosystem.

### Lockfiles
- **package-lock.json** / **pnpm-lock.yaml**: Frontend lockfiles
- **requirements.txt** or **poetry.lock** / **Pipfile.lock**: Planned backend lockfiles

### Security
Regular dependency scanning should be implemented using:
- **npm audit** / **pnpm audit** for frontend
- **pip-audit** or **safety** for backend
- **Dependabot** or similar for automated updates

## Related Documents
- [ARCHITECTURE.md](01_ARCHITECTURE.md) - System architecture
- [API_CONTRACTS.md](05_API_CONTRACTS.md) - Backend API endpoints (to be updated for FastAPI)
- [MODEL_REGISTRY.md](04_MODEL_REGISTRY.md) - ML model details
- [FRONTEND_GRAPH.md](08_FRONTEND_GRAPH.md) - Frontend component structure

## Notes on Current vs. Planned Backend
The current backend in `frontend/server/` uses Express.js, but as per user preference, the planned backend will migrate to FastAPI with PostgreSQL. This document reflects the planned dependencies for the future backend stack.