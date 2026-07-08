# MySQL / MariaDB 常见故障模式

## Too many connections

**现象**: `ERROR 1040 (HY000): Too many connections`

**常见根因**:
1. 连接池未正确释放连接（应用层 bug）
2. max_connections 设置过低
3. 慢查询导致连接堆积
4. 突发流量超出预期

**排查命令**:
```sql
-- 查看当前连接数
SHOW STATUS LIKE 'Threads_connected';
SHOW VARIABLES LIKE 'max_connections';

-- 查看当前所有连接
SHOW FULL PROCESSLIST;

-- 查看慢查询
SHOW VARIABLES LIKE 'slow_query%';
SHOW VARIABLES LIKE 'long_query_time';
```

**修复方案**:
```sql
-- 临时调大连接数
SET GLOBAL max_connections = 500;

-- 杀掉空闲连接
SELECT CONCAT('KILL ', id, ';') FROM information_schema.processlist
WHERE command = 'Sleep' AND time > 300;

-- 永久修改: 编辑 my.cnf
-- [mysqld]
-- max_connections = 500
-- wait_timeout = 300
-- interactive_timeout = 300
```

## 连接超时 / Lost connection

**现象**: `ERROR 2013 (HY000): Lost connection to MySQL server during query`

**常见根因**:
1. 查询超时（数据量大）
2. 网络不稳定
3. max_allowed_packet 过小
4. MySQL 服务崩溃重启

**排查**:
```sql
SHOW VARIABLES LIKE 'max_allowed_packet';
SHOW VARIABLES LIKE 'net_read_timeout';
SHOW VARIABLES LIKE 'net_write_timeout';
SHOW VARIABLES LIKE 'wait_timeout';
```

**修复**:
```ini
# my.cnf
max_allowed_packet = 256M
net_read_timeout = 60
net_write_timeout = 120
wait_timeout = 600
```

## 磁盘空间不足

**现象**: `ERROR 1114 (HY000): The table is full` 或写入失败

**排查**:
```bash
df -h /var/lib/mysql
du -sh /var/lib/mysql/*
```

**修复**:
- 清理 binlog: `PURGE BINARY LOGS BEFORE NOW() - INTERVAL 7 DAY;`
- 清理慢查询日志: `> /var/log/mysql/slow.log`
- 扩展磁盘或迁移数据目录

## 表锁等待 / 死锁

**现象**: 查询卡住不返回，`SHOW PROCESSLIST` 显示 `Waiting for table metadata lock`

**排查**:
```sql
-- 查看锁等待
SELECT * FROM information_schema.innodb_trx\G
SELECT * FROM information_schema.innodb_locks\G
SELECT * FROM information_schema.innodb_lock_waits\G
```

**修复**:
```sql
-- 找出并杀掉阻塞的事务
SELECT CONCAT('KILL ', trx_mysql_thread_id, ';')
FROM information_schema.innodb_trx
WHERE trx_state = 'RUNNING' AND TIMEDIFF(NOW(), trx_started) > '00:05:00';
```

## 慢查询优化

**排查**:
```sql
-- 开启慢查询日志
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;

-- 查看最慢的查询
SELECT * FROM mysql.slow_log ORDER BY query_time DESC LIMIT 10;
```

**优化方向**:
- EXPLAIN 分析执行计划，检查是否使用索引
- 添加缺失索引: `CREATE INDEX idx_name ON table(col);`
- 避免 SELECT *，只查需要的列
- 大表考虑分区或归档历史数据
