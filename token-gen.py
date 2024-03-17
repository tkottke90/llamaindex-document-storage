from typing import Literal
from llama_index.core.schema import BaseNode, TextNode
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from llama_index.core.extractors import TitleExtractor, QuestionsAnsweredExtractor
from llama_index.core import Document, Node
from llama_index.core.node_parser.file.html import HTMLNodeParser, DEFAULT_TAGS
from llama_index.core.ingestion import IngestionPipeline
from src.documents import loadWebPages
from src.file_utils import createOutputFile
from src.llm import documentTitle, answerFinder, get_service_context, knowledgeGraphAI
from bs4 import BeautifulSoup, Tag, SoupStrainer
from markdownify import markdownify as md
import re
import json
import time
from src.models.entities_model import Entity
from src.prompts import EntityRetrievalPrompt, EntityOutputParser
from src.regex.markdown_headers import markdownHeaderRegex
from src.log_utils import markdownTable
from langchain_core.exceptions import OutputParserException

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

class BSSearch():
  name: SoupStrainer = None
  attrs: SoupStrainer | dict[str, SoupStrainer] = None
  recursive: bool = None
  string: SoupStrainer = None

def loadWebsiteLeaveTables(url: str, exclusions: list[BSSearch] = None, extractions: list[BSSearch] = None):
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

  # Extract Links - Since this utility may be recursive
  # we want to avoid external links which could in turn produce
  # other external links.  Leading to the potential downloading
  # of the internet
  links: list[str] = list()
  for s in htmlBody.findAll(f'a', href=True):
    # When link is local to the page, add it to our list
    if (s['href'].startswith(url)):
      links.append(s['href'])

    s.extract()

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

  return websiteMd, links

def loadWebsite(url: str):
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
  htmlTables: list[Tag] = list()
  for s in htmlBody(['table']):
    htmlTables.append(s.extract())

  # Extract Links - Since this utility may be recursive
  # we want to avoid external links which could in turn produce
  # other external links.  Leading to the potential downloading
  # of the internet
  links: list[str] = list()
  for s in htmlBody.findAll(f'a', href=True):
    # When link is local to the page, add it to our list
    if (s['href'].startswith(url)):
      links.append(s['href'])

    s.extract()

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

  tables: list[str] = list()
  for table in htmlTables:
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

    tables.append(parsedTable)

  return websiteMd, links, tables

## Start

log = createOutputFile('./kg-output', 'token-gen')
log.write("""With this experiment I was attempting to determine which chunking solution to use for Markdown styled text documents with the goal of using HTML to Markdown to convert web pages into plain text and then consuming the document into a RAG System (specifically graph and vector stores).

The following shows the output of my experiments so far.  I have established a solid pipeline step for the loading of static web pages and this shows the results from each step.


---\n""")

print(f'=> Loading URL: [{SOURCE_URL}]')
log.write(f'## Loading Webpage: [{SOURCE_URL}]\n\n')

log.write('Here we load the web page specified in the SOURCE_URL variable.  The below table shows some details about the process:\n\n')

websiteMd,links, tables = loadWebsite(SOURCE_URL)

log.write(
  markdownTable(
    ['Result', 'Value'],
    [
      ['Links Found', len(links)],
      ['Tables Found', len(tables)],
      ['MD Size', len(websiteMd)]
    ]
  )
)


log.write("""
As part of this process we extract the links ('a' tags) from the HTML document.  Links that share the same hostname as the current page are saved and returned as Links (see below).  Other links are discarded as they typically are unrelated to the content we are consuming and have the potential if followed recursively to end in a never-ending download.
          
""")

log.write('\n**Links Found in HTML:**')
log.write(f'```json\n{json.dumps(links, indent=2)}\n```')

log.write("""

We also extract the tables from the HTML.  This was done as part of the experiment as it was a concern that there may be issues creating indexes since the tables are not semantic.

**Tables found in document:**
""")

log.write('```text')
for table in tables:
  log.write(table)
log.write('```')

log.write('\n---\n')

log.write('## Chunk Markdown\n\n')

evaluatorQuestion = 'What is the purpose of levels?'

log.write(f"""The next step is to break up the document into small chunks.  The goal here is to make is to make the document more consumable by the LLM by only providing chunks that are most relevant to the users query.
          
I test 4 types of chunking solutions:
1. Recursive (recommended by LangChain)
2. Markdown Header
3. Custom Markdown Header <- Home Rolled
4. Semantic (Beta)

Below are the timing results and the answer to the question: "{evaluatorQuestion}"

""")

print(f'==> Importing Modules')
from llama_index.core import VectorStoreIndex
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.documents import Document
from typing import Callable

