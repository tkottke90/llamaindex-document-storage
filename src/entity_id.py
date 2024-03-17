from io import TextIOWrapper
from llama_index.core.extractors import KeywordExtractor, QuestionsAnsweredExtractor
from llama_index.extractors.entity import EntityExtractor
from llama_index.core.schema import BaseNode, TextNode

def _entityExtractor(nodes: list[TextNode]):
  ...

def _evaluateEntityExtractors():
  ...


def entityExtraction(log: TextIOWrapper):
  log.write('## Knowledge Graph Creation: Entity Extraction \n\n')

  log.write(f"""With a better idea on how to create the chunks, the next step is to pass through chunks through the LLM to extract entities.  These will form our Nodes in the graph database.

We can achieve this using a few techniques from both within and outside of LlamaIndex

  """)
