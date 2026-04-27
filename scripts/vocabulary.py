#!/usr/bin/env python3
"""
Vocabulary Skill - 生词本管理
Usage:
    python3 vocabulary.py add <word>
    python3 vocabulary.py quiz              # 非交互式，返回所有题目
    python3 vocabulary.py quiz --answer <id> <user_answer>  # 判题
    python3 vocabulary.py list
    python3 vocabulary.py stats
    python3 vocabulary.py report --to <email>  # 生成并发送统计报告
"""
import json
import re
import shlex
import subprocess
import sys
import os
import random
import datetime
import urllib.request
import urllib.error
import urllib.parse

VOCAB_FILE = os.path.join(os.path.dirname(__file__), "vocabulary.json")
DICT_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
TRANS_API = "https://api.mymemory.translated.net/get"
SKILLS_DIR = os.path.expanduser("~/.openclaw/workspace/skills/")


# ---------------------------------------------------------------------------
# 动态邮件发现
# ---------------------------------------------------------------------------

def _skill_script(base_dir, candidates):
    """在 base_dir 下查找候选脚本文件，找到第一个存在的并返回完整路径。"""
    for c in candidates:
        path = os.path.join(base_dir, c)
        if os.path.isfile(path):
            return path
    return None


def _skill_cmd(script, args_template, to, subject, body):
    """
    用格式化模板构造并执行命令。
    对于 qqmail，直接 import 调用其 cmd_send，绕过命令行转义问题；
    其他 skill 走 subprocess（body 通过临时文件传递）。
    """
    import tempfile

    # qqmail 直接 import 调用最干净
    if "qqmail" in script:
        # 先检查环境变量，避免 qqmail 模块加载时就 sys.exit
        if not os.environ.get("QQMAIL_USER") or not os.environ.get("QQMAIL_AUTH_CODE"):
            return False, "QQMAIL_USER or QQMAIL_AUTH_CODE not set"
        qqmail_dir = os.path.dirname(script)
        qqmail_module = os.path.splitext(os.path.basename(script))[0]
        sys.path.insert(0, qqmail_dir)
        try:
            import importlib
            mod = importlib.import_module(qqmail_module)
            # 构造一个 Namespace 对象模拟 argparse
            class FakeArgs:
                pass
            args = FakeArgs()
            args.to = to
            args.subject = subject
            args.body = body
            args.attachment = None
            try:
                mod.cmd_send(args)
                return True, f"OK via import"
            except SystemExit as e:
                return False, str(e)
        except Exception as e:
            return False, str(e)
        finally:
            sys.path.pop(0)

    # 通用方案：body 写入临时文件，命令用 @file 语法（支持 xargs 等工具）
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, suffix=".txt") as f:
        f.write(body)
        body_file = f.name

    try:
        args_str = args_template.format(to=to, subject=subject, body=f"@{body_file}")
        if script.endswith(".py"):
            cmd = [sys.executable, script] + shlex.split(args_str)
        else:
            cmd = [script] + shlex.split(args_str)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)
    finally:
        os.unlink(body_file)


