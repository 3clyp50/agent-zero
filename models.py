from enum import Enum
import os
from typing import Any, Callable, Awaitable
from langchain_openai import (
    OpenAI,
    ChatOpenAI,
    OpenAIEmbeddings,
    AzureChatOpenAI,
    AzureOpenAIEmbeddings,
    AzureOpenAI,
)
from langchain_ollama import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from langchain_huggingface import (
    HuggingFaceEmbeddings,
    ChatHuggingFace,
    HuggingFaceEndpoint,
)
from langchain_google_genai import (
    GoogleGenerativeAI,
    HarmBlockThreshold,
    HarmCategory,
    embeddings as google_embeddings,
)
from langchain_mistralai import ChatMistralAI
from python.helpers import dotenv, runtime
from python.helpers.dotenv import load_dotenv
from python.helpers.rate_limiter import RateLimiter
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

# Environment variables
load_dotenv()

# Configuration
DEFAULT_TEMPERATURE = 0.0

class ModelType(Enum):
    CHAT = "Chat"
    VISION = "Vision"
    EMBEDDING = "Embedding"

class ModelProvider(Enum):
    ANTHROPIC = "Anthropic"
    DEEPSEEK = "DeepSeek"
    GOOGLE = "Google"
    GROQ = "Groq"
    HUGGINGFACE = "HuggingFace"
    LMSTUDIO = "LM Studio"
    MISTRALAI = "Mistral AI"
    OLLAMA = "Ollama"
    OPENAI = "OpenAI"
    OPENAI_AZURE = "OpenAI Azure"
    OPENROUTER = "OpenRouter"
    SAMBANOVA = "Sambanova"
    OTHER = "Other"

rate_limiters: dict[str, RateLimiter] = {}

# Utility function to get API keys from environment variables
def get_api_key(service: str) -> str:
    return (
        dotenv.get_dotenv_value(f"API_KEY_{service.upper()}")
        or dotenv.get_dotenv_value(f"{service.upper()}_API_KEY")
        or "None"
    )

def get_model(type: ModelType, provider: ModelProvider, name: str, **kwargs):
    fnc_name = f"get_{provider.name.lower()}_{type.name.lower()}"  # e.g., get_openai_vision
    if fnc_name in globals():
        model = globals()[fnc_name](name, **kwargs)  # Call the appropriate getter
        return model
    else:
        raise ValueError(f"No getter function defined for {provider} and {type}")

def get_rate_limiter(
    provider: ModelProvider, name: str, requests: int, input: int, output: int
) -> RateLimiter:
    # Get or create
    key = f"{provider.name}\\{name}"
    rate_limiters[key] = limiter = rate_limiters.get(key, RateLimiter(seconds=60))
    # Always update
    limiter.limits["requests"] = requests or 0
    limiter.limits["input"] = input or 0
    limiter.limits["output"] = output or 0
    return limiter

def parse_chunk(chunk: Any) -> str:
    if isinstance(chunk, str):
        content = chunk
    elif hasattr(chunk, "content"):
        content = str(chunk.content)
    else:
        content = str(chunk)
    return content

# ----------------------------
# Provider-Specific Getter Functions
# ----------------------------

# --- Ollama Models ---
def get_ollama_base_url() -> str:
    return (
        dotenv.get_dotenv_value("OLLAMA_BASE_URL")
        or f"http://{runtime.get_local_url()}:11434"
    )

def get_ollama_chat(
    model_name: str,
    temperature=DEFAULT_TEMPERATURE,
    base_url: str = None,
    num_ctx: int = 8192,
    **kwargs,
):
    if not base_url:
        base_url = get_ollama_base_url()
    return ChatOllama(
        model=model_name,
        temperature=temperature,
        base_url=base_url,
        num_ctx=num_ctx,
        **kwargs,
    )

def get_ollama_embedding(
    model_name: str,
    temperature=DEFAULT_TEMPERATURE,
    base_url: str = None,
    **kwargs,
):
    if not base_url:
        base_url = get_ollama_base_url()
    return OllamaEmbeddings(
        model=model_name, temperature=temperature, base_url=base_url, **kwargs
    )

