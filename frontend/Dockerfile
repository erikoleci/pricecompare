# Build the static SPA, then serve it with nginx. `npm run build` itself
# (vue-tsc -b && vite build) WAS verified in the development sandbox - see
# README Phase 5/7 notes. Only the Docker packaging around it is untested,
# since Docker Hub isn't reachable from that sandbox either.

FROM node:20-alpine AS build
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
