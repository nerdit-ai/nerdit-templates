# static-site

A static site served by `nginxinc/nginx-unprivileged:alpine` — a **non-root**
image that listens on port 8080. Drop your HTML/CSS/JS under `site/`
(`index.html` is the entry point) and deploy.

Why not the stock `nginx` image: Nerdit runs containers with all Linux
capabilities dropped and no-new-privileges by default, and the stock
entrypoint chowns its cache directories as root, which fails under that
profile. This image owns its directories and needs no privileges.

## Deploy via the store

```bash
nerdit store deploy static-site --name my-site
```

## Run locally

```bash
docker build -t my-site . && docker run --rm -p 8080:8080 my-site
```
