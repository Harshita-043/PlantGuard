# PlantGuard AI Technical Decisions

## Overview
This document records significant technical decisions made during the development of PlantGuard AI, including the rationale, alternatives considered, and implications. Note that some decisions have been updated to reflect the user's preference for FastAPI and PostgreSQL backend.

## Decision 1: Frontend Framework - React with Vite
**Decision**: Use React 18 with Vite as the frontend framework and build tool.

**Rationale**:
- React provides a mature ecosystem with excellent community support
- Component-based architecture aligns well with the UI-intensive nature of the application
- Vite offers fast development server startup and hot module replacement
- React 18 includes automatic batching and concurrent rendering features
- Strong TypeScript support with excellent type definitions

**Alternatives Considered**:
- **Vue 3**: Good performance but smaller ecosystem for complex enterprise features
- **Svelte/SvelteKit**: Excellent performance but less mature tooling and fewer component libraries
- **Angular**: Opinionated framework with built-in solutions but steeper learning curve
- **Next.js**: Would require Node.js server for SSR, adding complexity for a primarily SPA app

**Implications**:
- Access to vast ecosystem of UI libraries and tools
- Need to manage state effectively (solved with React Query)
- Learning curve for team members new to React hooks
- Bundle size considerations requiring code splitting and optimization

## Decision 2: UI Component Library - Radix UI + Tailwind CSS
**Decision**: Use Radix UI primitive components styled with Tailwind CSS.

**Rationale**:
- Radix UI provides unstyled, accessible components that ensure WCAG compliance
- Tailwind CSS enables rapid UI development with utility-first approach
- Combination gives full control over design while maintaining accessibility
- No CSS-in-JS runtime overhead
- Easy to customize and theme

**Alternatives Considered**:
- **Material-UI (MUI)**: Comprehensive component library but heavier bundle and opinionated design
- **Ant Design**: Enterprise-focused but bundle size concerns and design constraints
- **Chakra UI**: Good developer experience but less flexible than Radix primitives
- **Headless UI**: Similar to Radix but smaller component selection
- **CSS Frameworks (Bootstrap, Bulma)**: Less flexible for custom designs

**Implications**:
- Need to build custom components from primitives (more initial work)
- Excellent accessibility foundation
- Consistent design system possible with Tailwind configuration
- Smaller bundle size with tree-shaking compared to comprehensive libraries

## Decision 3: State Management - React Query
**Decision**: Use React Query (tanstack/query) for server state management.

**Rationale**:
- Excellent caching, background updates, and stale-while-revalidate patterns
- Automatic deduplication of similar requests
- Built-in loading and error states
- Optimistic updates for mutations
- Devtools for debugging
- Excellent documentation and community support

**Alternatives Considered**:
- **Redux Toolkit**: More boilerplate but predictable state updates
- **Zustand**: Minimalist approach but lacks built-in caching and background updates
- **Recoil**: Experimental at time of decision, uncertain future
- **Jotai**: Similar to Zustand, minimal but missing advanced features
- **Context API + useState**: Would require manual implementation of caching and updating

**Implications**:
- Learning curve for React Query specific patterns
- Need to properly configure query keys and invalidation
- Excellent developer experience for data fetching
- Reduced boilerplate compared to Redux-style solutions

## Decision 4: Backend Framework - FastAPI (Updated per user preference)
**Decision**: Use FastAPI for the backend API server (changed from Express.js per user request).

**Rationale**:
- High performance (comparable to NodeJS/Go) - important for ML inference serving
- Automatic API documentation (Swagger UI, ReDoc) - reduces documentation overhead
- Built-in data validation with Pydantic - ensures data integrity
- Native async support - efficient for I/O operations
- Excellent developer experience and community
- Based on Starlette and Pydantic - solid foundations
- Easy to deploy and containerize

**Alternatives Considered**:
- **Express.js**: Current implementation but less performant for ML-heavy applications
- **NestJS**: Opinionated framework with TypeScript support but more complex
- **Flask**: Simpler but lacks built-in async and advanced features
- **Falcon**: High-performance but minimalist approach
- **APIStar**: Interesting but smaller ecosystem

