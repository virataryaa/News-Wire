# Commodity Wire — Status & GPU/Speed Investigation Notes

Last updated: 2026-09-14

## Current production state (this is what's actually live, untouched by today's experiments)

- **Summarizer**: Ollama, model `qwen2.5:14b`, forced **CPU-only** via `"num_gpu": 0`
  in `scripts/summarize.py` (the `_via_ollama` call). This is deliberate and safe,
  see findings below for why GPU isn't the default yet.
- **Chunk size**: `OLLAMA_CHUNK_SIZE = 15` in `scripts/summarize.py`.
- **Backlog cap**: `MAX_NEW_ITEMS_PER_RUN = 20` in `scripts/build.py`, keeps a single
  run from ballooning if the automation was off for a few days.
- **Fallback chain**: Ollama → Claude Code CLI (`claude -p`, uses the Pro
  subscription login, not the paid API) → rule-based filter. All three tiers exist
  so the pipeline never fully fails, but the Claude tier costs subscription usage,
  so today's GPU tests were deliberately run with that fallback disabled to keep
  this investigation token-free.
- Task Scheduler (`CoffeeWire Daily`, 7:00 AM) runs this exact CPU-only config
  every day. Nothing here needs fixing to keep that working, it already works,
  just slowly.

## The actual complaint being investigated

CPU inference works but is slow (~0.23s/token) and a full backlog run can take
several minutes. GPU is ~6.6x faster but heats the laptop noticeably under sustained
load. Today's session was about finding a middle ground. Short answer: **not solved
yet**, see below.

## What was tested today

### 1. Tiny/smaller models (to trade size for speed)
- `llama3:latest` (8B): ~1.7-1.8x faster than `qwen2.5:14b` on CPU, but **invented a
  fake "10% increase" statistic** that wasn't in the source. Rejected.
- `qwen2.5:1.5b`: ~4-6.5x faster, but hallucinated entire fabricated narratives
  (e.g. "this is the first significant rainfall since the previous harvest") and
  reused the exact same boilerplate sentence across two unrelated commodities.
  Confirms the pattern: smaller model = faster but *more* confidently wrong, not
  less. Rejected, more firmly than llama3.
- **Conclusion**: `qwen2.5:14b` is the floor for acceptable accuracy among locally
  available models. Don't go smaller.

### 2. Extractive summarization (`sumy`, TextRank) instead of an LLM entirely
- Installed cleanly, ran in 0.02-0.06s (basically free, zero heat).
- **Useless for our actual data**: most source items are a single headline with no
  article body. Extractive summarization picks among *existing* sentences, so on a
  one-sentence input it just echoes the same sentence back unchanged, no
  "detailed_summary" value added. Only would have helped on the handful of sources
  that already give multi-sentence text (Cecafe, Hedgepoint).
- **Conclusion**: not a fit given the input shape. Dead end.

### 3. CPU thread-count tuning (`num_thread`)
- Tested `None` (auto), 16, 24, 32 threads on the 24-core/32-thread i9-13950HX.
- No meaningful difference (61.8s-79.2s range, no trend, just noise).
- **Conclusion**: likely memory-bandwidth bound, not core-count bound. Not a lever.

### 4. GPU, full offload (`num_gpu: 48`, all layers on the RTX 4000 Ada)
- Isolated small tests (1-4 fake items): consistently ~0.03-0.035s/token,
  ~6.6x faster than CPU. Fast and clean *on small, clean, hand-written test items*.
- **Real-data results were inconsistent**, see table below.

### 5. GPU, half offload (`num_gpu: 24` of 48 layers)
- ~0.125s/token, ~1.8x faster than CPU but ~4x slower than full GPU.
- Only tested once on a small hand-written sample, not on real backlog data.
- Genuine middle ground if reliability can be sorted out, untested at scale.

### 6. GPU power-limit capping (`nvidia-smi -pl`)
- Would let us run full GPU speed but cap wattage/heat directly.
- **Blocked**: "Changing power management limit is not supported in current scope"
  without admin rights. Not attempted further, would need the user to run something
  as Administrator.

