from llama_index.core import SimpleDirectoryReader
from llama_index.readers.web  import SimpleWebPageReader
from llama_index.core import Document, VectorStoreIndex, StorageContext, load_index_from_storage, SummaryIndex, SimpleKeywordTableIndex
from .llm import get_service_context
from os import path, mkdir, getcwd
from llama_index.core.node_parser import MarkdownNodeParser, HTMLNodeParser
from llama_index.core.storage.docstore import SimpleDocumentStore


webStoreDir = './web-store';

parser = MarkdownNodeParser()

# load documents with deterministic IDs
def load_docs(directory):
  return SimpleDirectoryReader(directory, filename_as_id=True).load_data()

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
    storageContext = StorageContext.from_defaults(docstore=docStore)

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