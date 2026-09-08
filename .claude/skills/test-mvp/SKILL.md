---
name: test-mvp
description: Run MVP smoke tests against the local Docker Compose stack. Spawns the mvp-tester agent to hit all four services (Identity :8001, Catalog :8002, Planning :8003, Shopping :8004) and prints a pass/fail table. TRIGGER when the user types /test-mvp or asks to "smoke test the stack", "test the MVP", or "run integration tests".
---

# /test-mvp

Spawn the `mvp-tester` subagent to run the full MVP integration test suite.

```
Agent({
  subagent_type: "mvp-tester",
  description: "MVP smoke test run",
  prompt: "Run the full MVP test suite against the local Docker Compose stack. Follow the test suite in your instructions exactly — all 4 services, all test cases. Print the markdown results table when done."
})
```

When the agent returns its results table, display it to the user as-is.

If Docker is not running or a service health check fails immediately, report which services are down and suggest `docker compose up --build -d` to fix it.
