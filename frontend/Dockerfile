# ── MediaShare Frontend — Dockerfile ───────────────────────────────────────
# Frontend/DevOps: KKVRM Kalyanapriya
#
# Uses nginx to serve the 4 static HTML/CSS files

FROM nginx:1.25-alpine

# Remove nginx default page
RUN rm -rf /usr/share/nginx/html/*

# Copy all 4 frontend files into nginx's serve directory
COPY upload.html        /usr/share/nginx/html/upload.html
COPY media-list.html    /usr/share/nginx/html/media-list.html
COPY media-detail.html  /usr/share/nginx/html/media-detail.html
COPY style.css          /usr/share/nginx/html/style.css

# Copy custom nginx config (handles routing + API proxy)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Nginx serves on port 80 → mapped to 8080 on your machine
EXPOSE 80

# Health check
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
