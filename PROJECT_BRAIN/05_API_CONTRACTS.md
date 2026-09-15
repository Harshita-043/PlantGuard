# PlantGuard AI API Contracts

## Overview
This document defines the API contracts between the PlantGuard AI frontend and backend. The backend is built with Express.js and the frontend is a React/Vite application.

## Base URL
All API endpoints are prefixed with `/api`.

## Common Patterns
- **Request/Response Format**: JSON
- **Error Responses**: 
  ```json
  {
    "error": {
      "message": "Human-readable error message",
      "code": "ERROR_CODE",
      "details": {} // Optional additional details
    }
  }
  ```
- **Success Responses**: Vary by endpoint, typically return the requested resource or operation status.
- **Authentication**: Currently not implemented; planned for future versions.
- **Rate Limiting**: Not currently implemented; planned for future versions.

## Endpoints

### Health Check
- **Endpoint**: `GET /api/ping`
- **Description**: Simple health check endpoint to verify the backend is running.
- **Request**: No parameters
- **Response**:
  ```json
  {
    "message": "ping pong" // From environment variable PING_MESSAGE
  }
  ```
- **Example**:
  ```bash
  curl http://localhost:3000/api/ping
  # Response: {"message":"ping pong"}
  ```

### Demo Endpoint
- **Endpoint**: `GET /api/demo`
- **Description**: Example endpoint demonstrating API structure.
- **Request**: No parameters
- **Response**:
  ```json
  {
    "message": "Hello from Express server"
  }
  ```
- **Shared Type**: `DemoResponse` (in `@shared/api`)

### Plant Scanning (Planned)
- **Endpoint**: `POST /api/scan`
- **Description**: Upload a plant leaf image for disease classification.
- **Request**:
  - **Content-Type**: `multipart/form-data`
  - **Body**:
    - `image`: File (JPEG, PNG, etc.) - required
    - `plantId`: String (optional) - if scanning an existing plant in user's collection
    - `location`: String (optional) - where the plant is located
- **Response** (Success):
  ```json
  {
    "success": true,
    "data": {
      "scanId": "string (UUID)",
      "plantId": "string (UUID, optional)",
      "timestamp": "ISO 8601 timestamp",
      "predictions": [
        {
          "classIndex": number,
          "className": "string (e.g., 'Tomato___Early_blight')",
          "confidence": number (0-1)
        }
      ],
      "topPrediction": {
        "classIndex": number,
        "className": "string",
        "confidence": number
      },
      "recommendedActions": ["string"] // Optional, based on prediction
    }
  }
  ```
- **Response** (Error):
  ```json
  {
    "error": {
      "message": "Invalid image format",
      "code": "INVALID_IMAGE",
      "details": { "supportedTypes": ["image/jpeg", "image/png"] }
    }
  }
  ```
- **Notes**:
  - Image will be preprocessed to 224x224 before model inference
  - Returns top 5 predictions by default
  - Requires authentication in future versions

### Plant Management (Planned)
#### Get User's Plants
- **Endpoint**: `GET /api/plants`
- **Description**: Retrieve list of plants in user's collection.
- **Request**: 
  - Query Parameters:
    - `page`: Number (default: 1)
    - `limit`: Number (default: 20)
    - `search`: String (optional, filter by name/species)
    - `status`: String (optional, filter by health status)
- **Response**:
  ```json
  {
    "success": true,
    "data": {
      "plants": [
        {
          "id": "string (UUID)",
          "name": "string",
          "species": "string",
          "location": "string",
          "healthScore": number (0-100),
          "status": "string (Healthy/Needs attention/etc.)",
          "lastScan": "ISO 8601 timestamp",
          "imageUrl": "string (URL to plant image)"
        }
      ],
      "pagination": {
        "page": number,
        "limit": number,
        "total": number,
        "totalPages": number
      }
    }
  }
  ```

#### Add New Plant
- **Endpoint**: `POST /api/plants`
- **Description**: Add a new plant to user's collection.
- **Request**:
  ```json
  {
    "name": "string (required)",
    "species": "string (required)",
    "location": "string (optional)",
    "imageUrl": "string (optional, URL to initial plant image)"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "data": {
      "id": "string (UUID)",
      "name": "string",
      "species": "string",
      "location": "string",
      "healthScore": number,
      "status": "string",
      "lastScan": null,
      "createdAt": "ISO 8601 timestamp"
    }
  }
  ```

#### Get Plant Details
- **Endpoint**: `GET /api/plants/:plantId`
- **Description**: Get details for a specific plant.
- **Request**: 
  - Path Parameter: `plantId` (UUID)
- **Response**:
  ```json
  {
    "success": true,
    "data": {
      "id": "string",
      "name": "string",
      "species": "string",
      "location": "string",
      "healthScore": number,
      "status": "string",
      "lastScan": "ISO 8601 timestamp or null",
      "scans": [
        {
          "id": "string",
          "timestamp": "ISO 8601 timestamp",
          "topPrediction": {
            "className": "string",
            "confidence": number
          },
          "imageUrl": "string"
        }
      ]
    }
  }
  ```

#### Update Plant
- **Endpoint**: `PUT /api/plants/:plantId`
- **Description**: Update plant information.
- **Request**: 
  - Path Parameter: `plantId`
  - Body: Partial plant object (name, species, location)
- **Response**: Updated plant object (same structure as GET)

#### Delete Plant
- **Endpoint**: `DELETE /api/plants/:plantId`
- **Description**: Remove a plant from user's collection.
- **Request**: Path Parameter: `plantId`
- **Response**:
  ```json
  {
    "success": true,
    "message": "Plant deleted successfully"
  }
  ```

