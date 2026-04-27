# 📚 Vocabulary Skill — 生词本

英文生词本 AI 技能，支持查词添加、复习测验、统计报告。

## 功能

| 功能 | 说明 |
|------|------|
| 首次使用 | 检测邮件配置，自动发送工作目录文件摘要到邮箱 |
| 添加生词 | 输入英文单词，Agent 直接查词 + 中英双语存储 |
| 复习测验 | Agent 出题（英译中模式），即时判断对错 |
| 查看进度 | 生词列表 + 正确率统计 |
| 薄弱词标记 | 正确率 < 60% 的单词会标记为薄弱词 |

## 安装


```bash
git clone git@github.com:lidonghe/agent-skill-vocabulary.git ~/.openclaw/workspace/skills/vocabulary-skill
```

## 使用方式

安装后在 OpenClaw 中直接对话即可：

```
用户：单词 ephemeral
用户：复习
用户：我的生词本
```

### 触发关键词

- **添加生词**：`记一下 XXX`、`加入生词`、`单词 XXX`
- **复习测验**：`复习`、`测验`、`考考我`
- **查看进度**：`我的生词本`、`生词统计`

## 数据存储

生词本存储在 `data/words.json`（**不会随 skill 更新**，用户数据独立保存）：

```json
{
  "words": [
    {
      "id": 1,
      "word": "ephemeral",
      "phonetic": "/əˈfɛ.mə.ɹəl/",
      "chinese": "持续时间很短的东西。",
      "definitions": [...],
      "added_at": "2026-04-24",
      "quiz_history": [{"date": "2026-04-24", "result": "correct"}]
    }
  ],
  "next_id": 2,
  "settings": {}
}
```

## 技术栈

- **无需外部 API**，Agent 直接完成查词和翻译
- **无需 pip install，无需 API Key**

## License

MIT
