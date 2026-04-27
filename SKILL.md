---
name: vocabulary
description: 生词本技能。当用户输入英文生词想要记入生词本、复习单词、做测验，或查看生词本进度时触发。支持英文单词的查词、存储（中英双语）、复习测验和统计。
---

# Vocabulary Skill — 生词本

管理英文生词本，支持查词添加、中英双语存储、英译中复习测验。

## 数据文件

生词本存储在 `scripts/vocabulary.json`，每次操作后自动保存。

## 命令接口

### 添加生词

```bash
python3 {baseDir}/scripts/vocabulary.py add <word>
```

- 自动从 Free Dictionary API 查询英文释义
- 自动将第一个英文释义翻译为中文（MyMemory API）
- 存储内容：单词、音标、中文翻译、英文释义、例句
- 若单词已存在，提示用户并跳过

### 复习测验（英译中模式）

```bash
python3 {baseDir}/scripts/vocabulary.py quiz [--limit N]
```

- 随机抽取 N 个单词（默认全部）
- 显示：**英文单词 + 音标**，用户口述或输入中文意思
- 答案判断：用户输入中包含正确中文翻译即为正确
- 实时显示对错，记录到 `quiz_history`
- 输入 `q` 可中途退出
- 结束后显示本次正确率

### 查看生词本

```bash
python3 {baseDir}/scripts/vocabulary.py list
```

- 列出所有单词、中文翻译、正确率、添加日期

### 查看统计

```bash
python3 {baseDir}/scripts/vocabulary.py stats
```

- 总单词数、总测验次数、总正确率
- 薄弱词列表（正确率 < 60%）

### 发送统计邮件报告

```bash
python3 {baseDir}/scripts/vocabulary.py report --to <email>
```

- 自动发现系统中可用的邮件 skill 并发送
- 邮件主题：「📝 生词本统计报告 YYYY-MM-DD」
- 邮件正文：生词本统计（总单词数、测验次数、正确率、薄弱词）

## 数据结构

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

## 测验与统计流程（Agent 交互模式）

测验和统计流程全部由 Agent 通过读写 `vocabulary.json` 实现，无需调用脚本交互。

**测验流程：**
1. 读取 `vocabulary.json`，随机抽取单词
2. 逐题展示给用户（英文 + 音标），等待用户回复中文
3. Agent 判断对错，直接更新对应单词的 `quiz_history`
4. 循环直到题目答完，显示本次正确率

**统计流程：**
1. 读取 `vocabulary.json`
2. 聚合所有单词的 `quiz_history`，计算各项指标
3. 展示给用户

**发送统计邮件（动态发现）：**
当用户要求发送统计报告时，Agent 调用 `vocabulary.py report --to <addr>`，脚本内部：
1. 扫描 `~/.openclaw/workspace/skills/` 下所有已安装的邮件 skill
2. 按优先级尝试调用可用 skill 的发送命令
3. 成功发送后返回结果；未发现任何邮件 skill 时告知用户

**支持的邮件 skill（自动发现）：**

| Skill | 检测方式 | 发送命令 |
|-------|---------|---------|
| `qqmail` | `scripts/qqmail.py` 存在 | `python3 qqmail.py send --to --subject --body` |
| `email-163-com` | `scripts/*.py` 存在 | `python3 *.py send --to --subject --body` |
| 其他邮件 skill | 目录含 `email`/`mail` 关键词 | 尝试运行 `send` 子命令 |

其他用户安装任意邮件 skill 后，报告功能无需额外配置即可自动工作。

## 触发关键词

- 添加生词：`记一下`、`加入生词`、`单词 <word>`、直接给出英文单词
- 复习测验：`复习`、`测验`、`考考我`
- 查看进度：`我的生词本`、`生词统计`
- 发送报告：`发送统计`、`报告给我`、`邮件通知`
