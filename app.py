import os
import uuid

from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash

from db import execute_insert, execute_one, execute_query
from validacoes.validacoes_emprestimo import validar_emprestimo
from validacoes.validacoes_livro import CATEGORIAS, extensao_da_capa, validar_livro
from validacoes.validacoes_perfil import validar_perfil
from validacoes.validacoes_usuario import UFS, formatar_cep, formatar_celular, formatar_cpf, validar_usuario

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Liga a proteção CSRF: todo formulário POST do sistema vai precisar do token
CSRFProtect(app)

# As capas dos livros ficam em static/uploads. O Flask recusa (erro 413) pedidos com mais de 2 MB.
PASTA_UPLOADS = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

os.makedirs(PASTA_UPLOADS, exist_ok=True)

# As colunas que as telas de usuário leem. A senha fica de fora de propósito.
SELECT_USUARIO = (
    'SELECT u.id_usuario, u.nome, u.email, u.celular, u.data_nascimento, u.cpf, '
    'u.perfil_id, u.cep, u.endereco, u.numero, u.complemento, u.cidade, u.estado, '
    'u.criado_em, u.atualizado_em, p.nome AS perfil, p.descricao AS perfil_descricao '
    'FROM usuarios u '
    'JOIN perfis p ON p.id_perfil = u.perfil_id'
)

# As colunas que as telas de livro leem.
SELECT_LIVRO = (
    'SELECT id_livro, titulo, autor, categoria, ano_publicacao, quantidade, isbn, editora, '
    'capa, ativo, criado_em, atualizado_em '
    'FROM livros'
)

# As colunas que as telas de empréstimo leem.
SELECT_EMPRESTIMO = (
    'SELECT e.id_emprestimo, e.usuario_id, e.livro_id, e.data_emprestimo, '
    'e.devolucao_prevista, e.data_devolucao, e.status, e.observacao, e.criado_em, '
    'u.nome AS usuario, l.titulo AS livro '
    'FROM emprestimos e '
    'JOIN usuarios u ON u.id_usuario = e.usuario_id '
    'JOIN livros l ON l.id_livro = e.livro_id'
)


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
# PÁGINAS PRINCIPAIS
# ==============================================================================

@app.route('/')
def index():
    # A raiz não mostra nada: só leva para a tela de login
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Quem já entrou não precisa ver a tela de login
    if 'id_usuario' in session:
        return redirect(url_for('dashboard'))

    email = ''

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')

        # Só o login lê a coluna senha (o hash)
        usuario = execute_one(
            'SELECT u.id_usuario, u.nome, u.senha, p.nome AS perfil '
            'FROM usuarios u '
            'JOIN perfis p ON p.id_perfil = u.perfil_id '
            'WHERE u.email = %s',
            (email,),
        )

        if usuario is not None and check_password_hash(usuario['senha'], senha):
            # Guarda na session quem entrou (o cookie assinado pela secret_key)
            session.clear()
            session['id_usuario'] = usuario['id_usuario']
            session['nome'] = usuario['nome']
            session['perfil'] = usuario['perfil']
            flash(f'Você entrou como {usuario["nome"]}.', 'success')
            return redirect(url_for('dashboard'))

        # A mesma mensagem para e-mail inexistente e senha errada
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
        flash('Entre para continuar.', 'danger')
        return redirect(url_for('login'))

    # Conta as linhas de cada tabela para os cartões da Home
    perfis = execute_one('SELECT COUNT(*) AS total FROM perfis')
    usuarios = execute_one('SELECT COUNT(*) AS total FROM usuarios')
    livros = execute_one('SELECT COUNT(*) AS total FROM livros')
    emprestimos = execute_one(
        "SELECT COUNT(*) AS total FROM emprestimos WHERE status = 'Em andamento'"
    )

    return render_template('dashboard.html', titulo='Biblioteca Virtual',
                           total_perfis=perfis['total'],
                           total_usuarios=usuarios['total'],
                           total_livros=livros['total'],
                           total_emprestimos=emprestimos['total'])


# ==============================================================================
# PERFIS
# ==============================================================================

@app.route('/perfis')
def listar_perfis():
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'danger')
        return redirect(url_for('login'))

    # Busca a lista de perfis na tabela do banco
    perfis = execute_query(
        'SELECT id_perfil, nome, descricao, criado_em FROM perfis ORDER BY nome',
        fetch=True,
    )

    return render_template('perfis/perfis_lista.html', titulo='Perfis', perfis=perfis)


