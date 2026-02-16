#!/usr/bin/env python3
"""
LLM 内容处理工具 — 调用 LLM 处理深度文本任务（启用深度思考）。

用途：翻译、摘要、改写、分析等不需要 tool calling 的纯文本任务。
支持 DeepSeek R1 深度思考模式。

用法:
    # 翻译
    python llm_process.py translate --text "Hello World" --target zh

    # 翻译文件
    python llm_process.py translate --file input.md --target zh --output result.md

    # 自定义 prompt
    python llm_process.py custom --prompt "请总结以下文章的要点" --file article.md

    # 摘要
    python llm_process.py summarize --file article.md

环境变量:
    LLM_API_BASE   - API 地址
    LLM_API_KEY    - API 密钥
    LLM_MODEL      - 模型名 (默认: deepseek-reasoner)
    LLM_THINKING   - 启用深度思考 (1=启用, 默认: 1)
"""

import argparse
import json
import os
import re
import sys

import httpx


DEFAULT_API_BASE = os.environ.get("LLM_API_BASE", "https://api.deepseek.com/v1")
DEFAULT_API_KEY = os.environ.get("LLM_API_KEY", os.environ.get("DEEPSEEK_API_KEY", ""))
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "deepseek-reasoner")
ENABLE_THINKING = os.environ.get("LLM_THINKING", "1") == "1"
TIMEOUT = 180


def call_llm(prompt, system_prompt="", max_tokens=4096):
    """调用 LLM API (支持 GLM-5 深度思考模式)"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEFAULT_API_KEY}",
    }

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": DEFAULT_MODEL,
        "messages": messages,
        "max_tokens": max_tokens if not ENABLE_THINKING else 65536,
        "temperature": 1.0 if ENABLE_THINKING else 0.3,
    }

    # GLM-5 深度思考
    if ENABLE_THINKING:
        payload["thinking"] = {"type": "enabled"}

    response = httpx.post(
        f"{DEFAULT_API_BASE}/chat/completions",
        headers=headers,
        json=payload,
        timeout=TIMEOUT,
    )
    response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"]["content"] or ""

    # 清理思考标签 (<think> / reasoning_content)
    if "<think>" in content:
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

    return content


def translate(text, target_lang="zh"):
    """翻译文本"""
    lang_map = {
        "zh": "中文",
        "en": "English",
        "ja": "日本語",
        "ko": "한국어",
    }
    target = lang_map.get(target_lang, target_lang)

    prompt = f"""请将以下内容翻译为{target}。要求：
1. 保持原文格式（Markdown 格式、段落、列表等）
2. 翻译要自然流畅，不要生硬的机翻
3. 专有名词保留英文（如 AI、BBC、CEO 等）
4. 只输出翻译结果，不要解释

---
{text}
"""
    return call_llm(prompt)


def summarize(text, style="bullet"):
    """生成摘要"""
    style_desc = {
        "bullet": "用要点列表形式",
        "paragraph": "用简短段落形式",
        "oneline": "用一句话概括",
    }
    desc = style_desc.get(style, style)

    prompt = f"""请{desc}总结以下内容的核心要点。用中文回复。

---
{text}
"""
    return call_llm(prompt)


def custom_process(prompt, text):
    """自定义 prompt 处理"""
    full_prompt = f"""{prompt}

---
{text}
"""
    return call_llm(full_prompt)


def main():
    parser = argparse.ArgumentParser(description="LLM 内容处理工具 (自有算力)")
    subparsers = parser.add_subparsers(dest="command", help="处理命令")

    # translate
    tp = subparsers.add_parser("translate", help="翻译")
    tp.add_argument("--text", help="直接传入文本")
    tp.add_argument("--file", help="从文件读取")
    tp.add_argument("--target", default="zh", help="目标语言 (zh/en/ja/ko)")
    tp.add_argument("--output", "-o", help="保存到文件")

    # summarize
    sp = subparsers.add_parser("summarize", help="摘要")
    sp.add_argument("--text", help="直接传入文本")
    sp.add_argument("--file", help="从文件读取")
    sp.add_argument("--style", default="bullet", choices=["bullet", "paragraph", "oneline"])
    sp.add_argument("--output", "-o", help="保存到文件")

    # custom
    cp = subparsers.add_parser("custom", help="自定义 prompt")
    cp.add_argument("--prompt", required=True, help="处理指令")
    cp.add_argument("--text", help="直接传入文本")
    cp.add_argument("--file", help="从文件读取")
    cp.add_argument("--output", "-o", help="保存到文件")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 获取输入文本
    text = args.text or ""
    if hasattr(args, "file") and args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    if not text:
        print("❌ 需要提供 --text 或 --file", file=sys.stderr)
        sys.exit(1)

    # 处理
    try:
        if args.command == "translate":
            result = translate(text, args.target)
        elif args.command == "summarize":
            result = summarize(text, args.style)
        elif args.command == "custom":
            result = custom_process(args.prompt, text)
        else:
            parser.print_help()
            sys.exit(1)
    except Exception as e:
        print(f"❌ LLM 调用失败: {e}", file=sys.stderr)
        sys.exit(1)

    # 输出
    output_path = getattr(args, "output", None)
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"✅ 已保存到 {output_path} ({len(result)} 字符)")
    else:
        print(result)


if __name__ == "__main__":
    main()
