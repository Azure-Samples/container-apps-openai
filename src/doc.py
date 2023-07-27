# Import packages
import os
import io
import sys
import time
import openai
import random
import logging
import chainlit as cl
from pypdf import PdfReader
from docx import Document
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from dotenv import dotenv_values
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.chat_models import AzureChatOpenAI
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

# These three lines swap the stdlib sqlite3 lib with the pysqlite3 package
__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

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
chat_completion_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
embeddings_deployment = os.getenv("AZURE_OPENAI_ADA_DEPLOYMENT")
model = os.getenv("AZURE_OPENAI_MODEL")
max_size_mb = int(os.getenv("CHAINLIT_MAX_SIZE_MB", 100))
max_files = int(os.getenv("CHAINLIT_MAX_FILES", 10))
text_splitter_chunk_size = int(os.getenv("TEXT_SPLITTER_CHUNK_SIZE", 1000))
text_splitter_chunk_overlap = int(os.getenv("TEXT_SPLITTER_CHUNK_OVERLAP", 10))
embeddings_chunk_size = int(os.getenv("EMBEDDINGS_CHUNK_SIZE", 16))
max_retries = int(os.getenv("MAX_RETRIES", 5))
backoff_in_seconds = float(os.getenv("BACKOFF_IN_SECONDS", 1))
token_refresh_interval = int(os.getenv("TOKEN_REFRESH_INTERVAL", 1800))

# Configure system prompt
system_template = """Use the following pieces of context to answer the users question.
If you don't know the answer, just say that you don't know, don't try to make up an answer.
ALWAYS return a "SOURCES" part in your answer.
The "SOURCES" part should be a reference to the source of the document from which you got your answer.

Example of your response should be:

```
The answer is foo
SOURCES: xyz
```

Begin!
----------------
{summaries}"""
messages = [
    SystemMessagePromptTemplate.from_template(system_template),
    HumanMessagePromptTemplate.from_template("{question}"),
]
prompt = ChatPromptTemplate.from_messages(messages)
chain_type_kwargs = {"prompt": prompt}

# Configure OpenAI
openai.api_type = api_type
openai.api_version = api_version
openai.api_base = api_base
openai.api_key = api_key

# Set default Azure credential
default_credential = DefaultAzureCredential(
) if openai.api_type  ==  "azure_ad" else None

# Configure a logger
logging.basicConfig(stream = sys.stdout,
                    format = '[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
                    level = logging.INFO)
logger = logging.getLogger(__name__)

# Refresh the OpenAI security token every 45 minutes
def refresh_openai_token():
    token = cl.user_session.get('openai_token')
    if token  ==  None or token.expires_on < int(time.time()) - token_refresh_interval:
        cl.user_session.set('openai_token', default_credential.get_token(
            "https://cognitiveservices.azure.com/.default"))
        openai.api_key = cl.user_session.get('openai_token').token

def backoff(attempt : int) -> float:
    return backoff_in_seconds * 2**attempt + random.uniform(0, 1)

