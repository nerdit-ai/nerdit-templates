# nerdit-templates

Curated app templates for the [Nerdit](https://github.com/nerdit-ai) store.
Each subdirectory is a self-contained app with its own `nerdit.toml`, deployable
in one command:

```bash
nerdit store list
nerdit store deploy <id> --name my-app
```

| id | subdir | stack | AI |
|----|--------|-------|----|
| `fastapi-ai-chat` | [`fastapi-ai-chat/`](fastapi-ai-chat) | Python · FastAPI | ✅ `[ai.default]` (Ollama) |
| `fastapi-api-starter` | [`fastapi-api-starter/`](fastapi-api-starter) | Python · FastAPI | — |
| `node-starter` | [`node-starter/`](node-starter) | Node · Express | — |

## Versioning

The Nerdit store pins each entry to a **git tag** (e.g. `v1.0.0`), so the
catalog never drifts under users. A template changes only when the catalog is
updated to point at a new tag. To add a template: add a subdir with its own
`nerdit.toml`, then add a catalog entry in the Nerdit repo's
`config/app_templates/builtin.json`.

## License

MIT
