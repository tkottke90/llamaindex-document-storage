import json
from langchain_core.pydantic_v1 import BaseModel, Field, validator

class Property(BaseModel):
  """A single property consisting of key and value"""
  key: str = Field(..., description="key")
  value: str = Field(..., description="value")

class Entity(BaseModel):
  """Represents a node in a graph with associated properties.

    Attributes:
        id str: A unique identifier for the node.
        label (str): The type or label of the node, default is "Node".
        properties (dict): Additional properties and metadata associated with the node.
  """

  name: str = Field(description="the entities name as it appears in the source material")
  label: str = Field(description="The type or label of the node, default is 'Node'")
  properties: dict[str, Property] = Field(default_factory=dict, description="Additional properties and metadata associated with the node.")

  def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)


class Relationship(BaseModel):
  """Represents a directed relationship between two nodes in a graph.

    Attributes:
        source (Entity): The source node of the relationship.
        target (Entity): The target node of the relationship.
        type (str): The type of the relationship, default is 'CONNECTED_TO'
        properties (dict): Additional properties associated with the relationship.
  """

  source: Entity = Field(description="The source node of the relationship")
  target: Entity = Field(description="The target node of the relationship")
  type: str = Field(description="The type of the relationship, default is 'CONNECTED_TO")
  properties: dict[str, Property] = Field(default_factory=dict, description="Additional properties associated with the relationship")

class EntityList(BaseModel):
  """Represents a directed relationship between two nodes in a graph.

    Attributes:
        entities (List[Entity]): List of entities found in a given text
  """ 
  entities: list[Entity] = Field(description="List of entities")
