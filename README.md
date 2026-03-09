# Personal Knowledge Garden

> **This project is in a very raw, early stage of development.** Expect breaking changes, incomplete features, and rough edges. Use at your own risk.

A local-first CLI tool for building a personal knowledge base. Ingest documents, chat with your data using AI, discover concept connections, generate flashcards, and surface unexpected insights — all running privately on your machine.

## What Is This?

Think of it as a **second brain** that lives in your terminal. You feed it documents (notes, PDFs, articles), and it:

1. **Remembers everything** — stores and indexes your documents locally
2. **Answers your questions** — chat with your knowledge using AI (like ChatGPT, but private and local)
3. **Finds connections** — automatically discovers how concepts across different documents relate to each other
4. **Creates flashcards** — generates study cards from your content with spaced repetition scheduling
5. **Surfaces insights** — finds surprising relationships between ideas you might have missed

No cloud. No API keys. No subscriptions. Everything runs on your computer.

## Quick Start

### Step 1: Install Prerequisites

You need three things installed on your computer:

**Python 3.12 or newer**
- Download from [python.org](https://www.python.org/downloads/) or use your system package manager
- Verify: run `python --version` in your terminal — it should show 3.12 or higher

**uv (Python package manager)**
- Install by running this in your terminal:
  ```bash
  # Windows (PowerShell)
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

  # macOS / Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- Verify: `uv --version`

**Ollama (local AI engine)**
- Download from [ollama.com](https://ollama.com) and install it
- After installing, Ollama runs in the background automatically
- Verify: `ollama --version`

### Step 2: Set Up the Garden

```bash
# Clone the project
git clone https://github.com/ZholamanKuangaliyev/personal-knowledge-garden
cd personal-knowledge-garden

# Install dependencies
uv sync

# Download the AI models (this may take a few minutes on first run)
ollama pull qwen3.5:9b
ollama pull nomic-embed-text
```

That's it. You're ready to go.

## Your First 5 Minutes

Here's a hands-on walkthrough to get you started:

### 1. Add a document to your garden

```bash
# Ingest any text, markdown, or PDF file
garden ingest my-notes.md

# You can also tag documents for easy filtering later
garden ingest research-paper.pdf --tag research
```

The garden will chunk your document, create embeddings, extract concepts, and generate flashcards — all automatically.

You can also drag and drop files directly into the chat — they'll be ingested automatically.

### 2. Chat with your knowledge

```bash
# Start an interactive chat session
garden chat
```

Ask questions about your documents. The AI will answer based on what you've ingested, citing sources. Type `quit` or press Ctrl+C to exit.

```bash
# Chat about a specific document only
garden chat --source my-notes.md

# Chat with a specific reasoning style
garden chat --role analyst
```

### 3. Explore what you've built

```bash
# See what's in your garden
garden status

# List all ingested documents
garden sources

# Browse concept connections
garden links

# Search your knowledge
garden search "machine learning"
```

### 4. Study with flashcards

```bash
# Review due flashcards (spaced repetition)
garden review
```

### 5. Discover insights

```bash
# Find surprising connections between concepts
garden surprise

# Generate ideas on a topic using your knowledge
garden ideate "project ideas"
```

## Commands Reference

| Command | Description |
|---------|-------------|
| `garden ingest <path> [--tag TAG]` | Load files (.txt, .md, .pdf), chunk, embed, and store them |
| `garden chat [-r ROLE] [-s SOURCE]` | Interactive chat with role-based reasoning and optional source filtering |
| `garden sources` | List all ingested documents with chunk counts and tags |
| `garden search <query> [--semantic]` | Search your garden; `--semantic` adds concept graph results |
| `garden links [--concept X] [--depth N]` | Explore the concept graph and connections between ideas |
| `garden review [--count N]` | Spaced repetition flashcard session using the SM-2 algorithm |
| `garden surprise [--count N]` | Surface unexpected cross-domain insights from your knowledge |
| `garden ideate <topic>` | Generate ideas grounded in your stored knowledge |
| `garden status` | Dashboard showing document, chunk, concept, and card counts |
| `garden sessions [list\|show\|delete]` | Browse, inspect, or delete past chat sessions |
| `garden forget <source>` | Remove a specific document and all its associated data |
| `garden clear` | Wipe all data from the garden (requires confirmation) |
| `garden config` | View current configuration |
| `garden config set <key> <value>` | Change a configuration value |
| `garden config models` | List installed Ollama models |
| `garden config use-model` | Interactively switch the active LLM model |
| `garden export [--format FORMAT]` | Export your garden (markdown, anki, or json) |

### Chat Roles

During chat, the AI can switch between different reasoning styles:

| Role | Best for |
|------|----------|
| `general` | Quick, direct answers (default) |
| `analyst` | Deep analysis, comparisons, pattern recognition |
| `summarizer` | Condensing and restructuring information |
| `creative` | Brainstorming, finding novel connections |
| `researcher` | Deep investigation, cross-referencing, fact-checking |

Switch roles during chat with `/switch analyst`, or start in a role with `garden chat --role analyst`. The AI can also auto-detect the best role based on your question.

### In-Chat Commands

While in `garden chat`, you can use these commands:

| Command | What it does |
|---------|-------------|
| `/roles` | Show available roles |
| `/switch <role>` | Switch to a different reasoning role |
| `/auto` | Toggle automatic role detection on/off |
| `drag & drop file` | Drop a .txt, .md, or .pdf file to ingest it inline |
| `quit` or Ctrl+C | Exit the chat |

## Changing Models

The default models are `qwen3.5:9b` (reasoning) and `nomic-embed-text` (understanding documents). You can swap them to any model available in Ollama.

```bash
# See what you're currently using
garden config

# Try a different AI model
garden config set llm_model llama3.1:8b

# Try a different embedding model
garden config set embedding_model mxbai-embed-large
```

Or browse and pick from your installed models interactively:

```bash
# List all installed Ollama models
garden config models

# Interactively choose a model
garden config use-model
```

You can also edit `garden.json` directly or use environment variables:

```bash
PKG_LLM_MODEL=mistral:7b garden chat
```

> **Important:** If you change the embedding model after ingesting documents, run `garden clear` and re-ingest everything. Different embedding models produce incompatible vector spaces.

## How It Works

**Ingestion** — Documents are split into chunks, embedded using `nomic-embed-text`, and stored in a local ChromaDB vector database. Concepts are extracted and linked in a knowledge graph. Duplicate files are detected by content hash and skipped.

**Chat** — Questions go through a LangGraph agent pipeline: routing, role detection, retrieval, relevance grading, and answer generation with source citations. If retrieved documents aren't relevant, the query is automatically rewritten (up to 2 retries).

**Concept Linking** — Concepts extracted from different documents are connected based on co-occurrence, shared terminology, and embedding-based semantic similarity.

**Spaced Repetition** — Flashcards are generated from your content and scheduled using the SM-2 algorithm. Cards resurface at increasing intervals based on recall quality.

**Insights** — The surprise engine finds distant cross-source concept pairs in the knowledge graph and asks the AI to identify non-obvious relationships.

## Data Storage

All your data stays local in the `data/` directory (gitignored):

```
data/
├── chroma/     # Vector embeddings (ChromaDB)
└── garden.db   # Flashcards, concepts, graph, document registry (SQLite)
```

To start fresh, run `garden clear` or delete the `data/` directory.

## Troubleshooting

**"Connection refused" or "Ollama not found"**
- Make sure Ollama is running. On most systems it starts automatically after installation. Try: `ollama serve`

**"Model not found"**
- You need to download models first: `ollama pull qwen3.5:9b` and `ollama pull nomic-embed-text`

**Chat gives wrong or irrelevant answers**
- Try `garden chat --source <filename>` to focus on a specific document
- Try `garden chat --role analyst` for deeper reasoning
- Make sure you've actually ingested the document: check with `garden sources`

**"No documents ingested yet"**
- Run `garden ingest <your-file>` first. Supported formats: `.txt`, `.md`, `.pdf`

**Want to start over?**
- `garden forget <source>` removes one document
- `garden clear` removes everything

## Privacy

Everything runs locally. Your documents, embeddings, and knowledge graph never leave your computer. The LLM runs through [Ollama](https://ollama.com) on localhost. There are no API calls to external services, no telemetry, no cloud storage.

## Tech Stack

| Component | Choice |
|-----------|--------|
| LLM | Ollama — qwen3.5:9b |
| Embeddings | Ollama — nomic-embed-text |
| Framework | LangChain + LangGraph |
| Vector Store | ChromaDB (embedded, local) |
| Database | SQLite |
| CLI | Click + Rich |
| Prompts | Jinja2 templates |
| Package Manager | uv |
| Testing | pytest (345+ tests) |

## Testing

```bash
uv sync --extra dev        # Install dev dependencies
uv run pytest              # Run all tests
uv run pytest -v           # Verbose output
uv run pytest --cov=garden # With coverage report
```

## Disclaimer

**The author is not responsible for any content generated by the AI models used in this program.** All generated output — including flashcards, insights, concept links, and chat responses — is produced by third-party large language models running locally on your machine. The author makes no guarantees about the accuracy, completeness, or appropriateness of any generated content.

By using this software, you acknowledge and agree that:

- You are solely responsible for how you use this program and any content it generates.
- You must comply with all applicable laws, regulations, and government rules in your jurisdiction.
- The author bears no liability for any damages, losses, or legal consequences arising from the use of this software or its generated output.
- It is your responsibility to verify and validate any information produced by this tool before relying on it.

## License and Distribution

**All rights reserved.** This software is provided for personal, individual use only.

- **No distribution** of this software is permitted, whether paid or free, in whole or in part.
- **No integration** into other projects, products, or services — commercial or non-commercial — is allowed without explicit written permission from the author.
- **No modification and redistribution** — you may not create derivative works for distribution.
- For any inquiries regarding licensing, integration, or use beyond personal use, you must contact and consult with the author directly.

Unauthorized distribution, reproduction, or integration of this software is strictly prohibited.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.
