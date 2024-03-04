# Website Download

As part of the RAG system, we need to collect and store data that will be queried by the application and provided as context to the LLM.  One possible source is of course the internet, where everything is both finite and infinite.

This article outlines my investigation and conclusion on the technique that can be used to create an embedding/index based on HTML based web content for the purposes of building a RAG system.  This is part of my ongoing effort to design a repatable pattern for LLM/RAG creation.

For this particular project, I am using the Dungeons & Dragons 5E SRD website.  The goal being to **build a ingestion technique for documents

## The Data Source

[https://www.5esrd.com/home/](https://www.5esrd.com/home/) is the URL for the SRD website.  Continuing with the idea that an AI Assistant for Dungeons & Dragons is a prime candidate, having this resource is a god-send.  Even more so because it is statically built and not a web app.  

This generally means that I can call a URL and the HTML document I get back includes _all_ of the important data for the page (so in this case basically sans ads).

The main benefit is that we do not need tools like Puppeteer or Selenium to _emulate_ a user and basically wait for the app to load before accessing any data.

> 🌶️ Hot Take 🌶️
> 
> Based on this observation and the overall trend of web applications over static websites.  I find myself thinking that a **requirement** of any web application developer should be to implement a text based interface if they wish to be supportive of LLMs.  While not valuable to publicly traded companies like Reddit or Facebook, it could be valuable to internal facing applications or document sites.

## Data Download



Using LlamaIndex, I have this broken down into 2 primary steps and 1 optional one:

1. HTML Document Retreival
2. HTML Document Parsing
3. [Optional] Link Search

Thankfully these steps can be easily carried out with a couple of tools:

1. **SimpleWebPageReader** - Takes an array of URLS and returns LlamaIndex _Document_ objects
2. **BeautifulSoup** - Parses HTML Documents and allows us to filter a part of the _Document's_ text AND allows us to run a _querySelectorAll_ (essentually) on the HTML to find anchor tags

In practice this can be summed up in the following functions:

```python
from llama_index.readers.web import SimpleWebPageReader
from bs4 import BeautifulSoup

def loadWebPages(urls: list[str]):
  return SimpleWebPageReader().load_data(urls)

def parseWebPage(html: str, contentTag: str = 'main'):
  htmlDoc = BeautifulSoup(html, 'html.parser')
  return htmlDoc.find(contentTag).text

def getLinks(html: str, url: str = "http://localhost"):
  htmlDoc = BeautifulSoup(html, 'html.parser')
  links = htmlDoc.findAll('a', recursive=True, href=re.compile("{}.*".format(url)))
  return map(lambda link: link['href'], links)
```

We load the web page into the application using the `loadWebPages` function.  This produces a `List[Document]` response.

As part of many static web pages, we have a nagivation bar, this would be present on _every_ page and we would have to redundantly parse the same links with each URL.  To avoid this we can pass each html text string (found in the Document under `Document.text`) and specify a fragment of the HTML document that we want to work with.  In the case of the SRD that is the `<main>` tag which surrounds the content relevent to the URL.

Finally since the pages follow a hirarchy, some will reference other sub-pages.  To get a full picture of the website we will want to download those as well.  The `getLinks` function takes care of that for us.  Importantly, it also filters links, as both a stop-gap for infinate downloads **and** a content filter which avoids downloading unrelated content (such as advertizement data).

Within the web url pipeline we can then chain these together to ingest the data from the web page,  I used the following function to achieve this:

```python
def getWebDocumentAndLinks(url: str, documents: list[Document] = [], links: set = set()):
  # This suggests a new url search, add the original link provided
  if (len(links) == 0):
    links.add(url)
  
  try:
    print("==> Loading Web URL [url: {}]".format(url))
    htmlDoc = loadWebPages([url])
    print("====> Parsing HTML [url: {}]".format(url))
    webPage = parseWebPage(htmlDoc[0].text)
    debug("====> Creating Document [url: {}]".format(url))
    documents.append(Document(text=webPage, doc_id=url))
    print("====> Getting Links [url: {}]".format(url))
    webPageLinks = getLinks(htmlDoc[0].text, url=url)

    for link in webPageLinks:
      if (link not in links):
        links.add(link)
        getWebDocumentAndLinks(link, documents=documents, links=links)
      else:
        debug("===> Link Already Loaded [url: {}]...Skipping".format(url))
  except:
    failedLinks.append(url)
  finally:
    return documents, links
```

The key benefit here is that I can provide a _root url_ and the script will take care of downloading every sub-path that is contained with the in the website using recursion.

> ⚠️ This takes a while
>
> This process takes a while.  For the 5E SRD there are apparently 20k documents
> ```
> Loading Pages Complete
>    Document Count: 20344
>    Link Count: 20352
> ```

## Data Download Optimization

Part of my problem with the data download was how long it took as well as how expensive it was.  The last time I looked all of those documents in-memory cost about 8 GB of ram to maintain.  

I felt there must be a better way to handle the data without needing my beefy Mac M1 Pro Max and it's 64 GB of RAM.  

So I went back to the drawing board on how to ingest documents.  