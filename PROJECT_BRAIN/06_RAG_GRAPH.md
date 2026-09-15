# PlantGuard AI RAG (Retrieval-Augmented Generation) Graph

## Overview
This document outlines the planned Retrieval-Augmented Generation (RAG) system for PlantGuard AI's AI assistant feature. The RAG system will enable the AI assistant to provide accurate, context-aware responses by retrieving relevant information from a knowledge base before generating responses.

## RAG Architecture
```
+------------------+     +------------------+     +------------------+
|   User Query     |---->|  Retriever       |---->|   Knowledge Base |
|                  |     |  (Embedding +    |     |  (Plant Care     |
|                  |     |   Vector Search) |     |   Guides, FAQs,  |
+------------------+     +------------------+     |   Research Papers)|
        ^                         ^             +------------------+
        |                         |
        |                         v
        |              +------------------+
        |              |   Context        |
        |              |   Aggregator     |
        |              +------------------+
        |                         ^
        |                         |
        |              +------------------+
        +<-------------|   LLM Generator  |
                       | (LLM with       |
                       |  retrieved      |
                       |  context)       |
                       +------------------+
                                   ^
                                   |
                                   v
                          +------------------+
                          |   Response       |
                          +------------------+
```

## Components

### 1. Knowledge Base
**Content Types**:
- Plant care guides (watering, sunlight, soil requirements)
- Disease identification and treatment information
- Pest management guidelines
- Seasonal care tips
- Plant-specific care instructions
- Botanical facts and trivia
- FAQs from user interactions
- Links to authoritative sources (university extensions, botanical gardens)

**Sources**:
- Curated expert content
- Agricultural extension services (USDA, university extensions)
- Botanical garden resources
- Peer-reviewed plant pathology literature
- User-generated content (moderated)

**Storage Format**:
- Vector database (e.g., Pinecone, Weaviate, or pgvector)
- Documents stored with metadata for filtering
- Embeddings generated using sentence-transformers or similar

### 2. Retrieval System
**Embedding Model**:
- Sentence-transformers/all-MiniLM-L6-v2 or similar
- Multilingual support planned for future
- Optimized for semantic search in plant care domain

**Retrieval Process**:
1. User query is converted to embedding
2. Similarity search against knowledge base vectors
3. Top-k results returned (typically k=5)
4. Results re-ranked using cross-encoder or MMR for diversity
5. Context window constructed from retrieved documents

**Retrieval Strategies**:
- **Semantic Search**: Primary method using vector similarity
- **Keyword Boosting**: For exact matches of plant names, disease terms
- **Metadata Filtering**: By plant type, season, care aspect
- **Hybrid Search**: Combining BM25 with vector search (planned)

### 3. Context Aggregation
**Functions**:
- Deduplication of similar content
- Truncation to fit LLM context window
- Prioritization by relevance score
- Formatting for LLM consumption (clear sections, citations)
- Attribution tracking for source citations

### 4. LLM Generator
**Base Model**:
- Currently planned to use the same LLM as the main API (Claude via Anthropic)
- Future: Fine-tuned or specialized model for plant care domain

**Generation Process**:
1. Receive: User query + retrieved context
2. Construct prompt: System prompt + context + user query
3. Generate: Response using LLM with temperature control
4. Post-process: Add citations, verify safety, format output

**Prompt Engineering**:
- System prompt: Defines AI assistant role, behavior, limitations
- Context injection: Clear separation of retrieved information
- Citation format: Inline or footnote-style references to sources
- Safety checks: Prevent harmful advice, encourage expert consultation

## Data Flow

### Indexing Pipeline (Offline)
```
Raw Documents --> Cleaning & Preprocessing --> Chunking --> Embedding Generation --> Vector Storage
```

### Query Processing Pipeline (Real-time)
```
User Query --> Query Understanding --> Retrieval --> Context Aggregation --> Augmented Generation --> Response Delivery
```

## Implementation Status
**Current State**: Not implemented
**Planned Features**:
1. Basic RAG pipeline with retrieval and generation
2. Plant care knowledge base initialization
3. Integration with AI assistant chat endpoint
4. Source citation in responses
5. Feedback loop for improving retrieval

**Missing Components**:
- Knowledge base content curation
- Embedding generation service
- Vector database setup
- Retrieval API endpoints
- RAG integration in chat handler
- UI components for displaying sources
- Evaluation metrics for RAG performance

## Knowledge Base Structure (Planned)

