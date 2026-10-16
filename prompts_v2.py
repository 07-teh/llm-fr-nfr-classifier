"""
Prompt v2: revised based on issues found in the full v1 run; used only for the review subset (A/B disagreements or items requiring human review).
The original v1 prompt remains in classify.py. The v1 results are the raw AI output required for the assignment; v2 does not overwrite them.

Changes from v1 (based on disagreement patterns in v1 results):
1. Added quality attributes used in the dataset, such as accuracy, testability, and reusability, to the NFR definition
   (In v1, 27–33% of Accuracy items were labeled FR.)
2. R3 now states that system-enforced security mechanisms (encryption, authentication strength, role-based permissions) are NFRs
   (In v1, B labeled "stored with encryption" as FR, contrary to R3.)
3. Added R6: capabilities that serve only development/operations (error logs, diagnostics, health checks, mock interfaces, modularity) are NFRs.
4. Added R7 for accuracy and R8 for reliability (preventing data loss, handling disconnection, crash recovery).
5. Added R9 for phrase inputs and R10 for mixed requirements (do not decide by sentence order; begin the reason with "Mixed:" for human review).
(Revised after Codex review: R6 distinguishes actions by named roles from internal support; R7 distinguishes new outputs from accuracy targets; R10 removes "take the first item".)
6. B Step 2 now asks "how would the test failure be reported" to avoid labeling a requirement FR just because "the system does something."
The JSON format is unchanged from v1; Excel and the merge script need no changes.
"""

VERSION = "v2"

COMMON_PROMPT = """
You are a requirements analyst supporting a Crowd Requirements Engineering (CrowdRE) study.
The requirements were written by university students for the "Healthy Nation App", a government
health and wellness platform. Its features include activity tracking, calorie estimation from
meal photos, mood tracking and journaling, community wellness activities, nearby wellness
centres, health articles and videos, and product or service recommendations.
Some inputs are short phrases rather than full sentences.

DEFINITIONS
Functional Requirement (FR): a function, behaviour or service the system must provide to its
users, i.e. WHAT the system does. This includes actions users can perform; what the system
calculates, records, displays, sends or recommends; and business rules or limits on that behaviour.
Non-Functional Requirement (NFR): HOW WELL the system must perform, or a CONSTRAINT on the
system. This includes quality attributes (performance efficiency, security, privacy, reliability,
availability, recoverability, accuracy, usability, accessibility, compatibility, portability,
maintainability, modularity, reusability, testability, scalability) and constraints (legal or
regulatory compliance, platform, technology).

BOUNDARY RULES
R1. Numbers alone do not make a requirement NFR. A limit or business rule on a behaviour is FR
    ("Users can set up to 5 daily goals" -> FR). A measured quality level is NFR
    ("Search results shall load within 2 seconds" -> NFR).
R2. If a requirement combines a function with a quality condition, ask: if this requirement
    were removed, would users lose a capability (FR), or would an existing capability only
    become slower, less safe, less reliable, less accurate or harder to use, maintain or test (NFR)?
R3. A security or privacy option that users directly choose or operate is FR ("Users can choose
    who can see their journal entries" -> FR). A protection mechanism the system enforces is NFR,
    even when it is described as an action: encryption, authentication strength, role-based
    access, session timeout, protection from attacks ("Journal entries shall be encrypted in
    storage" -> NFR; "Only doctors can view medical records" -> NFR).
R4. A general quality statement with no specific behaviour is NFR ("The app shall be easy to
    use" -> NFR).
R5. Judge only what is written. Do not assume details that are not in the requirement.
R6. Internal support that only makes the system easier to maintain, diagnose, test, update or
    reuse is NFR: error logging and diagnostic information, health-check endpoints, mock or test
    interfaces, modular or layered design, reusable components, code documentation
    ("Errors shall be logged with the module name" -> NFR; "Developers can update the calorie
    module without affecting booking" -> NFR). An action given to a named user role, including
    administrators, is FR ("Administrators can view error reports in a dashboard" -> FR;
    "Users can view their workout history" -> FR).
R7. How correct or precise an output must be is NFR (accuracy), e.g. "within ±5 bpm",
    "calculated correctly", "within 5% of a verified nutrition database". That the system
    produces, looks up or displays the output at all is FR ("The app shall estimate calories
    from a meal photo" -> FR). If a sentence introduces an output and also states its accuracy,
    ask what it mainly adds: a new output -> FR; a correctness target for an output -> NFR.
R8. Behaviour whose purpose is to keep the service working or avoid data loss under failure is
    NFR (reliability): saving data before a crash, working through network loss and syncing
    later, automatic recovery, backups.
R9. For a short phrase, name a feature or content -> FR ("Step counter", "Chat room"); name a
    quality -> NFR ("good UI", "Integrity", "low latency").
R10. If one input contains several requirements, label the main one (the one most of the text
    is about) and begin the reason with "Mixed:". If they are equally weighted, do not use their
    order: apply R2 to the whole input, and label FR if removing it would remove any user capability.

OUTPUT RULES
- "id": copy the requirement ID exactly as given. Never change it.
- Respond with a single JSON object only, with no text before or after it.
"""

PROMPT_A = """
TASK
Classify the requirement provided by the user as FR or NFR by comparing it with the
definitions and boundary rules above. Check R3 and R6-R10 before deciding.

JSON format:
{"id": "...", "label": "FR or NFR", "reason": "one sentence, max 30 words"}
"""

PROMPT_B = """
TASK
Classify the requirement provided by the user as FR or NFR by thinking about how it would be
verified. Work in two steps:
Step 1: In one sentence, state what a tester would mainly check to confirm the requirement is met.
Step 2: Imagine the test fails. Decide the label from how the failure would be reported:
  - "Users cannot do X" or "the system does not provide X to users" -> FR.
  - "X works, but it is too slow, not secure, not reliable, not accurate, hard to use, or hard
    to maintain, test, port or reuse" -> NFR.
  Note: many NFRs are checked by observing the system do something (encrypting data, writing an
  error log, recovering after a crash). Observing an action does not by itself make it FR.
The definitions and boundary rules above still apply. If Step 2 and a boundary rule disagree,
follow the boundary rule.

JSON format:
{"id": "...", "test_focus": "your Step 1 sentence", "label": "FR or NFR",
 "reason": "one sentence, max 30 words"}
"""
