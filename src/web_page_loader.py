from llama_index.readers.web  import SimpleWebPageReader
from bs4 import BeautifulSoup, SoupStrainer, Tag
from markdownify import markdownify as md
from typing import TypedDict
import re


def stringCleanUp(chunk: str, replacers: list[tuple[str, str, re.RegexFlag]]):
  """
  A wrapper function around the 're' modules "#sub" method.  This allows us to make multiple edits to a string
  """
  output = chunk;

  for replacer in replacers:
    flags = re.NOFLAG
    if (len(replacer) == 3):
      flags = replacer[2]

    output = re.sub(replacer[0], replacer[1], output, flags=flags)

  return output

BeautifulSoupSearch = TypedDict(
  'HTMLSearch',
  {
    'name': SoupStrainer,
    'attrs': SoupStrainer,
    'recursive': bool,
    'string': SoupStrainer
  }
)

def extractElements(html: Tag, search: BeautifulSoupSearch):
  output: list[Tag] = list()

  print(search.get('attrs'))
  elements = html.findAll(
    name=search.get('name'),
    attrs=search.get('attrs'),
    recursive=search.get('recursive') or True,
    string=search.get('string')
  )

  for elem in elements:
    output.append(elem.extract());

  return output;

def removeElements(html: Tag, search: BeautifulSoupSearch):
  extractElements(html, search)

def htmlToMarkdown(html: str):
  rawMdStr = md(str(html), heading_style="ATX")
  return stringCleanUp(
    rawMdStr,
    [
      [r'\n{3,}', '\n\n'],      # Remove excessive new lines
      [r'â', '-'],              # Remove unicode character
      [r'', ''],               # Remove unicode character
      [r'\x94', '', re.UNICODE] # Remove unicode character
    ]
  )

def loadWebsite(
    url: str,
    contentTag: str = None,
    excludedTags: list[BeautifulSoupSearch] | None = None,
    extractTags: dict[str, BeautifulSoupSearch] = None,
    extractLinks: bool | str = False
):
  # Pull in html using LlamaIndex Loader
  page = SimpleWebPageReader().load_data([url]).pop()

  # The 'page' is a string so we need to convert that to HTML.
  # BeautifulSoup can help us with that
  html = BeautifulSoup(page.text, 'html.parser')

  # Depending on the URL you may get better results by 
  if (contentTag):
    html = html.find(contentTag)

  # Setup the extracted tags dict
  extractedTags: dict[str, list[str]] = dict()

  # Links are a valuable part of parsing process.  This motivates
  # the option for links to be its own extraction task as opposed
  # requiring the user enter a BeautifulSoup query for links
  if (isinstance(extractLinks, str) or extractLinks == True):
    links = list()
    linkTags = extractElements(html, { 'name': 'a' })

    for link in linkTags:
      # If a string is passed, then we want to filter on that string
      href = link.get('href')

      if (not href or not isinstance(href, str)):
        continue;

      if (isinstance(extractLinks, str)):
        if (href.startswith(extractLinks)):
          links.append(link['href'])
      else:
        links.append(link['href'])
    
    extractedTags['a'] = links

  # If the extract tags arg has been provided, we want to go
  # find any instance of the search and return it as part of
  # the dict.
  if (extractTags):
    # Get the keys from the parameter
    keys = extractTags.keys();
    # Create a new dict using those keys
    for key, val in zip(keys, [list()]*len(keys)):
      extractedTags[key] = val

    for key in keys:
      search = extractTags[key]
      # Returns a list of html elements that match
      elements = extractElements(html, search)

      # All data should be markdown so we are going to
      # run the htmlToMarkdown cleanup
      for elem in elements:
        extractedTags[key].append(htmlToMarkdown(str(elem)))

  # If excluded strings have been provided, we need to remove
  # those from the HTML.  These will be HTML tags such as 'script'
  # or 'div'
  if (excludedTags):
    [removeElements(html, search) for search in excludedTags]
  
  # Once we have extracted all of the tags we have our "final"
  # HTML document that we can then convert into markdown
  markdown = htmlToMarkdown(str(html))

  return markdown, extractedTags