@app.route('/perfis/inserir', methods=['GET', 'POST'])
def inserir_perfil():
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'danger')
        return redirect(url_for('login'))

    # Inicializa variáveis para cada campo do formulário
    nome = ''
    descricao = ''

    # Executado apenas no envio do formulário (POST)
    if request.method == 'POST':
        # 1. Coleta os dados do formulário
        nome = request.form.get('nome', '').strip()

        # 'or None' garante que string vazia vire None (gravado como NULL no MySQL)
        descricao = request.form.get('descricao', '').strip() or None

        # -------------------------------------------------------------------------
        # 2. Validação dos campos
        erros = validar_perfil(nome, descricao)

        # 3. Se houver erros, exibe as mensagens
        if erros:
            for mensagem in erros:
                flash(mensagem, 'danger')

        # -------------------------------------------------------------------------
        # 4. Se não houver erros, tenta salvar no banco
        else:
            try:
                novo_id = execute_insert(
                    'INSERT INTO perfis (nome, descricao) VALUES (%s, %s)',
                    (nome, descricao),
                )

                flash(f'Perfil "{nome}" cadastrado (código {novo_id}).', 'success')
                return redirect(url_for('listar_perfis'))

            # Trata concorrência (duplicidade no momento do insert)
            except Error as erro:
                if erro.errno == 1062:
                    flash('Já existe um perfil com este nome.', 'danger')
                else:
                    # Com o raise: Se o MySQL cair, o cabo de rede desconectar ou houver um erro de
                    # sintaxe no SQL, o Python interrompe a execução imediatamente e mostra o
                    # Traceback com o erro real no console/log.
                    raise

    # Exibe a tela em caso de GET ou se houver erros (de validação ou de nome repetido)
    return render_template('perfis/perfil_form.html', acao='criar', id_perfil=None,
                           nome=nome, descricao=descricao)


@app.route('/perfis/<int:id_perfil>/editar', methods=['GET', 'POST'])
def editar_perfil(id_perfil):
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'danger')
        return redirect(url_for('login'))

    # Busca o perfil pelo código que veio no endereço
    perfil = execute_one(
        'SELECT id_perfil, nome, descricao FROM perfis WHERE id_perfil = %s',
        (id_perfil,),
    )

    # Código que não existe: mostra a página 404
    if perfil is None:
        abort(404)

    # O formulário começa com os valores que estão no banco
    nome = perfil['nome']
    descricao = perfil['descricao']

    # Executado apenas no envio do formulário (POST)
    if request.method == 'POST':
        # 1. Coleta os dados do formulário
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip() or None

        # -------------------------------------------------------------------------
        # 2. Validação dos campos (o id_perfil faz o próprio perfil não contar como repetido)
        erros = validar_perfil(nome, descricao, id_perfil)

        # 3. Se houver erros, exibe as mensagens
        if erros:
            for mensagem in erros:
                flash(mensagem, 'danger')

        # -------------------------------------------------------------------------
        # 4. Se não houver erros, tenta salvar no banco
        else:
            try:
                # O WHERE garante que só este perfil seja alterado
                execute_query(
                    'UPDATE perfis SET '
                    '    nome = %s, '
                    '    descricao = %s '
                    'WHERE id_perfil = %s',
                    (nome, descricao, id_perfil),
                )

                flash(f'Perfil "{nome}" atualizado.', 'success')
                return redirect(url_for('listar_perfis'))

            # Trata concorrência (duplicidade no momento do update)
            except Error as erro:
                if erro.errno == 1062:
                    flash('Já existe um perfil com este nome.', 'danger')
                else:
                    raise

    # Exibe a tela em caso de GET ou se houver erros (de validação ou de nome repetido)
    return render_template('perfis/perfil_form.html', acao='editar', id_perfil=id_perfil,
                           nome=nome, descricao=descricao)


