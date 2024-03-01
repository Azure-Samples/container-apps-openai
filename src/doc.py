# Import packages
import os
import io
import sys
import logging
import chainlit as cl
from chainlit.playground.config import AzureChatOpenAI
from pypdf import PdfReader
from docx import Document
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from dotenv import dotenv_values
from langchain.embeddings import AzureOpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores.chroma import Chroma
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.chat_models import AzureChatOpenAI
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

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
chat_completion_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
embeddings_deployment = os.getenv("AZURE_OPENAI_ADA_DEPLOYMENT")
model = os.getenv("AZURE_OPENAI_MODEL")
max_size_mb = int(os.getenv("CHAINLIT_MAX_SIZE_MB", 100))
max_files = int(os.getenv("CHAINLIT_MAX_FILES", 10))
max_files = int(os.getenv("CHAINLIT_MAX_FILES", 10))
text_splitter_chunk_size = int(os.getenv("TEXT_SPLITTER_CHUNK_SIZE", 1000))
text_splitter_chunk_overlap = int(os.getenv("TEXT_SPLITTER_CHUNK_OVERLAP", 10))
embeddings_chunk_size = int(os.getenv("EMBEDDINGS_CHUNK_SIZE", 16))
max_retries = int(os.getenv("MAX_RETRIES", 5))
retry_min_seconds = int(os.getenv("RETRY_MIN_SECONDS", 1))
retry_max_seconds = int(os.getenv("RETRY_MAX_SECONDS", 5))
timeout = int(os.getenv("TIMEOUT", 30))
debug = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

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

# Configure a logger
logging.basicConfig(
    stream=sys.stdout,
    format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Create Token Provider
if api_type == "azure_ad":
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )

# Setting the environment variables for the playground
if api_type == "azure":
    os.environ["AZURE_OPENAI_API_KEY"] = api_key
os.environ["AZURE_OPENAI_API_VERSION"] = api_version
os.environ["AZURE_OPENAI_ENDPOINT"] = api_base
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = chat_completion_deployment