## Real-data GPU reliability results (the actual blocker)

Ran genuinely-new, real fetched headlines (not test fixtures) through
`qwen2.5:14b` on full GPU, Claude fallback explicitly disabled so a chunk failure
just gets logged and skipped rather than silently costing tokens.

| Commodity | Items | Chunk size | Result |
|---|---|---|---|
| Cocoa | 13 | 10 | **Clean**: 50.1s total, 0 failures, kept 4 |
| Coffee | 37 | 15, then 10 | Both attempts mostly failed (malformed JSON / full timeouts), only a small trailing chunk succeeded each time |
| Sugar | 55 | 10 | Mostly failed: 4 of 6 chunks failed (2 malformed JSON, 2 full 300s timeouts), 782.3s total wasted, only 11 of 55 kept |
| Cotton | 33 | — | Not tested, paused here per user's request |

**Root cause is NOT the duplicate-process bug** that caused problems earlier in the
day (verified clean single `ollama` + single `llama-server` process before the
Sugar run, confirmed via `Get-Process`). This is a *different*, still-unexplained
reliability issue: the model intermittently returns malformed JSON (missing the
`"items"` array) or hangs completely for the full 300s timeout with no response,
even on a clean single-instance server, even at the smaller chunk size of 10.

No clear pattern found yet for *why* Cocoa's 10-item chunks worked perfectly while
Sugar's 10-item chunks mostly failed. Candidates not yet investigated:
- GPU/VRAM pressure accumulating over a long-running server session (many
  back-to-back generations without a restart) rather than being pinned to any
  single chunk's content.
- Something about specific headline content/length in the Sugar batch specifically
  (would need to isolate which sub-items, if any, are triggering it).
- `num_gpu: 48` may be an unusual value (the model has exactly 48 layers, so this
  forces *all* of them to GPU with none held back as headroom, worth trying 47 or
  44 instead of the exact max).

## Recommended next step (not yet done)

**Add retry logic**: if a chunk fails (malformed JSON or timeout), automatically
retry once (maybe with a short delay, or a fresh Ollama server restart between
attempts) before giving up on it. Today's failures were never retried, they were
deliberately left to fail and get logged so the reliability problem would be
visible rather than masked by an automatic Claude fallback. It's very possible a
simple retry turns most of today's failures into successes.

Until that's added and tested, **stay on the current CPU-only default**, it's
slow but has been 100% reliable in every test this week, including the two full
production runs that pushed real data to GitHub successfully.

## Also fixed today (already committed, unrelated to the GPU question)

- `detailed_summary` prompt no longer produces trading-recommendation language
  ("watch whether...", "the thing to watch is..."), purely descriptive now, per
  explicit user request. Applies to new items only, existing history items with
  the old phrasing were deliberately left to age out rather than backfilled.
- `num_gpu: 0` is now set directly in the API call (not via `CUDA_VISIBLE_DEVICES`
  environment variable), because the env-var approach kept silently reverting to
  GPU after Ollama restarts. This part is solid and committed.
- Fixed a recurring bug today where testing repeatedly left two `ollama`/
  `llama-server` processes running simultaneously, causing extreme slowdowns
  (timeouts) unrelated to CPU vs GPU choice. Cause was manually starting
  `ollama serve` without checking if one was already running first. `run.bat`
  already does this check correctly; this was only a problem during today's
  manual testing, not in the actual scheduled pipeline.

## If picking this back up tomorrow

1. Ollama server is currently **stopped** (paused deliberately, see above). It
   will auto-start again via `run.bat`'s self-healing check on the next real run,
   or you can start it manually: `ollama serve` (check nothing's already running
   on port 11434 first).
2. Production pipeline itself was never touched by today's experiments, it's
   still on the safe CPU-only, chunk-15, cap-20 config and will run fine as-is if
   you just want it to keep working while this gets sorted out.
3. If you want to keep investigating GPU speed, start with the retry-logic idea
   above rather than re-testing the same unreliable config.
