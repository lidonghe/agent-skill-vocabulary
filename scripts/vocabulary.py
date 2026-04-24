#!/usr/bin/env python3
"""
Vocabulary Skill - 生词本管理
Usage:
    python3 vocabulary.py add <word>
    python3 vocabulary.py quiz              # 非交互式，返回所有题目
    python3 vocabulary.py quiz --answer <id> <user_answer>  # 判题
    python3 vocabulary.py list
    python3 vocabulary.py stats
"""
import json
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


def load_vocab():
    if not os.path.exists(VOCAB_FILE):
        return {"words": [], "next_id": 1}
    try:
        with open(VOCAB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"words": [], "next_id": 1}


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


def cmd_quiz(limit=None):
    data = load_vocab()
    words = data.get("words", [])
    if not words:
        print("📭 生词本为空，先加几个单词吧！")
        return

    if limit is None:
        limit = len(words)

    sample = random.sample(words, min(limit, len(words)))

    # 输出所有题目，Agent 逐题展示给用户
    print(f"📝 测验开始！共 {len(sample)} 题\n")
    for w in sample:
        print(f"QID:{w['id']}|{w['word']}|{w.get('phonetic','')}")
    print("---END---")


def cmd_answer(qid, user_answer):
    data = load_vocab()
    words = data.get("words", [])

    w = next((x for x in words if str(x["id"]) == str(qid)), None)
    if not w:
        print(f"❌ 未找到 ID 为 {qid} 的单词。")
        return

    chinese_correct = w.get("chinese", "")
    is_correct = False
    if chinese_correct and chinese_correct in user_answer.strip():
        is_correct = True
    elif not chinese_correct and user_answer.strip():
        is_correct = True

    today = datetime.date.today().isoformat()
    result = "correct" if is_correct else "wrong"
    w["quiz_history"].append({"date": today, "result": result})
    save_vocab(data)

    if is_correct:
        print(f"✅ 正确！ {chinese_correct}")
    else:
        print(f"❌ 正确答案: **{chinese_correct}**")


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
        args = sys.argv[2:]
        if "--limit" in args:
            idx = args.index("--limit")
            limit = int(args[idx + 1]) if idx + 1 < len(args) else None
        if "--answer" in args:
            idx = args.index("--answer")
            qid = args[idx + 1]
            answer = args[idx + 2] if idx + 2 < len(args) else ""
            cmd_answer(qid, answer)
        else:
            cmd_quiz(limit)
    elif cmd == "list":
        cmd_list()
    elif cmd == "stats":
        cmd_stats()
    else:
        print(f"未知命令: {cmd}")
        print(__doc__)
        sys.exit(1)
