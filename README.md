
## 使用方法

### 1) 配置 .env

复制模板并填写你的配置：

```bash
cp env.example .env
```

`env.example` 内容示例：

```bash
TEMP_MAIL_BASE="<your-temp-mail-api>"
TEMP_MAIL_ADMIN_PASSWORD="<your-admin-password>"
TEMP_MAIL_DOMAIN="<your-domain>"
# TEMP_MAIL_DOMAINS="example.com,another.com"
# TEMP_MAIL_SITE_PASSWORD="<your-site-password>"
# TOKEN_OUTPUT_DIR="./tokens"
# OPENAI_SSL_VERIFY="0"
# SKIP_NET_CHECK="1"
```

说明：

- `TEMP_MAIL_BASE` 临时邮箱 API 基础地址
- `TEMP_MAIL_ADMIN_PASSWORD` 管理员密码
- `TEMP_MAIL_DOMAIN` 邮箱域名
- `TEMP_MAIL_DOMAINS` 多域名逗号分隔（优先级高于 `TEMP_MAIL_DOMAIN`）
- `TEMP_MAIL_SITE_PASSWORD` 站点密码（若启用 private site）
- `TOKEN_OUTPUT_DIR` Token JSON 保存目录（可选）
- `OPENAI_SSL_VERIFY` 设为 `0` 可关闭 TLS 证书校验（仅代理导致证书不匹配时使用）
- `SKIP_NET_CHECK` 设为 `1` 可跳过网络连接/地理位置检查

`.env` 已在 `.gitignore` 中忽略，不会被提交。

### 2) 运行脚本

```bash
python openai_register.py
```

### 3) 常见参数

运行时参数（查看 `-h` 可见全部选项）：

```bash
python openai_register.py -h
```

如果你需要代理，使用脚本提供的参数传入（具体参数名以 `-h` 输出为准）。
