# Gemini-Powered Ecosystem Narration — Entry Task

A Python script that reads marine ecosystem simulation events (CSV or JSON)
and produces a **2–4 sentence scientific narration** using the Gemini 1.5 Pro
API. A fully deterministic **mock mode** is included so the script runs
end-to-end without any API key.

---

## Repository structure

```
ecosystem-narration/
├── ecosystem_narrator.py        # Main script
├── data/
│   ├── ecosystem_events.csv     # Sample events (CSV)
│   └── ecosystem_events.json    # Same events (JSON envelope)
├── outputs/
│   ├── ecosystem_events_mock_output.txt    # Pre-generated mock output (CSV input)
│   └── ecosystem_events_json_mock_output.txt
├── tests/
│   └── test_narrator.py         # Unit tests (no API key needed)
└── README.md
```

---

## Requirements

- Python 3.10 or later (uses `list[dict]` type hints)
- No third-party packages needed for mock mode
- `google-generativeai` only required for live Gemini mode:

```bash
pip install google-generativeai
```

---

## Quickstart — mock mode (no API key)

```bash
python ecosystem_narrator.py --input data/ecosystem_events.csv --mock
```

```bash
python ecosystem_narrator.py --input data/ecosystem_events.json --mock
```

Add `--save-output` to write the result to `outputs/`:

```bash
python ecosystem_narrator.py --input data/ecosystem_events.csv --mock --save-output
```

---

## Live Gemini mode

Set your API key as an environment variable (recommended):

```bash
export GEMINI_API_KEY="your-key-here"
python ecosystem_narrator.py --input data/ecosystem_events.csv
```

Or pass it directly:

```bash
python ecosystem_narrator.py --input data/ecosystem_events.csv --api-key YOUR_KEY
```

---

## CLI reference

| Flag | Short | Description |
|---|---|---|
| `--input PATH` | `-i` | Path to `.csv` or `.json` event file (required) |
| `--mock` | `-m` | Use deterministic mock instead of Gemini API |
| `--api-key KEY` | `-k` | Gemini API key (overrides `GEMINI_API_KEY` env var) |
| `--save-output` | `-s` | Save formatted result to `outputs/` directory |

If no API key is found and `--mock` is not set, the script automatically
falls back to mock mode and prints a notice.

---

## How it works

```
Raw events (CSV/JSON)
       │
       ▼
load_events()          — parse rows from file
       │
       ▼
summarise_state()      — condense to compact JSON (population trends,
       │                  temperature range, key events)
       ▼
build_user_prompt()    — inject summary into prompt template
       │
       ├─── API key present? ──► call_gemini()  → Gemini 1.5 Pro response
       │
       └─── mock mode? ────────► call_mock()    → template-driven narration
                                                   (same logical constraints
                                                    as the real prompt)
       │
       ▼
format_output()        — print narration + prompt transparency block
```

### Why a two-stage pipeline?

Rather than sending all 20+ raw CSV rows to the model, `summarise_state()`
first condenses them into a compact JSON object containing population trends,
temperature deltas, and a list of key events. This keeps the prompt short and
deterministic — the same input always produces the same summary — which makes
outputs reproducible and auditable.

---

## Prompt design

**System prompt** (sets the role and hard constraints):

> You are a marine biologist narrating a real-time ecosystem simulation for a
> general science audience. You receive a structured JSON summary derived from
> simulation event data. Your task is to produce exactly 2-4 sentences of
> fluent, scientifically grounded narration that:
>
> 1. Opens with the most ecologically significant event or trend.
> 2. Identifies at least one clear causal relationship.
> 3. Closes with the overall health or trajectory of the ecosystem.
>
> Constraints: use only data present in the JSON; no bullet points; 60–120 words;
> scientifically accurate but accessible.

**User prompt** (injects the live simulation summary as JSON).

Both prompts are printed in every output run for full transparency.

---

## Sample output (mock mode, CSV input)

```
======================================================================
  GEMINI-POWERED ECOSYSTEM NARRATION  —  MOCK MODE
  Input : data/ecosystem_events.csv
  Events: 22  |  Duration: 80.4s
  Temp  : 27.3°C → 30.1°C  (Δ2.8°C)
======================================================================

NARRATION
---------
A rapid thermal spike of 2.8°C — from 27.3°C to 30.1°C — was the
defining event of this simulation window, triggering cascading
responses across multiple trophic levels. The elevated water
temperature drove early bleaching stress indicators on staghorn coral,
while the plankton bloom contracted sharply — a response consistent
with thermal inhibition of phytoplankton growth. Overall, the
ecosystem shows early warning signs of thermal degradation; sustained
temperatures above 29°C will require monitoring for reef-wide
bleaching in subsequent simulation windows.
```

Pre-generated outputs are in the `outputs/` directory.

---

## Running the tests

```bash
python -m pytest tests/ -v
# or without pytest:
python tests/test_narrator.py
```

Tests cover data loading, state summarisation, prompt building, mock
narration output, and command-line argument parsing — all without
requiring an API key.

---

## Extending this for the full project

This entry task is a minimal slice of the full
[Gemini-Powered Ecosystem Narration and Analysis Interface](https://summerofcode.withgoogle.com/)
project. The intended extension path is:

1. Replace file input with a live WebSocket feed from Unity (C#)
2. Call `summarise_state()` on a rolling 2-second window
3. Stream narration back to a Unity UI overlay in real time
4. Add a second prompt mode for causal explanation on user query
5. Add natural-language-to-spawn-command parsing with a validation layer
