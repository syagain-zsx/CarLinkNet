# 云服务器部署指南（Anolis OS 8）

本项目已用 **Docker + docker-compose** 打包成两个镜像，前后端一键部署、丝滑移植。服务器上只需装好 Docker，上传代码后一条命令即可运行，无需在服务器上手动装 Python/Node/各种依赖。

## 部署架构

```mermaid
graph LR
    A[🌐 用户浏览器] -->|http 80| B[🖥 nginx 前端容器]
    B -->|静态页面 dist| A
    B -->|反向代理 /api| C[⚙️ FastAPI 后端容器]
    C --> D[(🗄 SQLite + 上传文件<br/>持久卷 ids_persist)]

    style A fill:#BAE1FF,stroke:#4A90D9,stroke-width:2px
    style B fill:#BAFFC9,stroke:#4CAF50,stroke-width:2px
    style C fill:#FFE8BA,stroke:#FFA726,stroke-width:2px
    style D fill:#E8BAFF,stroke:#9C27B0,stroke-width:2px
```

- **前端容器**（nginx）：多阶段构建，Node 编译出 `dist/` 静态资源 → nginx 托管，并把 `/api` 反向代理到后端容器。
- **后端容器**（Python 3.13-slim）：FastAPI + 预训练模型，**CPU 版 PyTorch** 控制镜像体积。
- **持久卷**：SQLite 数据库与上传文件挂载到 `ids_persist`，容器重建不丢数据。

## 新增/改动文件清单

| 文件 | 作用 |
| --- | --- |
| `backend/Dockerfile` | 后端镜像（锁定版本 + CPU torch + 内置模型/数据） |
| `backend/.dockerignore` | 缩小构建上下文，排除运行时产物 |
| `backend/requirements.txt` | 锁定与训练环境一致的精确版本 |
| `backend/app/config.py` | 支持 `IDS_DB_PATH` / `IDS_UPLOAD_DIR` / `IDS_SECRET_KEY` 环境变量覆盖 |
| `frontend/Dockerfile` | 前端多阶段构建镜像 |
| `frontend/nginx.conf` | nginx 静态托管 + `/api` 反代后端 |
| `frontend/.dockerignore` | 排除 node_modules/dist |
| `docker-compose.yml` | 编排前后端 + 持久卷 + 健康检查 |
| `pack.sh` | 本地一键打包（排除无用文件） |
| `.env.example` | 国内镜像加速配置模板（复制为 `.env` 生效） |

---

## 一、服务器端一次性准备（装 Docker）

在 Anolis OS 8 上以 root 或 sudo 用户执行：

```bash
# 1. 安装依赖
sudo dnf install -y dnf-utils device-mapper-persistent-data lvm2

# 2. 添加 Docker CE 仓库（Anolis 8 兼容 CentOS 8 源）
sudo dnf config-manager --add-repo=https://download.docker.com/linux/centos/docker-ce.repo

# 3. 安装 Docker 引擎 + compose 插件
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 4. 启动并开机自启
sudo systemctl enable --now docker

# 5. 验证
docker --version
docker compose version
```

> **若提示 `docker` 包冲突**（Anolis AppStream 自带旧版 moby/docker），先 `sudo dnf remove -y docker`，或用 `sudo dnf install -y docker-ce --allowerasing` 重试。
>
> 如果只想用 `docker-compose`（v1 命令）而非 `docker compose`（v2 插件），把后面的 `docker compose` 换成 `docker-compose` 即可。

### 国内镜像加速（强烈建议）

国内服务器直连 Docker Hub / PyPI / npm 经常超时，按下面两步配置镜像即可丝滑构建。

