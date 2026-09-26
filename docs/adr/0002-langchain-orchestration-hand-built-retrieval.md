# LangChain for orchestration, hybrid retrieval built by hand

We use LangChain for model access and orchestration, but build hybrid retrieval (keyword search, embedding search, and rank fusion) ourselves and expose it to LangChain as a custom retriever. The project is learning-first: LangChain's chat-model interface is worth learning and makes switching between free OpenRouter models (development) and Claude Opus 5.5 (evaluation and real use) a config change, but a framework retriever would do the one part that most needs to be done honestly. Embeddings are local sentence-transformers.

## Considered Options

- **The Anthropic SDK directly, no framework.** Rejected: the user wants to learn LangChain in this project, and it gives provider switching for free.
- **LlamaIndex for the whole RAG pipeline.** Rejected: its built-in hybrid retriever would hide the retrieval we set out to learn. Comparing against it as a baseline stays open as an optional exercise.

## Consequences

- Claude is called through LangChain's Anthropic integration, OpenRouter through its OpenAI-compatible client. Real unpublished Drafts only go to Claude, because free OpenRouter endpoints may log and train on prompts.
- Claude Opus 5.5 rejects forced tool choice, so structured output must not rely on LangChain forcing a tool call.
