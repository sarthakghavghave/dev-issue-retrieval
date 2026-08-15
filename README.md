# Dev Issue Retrieval

A full-stack semantic search platform for discovering relevant developer issues and technical discussions from open-source repositories.

Live Demo: https://spring-ccmb.onrender.com/

## Overview

Dev Issue Retrieval lets developers search GitHub issues with natural language instead of exact keywords.

The system loads raw issue data from a cloud-hosted NEON database, preprocesses it through a Spring Boot backend, generates embeddings in an NLP service, indexes results with FAISS, and reranks candidates with a lightweight cross-encoder.

## Features

* Natural language search over GitHub issue content
* FAISS vector retrieval for fast similarity search
* TinyBERT cross-encoder reranking for better relevance
* Spring Boot web application
* FastAPI NLP service for embedding and indexing
* Dockerized deployment
* Automatic periodic incremental ingestion for new issues
* Cloud-backed raw issue storage via NEON
* Small models optimized for free-tier memory limits

## System Architecture

The system has three connected components:

1. Cloud NEON database stores raw GitHub issue records.
2. Spring Boot backend reads raw data, sends content to the NLP service, and manages indexing.
3. FastAPI NLP service preprocesses text, computes embeddings, updates FAISS, and serves search.

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
3. Embeddings are generated with a small sentence-transformers model.
4. FAISS index files and metadata are written to disk.

### Online / Search

1. User submits a query through the web UI.
2. Query text is encoded as an embedding.
3. FAISS retrieves top candidate issues.
4. TinyBERT reranks candidates.
5. Ranked issue results are returned.

## Models Used

* Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
* Cross-encoder reranker: `cross-encoder/ms-marco-TinyBERT-L-2-v2`

These smaller models help keep memory use low for cloud deployment on limited free-tier instances.

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
* Sentence Transformers
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
