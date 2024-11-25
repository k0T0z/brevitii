from flask import Flask
from threading import Thread

app = Flask(__name__)

# @app.route('/')
# def home():
#     return "Hello, I am Brevitii's Pinger!"


@app.route("/")
def index():
  return "Hello, I am Brevitii's Pinger!"


def run():
  # app.run(host='0.0.0.0',port=8080)
  from waitress import serve
  serve(app, host="0.0.0.0", port=8080)


def listen_for_brevitii():
  t = Thread(target=run)
  t.start()
