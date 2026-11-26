import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash

from db import execute_insert, execute_one, execute_query

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Liga a proteção CSRF: todo formulário POST do sistema vai precisar do token.
CSRFProtect(app)

# A senha fica fora deste SELECT de propósito: só a rota de login lê o hash.
SELECT_USUARIO = (
    'SELECT u.id_usuario, u.nome, u.email, u.celular, u.data_nascimento, u.cpf, '
    'u.perfil_id, u.cep, u.endereco, u.numero, u.complemento, u.cidade, u.estado, '
    'u.criado_em, u.atualizado_em, p.nome AS perfil, p.descricao AS perfil_descricao '
    'FROM usuarios u '
    'JOIN perfis p ON p.id_perfil = u.perfil_id'
)


# ============================================================================== 
# VALIDAÇÕES
# ============================================================================== 

UFS = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA',
       'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']


def validar_perfil(nome, descricao, id_perfil=0):
    erros = []

    if not nome:
        erros.append('Informe o nome do perfil.')
    elif len(nome) < 3:
        erros.append('O nome deve ter pelo menos 3 caracteres.')
    elif len(nome) > 100:
        erros.append('O nome deve ter no máximo 100 caracteres.')

    if descricao and len(descricao) > 255:
        erros.append('A descrição deve ter no máximo 255 caracteres.')

    if not erros:
        existente = execute_one(
            'SELECT id_perfil FROM perfis WHERE nome = %s AND id_perfil <> %s',
            (nome, id_perfil),
        )
        if existente:
            erros.append('Já existe um perfil com este nome.')

    return erros


def so_digitos(texto):
    resultado = ''
    for letra in texto:
        if letra in '0123456789':
            resultado = resultado + letra
    return resultado


def formatar_celular(celular):
    if not celular:
        return None

    digitos = so_digitos(celular)
    if len(digitos) == 11:
        return f'({digitos[0:2]}) {digitos[2:7]}-{digitos[7:11]}'

    return f'({digitos[0:2]}) {digitos[2:6]}-{digitos[6:10]}'


def formatar_cpf(cpf):
    if not cpf:
        return None

    digitos = so_digitos(cpf)
    return f'{digitos[0:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:11]}'


def formatar_cep(cep):
    if not cep:
        return None

    digitos = so_digitos(cep)
    return f'{digitos[0:5]}-{digitos[5:8]}'


def calcular_digito_cpf(digitos, quantidade):
    soma = 0
    for posicao in range(quantidade):
        peso = quantidade + 1 - posicao
        soma = soma + int(digitos[posicao]) * peso

    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0

    return resto


def validar_nome(nome):
    if not nome:
        return 'Informe o nome do usuário.'
    if len(nome) < 3:
        return 'O nome deve ter pelo menos 3 caracteres.'
    if len(nome) > 255:
        return 'O nome deve ter no máximo 255 caracteres.'
    return None


def validar_email(email, id_usuario):
    mensagem = 'Informe um e-mail válido, por exemplo nome@dominio.com.br.'

    if not email:
        return 'Informe o e-mail.'
    if len(email) > 255:
        return 'O e-mail deve ter no máximo 255 caracteres.'
    if ' ' in email or email.count('@') != 1:
        return mensagem

    antes, depois = email.split('@')
    if antes == '' or '.' not in depois:
        return mensagem
    if depois.startswith('.') or depois.endswith('.'):
        return mensagem

    existente = execute_one(
        'SELECT id_usuario FROM usuarios WHERE email = %s AND id_usuario <> %s',
        (email, id_usuario),
    )
    if existente:
        return 'Já existe um usuário com este e-mail.'

    return None


def validar_senha(senha, confirmacao):
    if len(senha) < 8:
        return 'A senha deve ter pelo menos 8 caracteres.'
    if len(senha) > 128:
        return 'A senha deve ter no máximo 128 caracteres.'

    tem_letra = False
    tem_numero = False
    for caractere in senha:
        if caractere.isalpha():
            tem_letra = True
        if caractere in '0123456789':
            tem_numero = True

    if not tem_letra or not tem_numero:
        return 'A senha deve ter letras e números.'
    if senha != confirmacao:
        return 'A confirmação da senha não confere.'

    return None