### Scan History (Planned)
- **Endpoint**: `GET /api/history`
- **Description**: Retrieve scan history for user's plants.
- **Request**:
  - Query Parameters:
    - `plantId`: String (optional, filter by specific plant)
    - `startDate`: ISO 8601 string (optional)
    - `endDate`: ISO 8601 string (optional)
    - `page`: Number (default: 1)
    - `limit`: Number (default: 20)
- **Response**:
  ```json
  {
    "success": true,
    "data": {
      "scans": [
        {
          "id": "string",
          "plantId": "string",
          "plantName": "string",
          "timestamp": "ISO 8601 timestamp",
          "topPrediction": {
            "className": "string",
            "confidence": number
          },
          "imageUrl": "string",
          "recommendedActions": ["string"]
        }
      ],
      "pagination": {
        "page": number,
        "limit": number,
        "total": number,
        "totalPages": number
      }
    }
  }
  ```

### Recommendations (Planned)
- **Endpoint**: `GET /api/recommendations`
- **Description**: Get care recommendations based on scan history and plant types.
- **Request**:
  - Query Parameters:
    - `plantId`: String (optional, filter by specific plant)
    - `type`: String (optional, e.g., "watering", "fertilizing", "disease-prevention")
- **Response**:
  ```json
  {
    "success": true,
    "data": {
      "recommendations": [
        {
          "id": "string",
          "title": "string",
          "description": "string",
          "type": "string",
          "priority": "low|medium|high",
          "relatedPlantId": "string (optional)",
          "createdAt": "ISO 8601 timestamp",
          "expiresAt": "ISO 8601 timestamp (optional)"
        }
      ]
    }
  }
  ```

### Weather Insights (Planned)
- **Endpoint**: `GET /api/weather`
- **Description**: Get weather information and insights for plant care.
- **Request**:
  - Query Parameters:
    - `location`: String (required, city or coordinates)
    - `days`: Number (optional, default: 3, forecast days)
- **Response**:
  ```json
  {
    "success": true,
    "data": {
      "location": "string",
      "current": {
        "temperature": number,
        "humidity": number,
        "description": "string",
        "timestamp": "ISO 8601 timestamp"
      },
      "forecast": [
        {
          "date": "ISO 8601 date",
          "temperatureMin": number,
          "temperatureMax": number,
          "humidity": number,
          "precipitationChance": number,
          "description": "string"
        }
      ],
      "insights": [
        {
          "type": "string (e.g., 'watering', 'fungal-risk')",
          "message": "string",
          "recommendation": "string"
        }
      ]
    }
  }
  ```

### AI Assistant (Planned)
- **Endpoint**: `POST /api/chat`
- **Description**: Send a message to the AI assistant and get a response.
- **Request**:
  ```json
  {
    "message": "string (required)",
    "context": { // Optional context about user's plants
      "plantId": "string (optional)",
      "recentScans": [ /* array of recent scan summaries */ ] (optional)
    }
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "data": {
      "message": "string (AI response)",
      "timestamp": "ISO 8601 timestamp",
      "suggestions": ["string"] // Optional follow-up questions
    }
  }
  ```
- **Alternative**: WebSocket endpoint for real-time chat (planned for future)

### User Profile (Planned)
- **Endpoint**: `GET /api/profile`
- **Description**: Get authenticated user's profile information.
- **Request**: None (authenticated via token/session)
- **Response**:
  ```json
  {
    "success": true,
    "data": {
      "id": "string",
      "name": "string",
      "email": "string",
      "avatarUrl": "string (optional)",
      "preferences": {
        "units": "metric|imperial",
        "notifications": boolean,
        "language": "string"
      }
    }
  }
  ```

- **Endpoint**: `PUT /api/profile`
- **Description**: Update user profile.
- **Request**: Partial profile object
- **Response**: Updated profile object

### Settings (Planned)
- **Endpoint**: `GET /api/settings`
- **Description**: Get user/application settings.
- **Request**: None
- **Response**:
  ```json
  {
    "success": true,
    "data": {
      "app": {
        "version": "string",
        "maintenanceMode": boolean
      },
      "user": {
        "notificationsEnabled": boolean,
        "emailNotifications": boolean,
        "pushNotifications": boolean,
        "scanReminders": boolean,
        "defaultLocation": "string"
      }
    }
  }
  ```

- **Endpoint**: `PUT /api/settings`
- **Description**: Update settings.
- **Request**: Settings object (partial)
- **Response**: Updated settings object

## Error Codes
- `VALIDATION_ERROR`: Request validation failed
- `UNAUTHORIZED`: Authentication required or invalid
- `FORBIDDEN`: Insufficient permissions
- `NOT_FOUND`: Resource not found
- `INVALID_IMAGE`: Uploaded file is not a valid image
- `MODEL_ERROR`: Error during ML inference
- `INTERNAL_ERROR`: Unexpected server error
- `RATE_LIMITED`: Too many requests

## Headers
- **Content-Type**: `application/json` for most endpoints
- **Authorization**: `Bearer <token>` (planned for future)
- **Accept**: `application/json`

## Future Considerations
1. **Authentication**: JWT or session-based auth
2. **Versioning**: `/api/v1/` prefix
3. **WebSocket**: For real-time features (chat, live updates)
4. **File Uploads**: Dedicated endpoint or signed URLs for image storage
5. **Pagination**: Standardized across list endpoints
6. **Filtering & Sorting**: Enhanced query parameters
7. **HATEOAS**: Links in responses for discoverability
8. **OpenAPI/Swagger**: Formal specification for documentation and client generation

## Related Documents
- [ARCHITECTURE.md](01_ARCHITECTURE.md) - System architecture
- [MODEL_REGISTRY.md](04_MODEL_REGISTRY.md) - ML model details
- [FRONTEND_GRAPH.md](08_FRONTEND_GRAPH.md) - Frontend components that will use these APIs