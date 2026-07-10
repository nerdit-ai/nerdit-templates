# node-starter

A minimal Node/Express web starter. Deploys as-is with Nerdit's Node buildpack
(`npm install` + `npm start`) — no build step. Serves a landing page at `/` and
a health check at `/health`.

## Deploy via the store

```bash
nerdit store deploy node-starter --name my-site
```

## Run locally

```bash
npm install
npm start
```
