from flask import Flask, Response, request
from llama_index.core import SimpleDirectoryReader, KnowledgeGraphIndex, ServiceContext
from src.documents import loadWebPages
from src.llm import get_service_context
from src.rebel import extract_triplets
import json

app = Flask(__name__)

@app.route('/load-url', methods=['GET'])
def getLoadedDocs():
  result = Response('{ "message": "Not Implemented" }', status=405, mimetype="application/json")
  return result;

@app.route('/load-url', methods=['POST'])
def createData():
  print('> Loading Docs {}'.format(json.dumps(request.json)))
  htmlDocs = loadWebPages(request.json)
  print('> Documents Loaded: {}'.format(len(htmlDocs)))
  return Response(json.dumps(request.json), mimetype="application/json")

if __name__ == '__main__':
  app.debug = True
  app.run()