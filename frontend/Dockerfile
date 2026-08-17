# 前端镜像：多阶段构建 —— Node 编译出静态资源 → nginx 托管并反代后端
FROM node:20-alpine AS build
# 可用 --build-arg / compose 环境变量覆盖为国内 npm 镜像
ARG NPM_REGISTRY=https://registry.npmjs.org
WORKDIR /app
COPY package*.json ./
RUN npm install --registry=${NPM_REGISTRY}
COPY . .
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
