import os
from .llm import get_embedding_size
from llama_index.graph_stores.neo4j import Neo4jGraphStore
from llama_index.vector_stores.neo4jvector import Neo4jVectorStore
from llama_index.storage.docstore.mongodb import MongoDocumentStore

MONGO_URL = os.environ.get('MONGO_DB_URL')
NEO4J_USERNAME = os.environ.get('NEO4J_USERNAME')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')
NEO4J_URL = os.environ.get('NEO4J_URL')
NEO4J_DB = os.environ.get('NEO4J_DB')

documentStore = MongoDocumentStore.from_uri(
  uri=MONGO_URL,
  db_name="knowledge-docs"
)

graphStore = Neo4jGraphStore(
  username=NEO4J_USERNAME,
  password=NEO4J_PASSWORD,
  database=NEO4J_DB,
  url=NEO4J_URL
)

vectorStore = Neo4jVectorStore(
  username=NEO4J_USERNAME,
  password=NEO4J_PASSWORD,
  url=NEO4J_URL,
  embedding_dimension=get_embedding_size()
)