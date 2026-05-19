Summarize the provided issue thread for a maintainer.

Return:
- A one-sentence summary of the problem, request, or question.
- The strongest evidence from the thread.
- Code-shaped entities, filenames, APIs, commands, versions, or error names when present.
- A suggested next action for triage.

Rules:
- Use only the supplied thread.
- Do not infer root cause beyond the evidence.
- Do not expose secrets, tokens, private emails, or stack traces beyond minimal redacted error names.
- If the thread is ambiguous, state what detail is missing.
