#
# Graph Database Ingester For 5e SRD Content
#
import dotenv
dotenv.load_dotenv()

import json
from llama_index.core import Document, KnowledgeGraphIndex, StorageContext, VectorStoreIndex, load_index_from_storage, load_graph_from_storage
from llama_index.core.extractors import TitleExtractor, QuestionsAnsweredExtractor
from llama_index.core.query_engine.graph_query_engine import ComposableGraphQueryEngine
from llama_index.extractors.entity import EntityExtractor
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.core.storage.docstore import SimpleDocumentStore
from os import path
from src.documents import loadWebPages, parseWebPage, getLinks
from src.db import graphStore, vectorStore, documentStore
from src.file_utils import createOutputFile
from src.llm import documentTitle, answerFinder, get_service_context
from src.log_utils import debug
from src.rebel import extract_triplets
from typing import Sequence
from datetime import datetime

# 1. Download Site

failedLinks = []

TARGET = "https://www.5esrd.com"
STORAGE = "./srd-store"

title = " Web Site Document Loader "
print("=" * len(title))
print(title)
print("=" * len(title))

print("> Creating Output File")
file = createOutputFile('./kg-output', 'srd-graph-result')

def loadIndex():
  context = StorageContext.from_defaults(graph_store=graphStore, vector_store=vectorStore, docstore=documentStore)
  graph = load_graph_from_storage(context, 'root')
  
  return context,graph

def loadWebsitesIntoGraph(url: str, context: StorageContext, links: set = set()):
  file.write(f'\n### URL: {url}\n')
  
  debug("==> Loading Web URL [url: {}]".format(url))
  document = loadWebPages([url]).pop()

  documentDetails: dict[str, any] = {
    "id": document.doc_id,
    "text": document.text[:20]
  }
  file.write('LlamaIndex Document Details:\n')
  file.write(f'```json\n')
  file.write(f'{json.dumps(documentDetails, indent=2)}')
  file.write(f'\n```\n\n')

  debug("====> Parsing HTML [url: {}]".format(url))
  htmlDoc = parseWebPage(document.text);

  file.write('HTML Document:\n')
  file.write(f'```html\n')
  file.write(f'{htmlDoc}')
  file.write(f'\n```\n')

  debug("====> Creating Document [url: {}]".format(url))
  now = datetime.now()
  createDate = f'{now:%Y%m%d%H%M%S}'
  nodes = metadataExtractor([Document(text=htmlDoc.text, id_=url, metadata={ "source": url, "createdAt": createDate })])

  file.write('Document Nodes w/ Metadata:\n')
  file.write(f'```json\n')
  file.write(f'{nodes}')
  file.write(f'\n```\n')

  context.docstore.add_documents(nodes, store_text=False)

  print(f'Docstore Size: {len(context.docstore.docs)}')

  debug("====> Loading Into Graph DB [url: {}]".format(url))

  KnowledgeGraphIndex(
    nodes=nodes,
    service_context=get_service_context(),
    kg_triplet_extract_fn=extract_triplets,
    storage_context=context,
    show_progress=True
  )

  debug("====> Getting Links [url: {}]".format(url))
  webPageLinks = getLinks(htmlDoc.encode_contents(formatter="html"), url=url)

  file.write('Links in HTML that match domain:\n')
  file.write(f'```json\n')
  file.write(json.dumps(webPageLinks, indent=2))
  file.write(f'\n```\n')

  debug(f'====> Links found: {len(webPageLinks)}')

  for link in webPageLinks:
    try:
      if (link not in links):
        links.add(link)
        loadWebsitesIntoGraph(link, context, links=links)
      else:
        debug("===> Link Already Loaded [url: {}]...Skipping".format(url))
    except Exception as error:
      print(f'{error}')
      failedLinks.append(link)
      exit()

