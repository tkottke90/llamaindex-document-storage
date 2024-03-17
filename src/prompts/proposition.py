from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser, OutputFixingParser
from langchain.prompts import ChatPromptTemplate
from llama_index.core.base.llms.types import ChatResponse, ChatMessage, MessageRole
from langchain_core.language_models.llms import BaseLLM
from llama_index.core.llms.llm import LLM

temp="""
Example:
Input: Title: ¯Eostre. Section: Theories and interpretations, Connection to Easter Hares. Content:
The earliest evidence for the Easter Hare (Osterhase) was recorded in south-west Germany in
1678 by the professor of medicine Georg Franck von Franckenau, but it remained unknown in
other parts of Germany until the 18th century. Scholar Richard Sermon writes that "hares were
frequently seen in gardens in spring, and thus may have served as a convenient explanation for the
origin of the colored eggs hidden there for children. Alternatively, there is a European tradition
that hares laid eggs, since a hare's scratch or form and a lapwing's nest look very similar, and
both occur on grassland and are first seen in the spring. In the nineteenth century the influence
of Easter cards, toys, and books was to make the Easter Hare/Rabbit popular throughout Europe.
German immigrants then exported the custom to Britain and America where it evolved into the
Easter Bunny."
Output: [ "The earliest evidence for the Easter Hare was recorded in south-west Germany in
1678 by Georg Franck von Franckenau.", "Georg Franck von Franckenau was a professor of
medicine.", "The evidence for the Easter Hare remained unknown in other parts of Germany until
the 18th century.", "Richard Sermon was a scholar.", "Richard Sermon writes a hypothesis about
the possible explanation for the connection between hares and the tradition during Easter", "Hares
were frequently seen in gardens in spring.", "Hares may have served as a convenient explanation
for the origin of the colored eggs hidden in gardens for children.", "There is a European tradition
that hares laid eggs.", "A hare's scratch or form and a lapwing's nest look very similar.", "Both
hares and lapwing's nests occur on grassland and are first seen in the spring.", "In the nineteenth
century the influence of Easter cards, toys, and books was to make the Easter Hare/Rabbit popular
throughout Europe.", "German immigrants exported the custom of the Easter Hare/Rabbit to
Britain and America.", "The custom of the Easter Hare/Rabbit evolved into the Easter Bunny in
Britain and America."]
"""

systemMessage = """
Decompose the "Content" into clear and simple propositions, ensuring they are interpretable out of
context.
1. Split compound sentence into simple sentences. Maintain the original phrasing from the input
whenever possible.
2. For any named entity that is accompanied by additional descriptive information, separate this
information into its own distinct proposition.
3. Decontextualize the proposition by adding necessary modifier to nouns or entire sentences
and replacing pronouns (e.g., "it", "he", "she", "they", "this", "that") with the full name of the
entities they refer to.

{format_instructions}

Decompose the following:
{input}
"""

class PropositionResponse(BaseModel):
  propositions: list[str] = Field(description="List of propositions found in the provided text")

propositionParser = PydanticOutputParser(pydantic_object=PropositionResponse)

class PropositionPrompt(dict):
  prompt: ChatPromptTemplate
  sentences: list[str]
  llm: BaseLLM
  lastMessage: str

  def __init__(self):
    dict.__init__(self)

    self.sentences = list()
    self.llm = None

    self.prompt = ChatPromptTemplate.from_template(
      template=systemMessage,
      partial_variables={
        "format_instructions": propositionParser.get_format_instructions()
      }
    )

  def chat(self, message: str, llm: BaseLLM = None) -> list[str]:
    if (llm):
      self['llm'] = llm
    
    if (not self['llm']):
      raise ValueError('Missing LLM, Please provide in constructor in in function call')

    self.llm = llm;
    self.lastMessage = message
    
    chain = self.prompt | self.llm

    chatResponse = chain.invoke(input=message)

    print(chatResponse)

    return self.parseResponse(chatResponse)

  def createPrompt(self, input: str):
    return ChatPromptTemplate.from_messages([ChatMessage(
      role=MessageRole.USER,
      content=self.prompt.format(input=input)
    )])

  def parseResponse(self, response: ChatResponse):
    output: list[str] = list()
    
    try:
      parsedResponse = propositionParser.parse(response.message.content)
    except:
      fixer = OutputFixingParser.from_llm(
        parser=propositionParser,
        llm=self.llm
      )

      parsedResponse: PropositionResponse = fixer.parse(self.lastMessage)
    finally:
      for chunk in parsedResponse.propositions:
        output.append(chunk)

      return output;