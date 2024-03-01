from llama_index.core import get_response_synthesizer
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine

def createQuery(query: str):
  def prompt(vectorStore, prompt: str):
    retriever = VectorIndexRetriever(
      index=vectorStore,
      similarity_top_k=3,
    )
    
    responseSynth = get_response_synthesizer(
      response_mode="tree_summarize",
      verbose=True
    )

    queryEngine = RetrieverQueryEngine(
      retriever=retriever,
      response_synthesizer=responseSynth
    )

    print ('=====================')
    print('Question: {}\n'.format(prompt))
    print('Response {}'.format(queryEngine.query(query.format(prompt=prompt))))
    print ('=====================') 

  return prompt