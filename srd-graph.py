#
# Graph Database Ingester For 5e SRD Content
#
import dotenv
dotenv.load_dotenv()

import json
from llama_index.core import Document, StorageContext, VectorStoreIndex, load_index_from_storage
from llama_index.core.extractors import TitleExtractor, QuestionsAnsweredExtractor
from llama_index.extractors.entity import EntityExtractor
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.schema import BaseNode
from llama_index.core.storage.docstore import SimpleDocumentStore
from os import path, mkdir
from src.documents import loadWebPages, parseWebPage, getLinks
from src.file_utils import createOutputFile
from src.llm import documentTitle, answerFinder, get_service_context
from src.log_utils import debug
from typing import Sequence

# 1. Download Site

failedLinks = []

STORAGE = "./srd-store"

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

def metadataExtractor():
  splitter = TokenTextSplitter(
    separator=" ", chunk_size=512, chunk_overlap=128
  )

  titleExtractor = TitleExtractor(nodes=5, llm=documentTitle)
  qaExtractor = QuestionsAnsweredExtractor(questions=3, llm=answerFinder)
  entity = EntityExtractor(prediction_threshold=0.75, label_entities=True)

  return [splitter, titleExtractor, qaExtractor, entity]

title = " Web Site Document Loader "
print("=" * len(title))
print(title)
print("=" * len(title))

print("> Creating Output File")
file = createOutputFile('./kg-output', 'srd-graph-result')

print("> Loading Web Pages")
docs, links = getWebDocumentAndLinks("https://www.5esrd.com/classes")

print("> Loading Pages Complete")
print("    Document Count: {}".format(len(docs)))
print("    Link Count: {}".format(len(links)))

file.write("## Web Page Loading\n\n")
file.write("| Item | Count |\n")
file.write("| :-: | :-: |\n")
file.write("| Documents | {} |\n".format(len(docs)))
file.write("| Links | {} |\n".format(len(links)))
file.write("| Failed Downloads | {} |\n\n".format(len(failedLinks)))
file.write("**Failed Links**\n".format(len(failedLinks)))
file.write("```json\n[\n".format(len(failedLinks)))
for badLink in failedLinks:
  file.write(" \"{}\",".format(badLink))
file.write("]\n```\n\n---\n".format(len(failedLinks)))

file.flush()

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