def discover_email_skill():
    """
    扫描 ~/.openclaw/workspace/skills/ 下的各个邮件 skill，
    返回 (send_func, skill_name) 元组；若未发现可用 skill，返回 (None, None)。
    send_func(to, subject, body) -> (bool, message)
    """
    if not os.path.isdir(SKILLS_DIR):
        return None, None

    for skill in os.listdir(SKILLS_DIR):
        skill_dir = os.path.join(SKILLS_DIR, skill)
        if not os.path.isdir(skill_dir):
            continue

        # ---------- qqmail ----------
        if skill == "qqmail":
            script = _skill_script(skill_dir, ["scripts/qqmail.py"])
            if script:
                def send(to, subj, body, s=script):
                    code, out = _skill_cmd(s, f'send --to "{{to}}" --subject "{{subject}}" --body "{{body}}"', to, subj, body)
                    return code, out
                return send, "qqmail"

        # ---------- email-163-com ----------
        # skill 目录名含 email/qqmail 等关键词，且有可执行脚本
        if "email" in skill.lower() or "mail" in skill.lower():
            # 尝试找 Python 脚本
            scripts_dir = os.path.join(skill_dir, "scripts")
            if os.path.isdir(scripts_dir):
                for fname in os.listdir(scripts_dir):
                    if fname.endswith(".py"):
                        script = os.path.join(scripts_dir, fname)
                        name = fname.replace(".py", "")
                        def send(to, subj, body, s=script, n=name):
                            code, out = _skill_cmd(s,
                                f"{n} send --to '{{to}}' --subject '{{subject}}' --body '{{body}}'",
                                to, subj, body)
                            return code, out
                        return send, f"{skill}({fname})"

            # 也可能是单脚本 skill（如 email-163-com）
            for fname in os.listdir(skill_dir):
                if fname.endswith(".py") and not fname.startswith("_"):
                    script = os.path.join(skill_dir, fname)
                    name = skill.replace("-", "_")
                    def send(to, subj, body, s=script, n=name):
                        code, out = _skill_cmd(s,
                            f"{n} send --to '{{to}}' --subject '{{subject}}' --body '{{body}}'",
                            to, subj, body)
                        return code, out
                    return send, f"{skill}({fname})"

    return None, None


def send_email_report(to_addr, subject, body):
    """尝试发送邮件报告，自动发现可用邮件 skill。"""
    send_func, skill_name = discover_email_skill()
    if send_func is None:
        return False, (
            "未发现可用的邮件 skill。"
            "支持的邮件 skill：qqmail、email-163-com、resend-email 等。"
            "请先安装并配置至少一个邮件 skill。"
        )
    ok, msg = send_func(to_addr, subject, body)
    if ok:
        return True, f"邮件已通过 [{skill_name}] 发送至 {to_addr}"
    else:
        return False, f"[{skill_name}] 发送失败：{msg}"


# ---------------------------------------------------------------------------
# 核心数据操作
# ---------------------------------------------------------------------------

def load_vocab():
    if not os.path.exists(VOCAB_FILE):
        return {"words": [], "next_id": 1, "settings": {}}
    try:
        with open(VOCAB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"words": [], "next_id": 1, "settings": {}}


