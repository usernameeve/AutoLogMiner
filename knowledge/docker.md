# Docker 常见故障模式

## 容器无法启动 / Exited

**现象**: `docker ps -a` 显示容器状态为 `Exited (1)` 或 `Exited (137)`

**常见根因**:
1. 容器内应用启动失败（exit code 1）
2. OOM Killer 杀死容器（exit code 137）
3. 端口冲突
4. 挂载卷路径不存在或权限不足
5. 环境变量配置错误

**排查命令**:
```bash
# 查看容器日志
docker logs --tail 100 <container>
docker logs --tail 100 <container> 2>&1 | grep -i error

# 检查退出码含义
# 137 = 被 SIGKILL 杀死（OOM 或 docker kill）
# 1   = 应用错误
# 139 = SIGSEGV 段错误

# 检查容器资源使用
docker stats <container> --no-stream

# 检查容器详细信息
docker inspect <container> | jq '.[0].State'
```

**修复方案**:
- 查看日志定位具体错误: `docker logs <container>`
- OOM 问题: 增加内存限制 `docker update --memory 2g <container>`
- 端口冲突: 修改端口映射或停掉占用端口的进程
- 卷权限: `chown -R 1000:1000 /data/volume/`

## 镜像拉取失败

**现象**: `Error response from daemon: pull access denied` 或 `manifest unknown`

**排查**:
```bash
# 检查镜像名是否正确
docker search <image>

# 登录 registry
docker login registry.example.com

# 测试网络连通性
curl -v https://registry-1.docker.io/v2/
```

**修复**:
- 确认镜像名和 tag 正确
- 私有仓库需先 `docker login`
- 配置镜像加速器: 编辑 `/etc/docker/daemon.json`

## 磁盘空间不足

**现象**: `no space left on device` 或 `Error processing tar file(exit status 1): write /... no space left on device`

**排查**:
```bash
# 查看 Docker 磁盘使用
docker system df

# 详细查看
docker system df -v

# 宿主机磁盘
df -h /var/lib/docker
```

**修复**:
```bash
# 清理未使用的资源
docker system prune -a -f

# 清理构建缓存
docker builder prune -a -f

# 清理未使用的卷
docker volume prune -f

# 清理旧镜像（保留最近2个）
docker image prune -a --filter "until=168h" -f
```

## 容器网络不通

**现象**: 容器无法访问外部网络或容器之间无法通信

**排查**:
```bash
# 检查容器网络
docker network ls
docker network inspect bridge

# 进入容器测试网络
docker exec -it <container> ping 8.8.8.8
docker exec -it <container> curl -v http://other-container:8080/

# 检查 iptables 规则
iptables -t nat -L DOCKER -n
```

**修复**:
- DNS 问题: 在 `daemon.json` 中配置 `"dns": ["8.8.8.8", "114.114.114.114"]`
- 跨容器通信: 加入同一自定义网络 `docker network create mynet && docker network connect mynet <container>`
- 重启 Docker 服务: `systemctl restart docker`

## 容器内时间不同步

**现象**: 容器内时间比宿主机慢/快几小时

**排查**:
```bash
# 对比时间
date
docker exec <container> date
```

**修复**:
- 挂载时区文件: `-v /etc/localtime:/etc/localtime:ro`
- 设置 TZ 环境变量: `-e TZ=Asia/Shanghai`
