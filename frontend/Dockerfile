FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci --no-audit --no-fund

COPY public ./public
COPY src ./src
COPY tsconfig.json ./

RUN npm run build

FROM node:18-alpine

WORKDIR /app

RUN npm install -g serve@14.2.4 --no-audit --no-fund

COPY --from=builder /app/build ./build

EXPOSE 3000

CMD ["serve", "-s", "build", "-l", "3000"]
