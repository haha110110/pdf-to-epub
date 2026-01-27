# Build Stage
FROM node:18-alpine as build

# Use host proxy
ENV http_proxy="http://127.0.0.1:10809"
ENV https_proxy="http://127.0.0.1:10809"

WORKDIR /app

COPY package.json package-lock.json* ./
# Remove registry mirror to use official npm
RUN npm install --legacy-peer-deps

COPY . .
RUN npm run build

# Production Stage
FROM nginx:alpine

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