@cl.on_chat_start
async def start():
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

    # Initialize the file list to None
    files = None

    # Wait for the user to upload a file
    while files == None:
        files = await cl.AskFileMessage(
            content=f"Please upload up to {max_files} `.pdf` or `.docx` files to begin.",
            accept=[
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ],
            max_size_mb=max_size_mb,
            max_files=max_files,
            timeout=86400,
            raise_on_timeout=False,
        ).send()

    # Create a message to inform the user that the files are being processed
    content = ""
    if len(files) == 1:
        content = f"Processing `{files[0].name}`..."
    else:
        files_names = [f"`{f.name}`" for f in files]
        content = f"Processing {', '.join(files_names)}..."
    logger.info(content)
    msg = cl.Message(content=content, author="Chatbot")
    await msg.send()

    # Create a list to store the texts of each file
    all_texts = []

    # Process each file uplodaded by the user
    for file in files:
        # Read file contents
        with open(file.path, "rb") as uploaded_file:
            file_contents = uploaded_file.read()

        logger.info("[%d] bytes were read from %s",
                    len(file_contents), file.path)

        # Create an in-memory buffer from the file content
        bytes = io.BytesIO(file_contents)

        # Get file extension
        extension = file.name.split(".")[-1]

        # Initialize the text variable
        text = ""

        # Read the file
        if extension == "pdf":
            reader = PdfReader(bytes)
            for i in range(len(reader.pages)):
                text += reader.pages[i].extract_text()
                if debug:
                    logger.info("[%s] read from %s", text, file.path)
        elif extension == "docx":
            doc = Document(bytes)
            paragraph_list = []
            for paragraph in doc.paragraphs:
                paragraph_list.append(paragraph.text)
                if debug:
                    logger.info("[%s] read from %s", paragraph.text, file.path)
            text = "\n".join(paragraph_list)

        # Split the text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=text_splitter_chunk_size,
            chunk_overlap=text_splitter_chunk_overlap,
        )
        texts = text_splitter.split_text(text)

        # Add the chunks and metadata to the list
        all_texts.extend(texts)

    # Create a metadata for each chunk
    metadatas = [{"source": f"{i}-pl"} for i in range(len(all_texts))]

    # Create a Chroma vector store
    if api_type == "azure":
        embeddings = AzureOpenAIEmbeddings(
            openai_api_version=api_version,
            openai_api_type=api_type,
            openai_api_key=api_key,
            azure_endpoint=api_base,
            azure_deployment=embeddings_deployment,
            max_retries=max_retries,
            retry_min_seconds=retry_min_seconds,
            retry_max_seconds=retry_max_seconds,
            chunk_size=embeddings_chunk_size,
            timeout=timeout,
        )
    else:
        embeddings = AzureOpenAIEmbeddings(
            openai_api_version=api_version,
            openai_api_type=api_type,
            azure_endpoint=api_base,
            azure_ad_token_provider=token_provider,
            azure_deployment=embeddings_deployment,
            max_retries=max_retries,
            retry_min_seconds=retry_min_seconds,
            retry_max_seconds=retry_max_seconds,
            chunk_size=embeddings_chunk_size,
            timeout=timeout,
        )

    # Create a Chroma vector store
    db = await cl.make_async(Chroma.from_texts)(
        all_texts, embeddings, metadatas=metadatas
    )

    # Create an AzureChatOpenAI llm
    if api_type == "azure":
        llm = AzureChatOpenAI(
            openai_api_type=api_type,
            openai_api_version=api_version,
            openai_api_key=api_key,
            azure_endpoint=api_base,
            temperature=temperature,
            azure_deployment=chat_completion_deployment,
            streaming=True,
            max_retries=max_retries,
            timeout=timeout,
        )
    else:
        llm = AzureChatOpenAI(
            openai_api_type=api_type,
            openai_api_version=api_version,
            azure_endpoint=api_base,
            api_key=api_key,
            temperature=temperature,
            azure_deployment=chat_completion_deployment,
            azure_ad_token_provider=token_provider,
            streaming=True,
            max_retries=max_retries,
            timeout=timeout,
        )

    # Create a chain that uses the Chroma vector store
    chain = RetrievalQAWithSourcesChain.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=db.as_retriever(),
        return_source_documents=True,
        chain_type_kwargs=chain_type_kwargs,
    )

    # Save the metadata and texts in the user session
    cl.user_session.set("metadatas", metadatas)
    cl.user_session.set("texts", all_texts)

    # Create a message to inform the user that the files are ready for queries
    content = ""
    if len(files) == 1:
        content = f"`{files[0].name}` processed. You can now ask questions!"
        logger.info(content)
    else:
        files_names = [f"`{f.name}`" for f in files]
        content = f"{', '.join(files_names)} processed. You can now ask questions."
        logger.info(content)
    msg.content = content
    msg.author = "Chatbot"
    await msg.update()

    # Store the chain in the user session
    cl.user_session.set("chain", chain)


@cl.on_message
async def main(message: cl.Message):
    # Retrieve the chain from the user session
    chain = cl.user_session.get("chain")

    # Create a callback handler
    cb = cl.AsyncLangchainCallbackHandler()

    # Get the response from the chain
    response = await chain.acall(message.content, callbacks=[cb])
    logger.info("Question: [%s]", message.content)

    # Get the answer and sources from the response
    answer = response["answer"]
    sources = response["sources"].strip()
    source_elements = []

    if debug:
        logger.info("Answer: [%s]", answer)

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
            source_elements.append(cl.Text(content=text, name=source_name))

        if found_sources:
            answer += f"\nSources: {', '.join(found_sources)}"
        else:
            answer += "\nNo sources found"

    await cl.Message(content=answer, elements=source_elements).send()

    # Setting the AZURE_OPENAI_API_KEY environment variable for the playground
    if api_type == "azure_ad":
        os.environ["AZURE_OPENAI_API_KEY"] = token_provider()
