from datetime import datetime

def createOutputFile(directory: str, fileName: str, timestamped=True):
  now = datetime.now()

  timestampStr = ""
  if (timestamped):
    timestampStr = "_{}".format(now.strftime("%Y%m%d%H%M%S"))

  outputFilename = "{}{}.md".format(fileName, timestampStr)

  file = open("{dir}/{filename}".format(dir=directory, filename=outputFilename), 'x')
  file.write("# Output File\n")
  file.write("**Date:** {}\n\n---\n".format(now.strftime("%Y%m%d%H%M%S")))

  return file