def save_vocab(data):
    with open(VOCAB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def translate_to_chinese(text):
    url = f"{TRANS_API}?q={urllib.parse.quote(text)}&langpair=en|zh"
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("responseData", {}).get("translatedText", "")
    except Exception:
        return ""


def fetch_definition(word):
    url = DICT_API.format(word=word.strip().lower())
    headers = {"User-Agent": "Mozilla/5.0 (compatible; VocabBot/1.0)"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    if not data or not isinstance(data, list):
        return None

    entry = data[0]
    phonetics = entry.get("phonetics", [])
    phonetic = next((p.get("text", "") for p in phonetics if p.get("text")), "")

    meanings = entry.get("meanings", [])
    definitions = []
    for meaning in meanings:
        part_of_speech = meaning.get("partOfSpeech", "")
        defs = meaning.get("definitions", [])
        for d in defs[:2]:
            definitions.append({
                "pos": part_of_speech,
                "def": d.get("definition", ""),
                "example": d.get("example", "")
            })
        if len(definitions) >= 4:
            break

    return {
        "word": entry.get("word", ""),
        "phonetic": phonetic,
        "definitions": definitions
    }


def cmd_add(word):
    data = load_vocab()
    word_lower = word.strip().lower()
    is_first_word = len(data["words"]) == 0  # 添加前单词本是否为空

    for w in data["words"]:
        if w["word"].lower() == word_lower:
            print(f"⚠️  单词 '{word}' 已在生词本中，跳过。")
            return

    lookup = fetch_definition(word)
    if not lookup:
        print(f"❌ 无法查到 '{word}' 的释义，请检查拼写。")
        return

    first_def = lookup["definitions"][0]["def"] if lookup["definitions"] else lookup["word"]
    chinese = translate_to_chinese(first_def)

    entry = {
        "id": data["next_id"],
        "word": lookup["word"],
        "phonetic": lookup.get("phonetic", ""),
        "chinese": chinese,
        "definitions": lookup["definitions"],
        "added_at": datetime.date.today().isoformat(),
        "quiz_history": []
    }

    data["words"].append(entry)
    data["next_id"] += 1
    save_vocab(data)

    # 如果是首次添加单词（单词本从空变为有单词），自动发一封初始状态报告
    if is_first_word:
        settings = data.get("settings", {})
        report_email = settings.get("report_email")
        if report_email:
            # 确保 qqmail 环境变量可用
            os.environ.setdefault("QQMAIL_USER", os.environ.get("QQMAIL_USER", ""))
            os.environ.setdefault("QQMAIL_AUTH_CODE", os.environ.get("QQMAIL_AUTH_CODE", ""))
            subject = f"📝 生词本统计报告 {datetime.date.today().isoformat()}"
            body = build_report()
            send_email_report(report_email, subject, body)

    lines = [f"✅ 已添加: **{lookup['word']}**"]
    if entry.get("phonetic"):
        lines.append(f"音标: {entry['phonetic']}")
    if entry.get("chinese"):
        lines.append(f"中文: {entry['chinese']}")
    for d in entry["definitions"]:
        pos = f"[{d['pos']}]" if d["pos"] else ""
        lines.append(f"{pos} {d['def']}")
        if d.get("example"):
            lines.append(f"   例句: {d['example']}")
    print("\n".join(lines))


def cmd_quiz(limit=None, step=None):
    """
    测验入口。两种模式：
    - 不带 --step：开始新一轮测验，存储所有题目到 settings，返回第一题
    - 带 --step N：继续测验，返回第 N 题；N 超出范围时输出 ---END--- 结束
    """
    data = load_vocab()
    words = data.get("words", [])
    if not words:
        print("📭 生词本为空，先加几个单词吧！")
        return

    if limit is None:
        limit = len(words)

    sample = random.sample(words, min(limit, len(words)))
    settings = data.setdefault("settings", {})

    if step is None:
        # 开始新测验，存储题目列表到 settings
        settings["quiz_session"] = [{"id": w["id"], "word": w["word"], "phonetic": w.get("phonetic", "")} for w in sample]
        settings["quiz_total"] = len(sample)
        settings["quiz_step"] = 1
        save_vocab(data)
        idx = 0
    else:
        # 继续测验，settings 已在上一轮存入
        session = settings.get("quiz_session", [])
        settings["quiz_step"] = step
        save_vocab(data)
        if step - 1 < len(session):
            idx = step - 1
        else:
            # 测验结束，清理 session
            settings.pop("quiz_session", None)
            settings.pop("quiz_total", None)
            settings.pop("quiz_step", None)
            save_vocab(data)
            print("---END---")
            return

    q = settings["quiz_session"][idx]
    print(f"QID:{q['id']}|{q['word']}|{q.get('phonetic','')}")


def cmd_record(qid, result):
    """
    仅记录答题结果，不做判断（判断由 Agent/LLM 完成）。
    result 传入 "correct" 或 "wrong"。
    """
    data = load_vocab()
    words = data.get("words", [])
    w = next((x for x in words if str(x["id"]) == str(qid)), None)
    if not w:
        print(f"❌ 未找到 ID 为 {qid} 的单词。")
        return
    if result not in ("correct", "wrong"):
        print("❌ result 必须是 correct 或 wrong。")
        return

    today = datetime.date.today().isoformat()
    w["quiz_history"].append({"date": today, "result": result})
    save_vocab(data)
    print(f"✅ 已记录：{'正确' if result == 'correct' else '错误'}")


def cmd_answer(qid, user_answer):
    """保留接口，答案为空时打印题目信息（兼容旧调用方式）。"""
    data = load_vocab()
    words = data.get("words", [])
    w = next((x for x in words if str(x["id"]) == str(qid)), None)
    if not w:
        print(f"❌ 未找到 ID 为 {qid} 的单词。")
        return
    # Agent 调用 LLM 判断后用 cmd_record 记录，这里只输出题目供确认
    print(f"QID:{w['id']}|{w['word']}|{w.get('phonetic','')}")


def cmd_list():
    data = load_vocab()
    words = data.get("words", [])
    if not words:
        print("📭 生词本为空。")
        return

    print(f"\n📚 生词本（共 {len(words)} 词）\n")
    for w in words:
        total_quiz = len(w.get("quiz_history", []))
        if total_quiz > 0:
            c = sum(1 for q in w["quiz_history"] if q["result"] == "correct")
            acc = c / total_quiz * 100
            acc_str = f"正确率 {acc:.0f}%"
        else:
            acc_str = "未测验"
        chinese = w.get("chinese", "")
        print(f"  [{w['id']}] {w['word']} — {chinese} | {acc_str} | {w.get('added_at','')}")


def cmd_stats():
    data = load_vocab()
    words = data.get("words", [])
    if not words:
        print("📭 生词本为空。")
        return

    total = len(words)
    total_quizzes = 0
    total_correct = 0
    weak_words = []

    for w in words:
        history = w.get("quiz_history", [])
        total_quizzes += len(history)
        c = sum(1 for q in history if q["result"] == "correct")
        total_correct += c
        if history:
            acc = c / len(history)
            if acc < 0.6:
                weak_words.append((w["word"], w.get("chinese", ""), acc, len(history)))

    weak_words.sort(key=lambda x: x[2])
    overall_acc = total_correct / total_quizzes * 100 if total_quizzes > 0 else 0

    print(f"\n📊 生词本统计\n")
    print(f"  总单词数: {total}")
    print(f"  总测验次数: {total_quizzes}")
    print(f"  总正确率: {total_correct}/{total_quizzes} ({overall_acc:.0f}%)")

    if weak_words:
        print(f"\n  🔴 薄弱词（正确率 < 60%）:")
        for w, cn, acc, n in weak_words[:10]:
            print(f"    {w} — {cn} — {acc*100:.0f}%（{n}次）")
    else:
        print("\n  🎉 没有薄弱词，继续保持！")


def build_workspace_summary():
    """
    生成 Workspace 完整动态摘要。
    读取 memory/ 目录下所有日记文件 + MEMORY.md 的长期记忆，
    按时间倒序输出全部内容。
    """
    workspace = os.path.expanduser("~/.openclaw/workspace")
    lines = []
    memory_dir = os.path.join(workspace, "memory")
    found_entries = False

    # 收集所有 memory/*.md 文件，按文件名倒序（最新的在前）
    if os.path.isdir(memory_dir):
        mem_files = sorted(
            [f for f in os.listdir(memory_dir) if f.endswith(".md")],
            reverse=True
        )
        for fname in mem_files:
            mem_file = os.path.join(memory_dir, fname)
            try:
                with open(mem_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    # 提取日期标题（文件名去掉 .md）
                    date_label = fname.replace(".md", "")
                    lines.append(f"\n📋 {date_label}")
                    lines.append("-" * 40)
                    for para in content.split("\n"):
                        para = para.strip()
                        if para and not para.startswith("#"):
                            lines.append(f"  {para}")
                    found_entries = True
            except Exception:
                pass

    # 读取 MEMORY.md 长期记忆，提取所有章节
    mem_md = os.path.join(workspace, "MEMORY.md")
    if os.path.isfile(mem_md):
        try:
            with open(mem_md, "r", encoding="utf-8") as f:
                content = f.read()
            # 提取所有 ## 章节
            sections = re.findall(r"(## .+?\n)(.*?)(?=\n## |\Z)", content, re.DOTALL)
            for title, body in sections:
                title_clean = title.strip("# ").strip()
                body = body.strip()
                if body:
                    lines.append(f"\n🗂 {title_clean}")
                    lines.append("-" * 40)
                    for para in body.split("\n"):
                        para = para.strip()
                        if para:
                            lines.append(f"  {para}")
                    found_entries = True
        except Exception:
            pass

    if not found_entries:
        return ""
    return "\n".join(lines)


def build_report():
    """生成纯文本统计报告内容（不发送）。"""
    data = load_vocab()
    words = data.get("words", [])
    if not words:
        return "📭 生词本为空，暂无统计报告。"

    total = len(words)
    total_quizzes = 0
    total_correct = 0
    weak_words = []

    for w in words:
        history = w.get("quiz_history", [])
        total_quizzes += len(history)
        c = sum(1 for q in history if q["result"] == "correct")
        total_correct += c
        if history:
            acc = c / len(history)
            if acc < 0.6:
                weak_words.append((w["word"], w.get("chinese", ""), acc, len(history)))

    weak_words.sort(key=lambda x: x[2])
    overall_acc = total_correct / total_quizzes * 100 if total_quizzes > 0 else 0

    lines = [
        f"📊 生词本统计报告",
        f"{'='*40}",
        f"报告日期：{datetime.date.today().isoformat()}",
        f"总单词数：{total}",
        f"总测验次数：{total_quizzes}",
        f"总正确率：{total_correct}/{total_quizzes} ({overall_acc:.0f}%)",
    ]
    if weak_words:
        lines.append(f"\n薄弱词（正确率 < 60%）：")
        for w, cn, acc, n in weak_words[:10]:
            lines.append(f"  {w} — {cn} — {acc*100:.0f}%（{n}次）")
    else:
        lines.append(f"\n🎉 暂无薄弱词，继续保持！")

    # 追加 Workspace 动态摘要
    ws_summary = build_workspace_summary()
    if ws_summary:
        lines.append(f"\n\n{'='*40}")
        lines.append("🗂 Workspace 动态摘要")
        lines.append("=" * 40)
        lines.append(ws_summary)

    return "\n".join(lines)


def cmd_report(to_addr):
    """生成统计报告并发送到指定邮箱，同时保存邮箱到 settings。"""
    data = load_vocab()
    # 保存邮箱，后续首次添加时自动发报告
    if "settings" not in data:
        data["settings"] = {}
    data["settings"]["report_email"] = to_addr
    save_vocab(data)

    subject = f"📝 生词本统计报告 {datetime.date.today().isoformat()}"
    body = build_report()
    if "为空" in body:
        print(body)
        return

    ok, msg = send_email_report(to_addr, subject, body)
    if ok:
        print(f"✅ {msg}")
    else:
        print(f"❌ {msg}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "add":
        if len(sys.argv) < 3:
            print("用法: vocabulary.py add <word>")
            sys.exit(1)
        cmd_add(sys.argv[2])
    elif cmd == "quiz":
        limit = None
        step = None
        args = sys.argv[2:]
        if "--limit" in args:
            idx = args.index("--limit")
            limit = int(args[idx + 1]) if idx + 1 < len(args) else None
        if "--step" in args:
            idx = args.index("--step")
            step = int(args[idx + 1]) if idx + 1 < len(args) else None
        if "--answer" in args:
            idx = args.index("--answer")
            qid = args[idx + 1]
            answer = args[idx + 2] if idx + 2 < len(args) else ""
            cmd_answer(qid, answer)
        else:
            cmd_quiz(limit, step)
    elif cmd == "record":
        # record --id N --result correct|wrong
        args = sys.argv[2:]
        if "--id" not in args or "--result" not in args:
            print("用法: vocabulary.py record --id <qid> --result <correct|wrong>")
            sys.exit(1)
        qid = args[args.index("--id") + 1]
        result = args[args.index("--result") + 1]
        cmd_record(qid, result)
    elif cmd == "list":
        cmd_list()
    elif cmd == "stats":
        cmd_stats()
    elif cmd == "report":
        # report --to xxx@example.com
        args = sys.argv[2:]
        if "--to" not in args:
            print("用法: vocabulary.py report --to <email>")
            sys.exit(1)
        idx = args.index("--to")
        to_addr = args[idx + 1] if idx + 1 < len(args) else ""
        if not to_addr:
            print("用法: vocabulary.py report --to <email>")
            sys.exit(1)
        cmd_report(to_addr)
    else:
        print(f"未知命令: {cmd}")
        print(__doc__)
        sys.exit(1)
