from langchain.output_parsers import PydanticOutputParser
from .models.entities_model import Entity, Relationship, EntityList

entityParser = PydanticOutputParser(pydantic_object=EntityList)
relationshipParser = PydanticOutputParser(pydantic_object=Relationship)

