# syntax=docker/dockerfile:1

# Runtime image serving static files via nginx
FROM nginx:stable-alpine AS runtime

# Copy built assets
COPY ./dist/ /usr/share/nginx/html/

EXPOSE 80