def langChainToLLamaIndex(langchainDocs: list[TextNode]) -> list[LlamaDoc]:
  llamaDocs: list[TextNode] = list()
  for doc in langchainDocs:
    llamaDocs.append(TextNode(text=doc.page_content))

  return llamaDocs

def recursiveTextSplitter(markdown: str) -> list[Document]:
  splitter = RecursiveCharacterTextSplitter(
    # Set a really small chunk size, just to show.
    chunk_size=1000,
    chunk_overlap=50,
    length_function=len,
    is_separator_regex=False,
  )

  return splitter.create_documents([markdown])

def markdownTextSplitter(markdown: str) -> list[Document]:
  splitter = MarkdownHeaderTextSplitter(
    strip_headers=False,
    headers_to_split_on = [
      ("#", "Header 1"),
      ("##", "Header 2"),
      ("###", "Header 3"),
      ("####", "Header 4"),
      ("#####", "Header 5"),
    ]
  )

  return splitter.split_text(markdown)

def customMarkdownTextSplitter(markdown: str) -> list[Document]:
  chunks = markdownHeaderParser(markdown, max_chunk_size=1000)

  # Add back tables
  chunks.extend(tables)

  documents: list[Document] = list()
  for chunk in chunks:
    documents.append(Document(chunk))

  return documents

def semanticTextSplitter(markdown: str) -> list[Document]:
  splitter = SemanticChunker(OllamaEmbeddings(model="mistral:7b"))
  return splitter.create_documents([markdown])

def evaluator(fn, name: str, fnInput: str):
  output = dict({
    'name': name,
    'success': False,
    'execution_msg': '',
    'splitter_result': '',
    'fn_execution_time': '',
    'index': None,
    'vector_execution_time': '',
    'query_result': '',
    'query_execution_time': ''
  });

  try:
    print(f'=> Evaluating: {name}')
    print('===> Splitting Document')
    tic = time.perf_counter()
    output['splitter_result'] = fn(fnInput)
    toc = time.perf_counter()
    output['fn_execution_time'] = f'{toc - tic:0.2f} sec'

    print('===> Converting to LlamaIndex Document')
    output['nodes'] = langChainToLLamaIndex(output['splitter_result'])

    tic = time.perf_counter()
    print('===> Creating Index')
    index = VectorStoreIndex.from_documents(output['nodes'], service_context=get_service_context())
    toc = time.perf_counter()
    output['vector_execution_time'] = f'{toc - tic:0.2f} sec'

    print('===> Creating Query Engine')
    queryEngine = index.as_query_engine(
      verbose=True,
      response_mode="tree_summarize"
    );

    tic = time.perf_counter()
    print('===> Querying LLM with Index')
    output['query_result'] = queryEngine.query(evaluatorQuestion)
    toc = time.perf_counter()
    output['query_execution_time'] = f'{toc - tic:0.2f} sec'
    
    print('===> Execution Complete')
    output['success'] = True
    output['execution_msg'] = 'Success'
  except KeyError as kErr:
    output['execution_msg'] = f'Dict Key Lookup Err [KeyError]: {kErr}'
    exit()
  except Exception as err:
    print('===> !! Execution Error !!')
    output['execution_msg'] = f'Error: {err}'
  finally:
    return output

testResults = dict({
  'recursive': evaluator(recursiveTextSplitter, 'Recursive', websiteMd),
  'markdown_header': evaluator(markdownTextSplitter, 'Markdown Header', websiteMd),
  'custom_markdown_header': evaluator(customMarkdownTextSplitter, 'Custom Markdown Header', websiteMd),
  'semantic': evaluator(semanticTextSplitter, 'Semantic', websiteMd)
})

resultHeaders = ['Name', 'Success', 'Splitter Time', 'Index Time', 'Query Time']
resultTable = []
resultDisplay = [];

for recordKey in testResults.keys():
  result = testResults[recordKey]
  resultTable.append(
    [ result['name'], result['success'], result['fn_execution_time'], result['vector_execution_time'], result['query_execution_time'] ]
  )
 
  msg = ''
  if (result['success']):
    msg = result['query_result']
  else:
    msg = result['execution_msg']

  resultDisplay.append('**{}**\n```\n{}\n```\n\n'.format(result['name'], msg))

log.write(markdownTable(
  headers=resultHeaders,
  values=resultTable
))

log.write(''.join(resultDisplay))

log.write("""> Result Analysis
> Based on the previous test it appears that both the {} and (especially) {} splitters provided the best results.

---\n""".format(testResults['custom_markdown_header']['name'], testResults['semantic']['name']))

print(f'> Semantic Table Test')
log.write('### Semantic w/ Tables \n\n')

