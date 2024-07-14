from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, Body, HTTPException, Query, status
from pydantic import UUID4
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from fastapi_pagination import Page, paginate

from workout_api.atleta.models import AtletaModel
from workout_api.atleta.schemas import AtletaIn, AtletaOut, AtletaUpdate
from workout_api.categorias.models import CategoriaModel
from workout_api.centro_treinamento.models import CentroTreinamentoModel
from workout_api.contrib.dependencies import DatabaseDependency


router = APIRouter()

@router.post(
    '/',
    summary='Criar novo atleta',
    status_code=status.HTTP_201_CREATED,
    response_model=AtletaOut
)
async def post(
    db_session: DatabaseDependency,
    atleta_in: AtletaIn = Body(...)
):
    categoria_nome = atleta_in.categoria.nome
    centro_treinamento_nome = atleta_in.centro_treinamento.nome


    categoria = (await db_session.execute(select(CategoriaModel).filter_by(nome=categoria_nome))).scalars().first()

    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'A categoria {categoria_nome} não foi encontrada'
        )
    
    centro_treinamento = (await db_session.execute(select(CentroTreinamentoModel).filter_by(nome=centro_treinamento_nome))).scalars().first()

    if not centro_treinamento:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'O centro de treinamento {centro_treinamento_nome} não foi encontrado'
        )
    
    try:
        atleta_out = AtletaOut(id=uuid4(), created_at=datetime.utcnow(), **atleta_in.model_dump())
        atleta_model = AtletaModel(**atleta_out.model_dump(exclude={'categoria', 'centro_treinamento'}))
        atleta_model.categoria_id = categoria.pk_id
        atleta_model.centro_treinamento_id = centro_treinamento.pk_id

        db_session.add(atleta_model)
        await db_session.commit()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail=f'Já existe um atleta cadastrado com o CPF: {atleta_in.cpf}'
        )

    return atleta_out


@router.get(
    '/',
    summary='Consultar todos os atletas',
    status_code=status.HTTP_200_OK,
    response_model=Page[AtletaOut]
)
async def query(
    db_session: DatabaseDependency,
    nome: str = Query(None),
    cpf: str = Query(None),
    limit: int = Query(2, description='Número máximo de itens por página'),
    offset: int = Query(0, description='Número de itens para pular')
):
    query = select(AtletaModel)

    if nome:
        query = query.where(AtletaModel.nome == nome)

    if cpf:
        query = query.where(AtletaModel.cpf == cpf)

    atletas = (await db_session.execute(query)).scalars().all()
    
    return paginate(atletas)


@router.get(
    '/formatted',
    summary='Consultar todos os atletas com dados formatados',
    status_code=status.HTTP_200_OK,
    response_model=list[dict],
)
async def get_formatted_atletas(db_session: DatabaseDependency) -> list[dict]:
    query = select(AtletaModel)
    atletas = await db_session.execute(query)
    atletas_dicts = []

    for atleta in atletas.scalars():
        atleta_dict = {
            "nome": atleta.nome,
            "centro_treinamento": {
                "nome": atleta.centro_treinamento.nome
            },
            "categoria": {
                "nome": atleta.categoria.nome
            }
        }
        atletas_dicts.append(atleta_dict)

    return atletas_dicts


@router.get(
    '/{id}',
    summary='Consultar atleta pelo ID',
    status_code=status.HTTP_200_OK,
    response_model=AtletaOut
)
async def query(id: UUID4, db_session: DatabaseDependency) -> AtletaOut:
    atleta: AtletaOut = (
        await db_session.execute(select(AtletaModel).filter_by(id=id))
    ).scalars().first()

    if not atleta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Atleta não encontrado no id: {id}'
        )
    
    return atleta


@router.patch(
    '/{id}',
    summary='Editar atleta pelo ID',
    status_code=status.HTTP_200_OK,
    response_model=AtletaOut
)
async def query(id: UUID4, db_session: DatabaseDependency, atleta_up: AtletaUpdate = Body(...)) -> AtletaOut:
    atleta: AtletaOut = (
        await db_session.execute(select(AtletaModel).filter_by(id=id))
    ).scalars().first()

    if not atleta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Atleta não encontrado no id: {id}'
        )
    
    atleta_update = atleta_up.model_dump(exclude_unset=True)
    for key, value in atleta_update.items():
        setattr(atleta, key, value)

    await db_session.commit()
    await db_session.refresh(atleta)
    
    return atleta


@router.delete(
    '/{id}',
    summary='Deletar atleta pelo ID',
    status_code=status.HTTP_204_NO_CONTENT
)
async def query(id: UUID4, db_session: DatabaseDependency) -> None:
    atleta: AtletaOut = (
        await db_session.execute(select(AtletaModel).filter_by(id=id))
    ).scalars().first()

    if not atleta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Atleta não encontrado no id: {id}'
        )
    
    await db_session.delete(atleta)
    await db_session.commit()