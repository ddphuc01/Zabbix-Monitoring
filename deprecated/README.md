# Deprecated Services

This directory contains AI services that are no longer in active use.

## Moved Services (2026-01-18)

### Removed AI Providers
- **Google Gemini API** - Replaced by Groq as primary AI provider
- **Ollama** - Local LLM server no longer needed
- **Qwen** - Local model replaced by cloud-based Groq

### Reason for Deprecation
The project has standardized on **Groq API (Llama 3.3-70B)** as the sole AI provider for:
- ✅ Better performance and speed
- ✅ Free tier (14,400 requests/day) sufficient for production
- ✅ Simplified architecture (fewer moving parts)
- ✅ Reduced resource consumption (no local LLM)

### Directory Structure
```
deprecated/
├── ai-services/
│   └── qwen-wrapper/          # Local Qwen LLM wrapper
├── docs/
│   ├── QWEN_QUICKSTART.md     # Qwen setup guide
│   └── QWEN_TEST_RESULTS.md   # Qwen testing results
└── scripts/
    └── telegram_qwen.sh       # Qwen Telegram integration script
```

### If You Need to Restore
To restore any service:
1. Copy files back to original locations
2. Uncomment relevant sections in `docker-compose.yml`
3. Add required environment variables to `.env`
4. Run `docker-compose up -d`

---
**Archive Date:** 2026-01-18  
**Archived By:** Cleanup Phase 1
