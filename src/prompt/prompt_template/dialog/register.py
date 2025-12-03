from src.prompt.PromptConfig import PromptConfig, register_prompt
from src.prompt.get_prompt import get_prompt

register_prompt(
    PromptConfig(
        name="RAG_answer",
        input_builder=lambda args: get_prompt("RAG_answer", "dialog").format(
            information=str(args["information"]),
            question=str(args["question"]),
        ),
        output_parser=lambda response: response,
        llm_args={
            "temperature": 0.2,
            "max_tokens": 2048,
        },
    )
)


