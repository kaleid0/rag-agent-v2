import json

from src.prompt.PromptConfig import PromptConfig, register_prompt
from src.prompt.get_prompt import get_prompt

register_prompt(
    PromptConfig(
        name="short_term_memory_summary",
        input_builder=lambda args: get_prompt(
            "short_term_memory_summary", "memory"
        ).format(messages=str(args["messages"])),
        output_parser=json.loads,
        llm_args={"format": "json", "temperature": 0, "max_tokens": 1000},
    )
)

register_prompt(
    PromptConfig(
        name="long_term_memory_summary",
        input_builder=lambda args: get_prompt(
            "long_term_memory_summary", "memory"
        ).format(messages=str(args["messages"])),
        output_parser=json.loads,
        llm_args={"format": "json", "temperature": 0, "max_tokens": 2000},
    )
)

register_prompt(
    PromptConfig(
        name="memory_merge",
        input_builder=lambda args: get_prompt("memory_merge", "memory").format(
            existing_summary=str(args["existing_summary"]),
            new_summary=str(args["new_summary"]),
        ),
        output_parser=json.loads,
        llm_args={"format": "json", "temperature": 0, "max_tokens": 2000},
    )
)
