# 通过 Docker 安装 Windows 11

使用 [dockur/windows](https://github.com/dockur/windows) 项目，在 Docker 容器中运行 Windows 11。

## 系统要求
- Ubuntu 22.04+ (x86_64)
- 至少 4 核 CPU、8GB 内存、64GB 磁盘空间
- 需要 sudo 权限（安装 Docker 及启用 KVM）

## 快速安装

```bash
bash tasks/install-windows-docker/install.sh
```

脚本会依次完成：
1. 安装 Docker Engine + Docker Compose（如果尚未安装）
2. 启用 KVM 虚拟化加速
3. 创建 `docker-compose.yml` 配置文件
4. 启动 Windows 11 容器

## 安装完成后

- 浏览器访问 **http://localhost:8006** 打开 Windows 桌面（noVNC）
- Windows 首次启动需要约 10-20 分钟完成安装
- 默认分配 4 核 CPU、8GB 内存、64GB 磁盘

## 常用命令

```bash
# 查看容器状态
docker compose -f ~/windows-docker/docker-compose.yml ps

# 停止 Windows
docker compose -f ~/windows-docker/docker-compose.yml stop

# 启动 Windows
docker compose -f ~/windows-docker/docker-compose.yml start

# 删除 Windows（数据保留在 ~/windows-docker/storage/）
docker compose -f ~/windows-docker/docker-compose.yml down

# 查看日志
docker compose -f ~/windows-docker/docker-compose.yml logs -f
```

## 自定义配置

编辑 `~/windows-docker/docker-compose.yml` 可修改：
- `RAM_SIZE`: 内存大小（默认 8G）
- `CPU_CORES`: CPU 核数（默认 4）
- `DISK_SIZE`: 磁盘大小（默认 64G）
- `VERSION`: Windows 版本（默认 win11）
