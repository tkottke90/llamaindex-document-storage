from datetime import datetime
from pydantic import BaseModel

def createOutputFile(directory: str, fileName: str, timestamped=True):
  now = datetime.now()

  timestampStr = ""
  if (timestamped):
    timestampStr = "_{}".format(now.strftime("%Y%m%d%H%M%S"))

  outputFilename = "{}{}.md".format(fileName, timestampStr)

  file = open("{dir}/{filename}".format(dir=directory, filename=outputFilename), 'x')
  file.write("# Output File\n")
  file.write("**Date:** {}\n\n".format(now.strftime("%Y%m%d%H%M%S")))

  return file

# class ReportSection:
#   header: str = "Section"
#   lines: list[str]

#   def __init__(
#       self,
#       title: str = None
#   ):
#     self.lines = list()

#     if (title):
#       header = title

#   def addLines(self, *lines: list[str]):
#     self.lines.extend(lines)

# class ExecutionReport(ReportSection):
#   author: str = None
#   timestamp: bool = False
#   sections: list[ReportSection] = list()
#   headerSection: ReportSection = ReportSection
#   currentSection: ReportSection = None

#   def __init__(
#       self,
#       title: str = None,
#       description: str = None
#   ):
#     self.lines = list()

#     if (title):
#       self.header = title

#     if (description):
#       self.description = description


#   def addSection(title: str = None, description: str = None):
#     ...

#   def addLines(self, *lines: list[str]):
#     if (not self.currentSection):
#       self.headerSection.addLines(lines)
#     else:
#       self.currentSection.addLines(lines)

#   def json(self):
#     ...

# m = ExecutionReport()
