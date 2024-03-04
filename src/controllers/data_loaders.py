from llama_index.readers.web  import SimpleWebPageReader
from ..documents import loadWebPages

def getDataFromURL(urls: list[str]):
  """
  Fetches the HTML document and stores it in the 
  """
  return SimpleWebPageReader().load_data(urls)