# PlantGuard AI Project Dependency Graph

## Overview
This document illustrates the high-level dependencies and relationships between major components of the PlantGuard AI system.

## Component Dependency Graph
```
+------------------+     +------------------+     +---------------------+
|   Frontend App   |<--->|   API Server     |<--->|   ML Model Service  |
|  (React/Vite)    |     |  (Express.js)    |     |  (TensorFlow Serving)|
+------------------+     +------------------+     +---------------------+
        ^                         ^                         ^
        |                         |                         |
        |        HTTP/JSON        |        gRPC/REST        |
        |                         |                         |
+------------------+     +------------------+     +---------------------+
|   Web Browser    |     |   Server (VPS)   |     |   ML Inference    |
|                  |     |                  |     |   Infrastructure  |
+------------------+     +------------------+     +---------------------+
        ^                         ^                         ^
        |                         |                         |
        |                         |                         |
+------------------+     +------------------+     +---------------------+
|   CDN (Netlify)  |     |   Database       |     |   Model Storage   |
|                  |     |  (PostgreSQL)    |     |  (Git/LFS/S3)     |
+------------------+     +------------------+     +---------------------+
```

## Detailed Dependency Breakdown

### 1. Frontend Dependencies
**Depends On**:
- **API Server**: For all data operations (plants, scans, recommendations, etc.)
- **ML Model Service**: Indirectly via API for scan functionality
- **Authentication Service**: For user login and session management (planned)
- **File Storage**: For storing and retrieving plant images (planned)

**Internal Dependencies**:
- React 18.3.1 (UI rendering)
- Vite 8.1.5 (build system)
- TypeScript 7.0.2 (type safety)
- Tailwind CSS 4.3.3 (styling)
- Radix UI primitives (accessible components)
- React Query 5.101.4 (state management)
- React Hook Form 7.82.0 (form handling)
- Framer Motion 12.42.2 (animations)
- Recharts 3.10.0 (data visualization)
- Lucide React (icons)
- date-fns (date handling)
- Zod 4.4.3 (validation)

### 2. Backend API Server Dependencies
**Depends On**:
- **Database**: For persistent storage of users, plants, scans, etc.
- **ML Model Service**: For plant disease classification
- **File Storage**: For storing uploaded plant images
- **Weather API**: For weather insights (planned)
- **Notification Service**: For alerts and reminders (planned)
- **RAG Service**: For AI assistant knowledge retrieval (planned)
- **Agent System**: For automated workflows (planned)

**Internal Dependencies**:
- Express.js 5.2.1 (web framework)
- CORS middleware (cross-origin requests)
- dotenv (environment variables)
- Zod 4.4.3 (request validation)
- PostgreSQL driver (planned)
- JWT library (planned for authentication)
- Multer or similar (planned for file uploads)
- TensorFlow.js or Python client (planned for ML inference)

### 3. ML Model Service Dependencies
**Depends On**:
- **Model Storage**: For loading trained model artifacts
- **Hardware Acceleration**: GPU/CPU for inference performance
- **Preprocessing Services**: For image preparation
- **Monitoring Service**: For performance tracking and drift detection

**Internal Dependencies**:
- TensorFlow/Keras (ML framework)
- NumPy (numerical computing)
- Pillow/PIL (image processing)
- TensorFlow Serving or equivalent (inference server)
- Model metadata and class names
- Preprocessing pipelines matching training

### 4. Database Dependencies
**Depends On**:
- **Infrastructure**: Server/storage for database hosting
- **Backup Systems**: For data durability and disaster recovery
- **Monitoring**: For performance and health tracking

**Internal Dependencies**:
- PostgreSQL (selected RDBMS)
- Connection pooling
- Migration system (Prisma, TypeORM, or similar)
- Indexing strategy for query performance
- Backup and replication configuration

### 5. File Storage Dependencies
**Depends On**:
- **Cloud Storage Provider**: (AWS S3, Google Cloud Storage, etc.)
- **CDN**: For fast image delivery (planned)
- **Security Services**: For malware scanning and access control

**Internal Dependencies**:
- Storage client libraries
- Image processing service (for thumbnails/resizing)
- Security scanning service
- Metadata database (for tracking files)

## Cross-Cutting Concerns Dependencies

### Authentication & Authorization
- **Depends On**: User database, token storage, possibly email service
- **Internal**: JWT library, password hashing, session management
- **Used By**: All components requiring user-specific data

### Monitoring & Logging
- **Depends On**: Storage for logs and metrics, alerting systems
- **Internal**: Logging frameworks, metrics collectors, tracing
- **Used By**: All components for observability

### Configuration & Secrets
- **Depends On**: Secret management service (AWS Secrets Manager, Vault, etc.)
- **Internal**: Configuration loading, validation
- **Used By**: All components for environment-specific settings

