from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core import VectorStoreIndex, KnowledgeGraphIndex, load_graph_from_storage, load_index_from_storage
from openai import BaseModel
from src.documents import createKnowledgeGraph, loadKnowledgeGraph, loadWebPages
from prompts.template import createQuery
from src.db import graphStore, vectorStore
from src.llm import get_service_context
from llama_index.core import StorageContext
from sys import exit

urls = [
  "https://www.5esrd.com/character-creation-outline/",
  # "https://www.5esrd.com/using-ability-scores",
  # "https://www.5esrd.com/backgrounds/",
  # "https://www.5esrd.com/database/background/",
  # "https://www.5esrd.com/races",
  # "https://www.5esrd.com/classes",
]

def getDocuments(context: StorageContext, urls: list[str]):
  try:
    SimpleDocumentStore.from_persist_dir('./doc-store')
  except:
    pages = loadWebPages(urls)
    nodes = MarkdownNodeParser().get_nodes_from_documents(pages)
    docStore = SimpleDocumentStore()
    docStore.add_documents(nodes)

    context.docstore = docStore
    context.persist('./doc-store')

    return nodes

def getGraphStore(context: StorageContext, nodes: list[BaseModel] = []):
  try:
    return load_graph_from_storage(context)
  except:
    kg = KnowledgeGraphIndex(
      nodes=nodes,
      service_context=get_service_context(),
      storage_context=context,
      max_triplets_per_chunk=10,
      show_progress=True,
      include_embeddings=True,
    )

    # context.persist()
    return kg

context = StorageContext.from_defaults(graph_store=graphStore)

pages = loadWebPages(urls)

print(pages);

# vectorStore = VectorStoreIndex.from_documents(
#   documents=loadWebPages(urls),
#   transformations=[
#     MarkdownNodeParser()
#   ],
#   service_context=get_service_context(),
#   show_progress=True
# )

# kgIndex = getGraphStore(context=context, nodes=docNodes)

prompt = """
# Knowledge Graph Instructions
## 1. Overview
You are a top-tier algorithm designed for extracting information in structured formats to build a knowledge graph.
- **Nodes** represent entities and concepts. They're akin to Wikipedia nodes.
- The aim is to achieve simplicity and clarity in the knowledge graph, making it accessible for a vast audience.
## 2. Labeling Nodes
- **Consistency**: Ensure you use basic or elementary types for node labels.
  - For example, when you identify an entity representing a person, always label it as **"person"**. Avoid using more specific terms like "mathematician" or "scientist".
- **Node IDs**: Never utilize integers as node IDs. Node IDs should be names or human-readable identifiers found in the text.
## 3. Handling Numerical Data and Dates
- Numerical data, like age or other related information, should be incorporated as attributes or properties of the respective nodes.
- **No Separate Nodes for Dates/Numbers**: Do not create separate nodes for dates or numerical values. Always attach them as attributes or properties of nodes.
- **Property Format**: Properties must be in a key-value format.
- **Quotation Marks**: Never use escaped single or double quotes within property values.
- **Naming Convention**: Use camelCase for property keys, e.g., `birthDate`.
## 4. Coreference Resolution
- **Maintain Entity Consistency**: When extracting entities, it's vital to ensure consistency.
If an entity, such as "John Doe", is mentioned multiple times in the text but is referred to by different names or pronouns (e.g., "Joe", "he"), 
always use the most complete identifier for that entity throughout the knowledge graph. In this example, use "John Doe" as the entity ID.  
Remember, the knowledge graph should be coherent and easily understandable, so maintaining consistency in entity references is crucial. 
## 5. Strict Compliance
Adhere to the rules strictly. Non-compliance will result in termination.

Below is the text to be analyzed:
"""

for doc in pages:
  


# query = vectorStore.as_query_engine()

# response = query.query()

exit()

graph = loadKnowledgeGraph(context)

query = graph.as_query_engine()

prompt = """
You are an AI Assistant focused on answer questions about Dungeons and Dragons 5th Edition.

I will ask you questions about Dungeons and Dragons 5th Edition and you will answer them.

Here is the question:
{}

Additionally I have found this information in the source material (SRD, Official Books)
{}
"""
query.query(createQuery)
createKnowledgeGraph(
  documents=loadWebPages(urls),
  context=context
)



