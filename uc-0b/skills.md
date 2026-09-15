skills:
  - name: retrieve_policy
    description: Loads the supplied plain-text HR policy and returns its numbered clauses as structured sections.
    input: "A readable .txt policy file path or UTF-8 text containing the HR leave policy and its numbered clauses."
    output: "A structured list of sections, where each item contains the clause number and the exact clause text, preserving the source order."
    error_handling: "Reject missing, unreadable, non-text, or empty input. Do not infer missing clauses. If numbering is ambiguous or a clause boundary cannot be determined, retain the exact text and flag the affected section for review."

  - name: summarize_policy
    description: Produces a clause-referenced HR policy summary from structured policy sections without changing their meaning.
    input: "A structured list of numbered policy sections containing clause numbers and source text."
    output: "A UTF-8 plain-text summary containing one identifiable entry for every source clause, with clause references, all conditions, thresholds, deadlines, approvers, exceptions, and consequences preserved."
    error_handling: "Reject missing or incomplete sections and report which clause references are absent. Never fill gaps from outside knowledge. If compression could change meaning, quote the affected clause verbatim and add an explicit review flag; do not soften or omit obligations."
