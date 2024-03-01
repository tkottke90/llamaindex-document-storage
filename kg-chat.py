from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core import ChatPromptTemplate, VectorStoreIndex
from src.documents import loadWebPages, parseWebPage, getLinks
from src.llm import ollama, codelama
from datetime import datetime
from llama_index.llms.ollama import Ollama


now = datetime.now()
timestampStr = now.strftime("%Y%m%d%H%M%S")
logFilename = "./kg-output/kg_log_{}.md".format(timestampStr)

logFile = open(logFilename, 'x')
logFile.write("# Knowledge Graph Log File\n")
logFile.write("**Date:**{}\n\n---\n".format(timestampStr))

def llmStep(label: str, prompt: str, llm: Ollama = None):
  print("> {}".format(label))
  
  if (llm):
    result = llm.complete(prompt)
  else:
    result = ollama.complete(prompt)
  
  logFile.write("""
## {label}

**Input:**
```
{prompt}
```

**Output:**
```
{result}
```

---
""".format(label=label, result=result, prompt=prompt))
  
  return result.text

kg_prompt_programs = """
# Knowledge Graph Instructions
## 1. Overview
You are a top-tier algorithm designed for extracting information in structured formats to build a knowledge graph. The aim is to capture the key details into a graph database using the Cypher Query Language.  This will require the identification of Entities in the input and relationships which tie those entities together. 
## 2. Labeling Entities
- **Consistency**: Ensure you use basic or elementary types for entities labels.
  - For example, when you identify an entity representing a person, always label it as **"person"**. Avoid using more specific terms like "mathematician" or "scientist".
- **Node IDs**: Never utilize integers as node IDs. Node IDs should be names or human-readable identifiers found in the text.
## Coreference Resolution
- **Maintain Entity Consistency**: When extracting entities, it's vital to ensure consistency.
If an entity, such as "John Doe", is mentioned multiple times in the text but is referred to by different names or pronouns (e.g., "Joe", "he"), 
always use the most complete identifier for that entity throughout the knowledge graph. In this example, use "John Doe" as the entity ID.  
Remember, the knowledge graph should be coherent and easily understandable, so maintaining consistency in entity references is crucial. 
## Strict Compliance
Adhere to the rules strictly. Non-compliance will result in termination.

The data requested should be contained within an OUTPUT section and the end of your response.  

Example Output:

OUTPUT:

State each step of the program and show your work for performing that step. Your output should NOT include data from the instructions.

{}
"""

urls = [
  # "https://www.5esrd.com/character-creation-outline/",
  # "https://www.5esrd.com/using-ability-scores",
  # "https://www.5esrd.com/backgrounds/",
  # "https://www.5esrd.com/database/background/",
  # "https://www.5esrd.com/races",
  # "https://www.5esrd.com/classes",
  "https://www.5esrd.com/races/elf/"
]

print("> Loading Pages")
pages = loadWebPages(urls)

pageContent = parseWebPage(pages[0].text)
formattedContent = pageContent.replace('\n\n', '')

logFile.write("""
# Page Contents

{contents}

# Links

""".format(contents=formattedContent))

links = getLinks(pages[0].text, url="https://www.5esrd.com/races")

for link in links:
  logFile.write("- {link}\n".format(link=link))

details = llmStep(
  label="Node Identification",
  prompt="""# Knowledge Graph Document Parser
## Description
You are a AI Assistant specializing in processing documents and identify key information based on the task with the express focus of building knowledge graphs.
The knowledge graph generated should be optimized for Retrieval Augmented Generated (RAG).

The knowledge graph will be built using the Cypher Query Lanaguage.  This query language is used by graph databases (such as Neo4j) to read/write data in the database.

## Task
Based on the provided prompt, take the following steps. Only provide the knowledge graph in the response.

1. Build a knowledge graph based on the information provided.

Here is the input: 
{input}
""".format(input=formattedContent)
)

code = llmStep(
  label="Code Gen",
  llm=codelama,
  prompt="""
Write a Cypher Query Language (CQL) query to upsert (create or update) all of the data and relationships found in the following information. Prioritize nodes over attributes for details found within the input as the data points may be shared with other nodes.

{input}
""".format(input=details)
)

print("== DONE ==")
exit()

races = llmStep(
  label="Race List",
  prompt="""
Create a list of all the links to races and sub-races described in the following markdown document. Skip any content BEFORE the "# Races" header. 

Output the list as a JSON array string.

Example Output:

[ "https://www.5esrd.com/races/elf/", "https://www.5esrd.com/races/human/" ]


Here is the document which contains the links:
----------------
{input}
----------------
""".format(input=pages[0].text)
)


exit()

kg = llmStep(
  label="KG Prompt",
  llm=codelama,
  prompt="""
Create a Cypher query to create nodes in a Neo4j which will insert nodes for the races in the given document.

Each node should have a label of "Race".  Sub-races should be their own race and not a property of their parent race.

Example Query:

CREATE (Human:Race {{name:"Human"}})
CREATE (Elf:Race {{name:"Elf"}})
CREATE (Dwarf:Race {{name:"Dwarf"}})
RETURN *

These are the races I want to add: Dwarf, Elf, Gnome, Half-Elf, Half-Orc, Human, Kenku, Lizardfolk, Minotaur, Orc, Pegasus, Satyr, Shapeshifter, Sprite, Troll, Werebeast, Witch
""".format(input=pages[0].text)
)

print(kg)

exit()

coreference = llmStep(
  label='Correference Resolution',
  prompt=kg_prompt_programs.format("""
# Review the input document and resolve any coreferences included in the document

# input document:
# ----------------
# {input}
# ----------------

# """.format(input=pages[0].text))
)


entities = llmStep(
  label='Entity Identification',
  prompt=kg_prompt_programs.format("""
Collect a list of named entities and output as a comma separated list so they can be easily read by software.  Entities should be capitalized.

input document:
----------------
{input}
----------------

""".format(input=coreference))
)


#1. Create a short 1-2 sentence description of each entity
#2. Identify the section in the input where the source is listed, if there are multiple use a comma separated list to display each section

graphNodes = llmStep(
  llm=codelama,
  label="Create Graph Nodes",
  prompt=kg_prompt_programs.format("""
Using Cypher Query Language, write a query which adds a node for each entity in the provided list

entities list:
----------------
{entities}
----------------

""".format(entities=entities, input=pages[0].text))
)

# print("Coreference Resolution")
# corefernced = ollama.complete(
#   kg_prompt_programs.format("""
# 1. Review the input document and resolve any coreferences included in the document

# input document:
# ----------------
# {input}
# ----------------

# """.format(input=pages[0].text))
# )

# logFile.write("## Coreference Result\n\n```\n{}\n```\n---".format(corefernced.text))

# print("> Entity Identification")
# response = ollama.complete(
#   kg_prompt_programs.format("""
# 2. Collect a list of named entities and output as a comma separated list

# input document:
# ----------------
# {input}
# ----------------

# """.format(input=corefernced.text))
# )

# logFile.write("## Entity Identification\n\n```\n{}\n```".format(response.text))

print("> Result")
print(graphNodes);