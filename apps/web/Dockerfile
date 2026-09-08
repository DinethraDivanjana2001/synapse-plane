FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install --fetch-retries=5 --fetch-retry-mintimeout=5000 --fetch-retry-maxtimeout=60000
COPY . .
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
