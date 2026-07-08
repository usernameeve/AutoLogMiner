# Nginx 常见故障模式

## 502 Bad Gateway

**现象**: 客户端收到 502 错误，Nginx error log 显示 `upstream prematurely closed connection`

**常见根因**:
1. 后端服务未启动或已崩溃
2. 后端服务响应超时（超过 proxy_read_timeout）
3. 后端服务返回了无效响应
4. PHP-FPM / Gunicorn / uWSGI 进程不足

**排查命令**:
```bash
# 检查后端服务是否在监听
netstat -tlnp | grep :8080
ss -tlnp | grep :8080

# 检查 Nginx 错误日志
tail -100 /var/log/nginx/error.log

# 检查后端进程是否存在
ps aux | grep gunicorn
systemctl status your-app

# 测试后端直接响应
curl -v http://127.0.0.1:8080/health
```

**修复方案**:
- 重启后端服务: `systemctl restart your-app`
- 增加超时时间: `proxy_read_timeout 300s;`
- 调整 upstream 缓冲: `proxy_buffer_size 128k; proxy_buffers 4 256k;`

## 504 Gateway Timeout

**现象**: 请求在 proxy_read_timeout 时间内未收到后端响应

**常见根因**:
1. 后端处理时间过长（慢查询、外部API调用慢）
2. proxy_read_timeout 设置过短
3. 后端服务死锁或hang住

**修复方案**:
- 调大超时: `proxy_read_timeout 120s; proxy_connect_timeout 60s;`
- 优化后端慢请求
- 考虑异步处理长请求

## 高并发场景 502/504 激增

**现象**: 流量高峰期大量 502

**排查**:
```bash
# 检查连接数
netstat -an | grep :80 | wc -l

# 检查 worker 进程
ps aux | grep nginx | grep worker

# 检查系统限制
ulimit -n
cat /proc/sys/net/core/somaxconn
```

**修复**:
```nginx
worker_processes auto;
worker_connections 4096;
worker_rlimit_nofile 65535;
events {
    use epoll;
    multi_accept on;
}
```

## 静态资源 404

**现象**: CSS/JS/图片返回 404

**排查**:
```bash
# 检查文件是否存在
ls -la /var/www/html/static/

# 检查 Nginx root 配置
nginx -T | grep -A5 "location.*static"

# 检查文件权限
namei -l /var/www/html/static/app.js
```

**修复**:
- 确保 root 路径正确且文件存在
- `chmod 755 /var/www/html/static/ -R`
- `chown nginx:nginx /var/www/html/ -R`

## SSL 证书问题

**现象**: 浏览器提示证书错误

**排查**:
```bash
# 检查证书有效期
openssl x509 -in /etc/nginx/ssl/cert.pem -noout -dates

# 检查证书和私钥是否匹配
openssl x509 -noout -modulus -in /etc/nginx/ssl/cert.pem | md5sum
openssl rsa -noout -modulus -in /etc/nginx/ssl/key.pem | md5sum
```

**修复**:
- 续期证书: `certbot renew`
- 检查配置中证书路径是否正确