def validar_perfil_id(perfil_id):
    try:
        numero = int(perfil_id)
    except (ValueError, TypeError):
        return 'Selecione um perfil.'

    perfil = execute_one('SELECT id_perfil FROM perfis WHERE id_perfil = %s', (numero,))
    if perfil is None:
        return 'Selecione um perfil válido.'

    return None


def validar_celular(celular):
    if not celular:
        return None

    digitos = so_digitos(celular)
    if len(digitos) != 10 and len(digitos) != 11:
        return 'Informe o celular com DDD, com 10 ou 11 dígitos.'

    return None


def validar_cpf(cpf, id_usuario):
    if not cpf:
        return None

    digitos = so_digitos(cpf)
    if len(digitos) != 11:
        return 'O CPF deve ter 11 dígitos.'
    if digitos == digitos[0] * 11:
        return 'Informe um CPF válido.'
    if calcular_digito_cpf(digitos, 9) != int(digitos[9]):
        return 'Informe um CPF válido.'
    if calcular_digito_cpf(digitos, 10) != int(digitos[10]):
        return 'Informe um CPF válido.'

    existente = execute_one(
        'SELECT id_usuario FROM usuarios WHERE cpf = %s AND id_usuario <> %s',
        (formatar_cpf(cpf), id_usuario),
    )
    if existente:
        return 'Já existe um usuário com este CPF.'

    return None


def validar_data_nascimento(texto):
    if not texto:
        return None

    try:
        data = datetime.strptime(texto, '%Y-%m-%d')
    except ValueError:
        return 'Informe uma data de nascimento válida.'

    if data > datetime.now():
        return 'A data de nascimento não pode estar no futuro.'
    if data.year < 1900:
        return 'A data de nascimento deve ser a partir de 1900.'

    return None


def validar_cep(cep):
    if not cep:
        return None

    if len(so_digitos(cep)) != 8:
        return 'Informe um CEP com 8 dígitos.'

    return None


def validar_estado(estado):
    if not estado:
        return None

    if estado not in UFS:
        return 'Selecione um estado válido.'

    return None


def validar_tamanho(valor, rotulo, maximo):
    if valor and len(valor) > maximo:
        return f'O campo {rotulo} deve ter no máximo {maximo} caracteres.'
    return None


def validar_usuario(dados, id_usuario=0):
    erros = []

    erro = validar_nome(dados['nome'])
    if erro:
        erros.append(erro)

    erro = validar_email(dados['email'], id_usuario)
    if erro:
        erros.append(erro)

    if id_usuario == 0 or dados['senha'] or dados['confirmacao']:
        erro = validar_senha(dados['senha'], dados['confirmacao'])
        if erro:
            erros.append(erro)

    erro = validar_perfil_id(dados['perfil_id'])
    if erro:
        erros.append(erro)

    erro = validar_celular(dados['celular'])
    if erro:
        erros.append(erro)

    erro = validar_cpf(dados['cpf'], id_usuario)
    if erro:
        erros.append(erro)

    erro = validar_data_nascimento(dados['data_nascimento'])
    if erro:
        erros.append(erro)

    erro = validar_cep(dados['cep'])
    if erro:
        erros.append(erro)

    erro = validar_tamanho(dados['endereco'], 'endereço', 255)
    if erro:
        erros.append(erro)

    erro = validar_tamanho(dados['numero'], 'número', 20)
    if erro:
        erros.append(erro)

    erro = validar_tamanho(dados['complemento'], 'complemento', 100)
    if erro:
        erros.append(erro)

    erro = validar_tamanho(dados['cidade'], 'cidade', 100)
    if erro:
        erros.append(erro)

    erro = validar_estado(dados['estado'])
    if erro:
        erros.append(erro)

    return erros


# ==============================================================================
# FILTROS DO JINJA
# ==============================================================================

@app.template_filter('data_br')
def data_br(valor):
    if valor is None:
        return '—'
    return valor.strftime('%d/%m/%Y')


@app.template_filter('data_hora_br')
def data_hora_br(valor):
    if valor is None:
        return '—'
    return valor.strftime('%d/%m/%Y às %H:%M')


@app.template_filter('cpf_oculto')
def cpf_oculto(cpf):
    if cpf is None:
        return '—'
    return '***.' + cpf[4:11] + '-**'


