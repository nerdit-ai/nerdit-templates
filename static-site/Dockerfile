# Static site on nginx, as a NON-ROOT image.
#
# Nerdit runs every container with all Linux capabilities dropped and
# no-new-privileges by default. The stock `nginx` image's entrypoint chowns its
# cache directories as root and dies under that profile
# (`chown(...) Operation not permitted`). nginx-unprivileged runs as uid 101,
# owns its own directories, and listens on 8080 — which is why it is the
# documented base for static sites on Nerdit.
FROM nginxinc/nginx-unprivileged:alpine

# Your site. Replace everything under site/ — index.html is the entry point.
COPY site/ /usr/share/nginx/html/

EXPOSE 8080