@app.route('/perfis/<int:id_perfil>/excluir', methods=['POST'])
def excluir_perfil(id_perfil):
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'danger')
        return redirect(url_for('login'))

    # Busca o perfil: confirma que ele existe e traz o nome para a mensagem
    perfil = execute_one(
        'SELECT id_perfil, nome FROM perfis WHERE id_perfil = %s',
        (id_perfil,),
    )

    # Código que não existe: mostra a página 404
    if perfil is None:
        abort(404)

    # Conta os usuários do perfil: um perfil em uso não pode ser excluído
    usuarios = execute_one(
        'SELECT COUNT(*) AS total FROM usuarios WHERE perfil_id = %s',
        (id_perfil,),
    )

    if usuarios['total'] > 0:
        flash(f'O perfil "{perfil["nome"]}" tem {usuarios["total"]} usuário(s) e não pode ser excluído.', 'danger')
        return redirect(url_for('listar_perfis'))

    try:
        # O WHERE garante que só este perfil seja excluído
        execute_query('DELETE FROM perfis WHERE id_perfil = %s', (id_perfil,))
        flash(f'Perfil "{perfil["nome"]}" excluído.', 'success')

    # Trata concorrência (um usuário cadastrado no perfil entre a contagem e o DELETE)
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
def listar_usuarios():
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    # O SELECT_USUARIO já traz o nome do perfil, pelo JOIN
    usuarios = execute_query(SELECT_USUARIO + ' ORDER BY u.nome', fetch=True)

    return render_template('usuarios/usuarios_lista.html', titulo='Usuários', usuarios=usuarios)