# ==============================================================================
# PÁGINAS PRINCIPAIS / LOGIN
# ==============================================================================

@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'id_usuario' in session:
        return redirect(url_for('dashboard'))

    email = ''

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')

        usuario = execute_one(
            'SELECT u.id_usuario, u.nome, u.senha, p.nome AS perfil '
            'FROM usuarios u '
            'JOIN perfis p ON p.id_perfil = u.perfil_id '
            'WHERE u.email = %s',
            (email,),
        )

        if usuario is not None and check_password_hash(usuario['senha'], senha):
            session.clear()
            session['id_usuario'] = usuario['id_usuario']
            session['nome'] = usuario['nome']
            session['perfil'] = usuario['perfil']
            flash(f'Você entrou como {usuario["nome"]}.', 'success')
            return redirect(url_for('dashboard'))

        flash('E-mail ou senha incorretos.', 'danger')

    return render_template('login.html', email=email)


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('Você saiu do sistema.', 'success')
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    perfis = execute_one('SELECT COUNT(*) AS total FROM perfis')
    usuarios = execute_one('SELECT COUNT(*) AS total FROM usuarios')

    return render_template(
        'dashboard.html',
        titulo='Biblioteca Virtual',
        total_perfis=perfis['total'],
        total_usuarios=usuarios['total'],
    )


# ==============================================================================
# PERFIS
# ==============================================================================

@app.route('/perfis')
@app.route('/perfis/listar')
def listar_perfis():
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    perfis = execute_query(
        'SELECT id_perfil, nome, descricao, criado_em FROM perfis ORDER BY nome',
        fetch=True,
    )

    return render_template('perfis/perfis_lista.html', titulo='Perfis', perfis=perfis)


@app.route('/perfis/inserir', methods=['GET', 'POST'])
def inserir_perfil():
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    nome = ''
    descricao = ''

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip() or None

        erros = validar_perfil(nome, descricao)

        if erros:
            for mensagem in erros:
                flash(mensagem, 'danger')
        else:
            try:
                novo_id = execute_insert(
                    'INSERT INTO perfis (nome, descricao) VALUES (%s, %s)',
                    (nome, descricao),
                )
                flash(f'Perfil "{nome}" cadastrado (código {novo_id}).', 'success')
                return redirect(url_for('listar_perfis'))
            except Error as erro:
                if erro.errno == 1062:
                    flash('Já existe um perfil com este nome.', 'danger')
                else:
                    raise

    return render_template(
        'perfis/perfil_form.html',
        acao='criar',
        id_perfil=None,
        nome=nome,
        descricao=descricao,
    )


@app.route('/perfis/<int:id_perfil>/editar', methods=['GET', 'POST'])
def editar_perfil(id_perfil):
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    perfil = execute_one(
        'SELECT id_perfil, nome, descricao FROM perfis WHERE id_perfil = %s',
        (id_perfil,),
    )

    if perfil is None:
        abort(404)

    nome = perfil['nome']
    descricao = perfil['descricao']

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip() or None

        erros = validar_perfil(nome, descricao, id_perfil)

        if erros:
            for mensagem in erros:
                flash(mensagem, 'danger')
        else:
            try:
                execute_query(
                    'UPDATE perfis SET nome = %s, descricao = %s WHERE id_perfil = %s',
                    (nome, descricao, id_perfil),
                )
                flash(f'Perfil "{nome}" atualizado.', 'success')
                return redirect(url_for('listar_perfis'))
            except Error as erro:
                if erro.errno == 1062:
                    flash('Já existe um perfil com este nome.', 'danger')
                else:
                    raise

    return render_template(
        'perfis/perfil_form.html',
        acao='editar',
        id_perfil=id_perfil,
        nome=nome,
        descricao=descricao,
    )


