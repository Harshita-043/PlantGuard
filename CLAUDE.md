# PlantGuard AI - CLAUDE.md

This file contains project-specific guidelines and instructions for working with the PlantGuard AI codebase.

## Project Overview
PlantGuard AI is a plant health monitoring application that uses AI to scan and diagnose plant diseases. The application consists of:
- React/Vite frontend with TypeScript
- Express.js backend (planned migration to FastAPI + PostgreSQL)
- TensorFlow/Keras ML model for plant disease classification (38 classes)

## Development Guidelines

### 1. Project Brain
The `PROJECT_BRAIN/` directory is the single source of truth for project documentation. All architectural decisions, API contracts, and technical specifications should be documented there.

### 2. Code Style
- Follow existing code patterns in the codebase
- Use TypeScript strictly - avoid `any` types when possible
- Format code with Prettier (already configured)
- Tailwind CSS utility classes for styling
- Radix UI primitives for accessible components

### 3. Frontend Specific
- React 18 with hooks for state management
- React Query for server state
- React Hook Form for form handling
- Framer Motion for animations
- Recharts for data visualization
- Lucide React for icons
- Mobile-first responsive design

### 4. Backend Specific (Current)
- Express.js 5.2.1
- Environment variables via dotenv
- Basic CORS configuration
- JSON body parsing
- Planned migration to FastAPI + PostgreSQL

### 5. ML Specific
- TensorFlow/Keras model stored in `ml/models/classification/`
- EfficientNetV2-B0 architecture
- 38 plant disease/health classes
- Input size: 224x224 RGB images
- Pretrained on ImageNet, fine-tuned on PlantVillage

### 6. Documentation
- Update `PROJECT_BRAIN/` files when making architectural changes
- Keep API contracts in sync with implementation
- Document all technical decisions in `10_DECISIONS.md`
- Update `12_CHANGELOG.md` with significant changes

### 7. Git Practices
- Commit frequently with descriptive messages
- Pull before pushing to avoid conflicts
- Use feature branches for significant changes
- Follow conventional commit format when possible

### 8. Testing
- Write unit tests for new functionality
- Maintain existing test coverage
- Use Vitest for frontend testing
- Plan for backend testing with pytest

## Current Status (as of 2026-09-09)
- ✅ Frontend UI components complete
- ✅ Basic backend endpoints (`/api/ping`, `/api/demo`)
- ✅ Trained ML model (95.94% accuracy)
- ❌ Missing API-ML integration
- ❌ Missing persistence layer (database)
- ❌ Missing authentication system
- ❌ Missing file upload handling
- ❌ Missing core plant scanning functionality

## Next Steps
1. Implement core API endpoints for plant management
2. Connect frontend to backend
3. Deploy ML model for inference
4. Add PostgreSQL database
5. Implement authentication system
6. Add image upload and processing

## Important Notes
- Do not modify application code without understanding the full impact
- Do not retrain or modify ML models without consulting PROJECT_BRAIN documentation
- Do not delete files without verifying they're not referenced elsewhere
- Do not change frontend styling without checking responsiveness
- The PROJECT_BRAIN directory must remain the single source of truth