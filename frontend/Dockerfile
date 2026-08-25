ARG NODE_IMAGE=docker.arvancloud.ir/node:20-alpine
ARG NGINX_IMAGE=docker.arvancloud.ir/nginx:1.27-alpine

FROM ${NODE_IMAGE} AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm config set registry https://registry.npmjs.org/ \
    && npm config set cache /root/.npm \
    && npm ci --prefer-offline --no-audit --progress=false

COPY . .

ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ARG VITE_LIVE_REPLAY_ENABLED=false
ENV VITE_LIVE_REPLAY_ENABLED=${VITE_LIVE_REPLAY_ENABLED}

RUN npm run build

FROM ${NGINX_IMAGE}

COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY nginx/security-headers.conf /etc/nginx/conf.d/security-headers.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
