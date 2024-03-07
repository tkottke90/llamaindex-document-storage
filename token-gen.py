from typing import Literal
from llama_index.core.schema import BaseNode, TextNode
from langchain.text_splitter import RecursiveCharacterTextSplitter
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from llama_index.core.extractors import TitleExtractor, QuestionsAnsweredExtractor
from llama_index.core import Document
from llama_index.core.node_parser.file.html import HTMLNodeParser, DEFAULT_TAGS
from llama_index.core.ingestion import IngestionPipeline
from src.documents import loadWebPages
from src.file_utils import createOutputFile
from src.llm import documentTitle, answerFinder, get_service_context, knowledgeGraphAI
from bs4 import BeautifulSoup, Tag
from markdownify import markdownify as md
import re

SOURCE_URL = "https://www.5esrd.com/classes"

## Utilities

def nodesToJson(nodes: list[BaseNode]):
  return list(map(lambda node: node.json(), nodes))

def splitMdByParagraph(markdownText: str, chunkList: list[str]):
  chunkList.extend(re.split('\n\n', markdownText))

def splitMdByHeader(markdownText: str, depth: int) -> list[str]:
  pattern = r'^#{' + str(depth) + r'}\s.*$'
  return re.split(pattern, markdownText, flags=re.MULTILINE)

def markdownHeaderParser(markdown: str, chunkList: list[str] = None, depth: int = None, max_chunk_size: int = None) -> list[str]:
  if (not depth):
    depth = 1

  if (not max_chunk_size):
    max_chunk_size = 500

  if (not chunkList):
    chunkList = list()

  subStrings = splitMdByHeader(markdown, depth)

  for documentPart in subStrings:
    if (len(documentPart) < max_chunk_size):
      chunkList.extend([documentPart])
    elif depth <= 5:
      newDepth = depth + 1
      markdownHeaderParser(documentPart, chunkList, depth=newDepth, max_chunk_size=max_chunk_size)
    else:
      splitMdByParagraph(documentPart, chunkList)

  return list(filter(lambda chunk: len(chunk) > 0, chunkList))

def stringCleanUp(chunk: str, replacers: list[tuple[str, str, re.RegexFlag]]):
  output = chunk;

  for replacer in replacers:
    flags = re.NOFLAG
    if (len(replacer) == 3):
      flags = replacer[2]

    output = re.sub(replacer[0], replacer[1], output, flags=flags)

  return output

## Start

log = createOutputFile('./kg-output', 'token-gen')

log.write(f'## Loading URL [{SOURCE_URL}]\n\nHTML Loaded:\n')
page = loadWebPages([SOURCE_URL]).pop();

# Get HTML and then filter down to the 'main' element.
# This is a 5esrd.com specific thing and may need to be
# more modularized in a larger system
html = BeautifulSoup(page.text, 'html.parser')
htmlBody = html.find('main')

# Extract Scripts - No Scripts (Capes)
for s in htmlBody(['script']):
  s.extract()

# Extract Expansion Panel - This is custom to 5esrd.com
# but highlights an opportunity to allow for custom
# removal in a more modularized system
for s in html.findAll('div', { "id": "toc_container" }):
  s.extract()

# Extract Tables - Need more control over who the tables show up
# as chunks, so we control that step manually by extracting them
# before the MD conversion
tables: list[Tag] = list()
for s in htmlBody(['table']):
  tables.append(s.extract())

# Extract External Links - Since this utility may be recursive
# we want to avoid external links which could in turn produce
# other external links.  Leading to the potential downloading
# of the internet
for s in htmlBody.findAll(f'a', href=True):
  if (not s['href'].startswith(SOURCE_URL)):
    s.extract()

log.write('```html\n')
log.write(htmlBody.prettify())
log.write('\n```\n\n---\n')

# Convert to markdown & cleanup
rawMdStr = md(str(htmlBody), heading_style="ATX")
websiteMd = stringCleanUp(
  rawMdStr,
  [
    [r'\n{3,}', '\n\n'],      # Remove excessive new lines
    [r'â', '-'],              # Remove unicode character
    [r'', ''],               # Remove unicode character
    [r'\x94', '', re.UNICODE] # Remove unicode character
  ]
)

