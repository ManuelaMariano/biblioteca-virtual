from flask import Flask, render_template

app = Flask(__name__)


@app.route('/')
def inicio():
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/usuarios/listar')
def listar_usuarios():
    return render_template('usuarios/usuarios-listar.html')


@app.route('/usuarios/inserir')
def inserir_usuario():
    return render_template('usuarios/usuarios-form.html')


@app.route('/livros/listar')
def listar_livros():
    return render_template('livros/livros-listar.html')


@app.route('/livros/inserir')
def inserir_livro():
    return render_template('livros/livros-form.html')


@app.route('/emprestimos/listar')
def listar_emprestimos():
    return render_template('emprestimos/emprestimos-listar.html')


@app.route('/emprestimos/inserir')
def inserir_emprestimo():
    return render_template('emprestimos/emprestimos-form.html')


@app.route('/recuperar-senha')
def recuperar_senha():
    return render_template('recuperar-senha.html')


if __name__ == '__main__':
    app.run(debug=True)
