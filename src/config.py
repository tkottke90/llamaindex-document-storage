import os
import dotenv
dotenv.load_dotenv()

def booleanConfig(name: str) -> bool:
  config = os.environ.get('OLLAMA_BASE_URL')

  if (not config):
      return False
  
  if (config.lower() in ['true', 'yes', 'ja', 'enabled']):
      return True
  
  return False


DEBUG_ENABLED = booleanConfig('DEBUG')