@app.route('/perfis/<int:id_perfil>/excluir', methods=['POST'])
def excluir_perfil(id_perfil):
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    perfil = execute_one(
        'SELECT id_perfil, nome FROM perfis WHERE id_perfil = %s',
        (id_perfil,),
    )

    if perfil is None:
        abort(404)

    usuarios = execute_one(
        'SELECT COUNT(*) AS total FROM usuarios WHERE perfil_id = %s',
        (id_perfil,),
    )

    if usuarios['total'] > 0:
        flash(
            f'O perfil "{perfil["nome"]}" tem {usuarios["total"]} usuário(s) e não pode ser excluído.',
            'danger',
        )
        return redirect(url_for('listar_perfis'))

    try:
        execute_query('DELETE FROM perfis WHERE id_perfil = %s', (id_perfil,))
        flash(f'Perfil "{perfil["nome"]}" excluído.', 'success')
    except Error as erro:
        if erro.errno == 1451:
            flash(f'O perfil "{perfil["nome"]}" está em uso e não pode ser excluído.', 'danger')
        else:
            raise

    return redirect(url_for('listar_perfis'))


# ==============================================================================
# USUÁRIOS
# ==============================================================================

@app.route('/usuarios')
@app.route('/usuarios/listar')
def listar_usuarios():
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    usuarios = execute_query(SELECT_USUARIO + ' ORDER BY u.nome', fetch=True)
    return render_template('usuarios/usuarios_lista.html', titulo='Usuários', usuarios=usuarios)


@app.route('/usuarios/inserir', methods=['GET', 'POST'])
def inserir_usuario():
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    dados = {}

    if request.method == 'POST':
        dados = {
            'nome': request.form.get('nome', '').strip(),
            'email': request.form.get('email', '').strip().lower(),
            'senha': request.form.get('senha', ''),
            'confirmacao': request.form.get('confirmacao', ''),
            'perfil_id': request.form.get('perfil_id', ''),
            'celular': request.form.get('celular', '').strip() or None,
            'data_nascimento': request.form.get('data_nascimento', '').strip() or None,
            'cpf': request.form.get('cpf', '').strip() or None,
            'cep': request.form.get('cep', '').strip() or None,
            'endereco': request.form.get('endereco', '').strip() or None,
            'numero': request.form.get('numero', '').strip() or None,
            'complemento': request.form.get('complemento', '').strip() or None,
            'cidade': request.form.get('cidade', '').strip() or None,
            'estado': request.form.get('estado', '') or None,
        }

        erros = validar_usuario(dados)

        if erros:
            for mensagem in erros:
                flash(mensagem, 'danger')
        else:
            try:
                novo_id = execute_insert(
                    'INSERT INTO usuarios (nome, email, senha, celular, data_nascimento, cpf, '
                    'perfil_id, cep, endereco, numero, complemento, cidade, estado) '
                    'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                    (
                        dados['nome'],
                        dados['email'],
                        generate_password_hash(dados['senha']),
                        formatar_celular(dados['celular']),
                        dados['data_nascimento'],
                        formatar_cpf(dados['cpf']),
                        dados['perfil_id'],
                        formatar_cep(dados['cep']),
                        dados['endereco'],
                        dados['numero'],
                        dados['complemento'],
                        dados['cidade'],
                        dados['estado'],
                    ),
                )
                flash(f'Usuário "{dados["nome"]}" cadastrado (código {novo_id}).', 'success')
                return redirect(url_for('listar_usuarios'))
            except Error as erro:
                if erro.errno == 1062:
                    flash('Já existe um usuário com este e-mail ou este CPF.', 'danger')
                else:
                    raise

    perfis = execute_query('SELECT id_perfil, nome FROM perfis ORDER BY nome', fetch=True)

    return render_template(
        'usuarios/usuario_form.html',
        acao='criar',
        id_usuario=None,
        dados=dados,
        perfis=perfis,
        ufs=UFS,
    )


@app.route('/usuarios/<int:id_usuario>')
def detalhar_usuario(id_usuario):
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    usuario = execute_one(SELECT_USUARIO + ' WHERE u.id_usuario = %s', (id_usuario,))

    if usuario is None:
        abort(404)

    return render_template('usuarios/usuario_detalhe.html', usuario=usuario)


