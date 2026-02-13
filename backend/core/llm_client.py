import groq
import sentry_sdk

from api.config import settings

client = groq.Groq(api_key=settings.GROQ_API_KEY)

def call_llm(prompt: str, model: str, temperature: float = 0.0, max_tokens: int = 2048) -> str:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )

        content = response.choices[0].message.content  
        if not content:
            raise ValueError("LLM returned an empty response.")
        return content
    except Exception as e:
        sentry_sdk.capture_exception(e)
        return "Final Answer: I encountered a technical issue connecting to my core services. Please try again shortly."