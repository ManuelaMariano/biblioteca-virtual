from datetime import datetime

from db import execute_one


def validar_emprestimo(dados, verificar_disponibilidade=True):
    erros = []

    try:
        usuario_id = int(dados.get('usuario_id', ''))
    except (ValueError, TypeError):
        usuario_id = 0

    try:
        livro_id = int(dados.get('livro_id', ''))
    except (ValueError, TypeError):
        livro_id = 0

    if usuario_id == 0:
        erros.append('Selecione um usuário.')
    else:
        usuario = execute_one(
            'SELECT id_usuario FROM usuarios WHERE id_usuario = %s',
            (usuario_id,),
        )
        if usuario is None:
            erros.append('Selecione um usuário válido.')

    if livro_id == 0:
        erros.append('Selecione um livro.')
    else:
        livro = execute_one(
            'SELECT id_livro, quantidade, ativo FROM livros WHERE id_livro = %s',
            (livro_id,),
        )
        if livro is None:
            erros.append('Selecione um livro válido.')
        elif verificar_disponibilidade:
            if not livro['ativo']:
                erros.append('O livro selecionado está inativo.')
            elif livro['quantidade'] <= 0:
                erros.append('Não há exemplar disponível deste livro.')

    data_emprestimo = dados.get('data_emprestimo')
    devolucao_prevista = dados.get('devolucao_prevista')

    try:
        data_inicio = datetime.strptime(data_emprestimo, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        data_inicio = None
        erros.append('Informe uma data de empréstimo válida.')

    try:
        data_prevista = datetime.strptime(devolucao_prevista, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        data_prevista = None
        erros.append('Informe uma data de devolução prevista válida.')

    if data_inicio and data_prevista and data_prevista < data_inicio:
        erros.append('A devolução prevista não pode ser anterior à data do empréstimo.')

    observacao = dados.get('observacao')
    if observacao and len(observacao) > 255:
        erros.append('A observação deve ter no máximo 255 caracteres.')

    return erros
