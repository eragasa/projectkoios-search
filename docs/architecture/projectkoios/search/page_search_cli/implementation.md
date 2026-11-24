# Page-search CLI implementation

The CLI accepts an explicit database path and either the `status` or `query`
operation. Query limit and offset values pass unchanged to the owner API for
validation. Dataclass and tuple results are recursively converted to JSON-safe
objects; the adapter does not open SQLite or implement ranking.

```mermaid
sequenceDiagram
    participant Operator
    participant CLI
    participant Owner as PageSearchIndex
    Operator->>CLI: status or bounded query
    CLI->>Owner: owner API call
    Owner-->>CLI: immutable DTO
    CLI-->>Operator: sorted JSON
```
