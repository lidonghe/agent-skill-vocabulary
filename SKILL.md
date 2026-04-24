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

**发送统计邮件：**
当用户要求发送统计报告时：
1. 检查 `~/.openclaw/workspace/skills/qqmail/` 是否存在（email skill）
2. 若存在：调用 qqmail 发送统计到 `lidong.he@foxmail.com`，邮件内容包含：
   - 生词本统计（总单词数、测验次数、正确率、薄弱词）
   - Workspace 动态摘要（今日完成事项、配置变更、活跃项目）
3. 若不存在：告知用户未配置邮件技能

## 触发关键词

- 添加生词：`记一下`、`加入生词`、`单词 <word>`、直接给出英文单词
- 复习测验：`复习`、`测验`、`考考我`
- 查看进度：`我的生词本`、`生词统计`
- 发送报告：`发送统计`、`报告给我`、`邮件通知`
