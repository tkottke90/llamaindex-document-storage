from flask import Flask, Response, request

app = Flask(__name__)

@app.route('/load-data', methods=['POST'])
def createData():
  if (request.method == 'POST'):
    print('Load data')
  else:
    result = Response('{ "message": "Not Implemented" }', status=405, mimetype="application/json")
  return result

if __name__ == '__main__':
  app.run()