from flask import Flask
from routes.upload_route import upload_blueprint
# from routes.token_route import token_blueprint

app = Flask(__name__)

# Registering API routes
app.register_blueprint(upload_blueprint)
# app.register_blueprint(token_blueprint)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)