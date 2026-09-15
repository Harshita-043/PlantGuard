# PlantGuard AI Agent Graph

## Overview
This document describes the planned AI agent system for PlantGuard AI. The agent system will automate complex plant care workflows by combining ML model inference, knowledge retrieval, and decision-making capabilities.

## Agent Architecture
```
+------------------+     +------------------+     +------------------+
|   User Request   |---->|   Orchestrator   |<----|   Memory Store   |
| (Chat/Voice/etc) |     |  (Task Planning) |     |  (User Plants,   |
|                  |     |                  |     |   Scan History,  |
+------------------+     +------------------+     |   Preferences)   |
        ^                         ^             +------------------+
        |                         |
        |                  +------------------+
        |                  |   Tool Registry  |
        |                  |  (ML Model,     |
        |                  |   RAG, Weather, |
        |                  |   Calendar, etc)|
        |                  +------------------+
        |                         ^
        |                         |
        |              +------------------+
        +<-------------|   Specialized    |
                       |   Agents         |
                       |  (Diagnosis,     |
                       |   Care Planner,  |
                       |   Expert, etc)   |
                       +------------------+
                                   ^
                                   |
                                   v
                          +------------------+
                          |   Action         |
                          |   Execution      |
                          +------------------+
                                   ^
                                   |
                                   v
                          +------------------+
                          |   Response       |
                          +------------------+
```

## Core Components

### 1. Orchestrator (Central Agent)
**Responsibilities**:
- Understand user intent from natural language
- Break down complex requests into subtasks
- Coordinate between specialized agents
- Manage conversation state and context
- Handle follow-up questions and clarifications

**Capabilities**:
- Task decomposition and planning
- Agent selection and routing
- Conflict resolution between agent recommendations
- Conversation memory management
- Fallback to human expert when needed

### 2. Memory Store
**Content**:
- User profile and preferences
- Plant collection details (species, locations, health history)
- Scan history with timestamps and results
- Care activities and reminders
- User feedback and corrections
- Environmental data (local weather, season)

**Storage**:
- Structured database (likely PostgreSQL or similar)
- Vector embeddings for semantic search of plant care notes
- Time-series data for health tracking

### 3. Tool Registry
**Available Tools**:
- **ML Model Tool**: Plant disease classification from images
- **RAG Tool**: Retrieve plant care information from knowledge base
- **Weather Tool**: Get current and forecast weather data
- **Calendar Tool**: Schedule care activities and reminders
- **Notification Tool**: Send alerts and reminders to users
- **Image Processing Tool**: Preprocess images for ML model
- **Location Tool**: Get user location for localized advice
- **Database Tool**: Read/write user and plant data

### 4. Specialized Agents
Each agent focuses on a specific domain of plant care expertise:

#### Plant Doctor Agent (Diagnosis Specialist)
- **Role**: Analyze plant symptoms and provide disease/pest assessments
- **Inputs**: Images, symptom descriptions, plant species, environmental conditions
- **Outputs**: Likely diagnoses, confidence scores, recommended next steps
- **Tools Used**: ML Model Tool, RAG Tool, Image Processing Tool
- **Knowledge Base**: Plant pathology, entomology, horticulture

#### Care Planner Agent (Prevention & Maintenance)
- **Role**: Create personalized care schedules and preventive plans
- **Inputs**: Plant species, location, season, current health status
- **Outputs**: Watering schedule, fertilizing plan, pruning timeline, preventive treatments
- **Tools Used**: RAG Tool, Weather Tool, Calendar Tool, Database Tool
- **Knowledge Base**: Horticultural best practices, seasonal guides

#### Expert Consultant Agent (Escalation & Education)
- **Role**: Provide expert-level advice and educational content
- **Inputs**: Complex cases, user questions, diagnostic uncertainty
- **Outputs**: Detailed explanations, treatment options, when to seek professional help
- **Tools Used**: RAG Tool, Database Tool
- **Knowledge Base**: Expert literature, case studies, university extension resources

#### Growth Tracker Agent (Monitoring & Analytics)
- **Role**: Track plant progress over time and identify trends
- **Inputs**: Historical scan data, care activities, environmental data
- **Outputs**: Growth trends, health improvements/declines, anomaly detection
- **Tools Used**: Database Tool, ML Model Tool (for consistency checking)
- **Knowledge Base**: Normal growth patterns, stress indicators

## Agent Communication Patterns

### Sequential Processing
For linear workflows:
```
User -> Orchestrator -> Specialist Agent -> Orchestrator -> User
```
Example: User asks "Why are my tomato leaves yellow?" -> Orchestrator routes to Plant Doctor -> Plant Doctor analyzes -> Returns diagnosis -> Orchestrator formats response.

### Parallel Processing
For comprehensive assessments:
```
User -> Orchestrator -> [Specialist Agents in Parallel] -> Orchestrator -> User
```
Example: User requests "Complete care plan for my garden" -> Orchestrator sends to Plant Doctor (health check), Care Planner (schedule), Growth Tracker (baseline) -> Combines results.

### Hierarchical Processing
For complex cases requiring consultation:
```
User -> Orchestrator -> Primary Agent -> Orchestrator -> Consultant Agent -> Orchestrator -> User
```
Example: Plant Doctor uncertain about diagnosis -> Consults Expert Consultant for second opinion.

## Decision Making Framework

### Confidence Thresholds
- **High Confidence** (>0.9): Direct response to user
- **Medium Confidence** (0.7-0.9): Response with suggestion to verify
- **Low Confidence** (<0.7): Request for more information or suggest expert consultation