**Implications**:
- Need to learn FastAPI patterns (but similar to Express in many ways)
- Automatic API documentation reduces documentation burden
- Pydantic validation provides excellent data validation
- Async/await pattern for better concurrency
- Easy migration path from current Express.js implementation
- Excellent performance for ML model serving endpoints

## Decision 5: Database - PostgreSQL (Updated per user preference)
**Decision**: Use PostgreSQL as the primary database (changed from planned SQLite/other per user request).

**Rationale**:
- Robust, open-source relational database with excellent performance
- Rich feature set including JSONB for flexible schema needs
- Strong community and extensive documentation
- Excellent support for geospatial data (if needed for location features)
- ACID compliance for data integrity
- Good fit for relational data model (users, plants, scans, etc.)
- Horizontal scaling options available
- Widely used in production applications

**Alternatives Considered**:
- **SQLite**: Simpler but not suitable for concurrent production use
- **MongoDB**: Document-based but less ideal for relational data
- **MySQL**: Good alternative but PostgreSQL has more advanced features
- **Firebase Firestore**: Managed service but potential vendor lock-in and cost
- **Supabase**: Built on PostgreSQL but adds abstraction layer

**Implications**:
- Need to learn PostgreSQL administration and optimization
- Will require setting up connection pooling
- Need to design proper schema with relationships
- Migration scripts will be needed for schema changes
- Excellent tooling available (pgAdmin, psql, etc.)
- Strong foundation for application growth

## Decision 6: Validation - Pydantic (Backend) + Zod (Frontend)
**Decision**: Use Pydantic for backend data validation and Zod for frontend validation.

**Rationale**:
- Pydantic integrates deeply with FastAPI for automatic validation and documentation
- Zod provides excellent TypeScript integration for frontend validation
- Both use schema-based validation with excellent developer experience
- Pydantic models can be shared between backend and frontend via code generation
- Excellent error messages and customization options
- Can generate JSON Schema for API documentation

**Alternatives Considered**:
- **Marshmallow**: Popular but less integrated with FastAPI
- **Validators**: Simple but lacks advanced features
- **WTForms**: More for traditional web forms than APIs
- **Joi** (frontend): Good but Zod has better TypeScript integration
- **Yup** (frontend): Good but被 superseded by Zod in many projects

**Implications**:
- Consistent validation approach across frontend and backend
- Automatic API documentation from Pydantic models
- Type safety from schema inference in both ecosystems
- Need to define schemas for all API endpoints
- Potential for model sharing between frontend and backend
- Excellent developer experience with helpful error messages

## Decision 7: Styling Approach - Tailwind CSS
**Decision**: Use Tailwind CSS for styling.

**Rationale**:
- Utility-first approach speeds up development
- No need to context-switch between HTML and CSS files
- Excellent responsiveness with built-in breakpoints
- Easy to maintain and refactor
- PurgeCSS removes unused styles for minimal production CSS
- Consistent design through constraint-based utility classes

**Alternatives Considered**:
- **CSS Modules**: Scoped CSS but requires context switching
- **Styled Components**: CSS-in-JS with runtime overhead
- **Emotion**: Similar to Styled Components
- **Traditional CSS/Sass**: More flexible but prone to inconsistencies
- **CSS Framework (Bootstrap)**: Less customizable but faster initial development

**Implications**:
- Learning curve for utility-first mindset
- Need to establish naming conventions for complex components
- Excellent for rapid prototyping and iteration
- Potential for lengthy class names requiring careful formatting

## Decision 8: Icons - Lucide React
**Decision**: Use Lucide React for icons.

**Rationale**:
- Beautiful, consistent icon set
- Tree-shakeable imports (only use what you import)
- MIT license (permissive)
- Regular updates with new icons
- Simple SVG-based implementation
- Good balance of familiarity and uniqueness

**Alternatives Considered**:
- **Font Awesome**: Icon font approach (less performant than SVG)
- **Material Icons**: Google's icon set but licensing considerations
- **Heroicons**: Excellent but smaller selection than Lucide
- **Tabler Icons**: Good alternative but less popular
- **Custom SVG Icons**: Would require building and maintaining icon library

