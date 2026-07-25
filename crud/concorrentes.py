from decimal import Decimal
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from database.models.concorrente import Concorrente
from database.models.preco_concorrente import PrecoConcorrente
from database.models.produto import Produto


TIPOS_CORRESPONDENCIA_VALIDOS = {
    "exato",
    "similar",
}


def normalizar_dominio(dominio: str) -> str:
    """
    Normaliza um domínio ou URL.

    Exemplos:
    https://www.exemplo.com.br/produto -> exemplo.com.br
    www.exemplo.com.br -> exemplo.com.br
    exemplo.com.br -> exemplo.com.br
    """

    valor = dominio.strip().lower()

    if not valor:
        raise ValueError(
            "O domínio do concorrente não pode estar vazio."
        )

    if "://" not in valor:
        valor = f"https://{valor}"

    dominio_extraido = urlparse(valor).netloc.lower()

    if dominio_extraido.startswith("www."):
        dominio_extraido = dominio_extraido[4:]

    dominio_extraido = dominio_extraido.split(":")[0]

    if not dominio_extraido or "." not in dominio_extraido:
        raise ValueError(
            "O domínio informado não é válido."
        )

    return dominio_extraido


def listar_concorrentes(
    sessao: Session,
    apenas_ativos: bool = True,
) -> list[Concorrente]:
    """Lista os concorrentes ordenados pelo nome."""

    consulta = select(Concorrente).order_by(
        Concorrente.nome.asc()
    )

    if apenas_ativos:
        consulta = consulta.where(
            Concorrente.ativo.is_(True)
        )

    return list(sessao.scalars(consulta).all())


def buscar_concorrente_por_id(
    sessao: Session,
    concorrente_id: int,
) -> Concorrente | None:
    """Busca um concorrente pelo ID."""

    return sessao.get(Concorrente, concorrente_id)


def buscar_concorrente_por_dominio(
    sessao: Session,
    dominio: str,
) -> Concorrente | None:
    """Busca um concorrente pelo domínio normalizado."""

    dominio_normalizado = normalizar_dominio(dominio)

    consulta = select(Concorrente).where(
        Concorrente.dominio == dominio_normalizado
    )

    return sessao.scalar(consulta)


def cadastrar_concorrente(
    sessao: Session,
    nome: str,
    dominio: str,
    ativo: bool = True,
) -> Concorrente:
    """Cadastra um novo concorrente."""

    nome_limpo = nome.strip()
    dominio_normalizado = normalizar_dominio(dominio)

    if not nome_limpo:
        raise ValueError(
            "O nome do concorrente não pode estar vazio."
        )

    concorrente_existente = buscar_concorrente_por_dominio(
        sessao=sessao,
        dominio=dominio_normalizado,
    )

    if concorrente_existente is not None:
        raise ValueError(
            "Já existe um concorrente cadastrado com o domínio "
            f"'{dominio_normalizado}'."
        )

    concorrente = Concorrente(
        nome=nome_limpo,
        dominio=dominio_normalizado,
        ativo=ativo,
    )

    sessao.add(concorrente)
    sessao.flush()
    sessao.refresh(concorrente)

    return concorrente


def obter_ou_cadastrar_concorrente(
    sessao: Session,
    nome: str,
    dominio: str,
) -> Concorrente:
    """
    Retorna um concorrente existente ou cria um novo.

    Essa função será útil posteriormente durante a coleta automática
    de preços na web.
    """

    concorrente = buscar_concorrente_por_dominio(
        sessao=sessao,
        dominio=dominio,
    )

    if concorrente is not None:
        return concorrente

    return cadastrar_concorrente(
        sessao=sessao,
        nome=nome,
        dominio=dominio,
    )


def atualizar_concorrente(
    sessao: Session,
    concorrente_id: int,
    nome: str | None = None,
    dominio: str | None = None,
    ativo: bool | None = None,
) -> Concorrente:
    """Atualiza os dados de um concorrente."""

    concorrente = buscar_concorrente_por_id(
        sessao=sessao,
        concorrente_id=concorrente_id,
    )

    if concorrente is None:
        raise ValueError(
            f"Concorrente com ID {concorrente_id} não encontrado."
        )

    if nome is not None:
        nome_limpo = nome.strip()

        if not nome_limpo:
            raise ValueError(
                "O nome do concorrente não pode estar vazio."
            )

        concorrente.nome = nome_limpo

    if dominio is not None:
        dominio_normalizado = normalizar_dominio(dominio)

        concorrente_mesmo_dominio = (
            buscar_concorrente_por_dominio(
                sessao=sessao,
                dominio=dominio_normalizado,
            )
        )

        if (
            concorrente_mesmo_dominio is not None
            and concorrente_mesmo_dominio.id != concorrente.id
        ):
            raise ValueError(
                "Já existe outro concorrente cadastrado com o "
                f"domínio '{dominio_normalizado}'."
            )

        concorrente.dominio = dominio_normalizado

    if ativo is not None:
        concorrente.ativo = ativo

    sessao.flush()
    sessao.refresh(concorrente)

    return concorrente