@app.route('/usuarios/inserir', methods=['GET', 'POST'])
def inserir_usuario():
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    # Com muitos campos, o formulário inteiro fica em um dicionário (vazio no GET)
    dados = {}

    if request.method == 'POST':
        # 1. Coleta os dados do formulário (os opcionais com 'or None')
        dados = {
            'nome': request.form.get('nome', '').strip(),
            'email': request.form.get('email', '').strip().lower(),
            'senha': request.form.get('senha', ''),  # a senha não leva strip: espaço pode fazer parte dela
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

        # 2. A validação recebe o dicionário inteiro
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
                        generate_password_hash(dados['senha']),  # grava o hash, nunca a senha
                        formatar_celular(dados['celular']),      # celular, CPF e CEP vão formatados
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

            # Duas colunas UNIQUE: o 1062 pode ser do e-mail ou do CPF
            except Error as erro:
                if erro.errno == 1062:
                    flash('Já existe um usuário com este e-mail ou este CPF.', 'danger')
                else:
                    raise

    # As opções do <select> de perfil vêm da tabela perfis
    perfis = execute_query('SELECT id_perfil, nome FROM perfis ORDER BY nome', fetch=True)

    return render_template('usuarios/usuario_form.html', acao='criar', id_usuario=None,
                           dados=dados, perfis=perfis, ufs=UFS)


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

    # No GET, o formulário começa com a linha que veio do banco
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

        # O id_usuario faz o próprio usuário não contar como repetido e torna a senha opcional
        erros = validar_usuario(dados, id_usuario)

        if erros:
            for mensagem in erros:
                flash(mensagem, 'danger')
        else:
            # O UPDATE é montado em partes: a senha só entra se uma nova foi digitada
            sql = (
                'UPDATE usuarios SET '
                '    nome = %s, '
                '    email = %s, '
                '    celular = %s, '
                '    data_nascimento = %s, '
                '    cpf = %s, '
                '    perfil_id = %s, '
                '    cep = %s, '
                '    endereco = %s, '
                '    numero = %s, '
                '    complemento = %s, '
                '    cidade = %s, '
                '    estado = %s'
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

    return render_template('usuarios/usuario_form.html', acao='editar', id_usuario=id_usuario,
                           dados=dados, perfis=perfis, ufs=UFS)


@app.route('/usuarios/<int:id_usuario>/excluir', methods=['POST'])
def excluir_usuario(id_usuario):
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    # Quem está logado não pode excluir a si mesmo
    if id_usuario == session['id_usuario']:
        flash('Você não pode excluir o seu próprio usuário.', 'danger')
        return redirect(url_for('listar_usuarios'))

    usuario = execute_one(
        'SELECT id_usuario, nome FROM usuarios WHERE id_usuario = %s',
        (id_usuario,),
    )

    if usuario is None:
        abort(404)

    # Nenhuma tabela depende de usuarios: não há contagem nem erro 1451
    try:
        execute_query('DELETE FROM usuarios WHERE id_usuario = %s', (id_usuario,))
        flash(f'Usuário "{usuario["nome"]}" excluído.', 'success')
    except Error as erro:
        if erro.errno == 1451:
            flash('Este usuário possui empréstimos registrados e não pode ser excluído.', 'danger')
        else:
            raise

    return redirect(url_for('listar_usuarios'))


# ==============================================================================
# LIVROS
# ==============================================================================

@app.route('/livros')
def listar_livros():
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    livros = execute_query(SELECT_LIVRO + ' ORDER BY titulo', fetch=True)
    return render_template('livros/livros_lista.html', titulo='Livros', livros=livros)


def salvar_capa(capa):
    # O arquivo ganha um nome novo e único; o banco guarda o caminho relativo à pasta static.
    nome_arquivo = uuid.uuid4().hex + '.' + extensao_da_capa(capa.filename)
    capa.save(os.path.join(PASTA_UPLOADS, nome_arquivo))
    return 'uploads/' + nome_arquivo


def apagar_capa(caminho):
    if caminho is None:
        return

    arquivo = os.path.join(app.root_path, 'static', caminho)
    if os.path.exists(arquivo):
        os.remove(arquivo)


@app.route('/livros/inserir', methods=['GET', 'POST'])
def inserir_livro():
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    dados = {'quantidade': 0, 'ativo': 1}

    if request.method == 'POST':
        dados = {
            'titulo': request.form.get('titulo', '').strip(),
            'autor': request.form.get('autor', '').strip(),
            'categoria': request.form.get('categoria', '') or None,
            'ano_publicacao': request.form.get('ano_publicacao', '').strip() or None,
            'quantidade': request.form.get('quantidade', '').strip(),
            'isbn': request.form.get('isbn', '').strip() or None,
            'editora': request.form.get('editora', '').strip() or None,
        }

        if request.form.get('ativo') == '1':
            dados['ativo'] = 1
        else:
            dados['ativo'] = 0

        capa = request.files.get('capa')
        if capa is not None and capa.filename == '':
            capa = None

        erros = validar_livro(dados, capa)

        if erros:
            for mensagem in erros:
                flash(mensagem, 'danger')
        else:
            caminho_capa = None
            if capa is not None:
                caminho_capa = salvar_capa(capa)

            try:
                novo_id = execute_insert(
                    'INSERT INTO livros (titulo, autor, categoria, ano_publicacao, quantidade, isbn, editora, capa, ativo) '
                    'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
                    (
                        dados['titulo'],
                        dados['autor'],
                        dados['categoria'],
                        dados['ano_publicacao'],
                        int(dados['quantidade']),
                        dados['isbn'],
                        dados['editora'],
                        caminho_capa,
                        dados['ativo'],
                    ),
                )
                flash(f'Livro "{dados["titulo"]}" cadastrado (código {novo_id}).', 'success')
                return redirect(url_for('listar_livros'))
            except Error as erro:
                if caminho_capa is not None:
                    apagar_capa(caminho_capa)
                if erro.errno == 1062:
                    flash('Já existe um livro com este ISBN.', 'danger')
                else:
                    raise

    return render_template(
        'livros/livro_form.html',
        acao='criar',
        id_livro=None,
        dados=dados,
        categorias=CATEGORIAS,
        capa_atual=None,
    )


@app.route('/livros/<int:id_livro>/editar', methods=['GET', 'POST'])
def editar_livro(id_livro):
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    livro = execute_one(SELECT_LIVRO + ' WHERE id_livro = %s', (id_livro,))

    if livro is None:
        abort(404)

    dados = livro

    if request.method == 'POST':
        dados = {
            'titulo': request.form.get('titulo', '').strip(),
            'autor': request.form.get('autor', '').strip(),
            'categoria': request.form.get('categoria', '') or None,
            'ano_publicacao': request.form.get('ano_publicacao', '').strip() or None,
            'quantidade': request.form.get('quantidade', '').strip(),
            'isbn': request.form.get('isbn', '').strip() or None,
            'editora': request.form.get('editora', '').strip() or None,
        }

        if request.form.get('ativo') == '1':
            dados['ativo'] = 1
        else:
            dados['ativo'] = 0

        capa = request.files.get('capa')
        if capa is not None and capa.filename == '':
            capa = None

        erros = validar_livro(dados, capa)

        if erros:
            for mensagem in erros:
                flash(mensagem, 'danger')
        else:
            sql = (
                'UPDATE livros SET '
                'titulo = %s, autor = %s, categoria = %s, ano_publicacao = %s, '
                'quantidade = %s, isbn = %s, editora = %s, ativo = %s'
            )
            params = [
                dados['titulo'],
                dados['autor'],
                dados['categoria'],
                dados['ano_publicacao'],
                int(dados['quantidade']),
                dados['isbn'],
                dados['editora'],
                dados['ativo'],
            ]

            trocou_capa = False
            nova_capa = None
            if capa is not None:
                nova_capa = salvar_capa(capa)
                sql += ', capa = %s'
                params.append(nova_capa)
                trocou_capa = True
            elif request.form.get('remover_capa') == '1':
                sql += ', capa = %s'
                params.append(None)
                trocou_capa = True

            sql += ' WHERE id_livro = %s'
            params.append(id_livro)

            try:
                execute_query(sql, params)
                if trocou_capa:
                    apagar_capa(livro['capa'])
                flash(f'Livro "{dados["titulo"]}" atualizado.', 'success')
                return redirect(url_for('listar_livros'))
            except Error as erro:
                if nova_capa is not None:
                    apagar_capa(nova_capa)
                if erro.errno == 1062:
                    flash('Já existe um livro com este ISBN.', 'danger')
                else:
                    raise

    return render_template(
        'livros/livro_form.html',
        acao='editar',
        id_livro=id_livro,
        dados=dados,
        categorias=CATEGORIAS,
        capa_atual=livro['capa'],
    )


@app.route('/livros/<int:id_livro>/excluir', methods=['POST'])
def excluir_livro(id_livro):
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    livro = execute_one(
        'SELECT id_livro, titulo, capa FROM livros WHERE id_livro = %s',
        (id_livro,),
    )

    if livro is None:
        abort(404)

    try:
        execute_query('DELETE FROM livros WHERE id_livro = %s', (id_livro,))
        apagar_capa(livro['capa'])
        flash(f'Livro "{livro["titulo"]}" excluído.', 'success')
    except Error as erro:
        if erro.errno == 1451:
            flash('Este livro possui empréstimos registrados e não pode ser excluído.', 'danger')
        else:
            raise

    return redirect(url_for('listar_livros'))


# ============================================================================== 
# EMPRÉSTIMOS
# ============================================================================== 

@app.route('/emprestimos')
def listar_emprestimos():
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    emprestimos = execute_query(
        SELECT_EMPRESTIMO + ' ORDER BY e.id_emprestimo DESC',
        fetch=True,
    )

    return render_template(
        'emprestimos/emprestimos_lista.html',
        titulo='Empréstimos',
        emprestimos=emprestimos,
    )


@app.route('/emprestimos/inserir', methods=['GET', 'POST'])
def inserir_emprestimo():
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    dados = {}

    if request.method == 'POST':
        dados = {
            'usuario_id': request.form.get('usuario_id', ''),
            'livro_id': request.form.get('livro_id', ''),
            'data_emprestimo': request.form.get('data_emprestimo', ''),
            'devolucao_prevista': request.form.get('devolucao_prevista', ''),
            'observacao': request.form.get('observacao', '').strip() or None,
        }

        erros = validar_emprestimo(dados)

        if erros:
            for mensagem in erros:
                flash(mensagem, 'danger')
        else:
            novo_id = execute_insert(
                'INSERT INTO emprestimos '
                '(usuario_id, livro_id, data_emprestimo, devolucao_prevista, status, observacao) '
                "VALUES (%s, %s, %s, %s, 'Em andamento', %s)",
                (
                    dados['usuario_id'],
                    dados['livro_id'],
                    dados['data_emprestimo'],
                    dados['devolucao_prevista'],
                    dados['observacao'],
                ),
            )

            execute_query(
                'UPDATE livros SET quantidade = quantidade - 1 WHERE id_livro = %s',
                (dados['livro_id'],),
            )

            flash(f'Empréstimo cadastrado (código {novo_id}).', 'success')
            return redirect(url_for('listar_emprestimos'))

    usuarios = execute_query(
        'SELECT id_usuario, nome FROM usuarios ORDER BY nome',
        fetch=True,
    )
    livros = execute_query(
        'SELECT id_livro, titulo, quantidade FROM livros '
        'WHERE ativo = 1 AND quantidade > 0 ORDER BY titulo',
        fetch=True,
    )

    return render_template(
        'emprestimos/emprestimo_form.html',
        acao='criar',
        id_emprestimo=None,
        dados=dados,
        usuarios=usuarios,
        livros=livros,
        livro_atual=None,
    )


@app.route('/emprestimos/<int:id_emprestimo>/editar', methods=['GET', 'POST'])
def editar_emprestimo(id_emprestimo):
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    emprestimo = execute_one(
        SELECT_EMPRESTIMO + ' WHERE e.id_emprestimo = %s',
        (id_emprestimo,),
    )

    if emprestimo is None:
        abort(404)

    dados = emprestimo

    if request.method == 'POST':
        dados = {
            'usuario_id': request.form.get('usuario_id', ''),
            'livro_id': emprestimo['livro_id'],
            'data_emprestimo': request.form.get('data_emprestimo', ''),
            'devolucao_prevista': request.form.get('devolucao_prevista', ''),
            'observacao': request.form.get('observacao', '').strip() or None,
        }

        erros = validar_emprestimo(dados, verificar_disponibilidade=False)

        if erros:
            for mensagem in erros:
                flash(mensagem, 'danger')
        else:
            execute_query(
                'UPDATE emprestimos SET '
                'usuario_id = %s, data_emprestimo = %s, devolucao_prevista = %s, observacao = %s '
                'WHERE id_emprestimo = %s',
                (
                    dados['usuario_id'],
                    dados['data_emprestimo'],
                    dados['devolucao_prevista'],
                    dados['observacao'],
                    id_emprestimo,
                ),
            )

            flash('Empréstimo atualizado.', 'success')
            return redirect(url_for('listar_emprestimos'))

    usuarios = execute_query(
        'SELECT id_usuario, nome FROM usuarios ORDER BY nome',
        fetch=True,
    )

    return render_template(
        'emprestimos/emprestimo_form.html',
        acao='editar',
        id_emprestimo=id_emprestimo,
        dados=dados,
        usuarios=usuarios,
        livros=[],
        livro_atual=emprestimo,
    )


@app.route('/emprestimos/<int:id_emprestimo>/devolver', methods=['POST'])
def devolver_emprestimo(id_emprestimo):
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    emprestimo = execute_one(
        'SELECT id_emprestimo, livro_id, status FROM emprestimos WHERE id_emprestimo = %s',
        (id_emprestimo,),
    )

    if emprestimo is None:
        abort(404)

    if emprestimo['status'] == 'Devolvido':
        flash('Este empréstimo já foi devolvido.', 'warning')
        return redirect(url_for('listar_emprestimos'))

    execute_query(
        "UPDATE emprestimos SET status = 'Devolvido', data_devolucao = CURDATE() "
        'WHERE id_emprestimo = %s',
        (id_emprestimo,),
    )
    execute_query(
        'UPDATE livros SET quantidade = quantidade + 1 WHERE id_livro = %s',
        (emprestimo['livro_id'],),
    )

    flash('Devolução registrada com sucesso.', 'success')
    return redirect(url_for('listar_emprestimos'))


@app.route('/emprestimos/<int:id_emprestimo>/excluir', methods=['POST'])
def excluir_emprestimo(id_emprestimo):
    if 'id_usuario' not in session:
        flash('Entre para continuar.', 'warning')
        return redirect(url_for('login'))

    emprestimo = execute_one(
        'SELECT id_emprestimo, livro_id, status FROM emprestimos WHERE id_emprestimo = %s',
        (id_emprestimo,),
    )

    if emprestimo is None:
        abort(404)

    if emprestimo['status'] == 'Em andamento':
        execute_query(
            'UPDATE livros SET quantidade = quantidade + 1 WHERE id_livro = %s',
            (emprestimo['livro_id'],),
        )

    execute_query('DELETE FROM emprestimos WHERE id_emprestimo = %s', (id_emprestimo,))
    flash('Empréstimo excluído.', 'success')

    return redirect(url_for('listar_emprestimos'))


# ==============================================================================
# TELAS DE ERROS
# ==============================================================================

@app.errorhandler(404)
def pagina_nao_encontrada(erro):
    return render_template('404.html'), 404


@app.errorhandler(413)
def arquivo_grande_demais(erro):
    return render_template('413.html'), 413


@app.errorhandler(500)
def erro_no_servidor(erro):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True)