**Implications**:
- Consistent visual language across the application
- Easy to replace icons if needed
- Small bundle impact with tree-shaking
- Accessible by default (SVG with proper aria attributes)

## Decision 9: Animations - Framer Motion
**Decision**: Use Framer Motion for animations.

**Rationale**:
- Declarative animation API that feels natural in React
- Excellent performance with layout animations
- Gesture recognition capabilities
- Variants for complex animation sequences
- Server-side rendering compatibility
- Good documentation and examples

**Alternatives Considered**:
- **React Spring**: Physics-based animations but steeper learning curve
- **CSS Transitions/Animations**: Limited for complex interactions
- **GSAP**: Powerful but not React-specific, more imperative
- **React Move**: Data-driven animations but smaller community
- **No animations**: Simpler but less engaging user experience

**Implications**:
- Bundle size cost for animation library
- Need to use judiciously to avoid performance issues
- Excellent for micro-interactions and transitions
- Gesture capabilities enable advanced interactions

## Decision 10: Charts - Recharts
**Decision**: Use Recharts for data visualization.

**Rationale**:
- Built specifically for React with declarative API
- Combines React components with D3 underneath
- Good balance of customization and ease of use
- Responsive containers available
- Active maintenance and community
- Accessible by default with proper labeling

**Alternatives Considered**:
- **D3.js**: Most flexible but steep learning curve and manual DOM manipulation
- **Victory**: Formidable but API can be inconsistent
- **Chart.js**: Simple but less React-native feel
- **Visx**: Airbnb's library, low-level but powerful
- **Plotly.js**: Excellent for scientific charts but heavier bundle

**Implications**:
- Good for standard chart types (line, bar, pie, etc.)
- Limited for highly custom or complex visualizations
- Easy to implement common data visualization needs
- Responsive behavior built-in

## Decision 11: Forms - React Hook Form
**Decision**: Use React Hook Form for form management.

**Rationale**:
- Minimal re-renders (only updates when fields change)
- Built-in validation support
- Excellent performance
- Small bundle size
- Easy integration with UI libraries
- Excellent TypeScript support

**Alternatives Considered**:
- **Formik**: More features but more re-renders and larger bundle
- **Redux Form**: Ties form state to Redux (overkill for most cases)
- **Uncontrolled components**: Manual management, error-prone
- **Controlled components**: Simple but causes re-renders on every keystroke
- **React Final Form**: Similar to RHF but less popular

**Implications**:
- Excellent form performance
- Need to learn RHF specific patterns (useFieldArray, etc.)
- Easy to integrate with Zod validation via @hookform/resolvers
- Good developer experience with minimal boilerplate

## Decision 12: Date Handling - date-fns
**Decision**: Use date-fns for date manipulation and formatting.

**Rationale**:
- Immutable and pure functions
- Tree-shakeable (only import what you need)
- Comprehensive functionality
- Excellent TypeScript support
- No mutable Date objects issues
- Locale support for internationalization

**Alternatives Considered**:
- **Moment.js**: Comprehensive but massive bundle size and mutable
- **Luxon**: Modern alternative to Moment but still larger than date-fns
- **Dayjs**: Moment-like API but much smaller
- **Native Date object**: Error-prone and lacking functionality
- **date-fns-tz**: For timezone-specific functionality (when needed)

**Implications**:
- Consistent date handling across application
- Need to be mindful of immutability patterns
- Excellent for formatting, parsing, and manipulating dates
- Tree-shaking keeps bundle impact minimal

## Decision 13: Deployment Platform - Netlify (Frontend) + TBD (Backend/ML)
**Decision**: Use Netlify for frontend deployment. Backend and ML services deployment TBD (likely AWS/GCP/Azure or similar).

**Rationale for Netlify**:
- Excellent for static sites and serverless functions
- Continuous deployment from Git repositories
- Built-in CDN for global distribution
- Easy domain management and SSL
- Serverless functions for backend API (can migrate later)
- Generous free tier
- Excellent CLI and API for automation