def get_ollama_vision(
    model_name: str,
    temperature=DEFAULT_TEMPERATURE,
    base_url: str = None,
    **kwargs,
):
    if not base_url:
        base_url = get_ollama_base_url()
    # Replace ChatOllama with the appropriate Vision class if available
    # Assuming ChatOllama can handle vision tasks; adjust if there's a specific class
    return ChatOllama(
        model=model_name,
        temperature=temperature,
        base_url=base_url,
        num_ctx=8192,
        **kwargs,
    )

# --- HuggingFace Models ---
def get_huggingface_chat(
    model_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("huggingface") or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
    llm = HuggingFaceEndpoint(
        repo_id=model_name,
        task="text-generation",
        do_sample=True,
        temperature=temperature,
        **kwargs,
    )
    return ChatHuggingFace(llm=llm)

def get_huggingface_embedding(model_name: str, **kwargs):
    return HuggingFaceEmbeddings(model_name=model_name, **kwargs)

def get_huggingface_vision(
    model_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("huggingface") or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
    # Adjust the task as needed based on HuggingFace's vision capabilities
    llm = HuggingFaceEndpoint(
        repo_id=model_name,
        task="image-classification",  # Example task; adjust as needed
        do_sample=True,
        temperature=temperature,
        **kwargs,
    )
    # Replace ChatHuggingFace with the appropriate Vision class if available
    return ChatHuggingFace(llm=llm)  # Change to Vision-specific class if available

# --- LM Studio Models ---
def get_lmstudio_base_url() -> str:
    return (
        dotenv.get_dotenv_value("LM_STUDIO_BASE_URL")
        or f"http://{runtime.get_local_url()}:1234/v1"
    )

def get_lmstudio_chat(
    model_name: str,
    temperature=DEFAULT_TEMPERATURE,
    base_url: str = None,
    **kwargs,
):
    if not base_url:
        base_url = get_lmstudio_base_url()
    return ChatOpenAI(
        model_name=model_name,
        base_url=base_url,
        temperature=temperature,
        api_key="none",
        **kwargs,
    )  # type: ignore

def get_lmstudio_embedding(
    model_name: str,
    base_url: str = None,
    **kwargs,
):
    if not base_url:
        base_url = get_lmstudio_base_url()
    return OpenAIEmbeddings(
        model=model_name,
        api_key="none",
        base_url=base_url,
        check_embedding_ctx_length=False,
        **kwargs,
    )  # type: ignore

def get_lmstudio_vision(
    model_name: str,
    temperature=DEFAULT_TEMPERATURE,
    base_url: str = None,
    **kwargs,
):
    if not base_url:
        base_url = get_lmstudio_base_url()
    # Replace ChatOpenAI with the appropriate Vision class if available
    return ChatOpenAI(
        model_name=model_name,
        base_url=base_url,
        temperature=temperature,
        api_key="none",
        **kwargs,
    )  # type: ignore

# --- Anthropic Models ---
def get_anthropic_chat(
    model_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("anthropic")
    return ChatAnthropic(
        model_name=model_name,
        temperature=temperature,
        api_key=api_key,
        **kwargs,
    )  # type: ignore

def get_anthropic_embedding(
    model_name: str,
    api_key=None,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("anthropic")
    # Anthropic currently uses OpenAIEmbeddings as a placeholder; adjust if Antropic provides its own embeddings
    return OpenAIEmbeddings(
        model=model_name,
        api_key=api_key,
        **kwargs,
    )  # type: ignore

def get_anthropic_vision(
    model_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("anthropic")
    # Replace ChatAnthropic with the appropriate Vision class if available
    return ChatAnthropic(
        model_name=model_name,
        temperature=temperature,
        api_key=api_key,
        **kwargs,
    )  # Adjust if there's a specific Vision class

# --- OpenAI Models ---
def get_openai_chat(
    model_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("openai")
    return ChatOpenAI(
        model_name=model_name,
        temperature=temperature,
        api_key=api_key,
        **kwargs,
    )  # type: ignore

def get_openai_embedding(model_name: str, api_key=None, **kwargs):
    if not api_key:
        api_key = get_api_key("openai")
    return OpenAIEmbeddings(
        model=model_name,
        api_key=api_key,
        **kwargs,
    )  # type: ignore

def get_openai_azure_chat(
    deployment_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    azure_endpoint=None,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("openai_azure")
    if not azure_endpoint:
        azure_endpoint = dotenv.get_dotenv_value("OPENAI_AZURE_ENDPOINT")
    return AzureChatOpenAI(
        deployment_name=deployment_name,
        temperature=temperature,
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        **kwargs,
    )  # type: ignore

def get_openai_azure_embedding(
    deployment_name: str,
    api_key=None,
    azure_endpoint=None,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("openai_azure")
    if not azure_endpoint:
        azure_endpoint = dotenv.get_dotenv_value("OPENAI_AZURE_ENDPOINT")
    return AzureOpenAIEmbeddings(
        deployment_name=deployment_name,
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        **kwargs,
    )  # type: ignore

def get_openai_vision(
    model_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("openai")
    # Replace ChatOpenAI with the appropriate Vision class if available
    return ChatOpenAI(
        model_name=model_name,
        temperature=temperature,
        api_key=api_key,
        **kwargs,
    )
    # If OpenAI has a specific vision class, use that instead

# --- Google Models ---
def get_google_chat(
    model_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("google")
    return GoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        google_api_key=api_key,
        safety_settings={
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
        },
        **kwargs,
    )  # type: ignore

def get_google_embedding(
    model_name: str,
    api_key=None,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("google")
    return google_embeddings.GoogleGenerativeAIEmbeddings(
        model=model_name,
        api_key=api_key,
        **kwargs,
    )  # type: ignore

def get_google_vision(
    model_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("google")
    # Replace with appropriate Google vision class if available
    return GoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        google_api_key=api_key,
        safety_settings={
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
        },
        **kwargs,
    )
    # Adjust task if needed

# --- MistralAI Models ---
def get_mistralai_chat(
    model_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("mistral")
    return ChatMistralAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        **kwargs,
    )  # type: ignore

def get_mistralai_embedding(
    model_name: str,
    api_key=None,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("mistral")
    return OpenAIEmbeddings(
        model=model_name,
        api_key=api_key,
        **kwargs,
    )  # type: ignore

def get_mistralai_vision(
    model_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("mistral")
    return ChatMistralAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        **kwargs,
    )  # type: ignore

# --- Groq Models ---
def get_groq_chat(
    model_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("groq")
    return ChatGroq(
        model_name=model_name,
        temperature=temperature,
        api_key=api_key,
        **kwargs,
    )  # type: ignore

def get_groq_embedding(
    model_name: str,
    api_key=None,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("groq")
    return OpenAIEmbeddings(
        model=model_name,
        api_key=api_key,
        **kwargs,
    )  # type: ignore

def get_groq_vision(
    model_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("groq")
    # Replace ChatGroq with the appropriate Vision class if available
    return ChatGroq(
        model_name=model_name,
        temperature=temperature,
        api_key=api_key,
        **kwargs,
    )

# --- DeepSeek Models ---
def get_deepseek_chat(
    model_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    base_url=None,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("deepseek")
    if not base_url:
        base_url = (
            dotenv.get_dotenv_value("DEEPSEEK_BASE_URL")
            or "https://api.deepseek.com"
        )
    return ChatOpenAI(
        api_key=api_key,
        model=model_name,
        temperature=temperature,
        base_url=base_url,
        **kwargs,
    )  # type: ignore

def get_deepseek_embedding(
    model_name: str,
    api_key=None,
    base_url=None,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("deepseek")
    if not base_url:
        base_url = (
            dotenv.get_dotenv_value("DEEPSEEK_BASE_URL")
            or "https://api.deepseek.com"
        )
    return OpenAIEmbeddings(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        **kwargs,
    )  # type: ignore

def get_deepseek_vision(
    model_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    base_url=None,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("deepseek")
    if not base_url:
        base_url = (
            dotenv.get_dotenv_value("DEEPSEEK_BASE_URL")
            or "https://api.deepseek.com"
        )
    return ChatOpenAI(
        api_key=api_key,
        model=model_name,
        temperature=temperature,
        base_url=base_url,
        **kwargs,
    )  # type: ignore

# --- OpenRouter Models ---
def get_openrouter_chat(
    model_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    base_url=None,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("openrouter")
    if not base_url:
        base_url = (
            dotenv.get_dotenv_value("OPEN_ROUTER_BASE_URL")
            or "https://openrouter.ai/api/v1"
        )
    return ChatOpenAI(
        api_key=api_key,
        model=model_name,
        temperature=temperature,
        base_url=base_url,
        **kwargs,
    )  # type: ignore

def get_openrouter_embedding(
    model_name: str,
    api_key=None,
    base_url=None,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("openrouter")
    if not base_url:
        base_url = (
            dotenv.get_dotenv_value("OPEN_ROUTER_BASE_URL")
            or "https://openrouter.ai/api/v1"
        )
    return OpenAIEmbeddings(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        **kwargs,
    )  # type: ignore

def get_openrouter_vision(
    model_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    base_url=None,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("openrouter")
    if not base_url:
        base_url = (
            dotenv.get_dotenv_value("OPEN_ROUTER_BASE_URL")
            or "https://openrouter.ai/api/v1"
        )
    return ChatOpenAI(
        api_key=api_key,
        model=model_name,
        temperature=temperature,
        base_url=base_url,
        **kwargs,
    )  # type: ignore

# --- Sambanova Models ---
def get_sambanova_chat(
    model_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    base_url=None,
    max_tokens=1024,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("sambanova")
    if not base_url:
        base_url = (
            dotenv.get_dotenv_value("SAMBANOVA_BASE_URL")
            or "https://fast-api.snova.ai/v1"
        )
    return ChatOpenAI(
        api_key=api_key,
        model=model_name,
        temperature=temperature,
        base_url=base_url,
        max_tokens=max_tokens,
        **kwargs,
    )  # type: ignore

def get_sambanova_embedding(
    model_name: str,
    api_key=None,
    base_url=None,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("sambanova")
    if not base_url:
        base_url = (
            dotenv.get_dotenv_value("SAMBANOVA_BASE_URL")
            or "https://fast-api.snova.ai/v1"
        )
    # Sambanova currently uses OpenAIEmbeddings as a placeholder; adjust if Sambanova provides its own embeddings
    return OpenAIEmbeddings(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        **kwargs,
    )  # type: ignore

def get_sambanova_vision(
    model_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    base_url=None,
    max_tokens=1024,
    **kwargs,
):
    if not api_key:
        api_key = get_api_key("sambanova")
    if not base_url:
        base_url = (
            dotenv.get_dotenv_value("SAMBANOVA_BASE_URL")
            or "https://fast-api.snova.ai/v1"
        )
    return ChatOpenAI(
        api_key=api_key,
        model=model_name,
        temperature=temperature,
        base_url=base_url,
        max_tokens=max_tokens,
        **kwargs,
    )  # type: ignore

# --- Other Models ---
def get_other_chat(
    model_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    base_url=None,
    **kwargs,
):
    return ChatOpenAI(
        api_key=api_key,
        model=model_name,
        temperature=temperature,
        base_url=base_url,
        **kwargs,
    )  # type: ignore

def get_other_embedding(model_name: str, api_key=None, base_url=None, **kwargs):
    return OpenAIEmbeddings(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        **kwargs,
    )  # type: ignore

def get_other_vision(
    model_name: str,
    api_key=None,
    temperature=DEFAULT_TEMPERATURE,
    base_url=None,
    **kwargs,
):
    return ChatOpenAI(
        api_key=api_key,
        model=model_name,
        temperature=temperature,
        base_url=base_url,
        **kwargs,
    )  # type: ignore