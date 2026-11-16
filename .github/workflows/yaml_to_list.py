#!/usr/bin/env python3
"""
YAML <-> List 双向转换。
输入格式自动识别（按扩展名），输出格式由输出文件扩展名决定：
  - .list / .txt -> 纯文本，每行一条规则
  - .yaml / .yml -> YAML payload

用法: yaml_to_list.py <in> <out>
"""
import sys
import yaml


def normalize_to_text(raw):
    """把一条规则转成 text 写法，返回 None 表示丢弃。"""
    s = str(raw).strip()
    if not s or s.startswith("#"):
        return None

    s = s.rstrip(",").strip()
    if not s:
        return None

    # DOMAIN-SUFFIX,x  ->  +.x
    if s.upper().startswith("DOMAIN-SUFFIX"):
        parts = s.split(",", 1)
        if len(parts) == 2:
            domain = parts[1].strip().lstrip("+.")
            return f"+.{domain}"

    # DOMAIN,x  ->  x
    if s.upper().startswith("DOMAIN,"):
        parts = s.split(",", 1)
        if len(parts) == 2:
            return parts[1].strip()

    if "," in s:
        parts = [p.strip() for p in s.split(",")]
        s = ",".join(parts)

    return s


def normalize_to_yaml(raw):
    """把 text 写法转回 YAML 规则写法，返回 None 表示丢弃。"""
    s = str(raw).strip()
    if not s or s.startswith("#"):
        return None

    s = s.rstrip(",").strip()
    if not s:
        return None

    # +.x  ->  DOMAIN-SUFFIX,x
    if s.startswith("+."):
        return f"DOMAIN-SUFFIX,{s[2:]}"

    # 裸域名（不含逗号、不含斜杠、不是 IP 段）-> DOMAIN-SUFFIX
    if "," not in s and "/" not in s:
        if "," not in s and "/" not in s:

    # 其他规则原样保留，只去掉逗号周围空格
    if "," in s:
        parts = [p.strip() for p in s.split(",")]
        s = ",".join(parts)

    return s


def read_input(path):
    """按扩展名读取：list/txt 纯文本，其他 YAML。返回字符串列表。"""
    with open(path, encoding="utf-8") as f:
        content = f.read()

    lower = path.lower()

    if lower.endswith(".list") or lower.endswith(".txt"):
        return [ln.strip() for ln in content.splitlines() if ln.strip() and not ln.strip().startswith("#")]

    data = yaml.safe_load(content) or {}
    if isinstance(data, dict):
        payload = data.get("payload", []) or []
        return [str(x).strip() for x in payload if str(x).strip()]

    return [ln.strip() for ln in content.splitlines() if ln.strip() and not ln.strip().startswith("#")]


def is_text_output(path):
    lower = path.lower()
    return lower.endswith(".list") or lower.endswith(".txt")


def write_output(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        if is_text_output(path):
            f.write("\n".join(lines))
            if lines:
                f.write("\n")
        else:
            yaml.dump(
                {"payload": lines},
                f,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
                width=10**6,
            )


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    in_path, out_path = sys.argv[1], sys.argv[2]

    raw_items = read_input(in_path)

    # 根据输出方向选择归一化函数
    if is_text_output(out_path):
        norm_fn = normalize_to_text
    else:
        norm_fn = normalize_to_yaml

    lines = []
    seen = set()
    for item in raw_items:
        norm = norm_fn(item)
        if norm is None:
            continue
        if norm in seen:
            continue
        seen.add(norm)
        lines.append(norm)

    write_output(out_path, lines)

    print(f"[ok] {in_path} -> {out_path}: {len(lines)} lines")


if __name__ == "__main__":
    main()
