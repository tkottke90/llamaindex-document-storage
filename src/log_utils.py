from os import environ

def debug(message):
  if (environ['DEBUG']):
    print(message)