@app.route('/usuarios/<int:id_usuario>/editar', methods=['GET', 'POST'])
def editar_usuario(id_usuario):
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    usuario = execute_one(SELECT_USUARIO + ' WHERE u.id_usuario = %s', (id_usuario,))

    if usuario is None:
        abort(404)

    dados = usuario

    if request.method == 'POST':
        dados = {
            'nome': request.form.get('nome', '').strip(),
            'email': request.form.get('email', '').strip().lower(),
            'senha': request.form.get('senha', ''),
            'confirmacao': request.form.get('confirmacao', ''),
            'perfil_id': request.form.get('perfil_id', ''),
            'celular': request.form.get('celular', '').strip() or None,
            'data_nascimento': request.form.get('data_nascimento', '').strip() or None,
            'cpf': request.form.get('cpf', '').strip() or None,
            'cep': request.form.get('cep', '').strip() or None,
            'endereco': request.form.get('endereco', '').strip() or None,
            'numero': request.form.get('numero', '').strip() or None,
            'complemento': request.form.get('complemento', '').strip() or None,
            'cidade': request.form.get('cidade', '').strip() or None,
            'estado': request.form.get('estado', '') or None,
        }

        erros = validar_usuario(dados, id_usuario)

        if erros:
            for mensagem in erros:
                flash(mensagem, 'danger')
        else:
            sql = (
                'UPDATE usuarios SET '
                'nome = %s, email = %s, celular = %s, data_nascimento = %s, cpf = %s, '
                'perfil_id = %s, cep = %s, endereco = %s, numero = %s, complemento = %s, '
                'cidade = %s, estado = %s'
            )
            params = [
                dados['nome'],
                dados['email'],
                formatar_celular(dados['celular']),
                dados['data_nascimento'],
                formatar_cpf(dados['cpf']),
                dados['perfil_id'],
                formatar_cep(dados['cep']),
                dados['endereco'],
                dados['numero'],
                dados['complemento'],
                dados['cidade'],
                dados['estado'],
            ]

            if dados['senha']:
                sql += ', senha = %s'
                params.append(generate_password_hash(dados['senha']))

            sql += ' WHERE id_usuario = %s'
            params.append(id_usuario)

            try:
                execute_query(sql, params)
                flash(f'Usuário "{dados["nome"]}" atualizado.', 'success')
                return redirect(url_for('listar_usuarios'))
            except Error as erro:
                if erro.errno == 1062:
                    flash('Já existe um usuário com este e-mail ou este CPF.', 'danger')
                else:
                    raise

    perfis = execute_query('SELECT id_perfil, nome FROM perfis ORDER BY nome', fetch=True)

    return render_template(
        'usuarios/usuario_form.html',
        acao='editar',
        id_usuario=id_usuario,
        dados=dados,
        perfis=perfis,
        ufs=UFS,
    )


@app.route('/usuarios/<int:id_usuario>/excluir', methods=['POST'])
def excluir_usuario(id_usuario):
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    if id_usuario == session['id_usuario']:
        flash('Você não pode excluir o seu próprio usuário.', 'danger')
        return redirect(url_for('listar_usuarios'))

    usuario = execute_one(
        'SELECT id_usuario, nome FROM usuarios WHERE id_usuario = %s',
        (id_usuario,),
    )

    if usuario is None:
        abort(404)

    execute_query('DELETE FROM usuarios WHERE id_usuario = %s', (id_usuario,))
    flash(f'Usuário "{usuario["nome"]}" excluído.', 'success')
    return redirect(url_for('listar_usuarios'))


# ==============================================================================
# LIVROS — telas mantidas como etapa demonstrativa até o CRUD da próxima aula
# ==============================================================================

@app.route('/livros/listar')
def listar_livros():
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))
    return render_template('livros/livros-listar.html')


@app.route('/livros/inserir')
def inserir_livro():
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))
    return render_template('livros/livros-form.html')


# ==============================================================================
# EMPRÉSTIMOS — telas mantidas como etapa demonstrativa até o CRUD da próxima aula
# ==============================================================================

@app.route('/emprestimos/listar')
def listar_emprestimos():
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))
    return render_template('emprestimos/emprestimos-listar.html')


@app.route('/emprestimos/inserir')
def inserir_emprestimo():
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))
    return render_template('emprestimos/emprestimos-form.html')


# ==============================================================================
# TELAS DE ERRO
# ==============================================================================

@app.errorhandler(404)
def pagina_nao_encontrada(erro):
    return render_template('404.html'), 404


@app.errorhandler(500)
def erro_no_servidor(erro):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True)
