from flask import Flask

app = Flask(__name__)

@app.route("/")
def inicio():
    return "Biblioteca Virtual"

if __name__ == "__main__":
    app.run(debug=True)