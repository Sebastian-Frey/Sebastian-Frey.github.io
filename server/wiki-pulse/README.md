# Wiki Pulse — service

Live topic-cluster view of English Wikipedia edits. Single FastAPI process
that runs the Wikimedia SSE ingestor, a MiniLM embedder, HDBSCAN + UMAP
clustering loops, and a REST + WebSocket API. Deployed alongside Eternal
Chess on the existing DigitalOcean VPS.

See `../../docs/wiki-pulse-plan.md` for the full plan and
`../../docs/wiki-pulse-adr.md` for the hybrid DuckDB-on-VPS +
Supabase storage decision.

## Layout

```
app/                FastAPI app package
  main.py           entrypoint (routes + background tasks)
  ingestor.py       Wikimedia SSE → queue        [stub in phase 1]
  bucketer.py       queue → DuckDB edit_buckets  [stub in phase 1]
  embedder.py       MiniLM embed + upsert        [stub in phase 1]
  clusterer.py      HDBSCAN + UMAP loops         [stub in phase 1]
  api.py            REST routes
  ws.py             WebSocket route
  storage.py        DuckDB + Supabase clients
  labels.py         c-TF-IDF labelling           [stub in phase 1]
  umap_state.py     Procrustes-aligned UMAP      [stub in phase 1]
  config.py         env-driven constants
migrations/
  001_init.sql      paste into Supabase SQL editor
Dockerfile
requirements.txt
```

## Environment

| var | purpose |
|---|---|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | server-side key (never shipped to the browser) |
| `WIKIPULSE_DATA_DIR` | DuckDB + UMAP artefact dir, default `/var/lib/wikipulse` |
| `WIKIPULSE_USER_AGENT` | Wikimedia requires a contact UA |
| `WIKIPULSE_MIN_CLUSTER_SIZE` | HDBSCAN `min_cluster_size`, default 15 |

## Deploy

1. Run `migrations/001_init.sql` in the Supabase SQL editor.
2. Ensure the VPS `.env` has the variables above.
3. `cd server && docker compose up -d --build wikipulse`
4. `curl https://wiki.itssebastianfrey.com/api/stats` to verify.
