// Nerdit template: a minimal Node/Express web starter.
// Deploys as-is with Nerdit's Node buildpack (npm install + npm start).
const express = require("express");

const app = express();
const PORT = process.env.PORT || 3000;

// Liveness probe — Nerdit health-checks this path.
app.get("/health", (_req, res) => res.json({ status: "ok" }));

app.get("/", (_req, res) => {
  res.type("html").send(`<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Nerdit Node Starter</title>
  <style>
    :root { color-scheme: light dark; }
    body { font-family: system-ui, sans-serif; margin: 0; min-height: 100vh;
           display: grid; place-items: center; background: Canvas; color: CanvasText; }
    main { text-align: center; padding: 24px; }
    h1 { margin: 0 0 8px; font-size: 1.6rem; }
    p { margin: 4px 0; opacity: .8; }
    code { background: rgba(127,127,127,.18); padding: 2px 6px; border-radius: 6px; }
  </style>
</head>
<body>
  <main>
    <h1>🚀 Node Starter</h1>
    <p>Deployed on Nerdit. Edit <code>server.js</code> and redeploy.</p>
    <p>Health check at <code>/health</code>.</p>
  </main>
</body>
</html>`);
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`node-starter listening on ${PORT}`);
});