def desativar_concorrente(
    sessao: Session,
    concorrente_id: int,
) -> Concorrente:
    """Desativa um concorrente sem apagar seus preços históricos."""

    concorrente = buscar_concorrente_por_id(
        sessao=sessao,
        concorrente_id=concorrente_id,
    )

    if concorrente is None:
        raise ValueError(
            f"Concorrente com ID {concorrente_id} não encontrado."
        )

    concorrente.ativo = False

    sessao.flush()
    sessao.refresh(concorrente)

    return concorrente


def reativar_concorrente(
    sessao: Session,
    concorrente_id: int,
) -> Concorrente:
    """Reativa um concorrente."""

    concorrente = buscar_concorrente_por_id(
        sessao=sessao,
        concorrente_id=concorrente_id,
    )

    if concorrente is None:
        raise ValueError(
            f"Concorrente com ID {concorrente_id} não encontrado."
        )

    concorrente.ativo = True

    sessao.flush()
    sessao.refresh(concorrente)

    return concorrente


def registrar_preco_concorrente(
    sessao: Session,
    produto_id: int,
    concorrente_id: int,
    nome_produto_encontrado: str,
    preco: Decimal,
    url: str,
    similaridade: Decimal,
    tipo_correspondencia: str,
    moeda: str = "BRL",
    disponivel: bool = True,
) -> PrecoConcorrente:
    """Registra uma oferta encontrada em um site concorrente."""

    produto = sessao.get(Produto, produto_id)

    if produto is None:
        raise ValueError(
            f"Produto com ID {produto_id} não encontrado."
        )

    concorrente = sessao.get(
        Concorrente,
        concorrente_id,
    )

    if concorrente is None:
        raise ValueError(
            f"Concorrente com ID {concorrente_id} não encontrado."
        )

    if not concorrente.ativo:
        raise ValueError(
            f"O concorrente '{concorrente.nome}' está desativado."
        )

    nome_limpo = nome_produto_encontrado.strip()

    if not nome_limpo:
        raise ValueError(
            "O nome do produto encontrado não pode estar vazio."
        )

    preco_decimal = Decimal(str(preco))

    if preco_decimal <= 0:
        raise ValueError(
            "O preço encontrado deve ser maior que zero."
        )

    url_limpa = url.strip()

    if not url_limpa:
        raise ValueError(
            "A URL da oferta não pode estar vazia."
        )

    url_analisada = urlparse(url_limpa)

    if (
        url_analisada.scheme not in {"http", "https"}
        or not url_analisada.netloc
    ):
        raise ValueError(
            "A URL da oferta deve começar com http:// ou https://."
        )

    similaridade_decimal = Decimal(str(similaridade))

    if (
        similaridade_decimal < 0
        or similaridade_decimal > 1
    ):
        raise ValueError(
            "A similaridade deve estar entre 0 e 1."
        )

    tipo_limpo = tipo_correspondencia.strip().lower()

    if tipo_limpo not in TIPOS_CORRESPONDENCIA_VALIDOS:
        raise ValueError(
            "Tipo de correspondência inválido. "
            "Valores permitidos: exato ou similar."
        )

    moeda_limpa = moeda.strip().upper()

    if len(moeda_limpa) != 3:
        raise ValueError(
            "A moeda deve ser informada com uma sigla de 3 letras."
        )

    preco_concorrente = PrecoConcorrente(
        produto_id=produto_id,
        concorrente_id=concorrente_id,
        nome_produto_encontrado=nome_limpo,
        preco=preco_decimal,
        moeda=moeda_limpa,
        url=url_limpa,
        similaridade=similaridade_decimal,
        tipo_correspondencia=tipo_limpo,
        disponivel=disponivel,
    )

    sessao.add(preco_concorrente)
    sessao.flush()
    sessao.refresh(preco_concorrente)

    return preco_concorrente


def buscar_preco_concorrente_por_id(
    sessao: Session,
    preco_concorrente_id: int,
) -> PrecoConcorrente | None:
    """Busca um preço de concorrente pelo ID."""

    consulta = (
        select(PrecoConcorrente)
        .options(
            joinedload(PrecoConcorrente.produto),
            joinedload(PrecoConcorrente.concorrente),
        )
        .where(
            PrecoConcorrente.id == preco_concorrente_id
        )
    )

    return sessao.scalar(consulta)