**Alternatives Considered**:
- **Vercel**: Similar to Netlify but slightly different feature set
- **AWS Amplify**: More complex but deeper AWS integration
- **Firebase Hosting**: Good for Firebase ecosystem but limited backend
- **Traditional VPS/Server**: More control but more operational overhead
- **GitHub Pages**: Free but limited to static sites only

**Implications**:
- Easy to deploy frontend and backend (as serverless functions initially)
- Need to understand Netlify's serverless function limitations
- Great for rapid iteration and preview deployments
- Potential vendor lock-in considerations for complex applications
- Will need to plan migration to dedicated backend services as scale increases

## Decision 14: Package Manager - pnpm
**Decision**: Use pnpm as the package manager.

**Rationale**:
- Faster installation times
- Disk space efficient through content-addressable storage
- Strict dependency prevention (won't allow access to undeclared dependencies)
- Monorepo ready
- Compatible with npm ecosystem
- Excellent workspace support

**Alternatives Considered**:
- **npm**: Default but slower and less efficient
- **Yarn**: Good performance but pnpm has advantages in efficiency
- **Yarn Berry (v2+)**: Plug'n'play but compatibility issues
- **Bun**: Newer but less proven ecosystem

**Implications**:
- Faster CI/CD builds
- Less disk space usage
- Need to ensure team members use pnpm
- Potential issues with tools expecting npm/yarn lockfiles
- Excellent for future monorepo expansion

## Decision 15: ML Framework - TensorFlow/Keras
**Decision**: Use TensorFlow/Keras for the machine learning model.

**Rationale**:
- Industry standard for deep learning
- Excellent documentation and community support
- Keras provides high-level API for rapid prototyping
- TensorFlow provides scalability and production tools
- Multiple deployment options (TensorFlow Serving, TensorFlow Lite, TensorFlow.js)
- Good integration with Python scientific stack

**Alternatives Considered**:
- **PyTorch**: Popular in research but less production-focused tooling
- **Scikit-learn**: Excellent for traditional ML but not deep learning
- **MXNet**: Good performance but smaller community
- **CNTK**: Microsoft's toolkit but less community adoption
- **JAX**: Cutting-edge but newer and less production-ready

**Implications**:
- Access to vast ecosystem of ML tools and resources
- Need to manage Python environment and dependencies
- Model serving infrastructure required for production
- Good path for optimization and deployment options
- Steeper learning curve for deep learning concepts

## Decision 16: Model Architecture - EfficientNetV2-B0
**Decision**: Use EfficientNetV2-B0 as the base model architecture.

**Rationale**:
- Excellent accuracy-to-efficiency ratio
- State-of-the-art performance for image classification
- Built-in preprocessing optimized for ImageNet pretraining
- Good balance of accuracy and model size
- Efficient training and inference
- Well-studied architecture with known characteristics

**Alternatives Considered**:
- **EfficientNet-B0**: Older version, less efficient than V2
- **MobileNetV2/3**: Very efficient but lower accuracy ceiling
- **ResNet50**: Classic architecture but heavier than needed
- **Vision Transformers (ViT)**: State-of-the-art but heavier and data-hungry
- **EfficientNetV2-Larger**: Better accuracy but significantly larger model
- **Custom CNN**: Would require significant expertise and data

**Implications**:
- Good trade-off for mobile/web deployment
- Model size suitable for download and caching
- Transfer learning approach reduces training data needs
- Established architecture with known performance characteristics
- Potential to upgrade to larger EfficientNetV2 variants if accuracy needed

## Decision 17: Dataset - PlantVillage
**Decision**: Use the PlantVillage dataset for training and validation.

**Rationale**:
- Specifically designed for plant disease classification
- Large, diverse dataset with multiple plant species and diseases
- Expert-labeled images ensuring quality
- Publicly available and free to use
- Well-studied in plant pathology literature
- Includes healthy examples for each plant species

**Alternatives Considered**:
- **PlantDoc**: Smaller dataset with different imaging conditions
- **Custom collected data**: Would require significant effort to match quality/scale
- **Agricultural extension databases**: Often not public or image-based
- **Research paper datasets**: Often specialized to specific diseases/plants
- **Synthetic data generation**: Would require validation against real-world performance

**Implications**:
- Model will be strong on diseases well-represented in PlantVillage
- Potential geographic or imaging condition biases
- Need to evaluate performance on local/regional variants
- Excellent foundation for transfer learning with additional data
- Benchmarkable against existing research using same dataset

## Decision 18: Image Processing Approach
**Decision**: Use EfficientNetV2 built-in preprocessing for image inputs.

**Rationale**:
- Matches exactly what the model was trained on
- No need to implement custom normalization
- Consistent with TensorFlow/Keras applications
- Well-documented and tested approach
- Minimal code required for implementation

**Alternatives Considered**:
- **Simple rescaling (0-1)**: Would require retraining or fine-tuning
- **Standardization (mean=0, std=1)**: Common but not optimal for this architecture
- **Custom preprocessing per plant type**: Overly complex without clear benefit
- **Histogram equalization**: May help in some cases but adds complexity
- **No preprocessing**: Would significantly reduce model accuracy

**Implications**:
- Ensures consistency between training and inference
- Requires implementing the specific preprocessing steps
- Need to resize images to 224x224 before preprocessing
- Standard approach that other developers will recognize
- Easy to verify correctness against training code

## Decision 19: Confidence Thresholding
**Decision**: Implement confidence thresholding for model predictions.

**Rationale**:
- Prevents overconfident predictions on uncertain inputs
- Allows for "unknown" or "needs review" categories
- Improves user trust by acknowledging model limitations
- Enables escalation to human experts when confidence low
- Standard practice in ML applications for safety

**Alternatives Considered**:
- **Always show top prediction**: Simpler but potentially misleading
- **Show all predictions**: Overwhelming for users without medical context
- **Dynamic threshold based on entropy**: More complex but potentially better
- **Use model uncertainty techniques (MC dropout)**: More accurate but computationally expensive
- **No thresholding**: Simplest but risks overconfidence in wrong predictions

**Implications**:
- Need to determine appropriate threshold values through validation
- May require additional UI states for uncertain results
- Improves safety and reliability of the application
- Standard practice that users may expect in medical/agricultural AI
- Provides clear path for expert consultation when needed

## Decision 20: API Design - RESTful with JSON
**Decision**: Use RESTful API design with JSON request/response bodies.

**Rationale**:
- Widely understood and easy to consume
- Excellent tooling support (Postman, Swagger/OpenAPI, etc.)
- Stateless nature simplifies scaling and caching
- Human-readable and easy to debug
- Flexible enough for most application needs
- Industry standard for web APIs
- FastAPI provides automatic OpenAPI documentation

**Alternatives Considered**:
- **GraphQL**: Flexible querying but more complex caching and security considerations
- **gRPC**: Highly performant but requires protobuf and less browser-friendly
- **WebSocket**: Real-time bidirectional but overkill for request-response patterns
- **REST/HATEOAS**: More discoverable but adds complexity
- **JSON-RPC**: Simple but less flexible than REST

**Implications**:
- Easy for frontend developers to consume and test
- Well-understood patterns for API versioning and evolution
- Good caching behavior with proper headers
- Extensive documentation and best practices available
- Standard approach that reduces integration friction
- Automatic Swagger/OpenAPI docs from FastAPI reduce documentation burden

## Decision 21: Authentication Approach
**Decision**: Plan to implement JWT-based authentication.

**Rationale**:
- Stateless and scalable
- Works well with SPA architectures
- Easy to implement and understand
- Token can contain user information and permissions
- Standard approach with many libraries and best practices
- Works well with serverless architectures
- Integrates well with FastAPI security utilities

**Alternatives Considered**:
- **Session-based authentication**: Requires server-side storage, less scalable
- **OAuth 2.0**: Overkill for first-party applications but good for third-party access
- **API keys**: Simpler but less secure for user authentication
- **Magic links/Passwordless**: Good UX but requires email infrastructure
- **Third-party auth (Auth0, Firebase Auth)**: Feature-rich but adds dependency and cost

**Implications**:
- Need to implement secure token storage (httpOnly cookies or secure localStorage)
- Requires refreshing tokens and handling expiration
- Need to implement role-based access control (RBAC) if needed
- Standard approach with plenty of examples and libraries
- Good balance of security and usability for application type
- FastAPI has excellent security utilities for OAuth2/JWT

## Decision 22: Error Handling Approach
**Decision**: Implement centralized error handling with consistent error response format.

**Rationale**:
- Consistent API contract for error handling
- Easier for frontend to handle errors uniformly
- Prevents leaking internal implementation details
- Enables logging and monitoring of errors
- Standard practice for professional APIs
- FastAPI provides excellent exception handling capabilities

**Alternatives Considered**:
- **Let errors bubble up as HTTP status codes**: Less informative for clients
- **Different error formats per endpoint**: Inconsistent and harder to handle
- **No error handling**: Would crash server on unexpected conditions
- **Only log errors without client response**: Unhelpful for users
- **Return detailed stack traces**: Security risk and information leakage

**Implications**:
- Need to implement error handling middleware
- Define standard error response format
- Ensure all endpoints use the error handling mechanism
- Log errors appropriately for monitoring
- Return helpful but secure error messages to clients
- FastAPI makes this easy with exception handlers

## Decisions Yet to Be Made

### 1. ORM/Database Access Method
**Pending Decision**: Select ORM or database access method for PostgreSQL.
- Options: SQLAlchemy (Core or ORM), Tortoise ORM, Prisma (via query engine), raw asyncpg
- Factors: Team expertise, performance needs, migration capabilities, async support

### 2. Image Storage Solution
**Pending Decision**: Choose where to store uploaded plant images.
- Options: Cloud storage (AWS S3, Google Cloud Storage), PostgreSQL LOB/ByteA, traditional file storage
- Factors: Cost, scalability, backup needs, serving performance, security

### 3. ML Serving Infrastructure
**Pending Decision**: Determine how to serve the ML model for inference.
- Options: TensorFlow Serving, TensorFlow.js, TorchServe, custom FastAPI endpoints
- Factors: Latency requirements, batching needs, hardware availability, team expertise, GPU access

### 4. Internationalization Strategy
**Pending Decision**: Plan for multi-language support.
- Options: React-i18next (frontend), Python i18n libraries (backend), custom solution
- Factors: Target languages, translation workflow, RTL support, maintenance overhead

### 5. Monitoring and Observability
**Pending Decision**: Implement logging, metrics, and tracing.
- Options: ELK stack, Prometheus/Grafana, Datadog, Loki, custom solution
- Factors: Cost, complexity, alerting needs, team expertise, scale requirements

### 6. CI/CD Pipeline
**Pending Decision**: Set up automated testing and deployment.
- Options: GitHub Actions, GitLab CI, Jenkins, CircleCI, Netlify Build Plugins
- Factors: Team familiarity, integration needs, cost, testing requirements, deployment frequency

### 7. Testing Strategy
**Pending Decision**: Define comprehensive testing approach.
- Options: Unit testing (Vitest/pytest), integration testing, end-to-end testing (Playwright/Cypress)
- Factors: Coverage goals, test maintenance, CI time, testing pyramid principles, QA resources

## Related Documents
- [ARCHITECTURE.md](01_ARCHITECTURE.md) - System architecture overview
- [API_CONTRACTS.md](05_API_CONTRACTS.md) - Detailed API endpoint specifications (to be updated for FastAPI)
- [MODEL_REGISTRY.md](04_MODEL_REGISTRY.md) - ML model details and versioning
- [FRONTEND_GRAPH.md](08_FRONTEND_GRAPH.md) - Frontend component architecture
- [AGENT_GRAPH.md](07_AGENT_GRAPH.md) - Planned AI agent system
- [DEPENDENCIES.md](09_DEPENDENCIES.md) - Complete dependency listing