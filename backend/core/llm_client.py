import sentry_sdk
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from groq import Groq

from api.config import settings
from api.constants import AIModel

client = Groq(api_key=settings.GROQ_API_KEY)

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
    
async def call_agent(prompt: str, model: str, total_tokens: int) -> str:    
    try:
        llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name=model,
            temperature=0.0,
            max_tokens=800,
            stop_sequences=["Observation:", "\nObservation:"]
        )
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        if hasattr(response, 'response_metadata'):
            usage = response.response_metadata.get('token_usage', {})
            tokens = usage.get('total_tokens', 0)
            if tokens > 0:
                total_tokens += tokens
                
        return response.content, total_tokens

    except Exception as e:
        error_msg = str(e).lower()
        sentry_sdk.capture_exception(e)
        
        is_limit_error = any(x in error_msg for x in ["429", "rate_limit", "rate limit", "tokens_per_day", "limit_exceeded"])
        
        if is_limit_error:
            sentry_sdk.capture_message("[SFA Agent] API limit hit - using fallback model", level="info")
            try:
                fallback_client = client
                fallback_response = fallback_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=AIModel.LLAMA_31_8B,
                    temperature=0.0,
                    max_tokens=800,
                    stop=["Observation:", "\nObservation:"]
                )
                return fallback_response.choices[0].message.content.strip(), total_tokens
            except Exception as fallback_error:
                sentry_sdk.capture_exception(fallback_error)
                return "Final Answer: The AI service is currently busy. Please try again in a few minutes."
                
        return "Final Answer: I could not process that request. Please try again."