# Prompt Design

Both classifiers get the same **shared context** (system description, FR/NFR definitions, boundary rules, output rules), followed by their own **task**. Full prompt texts are in [`classify.py`](../classify.py) (v1) and [`prompts_v2.py`](../prompts_v2.py) (v2).

## Why two different classifiers

| | Classifier A | Classifier B |
|---|---|---|
| Model | `deepseek-flash` | `deepseek-v4-pro` |
| Thinking mode | off (temperature 0) | on |
| How it decides | Compares the requirement with the definitions and boundary rules | Asks what a tester would check, then labels from that |
| Output | `id`, `label`, `reason` | `id`, `test_focus`, `label`, `reason` |

The two classifiers judge the same requirement independently. Neither ever sees the other's answer. When they disagree, that row is flagged for human review. The idea is to use the disagreement between two viewpoints as a cheap signal of difficulty.

**Known limitation:** A and B differ in model, in thinking mode **and** in prompt. A disagreement therefore cannot be blamed on any single one of these. This was pointed out during development and accepted, because the goal was to flag rows for review, not to compare prompting methods.

## v1 boundary rules (used for the official run)

| Rule | Meaning |
|---|---|
| R1 | Numbers alone do not make a requirement NFR. A limit on a behaviour is FR; a measured quality level is NFR. |
| R2 | For mixed requirements: if it were removed, would the system lose a capability (FR) or only perform worse (NFR)? |
| R3 | A privacy or security option the user operates is FR; a protection property of the system is NFR. |
| R4 | A general quality statement with no specific behaviour is NFR. |
| R5 | Judge only what is written. |

The script also enforces the output rules. The reply must be a single JSON object, the label must be FR or NFR, the ID must be copied back exactly, required fields must be present, and the reason must be at most 30 words. Otherwise the call is retried up to 2 times, and then marked `INVALID`.

## What the v1 results showed

The prompt was audited using the 5,324 v1 results. "Survey sheet" below means the sheet (FR or NFR) the student was filling in. It shows the student's intent and is **not** an expert answer key.

1. **B's Step 2 leaned towards FR.** "After an input, the system does or shows something" also matches NFRs such as encryption or error logging. On the NFR sheet, B labelled FR more often than A did (Reliability 18% vs 7%, Security 20% vs 13%). B labelled "stored with encryption" as FR, which breaks R3.
2. **Missing quality attributes.** The NFR definition did not list accuracy, testability or reusability, and the survey has questions on all three. 27–33% of Accuracy answers were labelled FR.
3. **No rule for developer-facing features.** Error logs, health-check endpoints and mock interfaces were labelled FR.
4. **No rule for short phrases or multi-requirement cells.**

## v2 changes

- Added the missing quality attributes to the NFR definition.
- **R3** now says that a protection mechanism the system enforces is NFR, even when it is described as an action (encryption, authentication strength, role-based access, session timeout).
- **R6** (new): internal support that only helps maintenance, diagnosis or testing is NFR. An action given to a named role, such as an administrator, stays FR.
- **R7** (new): accuracy. The precision target of an output is NFR; producing the output at all is FR.
- **R8** (new): reliability. Behaviour that keeps the service working or prevents data loss is NFR.
- **R9** (new): a short phrase that names a feature is FR; one that names a quality is NFR.
- **R10** (new): for a cell with several requirements, label the main one and start the reason with `Mixed:`. Revised after Codex review so that **sentence order never decides the label**.
- **B Step 2** now asks how a failed test would be reported. "Users cannot do X" points to FR. "X works but is too slow, unsafe, unreliable or inaccurate" points to NFR.

## v2 results (on the 244 disputed rows only)

| | v1 A | v1 B | v2 A | v2 B |
|---|---|---|---|---|
| Matches survey sheet | 70.9% | 29.1% | 90.6% | 78.7% |
| FR-sheet rows (33) labelled FR | 12% | 88% | 85% | 91% |
| NFR-sheet rows (211) labelled NFR | 80% | 20% | 91% | 77% |

- On this subset, v2 A and v2 B agree on 197 of 244 rows (80.7%). v1 agreement here is 0% by construction, because the subset contains only disputed rows.
- v2 B changed 127 labels: 123 from FR to NFR and 4 from NFR to FR. It still labels 91% of FR-sheet rows as FR, so the fix did not swing too far the other way.
- 61 reasons start with `Mixed:`.
- The categories with the most remaining disagreement are Accuracy (12), Portability (9) and Usability (7).

**Limitations:** v2 was run only on the hardest rows, with no control group, so these numbers do **not** show that v2 is better on the full dataset. The v1 output remains the official AI result; v2 is used only as a reference column for human reviewers.
