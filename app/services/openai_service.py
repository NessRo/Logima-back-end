from openai import AsyncOpenAI
import asyncio
from app.config import Settings

settings = Settings()

class OpenAIService:
    def __init__(self, model: str = "gpt-5-mini", timeout_s: float = 8.0, retries: int = 1):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = model
        self.timeout_s = timeout_s
        self.retries = retries

    async def _call_with_retry(self, func, *args, **kwargs):
        last_err = None
        for _ in range(self.retries + 1):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=self.timeout_s)
            except Exception as e:
                last_err = e
                await asyncio.sleep(0.2)
        # fallback string on repeated failure
        return "AI summary unavailable."

    async def generate_outcome(self, description: str) -> str:
        """Summarize a project description into a short outcome statement."""
        system_prompt = (
            "You are a concise product coach. "
            "Given a project description, produce a 1–3 sentence outcome summary."
        )
        user_prompt = (
            f"Project description:\n{description.strip() or 'N/A'}\n\n"
            "Return only the outcome summary."
        )

        async def _call():
            resp = await self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_output_tokens=500,
            )
            return resp.output_text.strip()

        return await self._call_with_retry(_call)