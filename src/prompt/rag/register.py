"""
Dialog Prompts Registration
使用TOML配置文件自动注册prompts
"""

from pathlib import Path
from src.prompt.auto_register import register_prompts_from_toml

from src.prompt.get_prompt import get_prompt
from src.prompt.auto_register import register_custom_input_builder


def query_route_input_builder(args: dict) -> str:
    """
    query_route的自定义input_builder

    Args:
        args: 包含以下键的字典
            - titles: list[str]
            - keywords: list[list[str]]
            - question: str

    Returns:
        格式化后的prompt字符串
    """
    prompt = get_prompt("query_route", "rag")

    titles = args["titles"]
    keywords = args["keywords"]
    question = args["question"]

    # 将titles和keywords组合成字典
    collections = []
    for title, kws in zip(titles, keywords):
        collections.append({"collection": title, "keywords": kws})

    return prompt.format(collections=str(collections), question=str(question))


# 注册自定义input_builder
register_custom_input_builder("query_route", query_route_input_builder)


# 从同目录下的prompts.toml文件自动注册所有prompts
current_dir = Path(__file__).parent
toml_path = current_dir / "prompts.toml"

registered_prompts = register_prompts_from_toml(toml_path)
