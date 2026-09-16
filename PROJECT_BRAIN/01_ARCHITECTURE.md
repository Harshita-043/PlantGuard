# PlantGuard AI Architecture

## High-Level Architecture
PlantGuard AI follows a service-oriented architecture with clean separation of concerns:
1. **Frontend (Client)**: React/Vite application for user interface
2. **Backend (Server)**: FastAPI API server with isolated ML service layer
3. **Machine Learning Services**: Isolated service interfaces for ML components (to be implemented independently)

## Component Diagram
```
+------------------+     +------------------+     +---------------------+
|   Frontend App   |<--->|   API Server     |<--->|   ML Service Layer  |
|  (React/Vite)    |     |  (FastAPI)       |     |  (Isolated Services)|
+------------------+     +------------------+     +---------------------+
        ^                         ^                         ^
        |                         |                         |
        |        HTTP/JSON        |        HTTP/JSON        |
        |                         |                         |
+------------------+     +------------------+     +---------------------+
|   Web Browser    |     |   Server (VPS)   |     |   ML Inference    |
|                  |     |                  |     |   Infrastructure  |
+------------------+     +------------------+     +---------------------+
```

## Technology Stack

### Frontend
- **Framework**: React 18.3.1
- **Build Tool**: Vite 8.1.5
- **Styling**: Tailwind CSS 4.3.3
- **UI Components**: Radix UI primitives
- **State Management**: React Query (tanstack/query) 5.101.4
- **Forms**: React Hook Form 7.82.0
- **Routing**: React Router DOM 6.30.1
- **Charts**: Recharts 3.10.0
- **Animations**: Framer Motion 12.42.2
- **Icons**: Lucide React
- **TypeScript**: 7.0.2

### Backend
- **Runtime**: Node.js (via tsx)
- **Framework**: Express.js 5.2.1
- **Middleware**: CORS, body parsing
- **Environment**: dotenv 17.4.2
- **Validation**: Zod 4.4.3

### Machine Learning
- **Framework**: TensorFlow/Keras
- **Model Architecture**: EfficientNetV2-B0
- **Task**: Image classification (38 plant disease classes)
- **Input Size**: 224x224 RGB images
- **Pretrained Weights**: ImageNet
- **Fine-tuning**: Yes (on PlantVillage dataset)

### Development & DevOps
- **Package Manager**: pnpm 10.14.0
- **Linting/Formatting**: Prettier 3.9.6
- **Testing**: Vitest 4.1.10
- **Type Checking**: TypeScript tsc
- **Containerization**: Docker (via .dockerignore and implied Dockerfile)
- **Deployment**: Netlify (via netlify.toml)

## Data Flow

### User Interaction Flow
1. User interacts with frontend (e.g., uploads plant image)
2. Frontend sends image to backend API endpoint
3. Backend receives image and forwards to ML inference service
4. ML service processes image and returns prediction
5. Backend formats response and sends to frontend
6. Frontend displays results to user

### Current State (Audit Finding)
- **Missing Component**: ML inference service/API endpoint
- **Current Backend**: Only has `/api/ping` and `/api/demo` endpoints
- **Missing Integration**: No connection between frontend/backend and ML model

## Deployment Architecture
- **Frontend**: Built as static SPA, deployed to Netlify CDN
- **Backend**: Deployed as Node.js server (likely on same infrastructure as frontend via Netlify Functions or separate service)
- **ML Model**: Currently stored as Keras `.keras` files; needs serving infrastructure

## Security Considerations
- **CORS**: Configured to allow frontend origins
- **Input Validation**: Uses Zod for API validation (in shared/api.ts)
- **Environment Variables**: Managed via dotenv
- **Missing**: Authentication, rate limiting, image validation

## Scalability Considerations
- **Frontend**: CDN-cached static assets
- **Backend**: Horizontal scaling possible with stateless Express.js
- **ML Inference**: Requires GPU acceleration for real-time predictions; current model size allows CPU inference but may be slow

## Known Gaps
1. No ML serving infrastructure
2. Missing API endpoints for plant scanning
3. No authentication/authorization system
4. No persistent storage for user data/plants
5. No MLOps pipeline for model retraining