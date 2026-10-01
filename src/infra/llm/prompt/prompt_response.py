from infra.llm.prompt.prompt_title import PromptTitle


class PromptResponse:

    def __init__(self, title: PromptTitle, question: str, llm_response: str):
        self.title = title
        self.question = question
        self.llm_response = llm_response
