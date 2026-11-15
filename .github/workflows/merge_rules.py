#!/usr/bin/env python3
"""
合并两个 Clash 规则集，生成带多行注释头的新规则集。
支持输入：.yaml / .yml / .list / .txt
输出：按输出文件扩展名决定
  - .list / .txt  -> 纯文本，每行一条规则
  - .yaml / .yml  -> YAML payload

用法: merge_rules.py <name> <author> <base> <custom> <out>
"""
import sys
import datetime
import re
import yaml


class IndentDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


# DOMAIN-SUFFIX,x -> +.x（语义等价，安全）
CONVERT_SUFFIX_TO_PLUS = True

# DOMAIN,x -> x（会变成后缀匹配，注意语义变化）
CONVERT_DOMAIN_TO_BARE = True


def normalize(raw):
    """把一条规则规整成规范写法，返回 None 表示丢弃。"""
    s = str(raw).strip()

    if not s or s.startswith("#"):
        return None

    s = s.rstrip(",").strip()
    if not s:
        return None

    if CONVERT_SUFFIX_TO_PLUS:
        m = re.fullmatch(r"DOMAIN-SUFFIX\s*,\s*(.+)", s, re.IGNORECASE)
        if m:
            domain = m.group(1).strip().lstrip("+.")
            return f"+.{domain}"

    if CONVERT_DOMAIN_TO_BARE:
        m = re.fullmatch(r"DOMAIN\s*,\s*(.+)", s, re.IGNORECASE)
        if m:
            return m.group(1).strip()

    if "," in s:
        parts = [p.strip() for p in s.split(",")]
        s = ",".join(parts)

    return s


def _read_text_lines(content):
    """纯文本逐行读取，跳过空行和注释。"""
    result = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        result.append(line)
    return result


def load_payload(path):
    """按扩展名分流读取：.list/.txt 当纯文本，其他当 YAML。"""
    if not path:
        return []

    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"[warn] not found: {path}, treat as empty")
        return []

    lower = path.lower()

    if lower.endswith(".list") or lower.endswith(".txt"):
        raw_items = _read_text_lines(content)
    else:
        data = yaml.safe_load(content) or {}
        if isinstance(data, dict):
            payload = data.get("payload", []) or []
            raw_items = [str(x).strip() for x in payload if str(x).strip()]
        else:
            raw_items = _read_text_lines(content)

    result = []
    for item in raw_items:
        norm = normalize(item)
        if norm is not None:
            result.append(norm)
    return result


def is_text_output(out_path):
    lower = out_path.lower()
    return lower.endswith(".list") or lower.endswith(".txt")


def write_output(out_path, header, merged):
    """按输出扩展名写文件：list/txt 纯文本，yaml/yml 走 YAML。"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header)

        if is_text_output(out_path):
            # 纯文本：每行一条
            for item in merged:
                f.write(item + "\n")
        else:
            # YAML：payload 列表
            body = yaml.dump(
                {"payload": merged},
                Dumper=IndentDumper,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
                width=10**6,
            )
            f.write(body)


def main():
    if len(sys.argv) != 6:
        print(__doc__)
        sys.exit(1)

    name, author, base_path, custom_path, out_path = sys.argv[1:6]

    base = load_payload(base_path)
    custom = load_payload(custom_path)

    # 合并 + 去重，保持顺序：上游在前，自定义在后
    seen = set()
    merged = []
    for item in base + custom:
        if item not in seen:
            seen.add(item)
            merged.append(item)

    updated = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    updated_str = updated.strftime("%Y-%m-%d %H:%M:%S")

    header = (
        f"# NAME: {name}\n"
        f"# AUTHOR: {author}\n"
        f"# UPDATED: {updated_str}\n"
        f"# TOTAL: {len(merged)}\n"
        f"# BASE: {len(base)}\n"
        f"# CUSTOM: {len(custom)}\n"
    )

    write_output(out_path, header, merged)

    print(f"[ok] {out_path}: base={len(base)} custom={len(custom)} total={len(merged)}")


if __name__ == "__main__":
    main()
