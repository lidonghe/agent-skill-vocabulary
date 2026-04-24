# 📚 Vocabulary Skill — 生词本

英文生词本 AI 技能，支持查词添加、复习测验、统计和邮件报告。

## 功能

| 功能 | 说明 |
|------|------|
| 添加生词 | 输入英文单词，自动查词 + 中英双语存储 |
| 复习测验 | Agent 出题（英译中模式），即时判断对错 |
| 查看进度 | 生词列表 + 正确率统计 |
| 薄弱词标记 | 正确率 < 60% 的单词会标记为薄弱词 |
| 邮件报告 | 可将统计报告发送到指定邮箱 |

## 安装

**方式一：ClawHub（推荐）**
```bash
clawhub install lidonghe/agent-skill-vocabulary
```

**方式二：手动安装**
```bash
git clone git@github.com:lidonghe/agent-skill-vocabulary.git ~/.openclaw/workspace/skills/vocabulary-skill
```

## 配置

### QQMail（可选，邮件报告功能需要）

```bash
# 在 OpenClaw TOOLS.md 中添加：
QQMAIL_USER=你的QQ邮箱@qq.com
QQMAIL_AUTH_CODE=你的QQ邮箱授权码
```

> 授权码在 [mail.qq.com](https://mail.qq.com) → 设置 → 账户 → IMAP/SMTP服务 中生成。

### 管理员邮箱

邮件报告默认发送至 `lidong.he@foxmail.com`，可在 SKILL.md 中修改。

## 使用方式

安装后在 OpenClaw 中直接对话即可：

```
用户：单词 ephemeral
用户：复习
用户：我的生词本
用户：发送统计报告
```

### 触发关键词

- **添加生词**：`记一下 XXX`、`加入生词`、`单词 XXX`
- **复习测验**：`复习`、`测验`、`考考我`
- **查看进度**：`我的生词本`、`生词统计`
- **发送报告**：`发送统计`、`报告给我`、`邮件通知`

## 数据存储

生词本存储在 `scripts/vocabulary.json`（**不会随 skill 更新**，用户数据独立保存）：

```json
{
  "word": "ephemeral",
  "phonetic": "/əˈfɛ.mə.ɹəl/",
  "chinese": "持续时间很短的东西。",
  "definitions": [...],
  "added_at": "2026-04-24",
  "quiz_history": [
    { "date": "2026-04-24", "result": "correct" }
  ]
}
```

## 技术栈

- 英文词典：[Free Dictionary API](https://dictionaryapi.dev/)
- 中英翻译：[MyMemory API](https://mymemory.translated.net/)
- 邮件发送：QQMail IMAP/SMTP
- 全部使用 Python 标准库，**无需 pip install**

## License

MIT
