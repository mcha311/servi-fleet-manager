# Stage 1: Build
FROM node:18-alpine AS builder

WORKDIR /app

# 의존성 먼저 설치 (캐싱 최적화)
COPY package*.json ./
RUN npm ci

# 소스 복사 & 빌드
COPY . .
RUN npm run build

# Stage 2: Production
FROM nginx:alpine

# 빌드된 파일만 복사
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx 설정 (API 프록시)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]