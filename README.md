# dev-issue-retrieval

A backend-driven semantic retrieval platform for discovering relevant developer issues, discussions, and technical solutions from platforms like GitHub and StackOverflow.

## Overview

`dev-issue-retrieval` will continuously ingest developer issue discussions and retrieve semantically relevant technical problems using NLP-based retrieval pipelines.

The project focuses on:
- Spring Boot backend engineering
- semantic retrieval
- vector search
- reranking pipelines
- incremental indexing

## Tech Stack

- Java
- Spring Boot
- PostgreSQL
- FastAPI
- SBERT
- FAISS
- CrossEncoder (MS MARCO)

## Planned Features

- GitHub issue ingestion
- Semantic issue retrieval
- Vector similarity search
- CrossEncoder reranking
- Incremental indexing
- Search UI
- REST APIs

## Architecture

```text
GitHub / StackOverflow
        ↓
Spring Boot Ingestion
        ↓
PostgreSQL
        ↓
Embedding Service
        ↓
FAISS Vector Search
        ↓
Semantic Retrieval
        ↓
Reranking
```

## License
MIT License