def listar_precos_concorrentes(
    sessao: Session,
    produto_id: int | None = None,
    concorrente_id: int | None = None,
    apenas_disponiveis: bool = True,
    tipo_correspondencia: str | None = None,
) -> list[PrecoConcorrente]:
    """Lista preços coletados com filtros opcionais."""

    consulta = (
        select(PrecoConcorrente)
        .options(
            joinedload(PrecoConcorrente.produto),
            joinedload(PrecoConcorrente.concorrente),
        )
        .order_by(
            PrecoConcorrente.coletado_em.desc(),
            PrecoConcorrente.id.desc(),
        )
    )

    if produto_id is not None:
        consulta = consulta.where(
            PrecoConcorrente.produto_id == produto_id
        )

    if concorrente_id is not None:
        consulta = consulta.where(
            PrecoConcorrente.concorrente_id
            == concorrente_id
        )

    if apenas_disponiveis:
        consulta = consulta.where(
            PrecoConcorrente.disponivel.is_(True)
        )

    if tipo_correspondencia is not None:
        tipo_limpo = tipo_correspondencia.strip().lower()

        if tipo_limpo not in TIPOS_CORRESPONDENCIA_VALIDOS:
            raise ValueError(
                "Tipo de correspondência inválido. "
                "Valores permitidos: exato ou similar."
            )

        consulta = consulta.where(
            PrecoConcorrente.tipo_correspondencia
            == tipo_limpo
        )

    return list(sessao.scalars(consulta).all())


def listar_precos_por_produto(
    sessao: Session,
    produto_id: int,
    apenas_disponiveis: bool = True,
) -> list[PrecoConcorrente]:
    """Lista as ofertas encontradas para um produto."""

    produto = sessao.get(Produto, produto_id)

    if produto is None:
        raise ValueError(
            f"Produto com ID {produto_id} não encontrado."
        )

    consulta = (
        select(PrecoConcorrente)
        .options(
            joinedload(PrecoConcorrente.produto),
            joinedload(PrecoConcorrente.concorrente),
        )
        .where(
            PrecoConcorrente.produto_id == produto_id
        )
        .order_by(
            PrecoConcorrente.preco.asc(),
            PrecoConcorrente.coletado_em.desc(),
        )
    )

    if apenas_disponiveis:
        consulta = consulta.where(
            PrecoConcorrente.disponivel.is_(True)
        )

    return list(sessao.scalars(consulta).all())


def buscar_menor_preco_concorrente(
    sessao: Session,
    produto_id: int,
    apenas_correspondencia_exata: bool = False,
) -> PrecoConcorrente | None:
    """Busca a oferta disponível de menor preço para um produto."""

    consulta = (
        select(PrecoConcorrente)
        .options(
            joinedload(PrecoConcorrente.produto),
            joinedload(PrecoConcorrente.concorrente),
        )
        .where(
            PrecoConcorrente.produto_id == produto_id,
            PrecoConcorrente.disponivel.is_(True),
        )
        .order_by(
            PrecoConcorrente.preco.asc(),
            PrecoConcorrente.similaridade.desc(),
            PrecoConcorrente.coletado_em.desc(),
        )
        .limit(1)
    )

    if apenas_correspondencia_exata:
        consulta = consulta.where(
            PrecoConcorrente.tipo_correspondencia == "exato"
        )

    return sessao.scalar(consulta)


def marcar_preco_indisponivel(
    sessao: Session,
    preco_concorrente_id: int,
) -> PrecoConcorrente:
    """Marca uma oferta coletada como indisponível."""

    preco_concorrente = buscar_preco_concorrente_por_id(
        sessao=sessao,
        preco_concorrente_id=preco_concorrente_id,
    )

    if preco_concorrente is None:
        raise ValueError(
            "Preço de concorrente com ID "
            f"{preco_concorrente_id} não encontrado."
        )

    preco_concorrente.disponivel = False

    sessao.flush()
    sessao.refresh(preco_concorrente)

    return preco_concorrente


def marcar_preco_disponivel(
    sessao: Session,
    preco_concorrente_id: int,
) -> PrecoConcorrente:
    """Marca novamente uma oferta como disponível."""

    preco_concorrente = buscar_preco_concorrente_por_id(
        sessao=sessao,
        preco_concorrente_id=preco_concorrente_id,
    )

    if preco_concorrente is None:
        raise ValueError(
            "Preço de concorrente com ID "
            f"{preco_concorrente_id} não encontrado."
        )

    preco_concorrente.disponivel = True

    sessao.flush()
    sessao.refresh(preco_concorrente)

    return preco_concorrente