# Bug: singleton and request lifetimes are not honored

The container ignores the registered scope:

- A `SINGLETON` service is rebuilt on every `resolve` instead of being created
  once and reused for the process.
- A `REQUEST`-scoped service should be the same instance within one request
  context and a different instance across requests; today it is new every call.
- Resolving a request-scoped service without a request context should raise.

`TRANSIENT` (new instance every time) already works.
