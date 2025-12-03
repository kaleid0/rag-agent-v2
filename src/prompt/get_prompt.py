from pathlib import Path
import re

BASE_DIR = Path("src/prompt/prompt_template")


def md_to_xml(markdown_text: str) -> str:
    """
    将 Markdown 中的所有二级标题 ## title 转换为 XML 包裹形式
    示例：
        ## generate_query
        内容1
        ## query_route
        内容2
    转换为：
        <generate_query>
        内容1
        </generate_query>
        <query_route>
        内容2
        </query_route>
    """
    # 匹配所有二级标题
    pattern = r"^##\s+(.+)$"

    # 找到所有标题及其位置
    matches = list(re.finditer(pattern, markdown_text, flags=re.MULTILINE))
    if not matches:
        return markdown_text

    xml_parts = []
    for i, match in enumerate(matches):
        tag_name = match.group(1).strip().replace(" ", "_")  # 标签名
        start = match.end()  # 内容开始位置
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown_text)
        content = markdown_text[start:end].lstrip("\n").rstrip()  # 去掉多余换行
        xml_parts.append(f"<{tag_name}>\n{content}\n</{tag_name}>")

    return "\n".join(xml_parts)


def _preprocess(prompt: str) -> str:
    """删除 markdown 中的一级标题"""
    lines = prompt.splitlines()
    return "\n".join(line for line in lines if not line.startswith("# "))


def load_prompt(prompt_name: str, module_name: str) -> str:
    """读取 markdown prompt 文件"""
    file_path = BASE_DIR / module_name / f"{prompt_name}.md"

    if file_path.exists():
        return file_path.read_text(encoding="utf-8")
    else:
        raise FileNotFoundError(f"Prompt 文件不存在: {file_path.resolve()}\n")


def get_prompt(prompt_name: str, module_name: str) -> str:
    """
    读取 markdown prompt 并转为 xml tag prompt
    """
    markdown_text = load_prompt(prompt_name, module_name)
    markdown_text = _preprocess(markdown_text)
    return md_to_xml(markdown_text)
