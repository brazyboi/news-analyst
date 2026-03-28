## Multi-Agent Tech News Analyst (CLI)

Terminal-first tech news analysis app built with Typer and Rich.

<!-- ![CLI demo](docs/demo.gif) -->
### Setup

1. `uv sync`
2. Add `.env` in repo root with:
   - `ANTHROPIC_API_KEY=...`
   - `NEWS_API_KEY=...`

### Run

From repo root:

```bash
uv run news-analyst analyze --topic "AI chips" --companies NVIDIA,AMD,Intel
```

### More examples

```bash
uv run news-analyst analyze --topic "cloud security" --companies CrowdStrike,Palo Alto Networks,Zscaler
uv run news-analyst analyze --topic "consumer AI devices" --companies Apple,Meta,Amazon --days-back 14
```
