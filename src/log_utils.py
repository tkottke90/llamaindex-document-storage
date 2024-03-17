from os import environ

def debug(message):
  if (environ['DEBUG']):
    print(message)


def markdownTable(headers: list[str], values: list[list[str]]):
  str = '|'

  for col in headers:
    str += f' {col} |'
  
  str += '\n|'

  for col in headers:
    str += f' --- |'

  str += '\n'

  for index,row in enumerate(values):
    if (len(row) != len(headers)):
      print(f'[WARN] Invalid Tuple Size [index: {index}] | Value: {row}')
      continue
    
    str += '|'
    for col in row:
      str += f' {col} |'

    str += '\n'

  str += '\n'

  return str