### Taxonomy
```
Plant Care Knowledge Base
├── By Plant Type
│   ├── Flowering Plants
│   │   ├── Roses
│   │   ├── Orchids
│   │   └── ...
│   ├── Vegetables
│   │   ├── Tomatoes
│   │   ├── Peppers
│   │   └── ...
│   ├── Fruits
│   │   ├── Citrus
│   │   ├── Berries
│   │   └── ...
│   ├── Herbs
│   │   ├── Basil
│   │   ├── Mint
│   │   └── ...
│   └── Ornamentals
├── By Care Aspect
│   ├── Watering
│   ├── Sunlight
│   ├── Soil & Fertilizer
│   ├── Pruning
│   ├── Pest Management
│   └── Disease Prevention
├── By Problem Type
│   ├── Nutrient Deficiencies
│   ├── Fungal Diseases
│   ├── Bacterial Diseases
│   ├── Viral Diseases
│   ├── Insect Pests
│   └── Environmental Stress
└── By Season
    ├── Spring Care
    ├── Summer Care
    ├── Fall Care
    └── Winter Care
```

### Document Schema
```json
{
  "id": "unique_identifier",
  "title": "Document title",
  "content": "Main text content",
  "metadata": {
    "plantTypes": ["Tomato", "Pepper"], // Array of relevant plants
    "careAspects": ["Watering", "Fertilizing"],
    "problemTypes": ["Nutrient Deficiencies"],
    "seasons": ["Spring", "Summer"],
    "difficulty": "beginner|intermediate|advanced",
    "source": "Authoritative source name",
    "sourceUrl": "URL to original content (if web)",
    "language": "en",
    "lastUpdated": "ISO timestamp",
    "tags": ["tomato", "blossom end rot", "calcium"]
  }
}
```

## Integration Points

### With AI Assistant
1. **Chat Endpoint Enhancement**:
   - `/api/chat` will first retrieve relevant context
   - Context will be injected into the LLM prompt
   - Response will include citations when appropriate

2. **Streaming Support**:
   - For better UX, streaming responses with retrieved context
   - Progressive display as generation occurs

### With Frontend
1. **Chat Interface Updates**:
   - Display sources/citations for AI responses
   - Option to view full source documents
   - Feedback buttons for response quality (helpful/not helpful)

2. **Knowledge Base Exploration**:
   - Browse plants and care topics
   - Search knowledge base directly
   - Save favorite articles

## Evaluation Metrics

### Retrieval Quality
- **Mean Reciprocal Rank (MRR)**: Rank of first relevant result
- **Normalized Discounted Cumulative Gain (NDCG)**: Quality of ranking
- **Hit Rate@k**: Percentage of queries with at least one relevant result in top-k
- **Context Relevance**: Human evaluation of retrieved context usefulness

### Generation Quality
- **Answer Relevance**: Does answer address the user query?
- **Factual Consistency**: Is answer factually correct based on context?
- **Hallucination Rate**: Percentage of unsupported claims
- **Citation Accuracy**: Are citations properly attributed?

### User-Centric Metrics
- **Task Completion**: Did user get the information they needed?
- **User Satisfaction**: Rating of response helpfulness
- **Follow-up Reduction**: Fewer clarification questions needed
- **Expert Referral Rate**: Appropriate suggestions to consult experts

## Dependencies
- **Vector Database**: For storing and querying embeddings
- **Embedding Model**: For text-to-vector conversion
- **Document Processing**: For parsing and chunking source documents
- **LLM Access**: For generation component
- **Caching Layer**: For frequent queries (Redis or similar)

## Risks and Mitigations

### Risks
1. **Outdated Information**: Knowledge base becomes stale
2. **Incorrect Retrieval**: Wrong context leads to wrong answers
3. **Over-reliance**: Users trust AI without verification
4. **Bias in Sources**: Knowledge base reflects particular viewpoints
5. **Latency**: Retrieval adds delay to response

### Mitigations
1. **Regular Updates**: Scheduled refresh of knowledge base
2. **Confidence Scoring**: Indicate when retrieval confidence is low
3. **Disclaimers**: Encourage verification with experts for critical issues
4. **Diverse Sources**: Include multiple authoritative perspectives
5. **Performance Optimization**: Approximate nearest neighbor search, caching

## Future Enhancements
1. **Multilingual Support**: Non-English plant care resources
2. **Personalization**: Tailor recommendations to user's plants and location
3. **Multi-modal RAG**: Include images in retrieval (e.g., identify disease from photo then get treatment info)
4. **Feedback Loop**: Use user corrections to improve retrieval and generation
5. **External Knowledge**: Connect to agricultural APIs, weather services, etc.
6. **Expert Mode**: Option to include optional expert verification step

## Related Documents
- [ARCHITECTURE.md](01_ARCHITECTURE.md) - System architecture
- [AGENT_GRAPH.md](07_AGENT_GRAPH.md) - AI agent workflows that may use RAG
- [API_CONTRACTS.md](05_API_CONTRACTS.md) - Planned chat endpoint
- [FRONTEND_GRAPH.md](08_FRONTEND_GRAPH.md) - Chat UI components