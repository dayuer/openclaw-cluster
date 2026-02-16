# Browser Automation Skill

浏览器自动化 skill，支持网页登录、表单填写、点击操作、截图等。

## 依赖安装

```bash
pip install playwright
playwright install chromium
```

## 功能

| 功能 | 命令 | 说明 |
|------|------|------|
| 登录网页 | `login` | 自动填写用户名密码并登录 |
| 截图 | `screenshot` | 对页面进行截图 |
| 点击 | `click` | 点击页面元素 |
| 填写表单 | `fill` | 填写表单字段 |
| 等待 | `wait` | 等待元素出现或页面加载 |
| 获取内容 | `content` | 获取页面文本或HTML |
| 执行脚本 | `evaluate` | 执行JavaScript |

## 使用方法

### 1. 登录网页

```bash
python /app/workspace/skills/browser-automation/browser.py login \
  --url "https://example.com/login" \
  --username "your_username" \
  --password "your_password" \
  --username-selector "#username" \
  --password-selector "#password" \
  --submit-selector "button[type=submit]"
```

### 2. 截图

```bash
python /app/workspace/skills/browser-automation/browser.py screenshot \
  --url "https://example.com" \
  --output "/app/workspace/screenshot.png"
```

### 3. 自定义脚本

创建 JSON 配置文件：

```json
{
  "url": "https://example.com/login",
  "steps": [
    {"action": "fill", "selector": "#username", "value": "user123"},
    {"action": "fill", "selector": "#password", "value": "pass456"},
    {"action": "click", "selector": "button[type=submit]"},
    {"action": "wait", "selector": ".dashboard", "timeout": 5000},
    {"action": "screenshot", "output": "/app/workspace/result.png"}
  ]
}
```

执行：

```bash
python /app/workspace/skills/browser-automation/browser.py run --config /path/to/config.json
```

## 安全提示

⚠️ **密码安全**：
- 不要在命令行直接传递密码（会被记录到 shell history）
- 建议使用环境变量或配置文件
- 配置文件权限设为 600

```bash
export LOGIN_PASSWORD="your_password"
python browser.py login --url "..." --username "user" --password-env LOGIN_PASSWORD
```

## 常见选择器

| 元素 | 选择器示例 |
|------|-----------|
| 用户名输入框 | `#username`, `input[name=username]`, `input[type=text]` |
| 密码输入框 | `#password`, `input[name=password]`, `input[type=password]` |
| 登录按钮 | `button[type=submit]`, `.login-btn`, `#login-button` |
| 验证码输入框 | `#captcha`, `input[name=captcha]` |

## 无头模式

默认使用无头模式（headless），不显示浏览器窗口。如需调试：

```bash
python browser.py login --url "..." --username "..." --password "..." --no-headless
```
