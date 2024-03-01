# from documents import getIndex

# print('> Loading Index')
# vectorStore = getIndex(persistDir='./data-store', inputDir='./docs')

# print('> Querying LLM')
# queryEngine = vectorStore.as_query_engine()

# query="Tell me about what the rules say about a Fighters Hit Points"
# response = queryEngine.query(query)

# print('> Query:')
# print(query)
# print('> Response:')
# print(response)\

import dotenv
dotenv.load_dotenv();

# from prompts.template import createQuery
from src.documents import loadWebDocuments, loadKnowledgeGraph
from src.db import graphStore
from src.llm import ollama
from llama_index.core import StorageContext
from llama_index.core.query_engine import KnowledgeGraphQueryEngine
import json

queryStr = """
You are an AI Assistant knowledgeable in the rules for Dungeons and Dragons 5th Edition (a Table Top Role Playing Game, aka TTRPG).

You will assist by answering questions related to to this topic to the best of your abilities. Keep your answers short and concise. Avoid conversational answers. In your response please include your source.

If the answer is not provided in the context, state that you do not know the answer.

Here is my question:
{prompt}

Here is some context to help you answer the question:
"""

# query = """
# You Jack Sparrow, the pirate capitan of the Black Pearl. You will answer about playing a dice game called Dungeons and Dragons as yourself.

# Here is my question:
# {prompt}

# Here is some context to help you answer the question:
# """

urls = [
  "https://www.5esrd.com/classes/",
  "https://www.5esrd.com/database/class/fighter/"
]

# linkFile = open('srd-links.json')
# urls = json.load(linkFile)

print('> Loading Data')
vectors = loadWebDocuments(urls)

context = StorageContext.from_defaults(graph_store=graphStore)
graph = loadKnowledgeGraph(context)

query_engine = KnowledgeGraphQueryEngine(
    storage_context=context,
    llm=ollama,
    verbose=True,
)

print('> Querying Data')

# prompt = createQuery(queryStr)

response = query_engine.query(queryStr.format(prompt="How does my table roll initiative at the start of a fight?"))

# prompt(vectorStore=query_engine, prompt="How does my table roll initiative at the start of a fight?")
# prompt(vectorStore=vectors, prompt="How many attack dice is a greatsword?")
# prompt(vectorStore=vectors, prompt="What kind of damage does a shortsword inflict?")
# prompt(vectorStore=vectors, prompt="How many times can a Fighter attack as part of their action at level 4?")

print('\n== Complete ==')