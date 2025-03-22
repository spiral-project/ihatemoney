import os
  from flask import Flask

  app = Flask(__name__)

  @app.route('/')
  def home():
      return "Hello from Render!"

  if __name__ == '__main__':
      port = int(os.environ.get("PORT", 80))  # Default to port 80 if PORT isn't set
      app.run(host='0.0.0.0', port=port)
