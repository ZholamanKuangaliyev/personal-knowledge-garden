# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.4.1]

### Added
- `garden sources` command — lists all ingested documents with chunk counts, tags, and usage hints
- Document-scoped chat: `garden chat --source <name>` filters retrieval to a specific document
- Document-scoped chat: `garden chat --tag <name>` filters retrieval by tag
- Drag-and-drop file ingestion in chat — drop a .txt, .md, or .pdf path into the chat prompt and it auto-ingests with a live progress spinner, blocking further input until complete
- `garden config models` — lists all installed Ollama models in a table with name, size, and date; highlights the currently active model
- `garden config use-model` — interactive model picker that shows numbered list of installed models and saves selection to garden.json
- Extracted reusable `ingest_single_file()` function from the ingest CLI command for programmatic use

## [0.4.0]

### Performance & Pipeline
- Embedder is now a cached singleton — no re-initialization per call during ingestion
- Batch card INSERT via `executemany()` replaces per-card loop (10-20% faster card generation)
- Graph cache batch invalidation — deferred rebuild during multi-file ingestion instead of per-write
- LLM retry now uses exponential backoff with jitter to prevent thundering herd on reconnect
- Deterministic insight engine — exhaustive cross-source bridge pair ranking replaces random sampling

### Knowledge Graph Quality
- Semantic concept linking via embedding cosine similarity — concepts without word overlap now get linked
- Stopword filter prevents false-positive links from words like "in", "the", "is"
- Flashcard deduplication across chunks — normalized question matching prevents near-identical cards

### Knowledge Gap Awareness
- New `knowledge_gap` state flag — when retrieval retries are exhausted with no relevant docs, the generator is told explicitly, preventing hallucination
- Generator prompt now instructs the LLM to acknowledge when information is not in the garden

### New CLI Commands
- `garden sessions [list|show|delete]` — browse, inspect, and delete past chat sessions with prefix ID matching
- `garden search --semantic` — hybrid search combining vector results with concept graph neighbors

### Configurable Pipeline
- Moved all hardcoded constants to `Settings` (configurable via `garden.json` or `PKG_` env vars):
  - `grader_threshold` (embedding L2 distance cutoff, default 1.5)
  - `grader_content_len` (LLM grader truncation, default 300)
  - `rewriter_failed_docs` (rejected docs sent to rewriter, default 3)
  - `chat_max_history`, `chat_recent_full`, `chat_truncate_len` (chat context window)
  - `concept_batch_size` (chunks per LLM call during extraction, default 5)

### Data Model Enrichment (Schema v2)
- Concept: added `category` and `importance` fields
- Flashcard: added `last_reviewed_at`, `review_count`, `source_chunk_id` for review tracking and traceability
- Chunk: added `created_at` timestamp and extensible `metadata` dict
- SearchResult: added `chunk_index` and `metadata` from vector store
- Automatic schema migration on first run — existing databases upgraded seamlessly
- New indexes on `flashcards(created_at)`, `concept_links(weight)`, `documents(ingested_at)`

### Reliability
- Chat error messages now distinguish Ollama connection failures from generic errors
- Transaction safety documentation — ChromaDB writes recommended as last step
- Chat store query optimized — SQL subquery replaces Python-side reversal

## [0.3.2]

- Redesigned welcome screen with a data-driven 8x8 visualization grid replacing ASCII flower art
- Grid cells are color-coded proportionally to garden stats: docs, chunks, concepts, links, cards, due
- Responsive layout adapts to terminal width: vertical stack (<60), side-by-side (60-90), full layout (>90)
- Welcome module (`garden.ui.welcome`) built with pure, composable functions for easy testing
- Added color legend and all 6 garden metrics to the info panel
- Moved welcome logic out of `panels.py` into dedicated `welcome.py` module
- Extended test suite to 238 tests (new welcome grid, info, panel, and layout tests)

## [0.3.1]

- Upgraded default LLM from `qwen3:8b` to `qwen3.5:9b`
- Added agent role system with 5 roles: `general`, `analyst`, `summarizer`, `creative`, `researcher`
- Each role controls Chain-of-Thought reasoning via qwen3's native `/think` and `/no_think` tokens
- Auto role detection: the router automatically switches from `general` to a specialist role when the query warrants it
- Chat welcome screen with model info and document/concept counts
- In-chat commands: `/roles`, `/switch <role>`, `/auto` (toggle auto-detection)
- New `--role` / `-r` CLI option to start chat in a specific role
- Rewrote system preamble to allow versatile reasoning beyond strict RAG-only constraints
- Generator prompt now injects role-specific instructions and think mode tokens
- Extended test suite to 228 tests (new role system, prompt rendering, chat command tests)

## [0.3.0]

- Added structured logging across all modules via `garden.*` logger hierarchy
- All silent `except` blocks now log warnings/errors before swallowing exceptions
- Replaced `print()` calls in database migrations with proper `logger.info()` calls
- Agent nodes (router, grader, rewriter, retriever, generator) log routing decisions and fallbacks
- Knowledge modules (concept extractor, idea generator, insight engine) log LLM parse failures
- CLI commands (ingest, chat, clear, forget, export, search, status, migrate-embeddings) log operations and errors
- Store layer (vector store, database) logs initialization, queries, and deletions
- Ingestion layer (loader, embedder, PDF/text loaders) logs file processing
- All logging controlled via `-v` verbose flag: WARNING by default, DEBUG when verbose
- Added `search` and `export` CLI commands
- Added embedding model migration command (`garden migrate-embeddings`)
- Added `llm_utils` module with centralized LLM access and robust JSON response parsing
- Extended test suite to 204 tests

## [0.2.0]

- Migrated flashcards and knowledge graph storage from JSON files to SQLite
- Added duplicate detection during ingestion (content hash + source name)
- Added document registry to track ingested files
- Automatic one-time migration from JSON to SQLite on first run
- Added initial test suite (165 tests) covering all modules

## [0.1.0]

- Document ingestion with chunking and embedding (.txt, .md, .pdf)
- Interactive RAG chat with source citations
- LangGraph agent with routing, grading, and query rewriting
- Concept extraction and knowledge graph building
- Spaced repetition with SM-2 scheduling
- Cross-domain insight discovery
- Idea generation grounded in stored knowledge
- `forget` and `clear` commands for data management
- `config` command for viewing and changing models
- Swappable LLM and embedding models via CLI, config file, or env vars
- All processing runs locally through Ollama — no data leaves your machine
