from werkzeug.utils import secure_filename

CATEGORIAS = ['Romance', 'Literatura', 'Fantasia', 'Ficção', 'Terror', 'Biografia', 'Acadêmico', 'Outros']
QUANTIDADE_MAXIMA = 1000000
EXTENSOES_CAPA = ['jpg', 'jpeg', 'png', 'webp']


def so_digitos(texto):
    resultado = ''
    for letra in texto:
        if letra in '0123456789':
            resultado = resultado + letra
    return resultado


def extensao_da_capa(nome_arquivo):
    nome_seguro = secure_filename(nome_arquivo)
    if '.' not in nome_seguro:
        return ''
    return nome_seguro.rsplit('.', 1)[1].lower()


def validar_titulo(titulo):
    if not titulo:
        return 'Informe o título do livro.'
    if len(titulo) < 2:
        return 'O título deve ter pelo menos 2 caracteres.'
    if len(titulo) > 255:
        return 'O título deve ter no máximo 255 caracteres.'
    return None


def validar_autor(autor):
    if not autor:
        return 'Informe o autor do livro.'
    if len(autor) < 3:
        return 'O autor deve ter pelo menos 3 caracteres.'
    if len(autor) > 255:
        return 'O autor deve ter no máximo 255 caracteres.'
    return None


def validar_categoria(categoria):
    if not categoria:
        return None
    if categoria not in CATEGORIAS:
        return 'Selecione uma categoria válida.'
    return None


def validar_ano_publicacao(ano):
    if not ano:
        return None
    if so_digitos(ano) != ano:
        return 'O ano de publicação deve ser um número inteiro.'
    numero = int(ano)
    if numero < 1000 or numero > 2100:
        return 'Informe um ano de publicação válido.'
    return None


def validar_quantidade(quantidade):
    if not quantidade:
        return 'Informe a quantidade.'
    if so_digitos(quantidade) != quantidade:
        return 'A quantidade deve ser um número inteiro, sem sinal nem vírgula.'
    if int(quantidade) > QUANTIDADE_MAXIMA:
        return 'A quantidade máxima é 1.000.000.'
    return None


def validar_isbn(isbn):
    if isbn and len(isbn) > 20:
        return 'O ISBN deve ter no máximo 20 caracteres.'
    return None


def validar_editora(editora):
    if editora and len(editora) > 150:
        return 'A editora deve ter no máximo 150 caracteres.'
    return None


def validar_capa(capa):
    if capa is None:
        return None
    if extensao_da_capa(capa.filename) not in EXTENSOES_CAPA:
        return 'A capa deve ser um arquivo jpg, jpeg, png ou webp.'
    return None


def validar_livro(dados, capa):
    erros = []

    erro = validar_titulo(dados['titulo'])
    if erro:
        erros.append(erro)

    erro = validar_autor(dados['autor'])
    if erro:
        erros.append(erro)

    erro = validar_categoria(dados['categoria'])
    if erro:
        erros.append(erro)

    erro = validar_ano_publicacao(dados['ano_publicacao'])
    if erro:
        erros.append(erro)

    erro = validar_quantidade(dados['quantidade'])
    if erro:
        erros.append(erro)

    erro = validar_isbn(dados['isbn'])
    if erro:
        erros.append(erro)

    erro = validar_editora(dados['editora'])
    if erro:
        erros.append(erro)

    erro = validar_capa(capa)
    if erro:
        erros.append(erro)

    return erros
