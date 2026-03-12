# OpenAI Register (Password Flow)

## 核心功能
- 使用私有临时邮箱服务创建新邮箱并接收验证码。
- 走 OpenAI 密码注册流程，完成账号创建并保存 token。
- 可选代理支持，支持循环注册与随机等待。
- 产出 token JSON 与账号密码记录文件。

## 目录结构
- register_with_password.py  主脚本（密码注册）
- email_manager.py           临时邮箱管理器
- env.example                环境变量示例
- SESSION_NOTES.md           会话记录

## 环境配置
复制模板：

```bash
cp env.example .env
```

env.example 关键字段说明：

- TEMP_MAIL_BASE
  临时邮箱服务 API 基地址。例如: https://your-temp-mail-api

- TEMP_MAIL_ADMIN_PASSWORD
  临时邮箱服务管理员密码（用于 /admin/new_address）

- TEMP_MAIL_DOMAIN
  单个邮箱域名（如 example.com）

- TEMP_MAIL_DOMAINS
  多域名逗号分隔（优先级高于 TEMP_MAIL_DOMAIN）

- TOKEN_OUTPUT_DIR
  token JSON 保存目录（可选，默认当前目录）

- OPENAI_SSL_VERIFY
  设为 0 关闭 TLS 校验（仅代理或自签名证书时使用）

- SKIP_NET_CHECK
  设为 1 跳过网络/地区检查

提示：.env 已被 .gitignore 忽略，不会提交。

## 主脚本参数
脚本：`register_with_password.py`

```bash
python register_with_password.py -h
```

全部参数：
- --proxy
  代理地址，例如 http://127.0.0.1:7890

- --once
  只运行一次。省略此参数则会循环注册。

- --sleep-min
  循环模式下最短等待秒数（默认 5）

- --sleep-max
  循环模式下最长等待秒数（默认 30）

## 使用方式
单次运行：

```bash
python register_with_password.py --once
```

循环运行（带随机等待）：

```bash
python register_with_password.py --sleep-min 10 --sleep-max 60
```

通过代理运行：

```bash
python register_with_password.py --proxy http://127.0.0.1:7890 --once
```

## 输出文件
- token_*.json
  注册成功后生成的 token 文件。

- accounts.txt
  记录账号与密码，格式：email----password

这些文件已在 .gitignore 中忽略。

## 重要说明
- 每次运行都会创建新邮箱，不复用旧邮箱。
- OTP 会先触发发送，再轮询邮箱获取验证码。
- 若 OTP 超时，请确认 TEMP_MAIL_BASE 与邮箱服务正常。