log.write('```md\n')
log.write(websiteMd)
log.write('\n```\n\n---\n')

log.write('## Chunk Markdown \n\n')

# Generate Chunks based on markdown headers ('#') and possibly
# paragraphs that start with bolded text
chunks = markdownHeaderParser(websiteMd, max_chunk_size=1000)

## Add tables back
for table in tables:
  mdTable = md(str(table), heading_style="ATX")
  parsedTable = stringCleanUp(
    mdTable,
    [
      [r'\n{3,}', '\n\n'],      # Remove excessive new lines
      [r'\xC3', '-', re.UNICODE],              # Remove unicode character
      [r'', ''],               # Remove unicode character
      [r'\x94', '', re.UNICODE] # Remove unicode character
    ]
  )

  chunks.append(parsedTable)

log.write('| Index | Chunk |\n')
log.write('| :-: | --- |\n')
for id,chunk in enumerate(chunks):
  chunkStr = stringCleanUp(chunk, [
    [ '\n', '<br>' ],  # Convert new lines to line breaks for Markdown Table support
    [ r'^"', '']       # Strip leading double quote present in each element
  ])
  
  log.write(f'| {id} | {chunkStr}\n')

log.write('\n\n---\n')

# Next Steps - 20240306
#
#  1. Identify entities in each chunk
#  2. Create Nodes from Chunks
#  3. Add metadata (keywords, title, summary, questions)
#  4. Load nodes into Neo4j
#  5. Create Index & Store in Neo4j

exit()

log.write(f'## HTML Node Parser [Default Tags] \n\nNodes:')
htmlParser = HTMLNodeParser()
htmlNodes = htmlParser.get_nodes_from_documents([page])

log.write(f' {len(htmlNodes)}\n')

log.write(f'Tags: {DEFAULT_TAGS}\n\n')

log.write('```json\n')
log.write(f'{nodesToJson(htmlNodes)}')
log.write('\n```\n\n---\n')


log.write(f'## ~~HTML Node Parser [Custom Tags]~~\n\nNodes:')
customTags = DEFAULT_TAGS.copy()
customTags.append('a')
customHtmlNodes: list[TextNode] = HTMLNodeParser(tags=customTags).get_nodes_from_documents([page])

# Found that some of the nodes had empty string NODE.text values.  Wanted to filter
# those out, turns out they were not doing anything or adding any value
nonZeroNodes = list(filter(lambda node: node.text != "", customHtmlNodes))

log.write(f' {len(htmlNodes)}\n')
log.write(f'Custom Nodes: {len(customHtmlNodes)}\n')
log.write(f'Non-Empty Custom Nodes: {len(nonZeroNodes)}\n')
log.write(f'Tags: {customTags}\n\n')

# Below writes out the nodes as JSON to a JSON block
# log.write('```json\n')
# log.write(f'{nodesToJson(nonZeroNodes)}')
# log.write('\n```\n\n---\n')

# log.write(f'## Title Extractor \n\n')
# ## Using 'htmlNodes' as I dont really need the custom ones
# titleExtractor = TitleExtractor(nodes=5, llm=documentTitle)

# title = IngestionPipeline(
#   transformations=[htmlParser, titleExtractor]
# ).run(show_progress=True, documents=[Document(text=str(htmlBody), doc_id=SOURCE_URL)])

# log.write('```json\n')
# log.write(f'{title}')
# log.write('\n```\n\n---\n')

# log.write(f'## QA Extractor \n\n')
# ## Using 'htmlNodes' as I dont really need the custom ones
# qaExtractor = QuestionsAnsweredExtractor(questions=3, llm=answerFinder)

# withQA = IngestionPipeline(
#   transformations=[htmlParser, titleExtractor, qaExtractor]
# ).run(show_progress=True, documents=[Document(text=str(htmlBody), doc_id=SOURCE_URL)])

# log.write('```json\n')
# log.write(f'{nodesToJson(withQA)}')
# log.write('\n```\n\n---\n')