### Uncertainty Handling
1. **Clarification Questions**: Ask for missing information (image quality, symptom details)
2. **Multiple Hypotheses**: Present top 3 possibilities with evidence for each
3. **Escalation Path**: Connect to human expert or suggest lab testing
4. **Conservative Recommendations**: Suggest least harmful interventions first

## Current Implementation Status
**State**: Not implemented
**Planned Phases**:
1. **Phase 1**: Basic orchestrator with single specialist agent (Plant Doctor)
2. **Phase 2**: Add memory store and tool registry
3. **Phase 3**: Add additional specialized agents
4. **Phase 4**: Implement advanced coordination and learning capabilities

## Required Components

### Infrastructure
- **Agent Framework**: Likely using LangChain, LlamaIndex, or custom solution
- **LLM Access**: For reasoning and natural language understanding
- **Vector Database**: For memory and knowledge retrieval
- **API Gateway**: To expose agent capabilities to frontend
- **Authentication**: Secure access to user data

### Integration Points
1. **With ML Model**: Agents can invoke disease classification tool
2. **With RAG**: Agents can retrieve care information
3. **With Backend API**: Agents read/write user data through existing endpoints
4. **With Frontend**: Chat interface sends user queries to orchestrator

## Data Flow Examples

### Example 1: Disease Diagnosis Workflow
```
1. User: "My rose has black spots on leaves" (with image)
2. Frontend -> /api/agent/chat (with message and image)
3. Orchestrator: 
   - Identifies intent: disease diagnosis
   - Routes to Plant Doctor Agent
4. Plant Doctor Agent:
   - Uses Image Processing Tool to prepare image
   - Uses ML Model Tool for initial classification
   - Uses RAG Tool to look up rose diseases
   - Considers user description and image
5. Plant Doctor Agent -> Orchestrator: 
   - Diagnosis: Black spot disease (85% confidence)
   - Treatment: Remove affected leaves, fungicide spray
   - Prevention: Improve air circulation, avoid wet leaves
6. Orchestrator -> Frontend: Formatted response with diagnosis and advice
```

### Example 2: Care Planning Workflow
```
1. User: "Create a care plan for my Monstera and Snake Plant"
2. Orchestrator:
   - Identifies intent: care planning
   - Retrieves user's plant collection from memory
   - Splits into subtasks: Monstera care plan, Snake Plant care plan
3. Care Planner Agent (for each plant):
   - Gets plant details from memory
   - Checks current season and local weather
   - Retrieves species-specific care info from RAG
   - Creates watering, fertilizing, cleaning schedule
4. Orchestrator combines plans and checks for conflicts
5. Orchestrator -> Frontend: Unified care plan with calendar integration options
```

## Evaluation Metrics

### Agent Performance
- **Task Success Rate**: Percentage of user requests completed satisfactorily
- **Response Relevance**: How well agent responses address user queries
- **Diagnosis Accuracy**: For Plant Doctor, comparison with expert labels
- **Plan Adherence**: How often users follow care plan recommendations

### Interaction Quality
- **Conversation Length**: Number of exchanges needed to resolve query
- **Clarification Rate**: Percentage of responses requiring follow-up questions
- **User Satisfaction**: Post-interaction ratings
- **Escalation Rate**: Percentage of cases requiring human expert intervention

### System Metrics
- **Response Time**: End-to-end latency for agent processing
- **Tool Usage Efficiency**: Frequency and effectiveness of tool calls
- **Memory Utilization**: How effectively past interactions inform current responses
- **Scalability**: Concurrent user handling capacity

## Dependencies
- **LLM Service**: For natural language reasoning (Anthropic Claude or similar)
- **Vector Database**: Pinecone, Weaviate, or pgvector for memory/RAG
- **Orchestration Framework**: LangChain, LlamaIndex, or custom
- **Background Job System**: For async tasks (Celery, RabbitMQ, or similar)
- **Monitoring**: Logging, metrics, and tracing (ELK stack, Prometheus, etc.)

## Risks and Mitigations

### Risks
1. **Over-automation**: Users may follow incorrect advice without verification
2. **Complexity**: Agent systems can be difficult to debug and maintain
3. **Latency**: Multiple tool calls can increase response time
4. **Inconsistency**: Different agents may give conflicting advice
5. **Knowledge Gaps**: Agents may lack information for rare plants/diseases

### Mitigations
1. **Uncertainty Communication**: Always express confidence levels
2. **Expert Backup**: Clear escalation paths to human experts
3. **Consistency Checks**: Validate agent recommendations against each other
4. **Fallback Mechanisms**: Default to safe, general advice when uncertain
5. **Continuous Learning**: Update agent knowledge from expert corrections

## Future Enhancements
1. **Multi-modal Agents**: Process images, video, and sensor data natively
2. **Personalized Agents**: Fine-tune to individual user's plants and preferences
3. **Collaborative Agents**: Enable agent-to-agent consultation and debate
4. **Proactive Monitoring**: Agents that initiate check-ups based on plant schedules
5. **Community Knowledge**: Learn from anonymized, aggregated user experiences
6. **IoT Integration**: Connect to soil moisture sensors, light meters, etc.

## Related Documents
- [ARCHITECTURE.md](01_ARCHITECTURE.md) - System architecture
- [RAG_GRAPH.md](06_RAG_GRAPH.md) - Knowledge retrieval system used by agents
- [API_CONTRACTS.md](05_API_CONTRACTS.md) - Planned agent communication endpoints
- [FRONTEND_GRAPH.md](08_FRONTEND_GRAPH.md) - Chat UI for agent interactions