# Superseded — Historical Engineering Intelligence Toolchain Plan

**Superseded on:** 2026-11-04  
**Binding replacement:** [Principle 13 — Fully CUBI-owned, model-free Engineering Command Assistant](PRODUCT_PRINCIPLES.md) and [CUBI_INTERNAL_COMMAND_ASSISTANT_PRINCIPLE.md](CUBI_INTERNAL_COMMAND_ASSISTANT_PRINCIPLE.md).

This document's former architecture and toolchain recommendations are retained in Git history for audit context only. They are **not an implementation authority** after the owner-approved 2026-11-04 decision.

In particular, do not implement or preserve as supported options any local or remote AI model, Ollama, ChatGPT, OpenAI-compatible model endpoint, provider abstraction, external AI service, AI API/key, embeddings model, pretrained speech/OCR/language model, or provider fallback described in the former version of this document. These options are prohibited, including as optional or future alternatives.

The non-conflicting capability requirements from the former plan remain in scope only where restated in the binding replacement document: command understanding, typed project tools, project creation, safe execution, file/document intake, reporting, durable knowledge and learning, authorized research, backup/restore, multilingual support, voice, security, audit and cross-client integration.

The assistant is command-oriented, not an open-ended chatbot. All assistant intelligence and command logic must be implemented as CUBI-owned technology without third-party AI/ML inference models or external AI providers.

Do not use the former provider/model work packages, architecture diagrams or acceptance language as a basis for new implementation. Use the binding replacement document and Principle 13 instead.
