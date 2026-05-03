from openai import OpenAI
from app.core.generation_config import generation_config


class APIClient:

    def __init__(self):
        self.client = OpenAI(
            api_key=generation_config.API_KEY,
            base_url=generation_config.API_BASE_URL
        )
        self.model = generation_config.API_MODEL

    def generate(
            self,
            prompt: str,
            max_new_tokens: int = None,
            temperature: float = None,
            top_p: float = None,
            repetition_penalty: float = None
    ) -> str:

        max_new_tokens = max_new_tokens or generation_config.DEFAULT_MAX_NEW_TOKENS
        temperature = temperature if temperature is not None else generation_config.DEFAULT_TEMPERATURE
        top_p = top_p if top_p is not None else generation_config.DEFAULT_TOP_P
        repetition_penalty = repetition_penalty if repetition_penalty is not None else generation_config.DEFAULT_REPETITION_PENALTY

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            extra_body={
                "repetition_penalty": repetition_penalty
            } if repetition_penalty != 1.0 else {}
        )

        return response.choices[0].message.content