log.write(f"""One curiosity I did have about the Semantic search was how it might improve if I leave the tables included in the original document, as opposed to extracting them. I still believe thee may be benefit to extracting them from a UI perspective but 

""")

print(f'==> Loading Web Page')
semanticMd, links = loadWebsiteLeaveTables(SOURCE_URL)
print(f'==> Evaluating')
semanticTableResult = evaluator(semanticTextSplitter, 'SemanticTextSplitterWithTables', semanticMd)

print(f'==> Generating Result')
log.write(markdownTable(
  headers=resultHeaders,
  values=[
    [ semanticTableResult['name'], semanticTableResult['success'], semanticTableResult['fn_execution_time'], semanticTableResult['vector_execution_time'], semanticTableResult['query_execution_time'] ]
  ]
))

semanticMdMsg = ''
if (result['success']):
  semanticMdMsg = result['query_result']
else:
  semanticMdMsg = result['execution_msg']

log.write('**{}**\n```\n{}\n```\n\n'.format(semanticTableResult['name'], semanticMdMsg))

log.write(f"""

---\n""")

log.write('## Knowledge Graph Creation: Entity Extraction \n\n')
from llama_index.extractors.entity import EntityExtractor

entity_extractor = EntityExtractor(
    prediction_threshold=0.5,
    label_entities=False,  # include the entity label in the metadata (can be erroneous)
    device="cpu",  # set to "cuda" if you have a GPU
)

entity_extractor.process_nodes(semanticTableResult['nodes'])

exit()


from llama_index.core.extractors import KeywordExtractor, QuestionsAnsweredExtractor


log.write(f"""The next phase is to create a knowledge graph based on this information.  To create one we need to extract Entities (objects, events, situations, abstract concepts, etc) and Relationships (semantics which describe how entities are connected)

To this end I wanted to look at a couple of strategies for identifying entities:
1. Keyword

""")

exit()

log.write('## Custom Parser [Entities] \n\n')
log.write('This uses the custom ModFile I write for Ollama which is instructed to extract entities\n\n')

log.write('\n**ModFile:**\n')
with open('./ModelFiles/KGWebsiteModFile', 'r') as modFile:
  log.write(f'```docker\n{modFile.read()}\n```\n\n')

entitiesList: list[Entity] = list()


print('Parsing:\n')
for id,chunk in enumerate(chunks):
  print(f'\r{id} of {len(chunks)}')
  query = EntityRetrievalPrompt(chunk)
  response = knowledgeGraphAI.chat(messages=query, )

  # Response will contain step by step instructions.  We need only the output
  log.write(f'**Chunk Index**: {id}\n\n')

  log.write('| Metric | Details |\n| :-: | --- |\n')
  
  modelName = response.raw.get('model')
  log.write(f'| Model | {modelName}\n')

  totalDuration = response.raw.get('total_duration')
  log.write(f'| Total Duration | {totalDuration}\n')

  loadDuration = response.raw.get('load_duration')
  loadDurationPercent = format((loadDuration / totalDuration) * 100, '.2f')
  log.write(f'| Load Duration | {loadDuration} ({loadDurationPercent}%)\n')

  promptEvalDuration = response.raw.get('prompt_eval_duration')
  promptEvalDurationPercent = format((promptEvalDuration / totalDuration) * 100, '.2f')
  log.write(f'| Prompt Eval Duration | {promptEvalDuration} ({promptEvalDurationPercent}%)\n')

  evalDuration = response.raw.get('prompt_eval_duration')
  evalDurationPercent = format((evalDuration / totalDuration) * 100, '.2f')
  log.write(f'| Eval Duration | {evalDuration} ({evalDurationPercent}%)\n\n')

  log.write(f'```\nInput:\n{query}\n\nResponse:\n{response.raw}\n\n')
  try:
    result = EntityOutputParser(response.message.content)
    entitiesList.extend(result.entities);
  except OutputParserException as outputErr:
    result = outputErr
  except json.decoder.JSONDecodeError as jsonErr:
    result = f'JSON Error: {jsonErr}'
  except Exception as err:
    result = f'Unknown Error: {err}'

  log.write(f'Output:\n{result}```\n\n')

log.write(f'| Metric | Value |\n')
log.write(f'| :-: | :-: |\n')
log.write(f'| Entities Generated | {len(entitiesList)} |\n')

with open('entities.json', 'a') as entitiesJSON:
  entitiesJSON.write(
    json.dumps(entitiesList, indent=2)
  )

# Next Steps - 20240307
#
#  1. Add back removed headers
#  2. De-dup entities list
#  3. Move processes into parser file
#  4. Create Nodes from Chunks
#  5. Add metadata (keywords, title, summary, questions)
#  6. Load nodes into Neo4j
#  7. Create Index & Store in Neo4j

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