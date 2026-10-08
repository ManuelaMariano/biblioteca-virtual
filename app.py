from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

ESTADOS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT",
           "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO",
           "RR", "SC", "SP", "SE", "TO"]

# Campos de cada formulário (são os mesmos "name" dos inputs no HTML)
CAMPOS_USUARIO = ["nome", "email", "celular", "nascimento", "cpf", "nivel",
                  "cep", "endereco", "numero", "complemento", "cidade", "estado"]
CAMPOS_LIVRO = ["titulo", "autor", "categoria", "ano", "quantidade", "isbn", "editora"]
CAMPOS_EMPRESTIMO = ["usuario", "livro", "inicio", "devolucao", "status", "observacao"]

# "Banco de dados" provisório: listas de dicionários.
# Os dados voltam ao início quando o servidor é reiniciado.
lista_usuarios = [
    {"id": 1, "nome": "Maria Silva", "email": "maria@email.com",
     "celular": "(14) 99999-9999", "nascimento": "1998-05-12",
     "cpf": "123.456.789-00", "nivel": "Usuário", "cep": "17000-000",
     "endereco": "Rua das Flores", "numero": "120", "complemento": "Apto 4",
     "cidade": "Bauru", "estado": "SP"},
    {"id": 2, "nome": "João Souza", "email": "joao@email.com",
     "celular": "(14) 98888-7777", "nascimento": "1990-11-03",
     "cpf": "987.654.321-00", "nivel": "Administrador", "cep": "17010-100",
     "endereco": "Av. Brasil", "numero": "500", "complemento": "",
     "cidade": "Bauru", "estado": "SP"},
]

lista_livros = [
    {"id": 1, "titulo": "Dom Casmurro", "autor": "Machado de Assis",
     "categoria": "Romance", "ano": "1899", "quantidade": "3",
     "isbn": "978-85-359-0277-5", "editora": "Companhia das Letras"},
    {"id": 2, "titulo": "O Pequeno Príncipe", "autor": "Antoine de Saint-Exupéry",
     "categoria": "Ficção", "ano": "1943", "quantidade": "5",
     "isbn": "978-85-220-0023-1", "editora": "Agir"},
]

lista_emprestimos = [
    {"id": 1, "usuario": "Maria Silva", "livro": "Dom Casmurro",
     "inicio": "2026-10-01", "devolucao": "2026-10-15",
     "status": "Em andamento", "observacao": ""},
    {"id": 2, "usuario": "João Souza", "livro": "O Pequeno Príncipe",
     "inicio": "2026-09-20", "devolucao": "2026-10-04",
     "status": "Devolvido", "observacao": ""},
]


# ---------- Funções auxiliares ----------
def proximo_id(lista):
    maior = 0
    for item in lista:
        if item["id"] > maior:
            maior = item["id"]
    return maior + 1


def buscar(lista, id):
    for item in lista:
        if item["id"] == id:
            return item
    return None


# Filtro usado no HTML: {{ data | data_br }}  ->  2026-10-01 vira 01/10/2026
@app.template_filter("data_br")
def data_br(texto):
    if not texto:
        return ""
    return datetime.strptime(texto, "%Y-%m-%d").strftime("%d/%m/%Y")


# ---------- LOGIN (página sem menu) ----------
@app.route("/")
def login():
    return render_template("login.html")


# ---------- INÍCIO ----------
@app.route("/inicio")
def inicio():
    return render_template("index.html")


# ---------- USUÁRIOS ----------
@app.route("/usuarios")
def usuarios():
    return render_template("usuarios_listar.html", usuarios=lista_usuarios)


@app.route("/usuarios/cadastrar", methods=["GET", "POST"])
def cadastrar_usuario():
    if request.method == "POST":
        novo = {"id": proximo_id(lista_usuarios)}
        for campo in CAMPOS_USUARIO:
            novo[campo] = request.form[campo]
        lista_usuarios.append(novo)
        return redirect(url_for("usuarios"))
    return render_template("usuarios_cadastrar.html", estados=ESTADOS)


@app.route("/usuarios/editar/<int:id>", methods=["GET", "POST"])
def editar_usuario(id):
    usuario = buscar(lista_usuarios, id)
    if usuario is None:
        return redirect(url_for("usuarios"))
    if request.method == "POST":
        for campo in CAMPOS_USUARIO:
            usuario[campo] = request.form[campo]
        return redirect(url_for("usuarios"))
    return render_template("usuarios_editar.html", usuario=usuario, estados=ESTADOS)


@app.route("/usuarios/excluir/<int:id>", methods=["POST"])
def excluir_usuario(id):
    usuario = buscar(lista_usuarios, id)
    if usuario is not None:
        lista_usuarios.remove(usuario)
    return redirect(url_for("usuarios"))


# ---------- LIVROS ----------
@app.route("/livros")
def livros():
    return render_template("livros_listar.html", livros=lista_livros)


@app.route("/livros/cadastrar", methods=["GET", "POST"])
def cadastrar_livro():
    if request.method == "POST":
        novo = {"id": proximo_id(lista_livros)}
        for campo in CAMPOS_LIVRO:
            novo[campo] = request.form[campo]
        lista_livros.append(novo)
        return redirect(url_for("livros"))
    return render_template("livros_cadastrar.html")


@app.route("/livros/editar/<int:id>", methods=["GET", "POST"])
def editar_livro(id):
    livro = buscar(lista_livros, id)
    if livro is None:
        return redirect(url_for("livros"))
    if request.method == "POST":
        for campo in CAMPOS_LIVRO:
            livro[campo] = request.form[campo]
        return redirect(url_for("livros"))
    return render_template("livros_editar.html", livro=livro)


@app.route("/livros/excluir/<int:id>", methods=["POST"])
def excluir_livro(id):
    livro = buscar(lista_livros, id)
    if livro is not None:
        lista_livros.remove(livro)
    return redirect(url_for("livros"))


# ---------- EMPRÉSTIMOS ----------
@app.route("/emprestimos")
def emprestimos():
    return render_template("emprestimos_listar.html", emprestimos=lista_emprestimos)


@app.route("/emprestimos/cadastrar", methods=["GET", "POST"])
def cadastrar_emprestimo():
    if request.method == "POST":
        novo = {"id": proximo_id(lista_emprestimos)}
        for campo in CAMPOS_EMPRESTIMO:
            novo[campo] = request.form[campo]
        lista_emprestimos.append(novo)
        return redirect(url_for("emprestimos"))
    return render_template("emprestimos_cadastrar.html",
                           usuarios=lista_usuarios, livros=lista_livros)


@app.route("/emprestimos/editar/<int:id>", methods=["GET", "POST"])
def editar_emprestimo(id):
    emprestimo = buscar(lista_emprestimos, id)
    if emprestimo is None:
        return redirect(url_for("emprestimos"))
    if request.method == "POST":
        for campo in CAMPOS_EMPRESTIMO:
            emprestimo[campo] = request.form[campo]
        return redirect(url_for("emprestimos"))
    return render_template("emprestimos_editar.html", emprestimo=emprestimo,
                           usuarios=lista_usuarios, livros=lista_livros)


@app.route("/emprestimos/excluir/<int:id>", methods=["POST"])
def excluir_emprestimo(id):
    emprestimo = buscar(lista_emprestimos, id)
    if emprestimo is not None:
        lista_emprestimos.remove(emprestimo)
    return redirect(url_for("emprestimos"))


if __name__ == "__main__":
    app.run(debug=True)
