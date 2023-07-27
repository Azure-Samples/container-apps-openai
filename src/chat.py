# Import packages
import os
import sys
import time
import openai
import random
import logging
import chainlit as cl
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from dotenv import dotenv_values

# Load environment variables from .env file
if os.path.exists(".env"):
    load_dotenv(override = True)
    config = dotenv_values(".env")

# Read environment variables
temperature = float(os.environ.get("TEMPERATURE", 0.9))
api_base = os.getenv("AZURE_OPENAI_BASE")
api_key = os.getenv("AZURE_OPENAI_KEY")
api_type = os.environ.get("AZURE_OPENAI_TYPE", "azure")
api_version = os.environ.get("AZURE_OPENAI_VERSION", "2023-06-01-preview")
engine = os.getenv("AZURE_OPENAI_DEPLOYMENT")
model = os.getenv("AZURE_OPENAI_MODEL")
system_content = os.getenv("AZURE_OPENAI_SYSTEM_MESSAGE", "You are a helpful assistant.")
max_retries = int(os.getenv("MAX_RETRIES", 5))
backoff_in_seconds = float(os.getenv("BACKOFF_IN_SECONDS", 1))
token_refresh_interval = int(os.getenv("TOKEN_REFRESH_INTERVAL", 1800))

# Configure OpenAI
openai.api_type = api_type
openai.api_version = api_version
openai.api_base = api_base
openai.api_key = api_key

# Set default Azure credential
default_credential = DefaultAzureCredential(
) if openai.api_type ==  "azure_ad" else None

# Configure a logger
logging.basicConfig(stream = sys.stdout,
                    format = '[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
                    level = logging.INFO)
logger = logging.getLogger(__name__)

def backoff(attempt : int) -> float:
    return backoff_in_seconds * 2**attempt + random.uniform(0, 1)

# Refresh the OpenAI security token every 45 minutes
def refresh_openai_token():
    token = cl.user_session.get('openai_token')
    if token ==  None or token.expires_on < int(time.time()) - token_refresh_interval:
        cl.user_session.set('openai_token', default_credential.get_token(
            "https://cognitiveservices.azure.com/.default"))
        openai.api_key = cl.user_session.get('openai_token').token

@cl.on_chat_start
async def start_chat():
    await cl.Avatar(
        name = "Chatbot",
        url = "https://cdn-icons-png.flaticon.com/512/8649/8649595.png"
    ).send()
    await cl.Avatar(
        name = "Error",
        url = "https://cdn-icons-png.flaticon.com/512/8649/8649595.png"
    ).send()
    await cl.Avatar(
        name = "User",
        url = "https://media.architecturaldigest.com/photos/5f241de2c850b2a36b415024/master/w_1600%2Cc_limit/Luke-logo.png"
    ).send()
    cl.user_session.set(
        "message_history",
        [{"role": "system", "content": system_content}],
    )

@cl.on_message
async def main(message: str):
    message_history = cl.user_session.get("message_history")
    message_history.append({"role": "user", "content": message})

    # Create the Chainlit response message
    msg = cl.Message(content = "")

    # Retry the OpenAI API call if it fails
    for attempt in range(max_retries):
        try:
            # Refresh the OpenAI security token if using Azure AD
            if openai.api_type ==  "azure_ad":
                refresh_openai_token()

            # Send the message to OpenAI in an asynchronous mode and stream the response
            async for stream_resp in await openai.ChatCompletion.acreate(
                engine = engine,
                model = model,
                messages = message_history,
                temperature = temperature,
                stream = True
            ):
                if stream_resp and len(stream_resp.choices) > 0:
                    token = stream_resp.choices[0]["delta"].get("content", "")
                    await msg.stream_token(token)
            break
        except openai.error.Timeout:
            # Implement exponential backoff
            wait_time = backoff(attempt)
            logger.exception(f"OpenAI API timeout occurred. Waiting {wait_time} seconds and trying again.")
            time.sleep(wait_time)
        except openai.error.APIError:
            # Implement exponential backoff
            wait_time = backoff(attempt)
            logger.exception(f"OpenAI API error occurred. Waiting {wait_time} seconds and trying again.")
            time.sleep(wait_time)
        except openai.error.APIConnectionError:
            # Implement exponential backoff
            wait_time = backoff(attempt)
            logger.exception(f"OpenAI API connection error occurred. Check your network settings, proxy configuration, SSL certificates, or firewall rules. Waiting {wait_time} seconds and trying again.")
            time.sleep(wait_time)
        except openai.error.InvalidRequestError:
            # Implement exponential backoff
            wait_time = backoff(attempt)
            logger.exception(f"OpenAI API invalid request. Check the documentation for the specific API method you are calling and make sure you are sending valid and complete parameters. Waiting {wait_time} seconds and trying again.")
            time.sleep(wait_time)
        except openai.error.ServiceUnavailableError:
            # Implement exponential backoff
            wait_time = backoff(attempt)
            logger.exception(f"OpenAI API service unavailable. Waiting {wait_time} seconds and trying again.")
            time.sleep(wait_time)
        except Exception as e:
            logger.exception(f"A non retriable error occurred. {e}")
            break

    message_history.append({"role": "assistant", "content": msg.content})
    await msg.send()
