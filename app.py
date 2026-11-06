import os

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, url_for, request 
from flask_wtf.csrf import CSRFProtect

from db import execute_one

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Liga a proteção CSRF: todo formulário POST do sistema vai precisar do token
CSRFProtect(app)

# ==============================================================================
# PÁGINAS PRINCIPAIS
# ==============================================================================

@app.route('/')
def inicio():
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


# ==============================================================================
# Usuários
# ==============================================================================


@app.route('/usuarios/listar')
def listar_usuarios():
    return render_template('usuarios/usuarios-listar.html')


@app.route('/usuarios/inserir')
def inserir_usuario():
    return render_template('usuarios/usuarios-form.html')

# ==============================================================================
# Livros
# ==============================================================================

@app.route('/livros/listar')
def listar_livros():
    return render_template('livros/livros-listar.html')


@app.route('/livros/inserir')
def inserir_livro():
    return render_template('livros/livros-form.html')

# ==============================================================================
# Empréstimos
# ==============================================================================

@app.route('/emprestimos/listar')
def listar_emprestimos():
    return render_template('emprestimos/emprestimos-listar.html')


@app.route('/emprestimos/inserir')
def inserir_emprestimo():
    return render_template('emprestimos/emprestimos-form.html')


@app.route('/recuperar-senha')
def recuperar_senha():
    return render_template('recuperar-senha.html')

# ==============================================================================
# Perfil
# ==============================================================================

@app.route('/perfis/inserir', methods=['GET', 'POST'])
def inserir_perfil():
    
    if request.method == 'POST':
        redirect(url_for(listar_perfis))
        
        return render_template ('perfis/perfil-form.html')




@app.route('/perfis/listar')
def listar_perfis():
    return render_template ('perfis/perfis-listar.html')


# ==============================================================================
# TELAS DE ERROS
# ==============================================================================

@app.errorhandler(404)
def pagina_nao_encontrada(erro):
    return render_template('404.html'), 404


@app.errorhandler(500)
def erro_no_servidor(erro):
    return render_template('500.html'), 500
if __name__ == '__main__':
    app.run(debug=True)
