# Provider distill index

Machine facts: `src/tollgate/distill/*.json`  
Loader: `from tollgate.distill.loader import load_distill, research_view`

| ID | File | Notes |
|----|------|--------|
| deepseek | deepseek.json | system LLM |
| worker | worker.json | worker key |
| brave | brave.json | search + rate headers |
| elevenlabs | elevenlabs.json | TTS floor |
| openrouter | openrouter.json | free/paid chain |
| nvidia | nvidia.json | NIM |
| minimax | minimax.json | media |
| opencode_zen | opencode_zen.json | free chat |
| google | google.json | **high risk, off by default** |
| telegram | telegram.json | optional |

Update distill JSON when provider docs change — not scattered Python.