@cl.on_chat_start
async def start():
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

    # Initialize the file list to None
    files = None

    # Wait for the user to upload a file
    while files  ==  None:
        files = await cl.AskFileMessage(
            content = f"Please upload up to {max_files} `.pdf` or `.docx` files to begin.",
            accept = ["application/pdf",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
            max_size_mb = max_size_mb,
            max_files = max_files,
            timeout = 86400,
            raise_on_timeout = False
        ).send()

    # Create a message to inform the user that the files are being processed
    content = ''
    if (len(files)  ==  1):
        content = f"Processing `{files[0].name}`..."
    else:
        files_names = [f"`{f.name}`" for f in files]
        content = f"Processing {', '.join(files_names)}..."
    msg = cl.Message(content = content, author = "Chatbot")
    await msg.send()

    # Create a list to store the texts of each file
    all_texts = []

    # Process each file uplodaded by the user
    for file in files:

        # Create an in-memory buffer from the file content
        bytes = io.BytesIO(file.content)

        # Get file extension
        extension = file.name.split('.')[-1]

        # Initialize the text variable
        text = ''

        # Read the file
        if extension  ==  "pdf":
            reader = PdfReader(bytes)
            for i in range(len(reader.pages)):
                text +=  reader.pages[i].extract_text()
        elif extension  ==  "docx":
            doc = Document(bytes)
            paragraph_list = []
            for paragraph in doc.paragraphs:
                paragraph_list.append(paragraph.text)
            text = '\n'.join(paragraph_list)

        # Split the text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = text_splitter_chunk_size,
            chunk_overlap = text_splitter_chunk_overlap)
        texts = text_splitter.split_text(text)

        # Add the chunks and metadata to the list
        all_texts.extend(texts)

    # Create a metadata for each chunk
    metadatas = [{"source": f"{i}-pl"} for i in range(len(all_texts))]

    #  Refresh the OpenAI security token if using Azure AD
    if openai.api_type  ==  "azure_ad":
        refresh_openai_token()

    # Create a Chroma vector store
    embeddings = OpenAIEmbeddings(
        deployment = embeddings_deployment,
        openai_api_key = openai.api_key,
        openai_api_base = openai.api_base,
        openai_api_version = openai.api_version,
        openai_api_type = openai.api_type,
        chunk_size = embeddings_chunk_size)

    # Create a Chroma vector store
    db = await cl.make_async(Chroma.from_texts)(
        all_texts, embeddings, metadatas = metadatas
    )

    # Create an AzureChatOpenAI llm
    llm = AzureChatOpenAI(
        temperature = temperature,
        openai_api_key = openai.api_key,
        openai_api_base = openai.api_base,
        openai_api_version = openai.api_version,
        openai_api_type = openai.api_type,
        deployment_name = chat_completion_deployment)

    # Create a chain that uses the Chroma vector store
    chain = RetrievalQAWithSourcesChain.from_chain_type(
        llm = llm,
        chain_type = "stuff",
        retriever = db.as_retriever(),
        return_source_documents = True,
        chain_type_kwargs = chain_type_kwargs
    )

    # Save the metadata and texts in the user session
    cl.user_session.set("metadatas", metadatas)
    cl.user_session.set("texts", all_texts)

    # Create a message to inform the user that the files are ready for queries
    content = ''
    if (len(files)  ==  1):
        content = f"`{files[0].name}` processed. You can now ask questions!"
    else:
        files_names = [f"`{f.name}`" for f in files]
        content = f"{', '.join(files_names)} processed. You can now ask questions."
    msg.content = content
    msg.author = "Chatbot"
    await msg.update()

    # Store the chain in the user session
    cl.user_session.set("chain", chain)

@cl.on_message
async def run(message: str):
    # Retrieve the chain from the user session
    chain = cl.user_session.get("chain")
    
    # Initialize the response
    response =  None

    # Retry the OpenAI API call if it fails
    for attempt in range(max_retries):
        try:
            # Refresh the OpenAI security token if using Azure AD
            if openai.api_type  ==  "azure_ad":
                refresh_openai_token()

            # Ask the question to the chain
            response = await chain.acall(message, callbacks = [cl.AsyncLangchainCallbackHandler()])
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

    # Get the answer and sources from the response
    answer = response["answer"]
    sources = response["sources"].strip()
    source_elements = []

    # Get the metadata and texts from the user session
    metadatas = cl.user_session.get("metadatas")
    all_sources = [m["source"] for m in metadatas]
    texts = cl.user_session.get("texts")

    if sources:
        found_sources = []

        # Add the sources to the message
        for source in sources.split(","):
            source_name = source.strip().replace(".", "")
            # Get the index of the source
            try:
                index = all_sources.index(source_name)
            except ValueError:
                continue
            text = texts[index]
            found_sources.append(source_name)
            # Create the text element referenced in the message
            source_elements.append(cl.Text(content = text, name = source_name))

        if found_sources:
            answer +=  f"\nSources: {', '.join(found_sources)}"
        else:
            answer +=  "\nNo sources found"

    await cl.Message(content = answer, elements = source_elements).send()