### CI/CD Pipeline
- **Depends On**: Source control (Git), container registry, deployment platforms
- **Internal**: Build scripts, test suites, deployment configurations
- **Used By**: All components for release management

## Data Flow Dependencies

### Plant Scan Workflow
```
User Image --> Frontend --> API Server --> Image Storage --> 
Preprocessing --> ML Model --> Inference --> Results --> 
API Server --> Database --> Frontend Display
```

### Plant Management Workflow
```
User Input --> Frontend --> API Server --> Validation --> 
Database --> API Server --> Frontend Update
```

### AI Assistant Workflow
```
User Query --> Frontend --> API Server --> 
RAG Retrieval --> Knowledge Base --> 
LLM Generation --> API Server --> Frontend Response
```

### Agent System Workflow
```
User Request --> Frontend --> API Server --> 
Agent Orchestrator --> 
[Specialized Agents] --> 
[Tools: ML, RAG, Weather, etc.] --> 
Orchestrator --> API Server --> Frontend Response
```

## Deployment Environment Dependencies

### Development
- **Depends On**: Local machine, package managers, development databases
- **Tools**: Vite dev server, Node.js, PostgreSQL local instance

### Testing
- **Depends On**: Test databases, mock services, test runners
- **Tools**: Vitest, Playwright/Cypress, testing databases

### Staging
- **Depends On**: Staging servers, staging databases, monitoring
- **Tools**: CI/CD pipeline, deployment scripts, health checks

### Production
- **Depends On**: Production infrastructure, CDNs, managed services
- **Tools**: Load balancers, auto-scaling, backup systems, CDNs

## Technology Stack Summary

### Frontend
- **Framework**: React 18.3.1
- **Language**: TypeScript 7.0.2
- **Build Tool**: Vite 8.1.5
- **Styling**: Tailwind CSS 4.3.3
- **UI Library**: Radix UI primitives
- **State Management**: React Query 5.101.4
- **Forms**: React Hook Form 7.82.0
- **HTTP Client**: Fetch API (via React Query)
- **Icons**: Lucide React

### Backend
- **Framework**: Express.js 5.2.1
- **Language**: TypeScript/JavaScript (via tsx)
- **Validation**: Zod 4.4.3
- **Environment**: dotenv
- **Middleware**: CORS, body parsing
- **Planned**: PostgreSQL, JWT, file upload, error handling

### Machine Learning
- **Framework**: TensorFlow/Keras
- **Model Architecture**: EfficientNetV2-B0
- **Format**: Keras SavedModel (.keras)
- **Input Size**: 224x224 RGB
- **Classes**: 38 plant disease/health states
- **Planned Serving**: TensorFlow Serving or equivalent

### Infrastructure
- **Deployment**: Netlify (frontend), TBD (backend/ML)
- **Database**: PostgreSQL (planned)
- **File Storage**: Cloud storage (planned)
- **Monitoring**: TBD (planned)
- **CI/CD**: GitHub Actions or similar (planned)

## Critical Path Dependencies
These are dependencies that must be in place for core functionality:

1. **For Basic Plant Scanning**:
   - Frontend → API Server connection
   - API Server → ML Model Service connection
   - ML Model → Model artifacts access
   - Image preprocessing pipeline

2. **For Plant Management**:
   - Frontend → API Server connection
   - API Server → Database connection
   - Database schema for plants/users

3. **For User Experience**:
   - Authentication system
   - Error handling and loading states
   - Responsive design implementation

## Risk Assessment by Dependency

### High Risk (Blocking)
- **ML Model Service**: Without this, scanning cannot work
- **Database**: Without this, no data persistence
- **API-ML Connection**: Without this, no intelligent features

### Medium Risk (Degraded Experience)
- **File Storage**: Without this, no image persistence
- **Authentication**: Without this, no user-specific data
- **Error Handling**: Without this, poor user experience

### Low Risk (Enhancements)
- **Weather API**: Enhances but not core to scanning
- **RAG System**: Enhances AI assistant but not required for basic function
- **Agent System**: Enhances automation but not required for MVP

## Related Documents
- [ARCHITECTURE.md](01_ARCHITECTURE.md) - Detailed architecture
- [API_CONTRACTS.md](05_API_CONTRACTS.md) - API specifications
- [MODEL_REGISTRY.md](04_MODEL_REGISTRY.md) - ML model details
- [FRONTEND_GRAPH.md](08_FRONTEND_GRAPH.md) - Frontend architecture
- [AGENT_GRAPH.md](07_AGENT_GRAPH.md) - Agent system design
- [RAG_GRAPH.md](06_RAG_GRAPH.md) - RAG system design
- [DEPENDENCIES.md](09_DEPENDENCIES.md) - Complete dependency listing