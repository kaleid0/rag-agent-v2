import json

from src.prompt.PromptConfig import PromptConfig, register_prompt
from src.prompt.get_prompt import get_prompt

register_prompt(
    PromptConfig(
        name="extract_abstract",
        input_builder=lambda args: get_prompt("extract_abstract", "rag").format(
            text=str(args["text"])
        ),
        output_parser=json.loads,
        llm_args={"format": "json", "temperature": 0, "max_tokens": 1000},
    )
)

register_prompt(
    PromptConfig(
        name="extract_title",
        input_builder=lambda args: get_prompt("extract_title", "rag").format(
            text=str(args["text"])
        ),
        output_parser=json.loads,
        llm_args={"format": "json", "temperature": 0, "max_tokens": 200},
    )
)


register_prompt(
    PromptConfig(
        name="query_rewrite",
        input_builder=lambda args: get_prompt("query_rewrite", "rag").format(
            question=str(args["question"])
        ),
        output_parser=json.loads,
        llm_args={"format": "json", "temperature": 0, "max_tokens": 200},
    )
)


def query_route_inpput_builder(
    titles: list[str], keywords: list[list[str]], question: str
) -> str:
    prompt = get_prompt("query_route", "rag")
    collections = {}
    for title, kws in zip(titles, keywords):
        collections[title] = kws
    return prompt.format(collections=str(collections), question=str(question))


register_prompt(
    PromptConfig(
        name="query_route",
        input_builder=lambda args: query_route_inpput_builder(
            titles=args["titles"],
            keywords=args["keywords"],
            question=args["question"],
        ),
        output_parser=json.loads,
        llm_args={"format": "json", "temperature": 0, "max_tokens": 200},
    )
)

register_prompt(
    PromptConfig(
        name="grade_texts",
        input_builder=lambda args: get_prompt("grade_texts", "rag").format(
            query=str(args["query"]),
            text1=str(args["text1"]),
            text2=str(args["text2"]),
            text3=str(args["text3"]),
            text4=str(args["text4"]),
            text5=str(args["text5"]),
        ),
        output_parser=json.loads,
        llm_args={"format": "json", "temperature": 0, "max_tokens": 100},
    )
)
