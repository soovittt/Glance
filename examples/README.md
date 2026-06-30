# Examples

## `run_browser_agent.py` — the real end-to-end test ⭐

A **real Claude computer-use agent** driving a **real headless browser**, with
Glance hooked into the screenshot step. It runs an actual task and prints the real
token usage plus Glance's exact savings on that run. This is the proof that Glance
works with Claude computer use.

```bash
pip install -e ".[examples]"
playwright install chromium
export ANTHROPIC_API_KEY=...

# Glance ON (default):
python examples/run_browser_agent.py --task "Go to example.com and click the 'More information' link"

# Baseline (Glance OFF) for comparison:
python examples/run_browser_agent.py --task "...same task..." --no-glance

# Watch it happen in a visible window:
python examples/run_browser_agent.py --task "..." --headful
```

What you'll see at the end:

```
============================================================
  Glance: ON
  frames=18 skipped=6 (33%) tokens=14310 vs baseline=21390 saved=7080 (33%)
  real API tokens this run: input=21044 output=512
  >>> Glance skipped 6 redundant screenshots, ~7080 image tokens (33%) on THIS run.
============================================================
```

The `saved` number is apples-to-apples: it's what Glance sent vs. what the *same
trajectory* would have sent without it — no cross-run noise.

> Note: this spends real API tokens and needs network. Coordinates from the
> `computer` tool map directly onto the browser viewport (`WIDTH`x`HEIGHT`).

## `anthropic_loop.py` — the minimal shape

A trimmed, illustrative computer-use loop showing exactly where Glance plugs in
(the line marked `# <-- GLANCE`) without the browser plumbing. Read this first if
you just want to see the integration seam.
