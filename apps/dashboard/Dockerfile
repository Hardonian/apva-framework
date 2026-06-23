FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

# Use Nginx to serve the static bundle
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
# SPA configuration for React Router (if needed)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
