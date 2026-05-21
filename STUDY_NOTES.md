# Maintainer Copilot Study Notes

This file is for rereading the project concepts after we finish each topic.

## RAG Flow

RAG means Retrieval-Augmented Generation. In this project, RAG answers repository questions by first retrieving grounded context from GitHub docs and resolved issues, then asking Groq to answer only from that retrieved context.

Short version:

```text
User question
-> Groq HyDE query expansion
-> SentenceTransformer embedding
-> pgvector dense search
-> BM25 keyword search
-> hybrid scoring
-> cross-encoder reranking
-> Groq grounded answer
-> citat
ions
```

### 1. Knowledge Source Sync

Main file:

```text
services/api/app/services/knowledge_source_service.py
```

This is the indexing step. It builds the knowledge base that RAG searches later.

The service uses:

```text
GitHubIngestClient -> fetch GitHub docs and closed issues
Chunker -> split long documents into smaller chunks
EmbeddingClient -> convert chunk text into vectors
DocumentChunkRepository -> store chunks and embeddings in Postgres/pgvector
```

Important flow:

```python
documents = await self.github.ingest(...)
chunks = self.chunker.chunk(...)
embeddings = self.embeddings.embed([chunk.content for chunk in chunks])
DocumentChunkRepository(session).replace_for_source(source_data.id, chunks)
```

Conceptually:

```text
GitHub repo
-> README/docs/resolved issues
-> chunks
-> embeddings
-> stored in Postgres with pgvector
```

### 2. Embeddings

Main file:

```text
services/api/app/infra/embeddings.py
```

The embedding model is:

```text
sentence-transformers/all-MiniLM-L6-v2
```

It creates vectors with:

```text
384 dimensions
```

Important code:

```python
vectors = self.model.encode(texts, normalize_embeddings=True)
```

This converts text into numeric vectors so the database can search by meaning.

Example:

```text
"How do I install it?"
```

can match:

```text
"Installation instructions"
```

even if the wording is not exactly the same.

### 3. Groq HyDE Query Expansion

Main files:

```text
services/api/app/services/rag_service.py
services/api/app/services/retrieval.py
prompts/hyde.md
```

HyDE means Hypothetical Document Embeddings.

Instead of embedding the raw user question directly, Groq first rewrites the question into a richer hypothetical document.

Example user question:

```text
How do I install requests?
```

Possible HyDE rewrite:

```text
The documentation explains installing Requests with pip, Python package management, and supported setup instructions.
```

Why this helps:

```text
Short or vague question
-> richer search text
-> better semantic retrieval
```

In `rag_service.py`, Groq is passed into retrieval:

```python
llm_client = llm or GroqClient()
retrieval = RetrievalService(llm=llm_client)
```

In `retrieval.py`, HyDE runs here:

```python
transformed_query = await self._hyde(question)
```

If Groq fails during HyDE, the code falls back to the original question:

```python
except Exception:
    return question
```

So HyDE improves retrieval, but it does not break the system if the LLM is temporarily unavailable.

### 4. Dense Search With pgvector

Main file:

```text
services/api/app/services/retrieval.py
```

After HyDE, the transformed query is embedded:

```python
query_embedding = self.embeddings.embed_one(transformed_query)
```

Then pgvector search runs:

```python
dense_chunks = repo.query_dense(...)
```

Dense search is semantic search. It finds chunks with similar meaning.

Good for:

```text
"How do I install it?"
```

matching:

```text
"Installation instructions"
```

### 5. BM25 Keyword Search

Main file:

```text
services/api/app/services/retrieval.py
```

BM25 search runs here:

```python
sparse_scores = _bm25_scores(transformed_query, all_chunks)
```

BM25 is keyword-based search. It is useful for exact technical terms.

Good for:

```text
ValueError
app.py
JWT
Redis
Python 3.11
```

This matters because maintainer questions often include exact filenames, errors, versions, and symbols.

### 6. Hybrid Retrieval

Main file:

```text
services/api/app/services/retrieval.py
```

The project combines dense semantic search and BM25 keyword search.

The score is:

```python
score = self.alpha * dense + (1 - self.alpha) * sparse
```

The current alpha is:

```python
alpha = 0.65
```

Meaning:

```text
65% dense semantic score
35% sparse BM25 keyword score
```

Why hybrid search is useful:

```text
Semantic search understands meaning.
BM25 preserves exact technical terms.
Together they are stronger than either one alone.
```

### 7. Cross-Encoder Reranking

Main file:

```text
services/api/app/services/retrieval.py
```

The reranker model is:

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

It reranks candidate chunks using:

```python
pairs = [(question, item.chunk.content) for item in chunks]
scores = self.reranker.predict(pairs)
```

The first retrieval stage finds possible chunks. The reranker then asks:

```text
For this exact question, which chunk is most relevant?
```

This improves the quality of the final context sent to Groq.

### 8. Grounded Answer Generation

Main file:

```text
services/api/app/services/rag_service.py
```

After retrieval, the code builds a context block:

```python
context = "\n\n".join(
    f"[{index + 1}] {item.chunk.title} ({item.chunk.external_ref})\n{item.chunk.content}"
    for index, item in enumerate(retrieved)
)
```

Then it creates a grounded prompt:

```python
"Answer only from the supplied context. If the context is insufficient, say there is no grounding."
```

This tells Groq:

```text
Do not answer from general knowledge.
Use only the retrieved repository context.
```

Then Groq generates the final answer:

```python
answer = await self.llm.complete(...)
```

### 9. Citations

Main file:

```text
services/api/app/services/rag_service.py
```

The answer includes citations from the top retrieved chunks:

```python
citations = [
    Citation(
        external_ref=item.chunk.external_ref,
        kind=item.chunk.kind,
        title=item.chunk.title,
    )
    for item in retrieved[:3]
]
```

Example citation:

```json
{
  "external_ref": "docs/user/install.md",
  "kind": "doc",
  "title": "Installation"
}
```

Citations make the answer traceable.

### 10. Example Flow

User asks:

```text
How do I install requests?
```

Groq HyDE rewrite:

```text
The Requests documentation explains installation with pip and Python package management.
```

Retrieval:

```text
pgvector finds semantically similar install docs.
BM25 finds exact words like pip and install.
Hybrid scoring merges both.
Cross-encoder reranks the best chunks.
```

Groq final answer:

```text
The documentation says Requests can be installed using pip.
```

Citation:

```text
README.md or docs/user/install.md
```

### 11. What Makes This Advanced RAG

This is more than basic vector search.

Basic RAG:

```text
chunk -> embed -> vector search -> LLM answer
```

This project:

```text
GitHub ingestion
-> chunking
-> embeddings
-> pgvector dense search
-> BM25 sparse search
-> hybrid retrieval
-> Groq HyDE query expansion
-> cross-encoder reranking
-> grounded generation
-> citations
```

Good summary:

```text
The project uses hybrid RAG with Groq-powered HyDE query expansion, SentenceTransformer embeddings, pgvector semantic retrieval, BM25 keyword retrieval, cross-encoder reranking, grounded Groq generation, and citations over GitHub docs and resolved issues.
```
