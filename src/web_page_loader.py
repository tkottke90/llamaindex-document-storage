import re
from datetime import datetime
from typing import Sequence
from llama_index.core import Document, StorageContext, KnowledgeGraphIndex
from llama_index.core.extractors import TitleExtractor, QuestionsAnsweredExtractor, KeywordExtractor
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.core.schema import BaseNode
from llama_index.extractors.entity.base import EntityExtractor
from llama_index.readers.web import SimpleWebPageReader
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from bs4 import BeautifulSoup
from .rebel import extract_triplets
from .llm import documentTitle, answerFinder, get_service_context
from .config import DEBUG_ENABLED
from .log_utils import debug

def loadWebPages(urls: list[str]):
  return SimpleWebPageReader().load_data(urls)

def parseWebPage(html: str, contentTag: str = 'main'):
  htmlDoc = BeautifulSoup(html, 'html.parser')
  return htmlDoc.find(contentTag)

def getLinks(html: str, url: str = "http://localhost"):
  htmlDoc = BeautifulSoup(html, 'html.parser')
  pattern = f'{url}.*'
  links = htmlDoc.findAll('a', recursive=True, href=re.compile(pattern))

def addNodesToKG(nodes: Sequence[BaseNode], context: StorageContext):
  KnowledgeGraphIndex(
    nodes=nodes,
    service_context=get_service_context(),
    kg_triplet_extract_fn=extract_triplets,
    storage_context=context,
    show_progress=DEBUG_ENABLED
  )

def metadataExtractor(documents: list[Document]):
  splitter = TokenTextSplitter(
    separator=" ", chunk_size=512, chunk_overlap=128
  )

  titleExtractor = TitleExtractor(nodes=5, llm=documentTitle)
  qaExtractor = QuestionsAnsweredExtractor(questions=3, llm=answerFinder)
  entity = EntityExtractor(prediction_threshold=0.75, label_entities=True)

  return IngestionPipeline(
    transformations=[
      splitter,
      titleExtractor,
      qaExtractor,
      entity
    ]
  ).run(documents=documents)

def load(url: str, context: StorageContext, links: set[str] = set()):
  debug("==> Loading Web URL [url: {}]".format(url))
  document = loadWebPages([url]).pop()

  debug("====> Parsing HTML [url: {}]".format(url))
  htmlDoc = parseWebPage(document.text);

  debug("====> Creating Document [url: {}]".format(url))
  now = datetime.now()
  createDate = f'{now:%Y%m%d%H%M%S}'
  nodes = metadataExtractor([
    Document(
      text=htmlDoc.text,
      id_=url,
      doc_id=url,
      metadata={ "source": url, "createdAt": createDate }
      )
    ])

  debug("====> Loading Into Graph DB [url: {}]".format(url))
  addNodesToKG(nodes, context)

  debug("====> Getting Links [url: {}]".format(url))
  webPageLinks = getLinks(htmlDoc.encode_contents(formatter="html"), url=url)

  exit()

  for link in webPageLinks:
    try:
      if (link not in links):
        links.add(link)
        load(link, context, links=links)
      else:
        debug("===> Link Already Loaded [url: {}]...Skipping".format(url))
    except Exception as error:
      print(f'{error}')
      print(f'Failed Link: {link}')
      exit()