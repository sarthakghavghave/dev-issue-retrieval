# Dev Issue Retrieval

A full-stack semantic search platform for discovering relevant developer issues and technical discussions from open-source repositories.

Live Demo: https://dev-issue.onrender.com/

## Overview

Dev Issue Retrieval lets developers search GitHub issues with natural language instead of exact keywords.

The system loads raw issue data from a cloud-hosted NEON database, preprocesses it through a Spring Boot backend, generates embeddings using the Hugging Face Inference API, indexes results with FAISS, and reranks candidates using the Jina Reranker API.

## Features

* Natural language search over GitHub issue content
* FAISS vector retrieval for fast similarity search
* Jina API reranking for better relevance
* Spring Boot web application
* FastAPI NLP service for search routing and indexing
* Dockerized deployment
* Automatic periodic incremental ingestion for new issues
* Cloud-backed raw issue storage via NEON
* External ML APIs optimized for free-tier memory limits

## System Architecture

The system has three connected components:

1. Cloud NEON database stores raw GitHub issue records.
2. Spring Boot backend reads raw data, sends content to the NLP service, and manages indexing.
3. FastAPI NLP service preprocesses text, fetches embeddings via API, updates FAISS, and serves search.

### Architecture Flow

```text
GitHub API
      ↓
Cloud NEON DB
      ↓
Spring Boot backend
      ↓
NLP service preprocessing + embedding
      ↓
FAISS index update
      ↓
Semantic reranking with user query
```

The backend also schedules automatic periodic ingestion so new or updated issues are added to the index over time.

## Retrieval Pipeline

### Offline / Indexing

1. Raw issues are ingested from the NEON database.
2. Text is cleaned and prepared for retrieval.
3. Embeddings are generated using the Hugging Face API.
4. FAISS index files and metadata are written to disk.

### Online / Search

1. User submits a query through the web UI.
2. Query text is encoded as an embedding.
3. FAISS retrieves top candidate issues.
4. Jina Reranker API reranks candidates.
5. Ranked issue results are returned.

## AI APIs Used

* Embeddings: Hugging Face Inference API (`sentence-transformers/all-MiniLM-L6-v2`)
* Reranking: Jina Reranker API (`jina-reranker-v2-base-multilingual`)

Using external APIs keeps the memory footprint near zero, allowing the service to run easily on free-tier cloud instances.

## Dataset

Current indexed dataset:

* ~5,500 curated GitHub issues
* Multiple open-source repositories
* Preprocessed and deduplicated issue content
* Metadata including labels, repository, URLs, and timestamps

## Tech Stack

### Backend

* Java 21
* Spring Boot
* Maven

### NLP Service

* FastAPI
* Python
* Hugging Face & Jina APIs
* FAISS

### Data Processing

* Pandas
* NumPy
* PyArrow

### Deployment

* Docker
* Render

## Local Development

### Start NLP Service

```bash
cd nlp-service
uvicorn scripts.retrieval_api:app --reload
```

### Start Spring Boot

```bash
cd backend
mvn spring-boot:run
```

### Docker

```bash
docker compose up --build
```

## License

MIT License
