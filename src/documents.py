from llama_index.core import SimpleDirectoryReader, KnowledgeGraphIndex
from llama_index.readers.web  import SimpleWebPageReader
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage, load_graph_from_storage, Document
from .llm import get_service_context
from .db import graphStore
from os import path
from llama_index.core.node_parser import MarkdownNodeParser, HTMLNodeParser
from llama_index.core.storage.docstore import SimpleDocumentStore
from bs4 import BeautifulSoup
import re

webStoreDir = './web-store';
DEFAULT_TAGS = ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "b", "i", "u", "section", "a"]
parser = MarkdownNodeParser()

# load documents with deterministic IDs
def load_docs(directory):
  return SimpleDirectoryReader(directory, filename_as_id=True).load_data()

def loadWebPages(urls: list[str]):
  return SimpleWebPageReader().load_data(urls)

def parseWebPage(html: str, contentTag: str = 'main'):
  htmlDoc = BeautifulSoup(html, 'html.parser')
  return htmlDoc.find(contentTag).text

def getLinks(html: str, url: str = "http://localhost"):
  htmlDoc = BeautifulSoup(html, 'html.parser')
  links = htmlDoc.findAll('a', recursive=True, href=re.compile("{}.*".format(url)))
  return map(lambda link: link['href'], links)


def createWebPageDocStore(urls: list[str]):
  docs = SimpleWebPageReader().load_data(urls)
  nodes = HTMLNodeParser().get_nodes_from_documents(docs)
  docsStore = SimpleDocumentStore()
  docsStore.add_documents(nodes)

  return docsStore


def createKnowledgeGraph(documents: list[Document], context: StorageContext):
  KnowledgeGraphIndex.build_index_from_nodes(
    nodes=HTMLNodeParser(tags=DEFAULT_TAGS).get_nodes_from_documents(documents)
  )
  
  KnowledgeGraphIndex.from_documents(
    documents,
    storage_context=context,
    service_context=get_service_context(),
    max_triplets_per_chunk=10,
    show_progress=True,
    include_embeddings=True,
  )

  context.persist()

def loadKnowledgeGraph(context: StorageContext):
  return load_graph_from_storage(context, 1);

# def loadVectorGraph():
#   storageContext = loadWebDocsIntoGraph()

#   try:
#     return load_index_from_storage(storageContext)
#   except:
#     storageContext.persist()
#     return storageContext.vector_store

# def loadWebDocsIntoGraph():
#   storageContext = StorageContext.from_defaults(graph_store=graphStore, vector_store=vectorStore)

#   return storageContext


def loadWebDocuments(urls, reload = False):
  dirExists = path.isdir(webStoreDir)

  if ((not reload) and dirExists):
    context = StorageContext.from_defaults(persist_dir=webStoreDir)
    return load_index_from_storage(context, service_context=get_service_context())
  else:
    # Fetch Docs from the web and convert to nodes
    documents = SimpleWebPageReader().load_data(urls)
    nodes = HTMLNodeParser().get_nodes_from_documents(documents, show_progress=reload)

    # Create a document store
    docStore = SimpleDocumentStore()
    docStore.add_documents(nodes)
    
    # Setup storage context based on document store
    storageContext = StorageContext.from_defaults(docstore=docStore, graph_store=graphStore)

    # Create vector store assigned to storage context
    vectorStore = VectorStoreIndex(nodes, storage_context=storageContext, service_context=get_service_context(), show_progress=reload)
    
    # Save storage context to disk
    storageContext.persist(webStoreDir)

    # Return vector store for querying
    return vectorStore

def getIndex(inputDir, persistDir, reload = False):
    if ((reload == True) or (path.isdir(persistDir) != True)):
      documents = SimpleDirectoryReader(inputDir).load_data()
      vectorStore = VectorStoreIndex.from_documents(
         documents=documents,
         transformations=[
            MarkdownNodeParser()
         ],
         service_context=get_service_context()
      )

      # index = VectorStoreIndex.build_index_from_nodes(vectorStore, nodes=markdownNodes, service_context=get_service_context())
      vectorStore.storage_context.persist(persist_dir=persistDir);
      return vectorStore
    else:
      context = StorageContext.from_defaults(persist_dir=persistDir)
      return load_index_from_storage(context, get_service_context=get_service_context)
