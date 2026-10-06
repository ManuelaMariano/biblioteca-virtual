from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/usuarios")
def usuarios():
    return render_template("usuarios_listar.html")


@app.route("/usuarios/cadastrar")
def cadastrar_usuario():
    return render_template("usuarios_cadastrar.html")


# LIVROS
@app.route("/livros")
def livros():
    return render_template("livros_listar.html")


@app.route("/livros/cadastrar")
def cadastrar_livro():
    return render_template("livros_cadastrar.html")


# EMPRÉSTIMOS
@app.route("/emprestimos")
def emprestimos():
    return render_template("emprestimos_listar.html")


@app.route("/emprestimos/cadastrar")
def cadastrar_emprestimo():
    return render_template("emprestimos_cadastrar.html")


if __name__ == "__main__":
    app.run(debug=True)























if __name__ == "__main__":
    app.run(debug=True)