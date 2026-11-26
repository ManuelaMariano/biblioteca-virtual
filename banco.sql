-- DROP DATABASE IF EXISTS bibliotecavirtual; -- use somente se quiser apagar tudo e recomeçar

CREATE DATABASE IF NOT EXISTS bibliotecavirtual
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE bibliotecavirtual;

CREATE TABLE IF NOT EXISTS perfis (
    id_perfil     BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome          VARCHAR(100) NOT NULL UNIQUE,
    descricao     VARCHAR(255),
    criado_em     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deletado_em   DATETIME NULL
);

CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome            VARCHAR(255) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    senha           VARCHAR(255) NOT NULL,
    celular         VARCHAR(20),
    data_nascimento DATE,
    cpf             VARCHAR(14) UNIQUE,
    perfil_id       BIGINT UNSIGNED NOT NULL,
    cep             VARCHAR(9),
    endereco        VARCHAR(255),
    numero          VARCHAR(20),
    complemento     VARCHAR(100),
    cidade          VARCHAR(100),
    estado          CHAR(2),
    criado_em       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em   TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deletado_em     DATETIME NULL,
    CONSTRAINT fk_usuarios_perfis
        FOREIGN KEY (perfil_id) REFERENCES perfis (id_perfil)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

-- As tabelas abaixo já ficam preparadas para o tema Biblioteca Virtual.
-- O CRUD delas pode ser desenvolvido na próxima etapa da disciplina.
CREATE TABLE IF NOT EXISTS livros (
    id_livro        BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    titulo          VARCHAR(255) NOT NULL,
    autor           VARCHAR(255) NOT NULL,
    categoria       VARCHAR(100),
    ano_publicacao  YEAR,
    quantidade      INT UNSIGNED NOT NULL DEFAULT 0,
    isbn            VARCHAR(20) UNIQUE,
    editora         VARCHAR(150),
    criado_em       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em   TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS emprestimos (
    id_emprestimo       BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    usuario_id          BIGINT UNSIGNED NOT NULL,
    livro_id            BIGINT UNSIGNED NOT NULL,
    data_emprestimo     DATE NOT NULL,
    devolucao_prevista  DATE NOT NULL,
    data_devolucao      DATE NULL,
    status              VARCHAR(30) NOT NULL DEFAULT 'Em andamento',
    observacao          VARCHAR(255),
    criado_em           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em       TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_emprestimos_usuarios
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id_usuario)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_emprestimos_livros
        FOREIGN KEY (livro_id) REFERENCES livros (id_livro)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);
