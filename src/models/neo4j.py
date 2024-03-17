from ..output_parsers import entityParser, relationshipParser
from ..llm import jsonOutputFixer
from langchain.output_parsers import OutputFixingParser
from langchain.prompts import ChatPromptTemplate
from llama_index.core.llms import ChatMessage, MessageRole

entityPromptTemplate = """You are an AI Agent who specializes in identifying "Entities" (such as objects, events, situations or abstract concepts) from a given text.

Take the text below delimited by triple backticks, and return any entities you find. Only return entities from the input.  Do not return entities from the examples

Input Text:
-------------
{input}
-------------

{formatInstructions}
"""
entityPrompt = ChatPromptTemplate.from_template(
  template=entityPromptTemplate,
  partial_variables={
    "formatInstructions": entityParser.get_format_instructions()
  }  
);

# entityPromptTemplate = """You are an AI Agent who specializes in identifying Relationships (semantics or relationships underlying these entities) from the given text and the list of entities

# Take the text below delimited by triple backticks, and return any entities you find.

# Input Text: ```{input}```

# {formatInstructions}
# """

# relationPrompt = PromptTemplate.from_template(
#   template=entityPromptTemplate,
#   input_variables=["input"],
#   partial_variables={
#     "formatInstructions"
#   }
# );

def EntityRetrievalPrompt(prompt: str):
  messages = [
    ChatMessage(
      role=MessageRole.USER,
      content=entityPrompt.format(input=prompt)
    )
  ]

  return messages

def EntityOutputParser(chat: str):
  try:
    return entityParser.parse(chat)
  except:
    fixer = OutputFixingParser.from_llm(
      parser=entityParser,
      llm=jsonOutputFixer
    )

    return fixer.parse(chat)