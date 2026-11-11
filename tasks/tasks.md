# Task suites

| ID | Task | Needs | Scoring |
|---|---|---|---|
| T1 | Code generation: Terraform module (hub VNet + NSGs) and Python interval-merge | none | auto: `terraform validate`, `tflint`, pytest |
| T2 | Debugging: 5 seeded-bug snippets (py/HCL/PowerShell) | none | auto: tests pass after fix |
| T3 | Video summary: extract knowledge from one chosen video | ffmpeg frames + whisper transcript + vision model | rubric 0-3: key points recalled vs human checklist |
| T4 | Azure currency Q&A: 10 questions on recent Azure resources/AVM/policy | web search tool | rubric: answer matches Microsoft Learn on date of run; cites source |
| T5 | Deal hunt: best price for Logitech Ergo (MX Ergo S / Ergo M575) | web search tool | rubric: real URL, price, retailer, in-stock; human spot-check |
| T6 | Image generation: 5 fixed prompts | separate image stack | human 0-3 on prompt fidelity; time per image |
| T7 | Context stress: recall fact at 12k and 28k tokens | none | auto: exact match |

## Rules
- Search tasks (T4, T5) need a tool-calling harness: give each model the same search tool and cap results to ~1.5k tokens each.
- Record tool-call validity (JSON parses, right args) separately from answer quality.
- Never let a model act on live purchases; T5 reports only.

## Inputs needed from user
- A video (URL or file) for T3.
- Preferred Ergo model and region/currency for T5.
- Image model choice or approval to research one for T6.
