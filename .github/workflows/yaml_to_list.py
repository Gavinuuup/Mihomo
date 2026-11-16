#!/usr/bin/env python3
"""
YAML <-> List 双向转换（区分 domain / ipcidr 两类）。

用法:
  yaml_to_list.py <type> <in> <out>

  <type> = domain | ipcidr
  <in>   = 输入文件（.yaml/.yml/.list/.txt）
  <out>  = 输出文件（.yaml/.yml/.list/.txt）

方向由输出扩展名决定：
  - .list / .txt -> 纯文本
  - .yaml / .yml -> YAML payload

domain 类:
  .list:  +.x  / 裸域名
  YAML :  +.x  / 裸域名
  classical 写法会转成上面的形式

ipcidr 类:
  .list / YAML: 裸 CIDR
  classical 写法会去掉 IP-CIDR 前缀
"""
import sys
import yaml


class IndentDumper(yaml.Dumper):
    """让列表作为字典值时也带缩进（覆盖 PyYAML 默认的 indentless）。"""
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


# ---------- 通用工具 ----------

def is_text_path(path):
    lower = path.lower()
    return lower.endswith(".list") or lower.endswith(".txt")


def strip_comments(lines):
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


def read_input(path):
    """按扩展名读取，返回原始字符串列表。"""
    with open(path, encoding="utf-8") as f:
        content = f.read()

    if is_text_path(path):
        return strip_comments(content.splitlines())

    data = yaml.safe_load(content) or {}
    if isinstance(data, dict):
        payload = data.get("payload", []) or []
        return [str(x).strip() for x in payload if str(x).strip()]

    return strip_comments(content.splitlines())


def write_output(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        if is_text_path(path):
            f.write("\n".join(lines))
            if lines:
                f.write("\n")
        else:
            yaml.dump(
                {"payload": lines},
                f,
                Dumper=IndentDumper,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
                width=10**6,
                indent=4,
            )


# ---------- domain 类 ----------

def domain_to_canonical(raw):
    """把任意 domain 写法规整成 mihomo domain 类的规范写法。
    - DOMAIN-SUFFIX,x -> +.x
    - DOMAIN,x        -> x
    - +.x / 裸域名    -> 原样
    """
    s = raw.strip()
    if not s:
        return None

    up = s.upper()

    if up.startswith("DOMAIN-SUFFIX"):
        parts = s.split(",", 1)
        if len(parts) == 2:
            return f"+.{parts[1].strip().lstrip('+.')}"

    if up.startswith("DOMAIN,"):
        parts = s.split(",", 1)
        if len(parts) == 2:
            return parts[1].strip()

    return s


# ---------- ipcidr 类 ----------

def ipcidr_to_canonical(raw):
    """把任意 ipcidr 写法规整成裸 CIDR。
    - IP-CIDR,x   -> x
    - IP-CIDR6,x  -> x
    - 裸 CIDR     -> 原样
    """
    s = raw.strip()
    if not s:
        return None

    up = s.upper()

    if up.startswith("IP-CIDR6"):
        parts = s.split(",", 1)
        if len(parts) == 2:
            return parts[1].strip()

    if up.startswith("IP-CIDR"):
        parts = s.split(",", 1)
        if len(parts) == 2:
            return parts[1].strip()

    return s


# ---------- 主流程 ----------

def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    rtype, in_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

    if rtype not in ("domain", "ipcidr"):
        print(f"ERROR: unsupported type: {rtype}")
        sys.exit(1)

    raw_items = read_input(in_path)

    norm_fn = domain_to_canonical if rtype == "domain" else ipcidr_to_canonical

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

    print(f"[ok] {rtype}: {in_path} -> {out_path}: {len(lines)} lines")


if __name__ == "__main__":
    main()
