# Local Ollama Provider Specification

## 1. Overview
- **Class**: `OllamaProvider` (`src/providers/ollama.py`)
- **Default Model**: `llama3.2`
- **Default Endpoint**: `http://localhost:11434`
- **Dependencies**: Python standard library (`urllib.request`) only - zero external packages required.

---

## 2. API Integration
Communicates with Ollama's local REST API:
1. **Health Check**: Pings `GET http://localhost:11434/api/tags` with a 3-second timeout during `is_available()`.
2. **Analysis Call**: Dispatches `POST http://localhost:11434/api/generate` with:
   - `stream: false`
   - `format: "json"`
   - `options: {"temperature": 0.0}`
3. Parses JSON from `response["response"]` string.
