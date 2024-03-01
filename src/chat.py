# Import packages
import os
import sys
from openai import AsyncAzureOpenAI
import logging
import chainlit as cl
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from dotenv import dotenv_values

# Load environment variables from .env file
if os.path.exists(".env"):
    load_dotenv(override=True)
    config = dotenv_values(".env")

# Read environment variables
temperature = float(os.environ.get("TEMPERATURE", 0.9))
api_base = os.getenv("AZURE_OPENAI_BASE")
api_key = os.getenv("AZURE_OPENAI_KEY")
api_type = os.environ.get("AZURE_OPENAI_TYPE", "azure")
api_version = os.environ.get("AZURE_OPENAI_VERSION", "2023-12-01-preview")
engine = os.getenv("AZURE_OPENAI_DEPLOYMENT")
model = os.getenv("AZURE_OPENAI_MODEL")
system_content = os.getenv(
    "AZURE_OPENAI_SYSTEM_MESSAGE", "You are a helpful assistant."
)
max_retries = int(os.getenv("MAX_RETRIES", 5))
timeout = int(os.getenv("TIMEOUT", 30))
debug = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

# Create Token Provider
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
)

# Configure OpenAI
if api_type == "azure":
    openai = AsyncAzureOpenAI(
        api_version=api_version,
        api_key=api_key,
        azure_endpoint=api_base,
        max_retries=max_retries,
        timeout=timeout,
    )
else:
    openai = AsyncAzureOpenAI(
        api_version=api_version,
        azure_endpoint=api_base,
        azure_ad_token_provider=token_provider,
        max_retries=max_retries,
        timeout=timeout,
    )

# Configure a logger
logging.basicConfig(
    stream=sys.stdout,
    format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


@cl.on_chat_start
async def start_chat():
    await cl.Avatar(
        name="Chatbot", url="https://cdn-icons-png.flaticon.com/512/8649/8649595.png"
    ).send()
    await cl.Avatar(
        name="Error", url="https://cdn-icons-png.flaticon.com/512/8649/8649595.png"
    ).send()
    await cl.Avatar(
        name="You",
        url="https://media.architecturaldigest.com/photos/5f241de2c850b2a36b415024/master/w_1600%2Cc_limit/Luke-logo.png",
    ).send()
    cl.user_session.set(
        "message_history",
        [{"role": "system", "content": system_content}],
    )


@cl.on_message
async def on_message(message: cl.Message):
    message_history = cl.user_session.get("message_history")
    message_history.append({"role": "user", "content": message.content})
    logger.info("Question: [%s]", message.content)

    # Create the Chainlit response message
    msg = cl.Message(content="")

    async for stream_resp in await openai.chat.completions.create(
        model=model,
        messages=message_history,
        temperature=temperature,
        stream=True,
    ):
        if stream_resp and len(stream_resp.choices) > 0:
            token = stream_resp.choices[0].delta.content or ""
            await msg.stream_token(token)

    if debug:
        logger.info("Answer: [%s]", msg.content)

    message_history.append({"role": "assistant", "content": msg.content})
    await msg.send()
