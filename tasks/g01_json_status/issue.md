You are a monitoring assistant. Produce a JSON object that summarizes the current status of a web service called "payments-api".

Requirements:
- Output must be a single valid JSON object and nothing else (no extra text, no markdown code fences, before or after it).
- It must have a field "status" whose value is exactly "ok".
- It must have a field "service" whose value is the service name.
- It must have a field "message" whose value is a short human-readable status message.
- The total length of your answer (as plain text) must be between 40 and 300 characters.

Put your final JSON answer after a line that says exactly:
--- ANSWER ---