def getDocumentStore(documents: Sequence[Document]):
  dirExists = path.isdir(STORAGE)

  if (dirExists):
    print("==> Existing Index Found, Updating...")
    context = StorageContext.from_defaults(persist_dir=STORAGE)
    index = load_index_from_storage(context, service_context=get_service_context())

    index.refresh(documents=documents)
    return context, index
  else:
    print("==> No Index Found, Creating...")
    # TODO => Switch to external document storage solution, possibly graph
    docStore = SimpleDocumentStore()
    docStore.add_documents(documents)
    storageContext = StorageContext.from_defaults(docstore=docStore)
    
    storageContext.persist(STORAGE)

    index = VectorStoreIndex.from_documents(
      documents,
      transformations=metadataExtractor(),
      storage_context=storageContext,
      service_context=get_service_context(),
      show_progress=True
    )

    storageContext.persist(STORAGE)
    return storageContext, index

def getWebDocumentAndLinks(url: str, documents: list[Document] = [], links: set = set()):
  # This suggests a new url search, add the original link provided
  if (len(links) == 0):
    links.add(url)
  
  try:
    debug("==> Loading Web URL [url: {}]".format(url))
    htmlDoc = loadWebPages([url])
    debug("====> Parsing HTML [url: {}]".format(url))
    webPage = parseWebPage(htmlDoc[0].text)
    debug("====> Creating Document [url: {}]".format(url))
    documents.append(Document(text=webPage, doc_id=url))
    debug("====> Getting Links [url: {}]".format(url))
    webPageLinks = getLinks(htmlDoc[0].text, url=url)

    for link in webPageLinks:
      if (link not in links):
        links.add(link)
        getWebDocumentAndLinks(link, documents=documents, links=links)
      else:
        debug("===> Link Already Loaded [url: {}]...Skipping".format(url))
  except:
    failedLinks.append(url)
  finally:
    return documents, links

def metadataExtractor(documents: list[Document]):
  splitter = TokenTextSplitter(
    separator=" ", chunk_size=512, chunk_overlap=128
  )

  titleExtractor = TitleExtractor(nodes=5, llm=documentTitle)
  qaExtractor = QuestionsAnsweredExtractor(questions=3, llm=answerFinder)
  entity = EntityExtractor(prediction_threshold=0.75, label_entities=True)

  return IngestionPipeline(transformations=[splitter, titleExtractor, qaExtractor, entity]).run(documents=documents)

print("> Loading Index from Neo4j")
context, graph = loadIndex()

print("> Loading Web Pages")
file.write(f'**Target:** {TARGET}\n\n')

file.write("""
---
## Loading Documents
**Details on the documents loaded into the system**

""")
loadWebsitesIntoGraph(TARGET, context=context)
# queryEngine = ComposableGraphQueryEngine(graph=graph)


file.write("## Web Page Loading Result\n\n")
file.write("| Item | Count |\n")
file.write("| :-: | :-: |\n")
file.write("| Documents | {} |\n".format(len(context.docstore.docs)))
file.write("| Failed Downloads | {} |\n\n".format(len(failedLinks)))
file.write("**Failed Links**\n".format(len(failedLinks)))
file.write("```json\n[\n".format(len(failedLinks)))
for badLink in failedLinks:
  file.write(" \"{}\",".format(badLink))
file.write("]\n```\n\n---\n".format(len(failedLinks)))

exit()

# 2. Create Graph Index & Store
print("> Process Documents")
storageContext, index = getDocumentStore(docs)

# 3. Make available
queryEngine = index.as_query_engine(
  verbose=True,
  response_mode="tree_summarize"
)

print("> Querying Data")
file.write("## Query Data\n")
questionA = "What saving throws is a Fighter proficient using?"
questionB = "How many attack dice is a greatsword?"
questionC = "Which spell does the most lighting damage regardless of class?"

file.write("Each question and it's evaluated answer\n\n")
print("==> Question A")
responseA = queryEngine.query(questionA)
file.write("```\nQuestion: {}\n\nAnswer:\n{}\n```\n\n".format(questionA, responseA))

print("==> Question B")
responseB = queryEngine.query(questionB)
file.write("```\nQuestion: {}\n\nAnswer:\n{}\n```\n\n".format(questionB, responseB))

print("==> Question C")
responseC = queryEngine.query(questionC)
file.write("```\nQuestion: {}\n\nAnswer:\n{}\n```\n\n".format(questionC, responseC))

print(" == Complete == ")
# 4. Create Flask Server