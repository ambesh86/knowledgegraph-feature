from infra.llm.prompt.goal_prompt_title import GoalPromptTitle


class GoalPromptResponse:

    def __init__(
        self, title: GoalPromptTitle, input: dict[str, str], llm_response: str
    ):
        self.title = title
        self.input = input
        self.llm_response = llm_response
