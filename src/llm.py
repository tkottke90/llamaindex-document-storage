#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from llama_index.core import ServiceContext
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
import importlib  

load_dotenv()

model="llama2"
baseUrl = os.environ.get('OLLAMA_BASE_URL')


ollama = Ollama(model=model, request_timeout=180.0)

def get_ollama():
    return ollama;

def get_service_context():
    return ServiceContext.from_defaults(llm=ollama, embed_model=OllamaEmbedding(model_name=model))