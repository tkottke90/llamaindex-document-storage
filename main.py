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

from llama_index.core import VectorStoreIndex, get_response_synthesizer
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from src.documents import loadWebDocuments
import json

query = """
You are an AI Assistant knowledgeable in the rules for Dungeons and Dragons 5th Edition (a Table Top Role Playing Game, aka TTRPG).

You will assist by answering questions related to to this topic to the best of your abilities. Keep your answers short and concise. Avoid conversational answers. In your response please include your source.
You should answer all inquiries like you are Jack Sparrow.

If the answer is not provided in the context, state that you do not know the answer.

Here is my question:
{prompt}

Here is some context to help you answer the question:
"""

# urls = [
#   "https://www.5esrd.com/classes/",
#   "https://www.5esrd.com/database/class/fighter/"
# ]

linkFile = open('srd-links.json')
urls = json.load(linkFile)

print('> Loading Data')
vectors = loadWebDocuments(urls)

print('> Querying Data')

def prompt(vectorStore, prompt):
  retriever = VectorIndexRetriever(
    index=vectorStore,
    similarity_top_k=3,
  )
  
  responseSynth = get_response_synthesizer(
    response_mode="tree_summarize"
  )

  queryEngine = RetrieverQueryEngine(
    retriever=retriever,
    response_synthesizer=responseSynth
  )

  print ('=====================')
  print('Question: {}\n'.format(prompt))
  print('Response {}'.format(queryEngine.query(query.format(prompt=prompt))))
  print ('=====================') 

# prompt(vectorStore=vectors, prompt="How many attack dice is a broadsword?")
prompt(vectorStore=vectors, prompt="How many attack dice is a greatsword?")
prompt(vectorStore=vectors, prompt="What kind of damage does a shortsword inflict?")
# prompt(vectorStore=vectors, prompt="What are the proficiencies for the Fighter Class?")

print('\n== Complete ==')