**① Docker 镜像加速（拉取基础镜像）**

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://hub.rat.dev",
    "https://dockerproxy.net",
    "https://docker.m.daocloud.io"
  ]
}
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker
```

> 镜像地址会不定期变动，若拉取仍慢，可搜索「Docker 镜像加速」获取最新可用地址；阿里云/腾讯云用户也可在控制台开通个人加速器获取专属地址。

**② pip / npm 镜像加速（构建时下载依赖）**

把 `.env.example` 复制为 `.env`（项目根目录，与 `docker-compose.yml` 同级），`docker compose` 会自动读取并套用清华 pip / 阿里云 pytorch / npmmirror 镜像：

```bash
cp .env.example .env
```

不创建 `.env` 也能构建（走官方源），只是国内网络下会慢或失败。

## 二、本地打包并上传

在**本地项目根目录**执行（Windows 用 Git Bash 或 WSL）：

```bash
# 打包（排除 node_modules / __pycache__ / ids.db 等）
bash pack.sh

# 上传到服务器（换成你自己的 IP / 用户名）
scp ids-deploy.tar.gz root@<服务器IP>:/opt/
```

在服务器上解压：

```bash
ssh root@<服务器IP>
mkdir -p /opt/ids && tar xzf /opt/ids-deploy.tar.gz -C /opt/ids
cd /opt/ids
ls   # 应看到 backend/ frontend/ docker-compose.yml
```

> 也支持用 `git` 上传（如果项目已 git 化），或直接用 Xftp / WinSCP 把 `backend/`、`frontend/`、`docker-compose.yml` 三个东西拖到服务器。

## 三、构建并启动

```bash
cd /opt/ids
docker compose up -d --build
```

首次构建需联网拉取依赖（约几分钟，主要是 CPU 版 torch 与 xgboost）。若已按上一步配置镜像（含 `.env`），会走国内加速。看到两个容器 `Started` 即成功：

```bash
docker compose ps
# ids-backend   ... Up (healthy)
# ids-frontend  ... Up
```

## 四、开放端口

两种防火墙都要放行 **80** 端口（想直接用 `/docs` 接口文档再放 8000）：

```bash
# 服务器系统防火墙（firewalld）
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=8000/tcp   # 可选
sudo firewall-cmd --reload
```

> **云服务器安全组**：登录云控制台（阿里云/腾讯云等），在「安全组」里添加入方向规则放行 TCP 80（和 8000）。这一步和系统防火墙是**两回事**，都做了才能从公网访问。

## 五、访问验证

```bash
# 本机验证
curl http://localhost/api/health
# 应返回 {"status":"ok","service":"工业互联网智能入侵检测系统"}

curl -I http://localhost/   # 应返回 HTTP 200
```

浏览器（或手机）打开：

```
http://<服务器公网IP>/
```

默认登录账号：`admin` / `admin123`。

---

## 常用运维命令

```bash
# 查看日志
docker compose logs -f backend
docker compose logs -f frontend

# 重启 / 停止
docker compose restart
docker compose down          # 停止并删除容器（持久卷数据保留）

# 更新代码后重新构建
docker compose up -d --build

# 查看资源占用（确认 CPU 版 torch 镜像体积合理）
docker images | grep ids
```

## 数据持久化说明

- 数据库 `ids.db` 与上传文件都在 Docker 卷 `ids_persist` 里，`docker compose down` 甚至 `down -v` 前注意备份。
- 备份：`docker run --rm -v ids_persist:/p -v $(pwd):/backup alpine tar czf /backup/ids_persist_backup.tar.gz -C /p .`

## 常见问题

- **构建时 torch 拉取慢/失败**：`--index-url https://download.pytorch.org/whl/cpu` 需访问外网，国内服务器可在 Dockerfile 里把该源换成清华镜像 `https://mirrors.tuna.tsinghua.edu.cn/pytorch/whl/cpu`。
- **端口被占用**：`docker compose` 里把 `80:80` 改成 `8080:80` 等，或先 `sudo systemctl stop firewalld` 排查。
- **SELinux 拦截**：Anolis 默认 `enforcing`，若容器启动报权限错误，先 `getenforce` 确认；演示环境可临时 `sudo setenforce 0`（生产不建议）。
- **模型加载报错**：确认 `backend/models/` 已随代码上传（`pack.sh` 不会排除它），且 requirements 版本与训练环境一致（本仓库已锁定）。
