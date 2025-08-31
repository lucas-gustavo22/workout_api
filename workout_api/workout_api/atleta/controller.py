from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, Body, HTTPException, Query, status
from fastapi_pagination import Page, add_pagination, paginate
from pydantic import UUID4
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError


from workout_api.atleta.models import AtletaModel
from workout_api.atleta.schemas import AtletaIn, AtletaOut, AtletaOutCustom, AtletaUpdate
from workout_api.atleta.models import AtletaModel
from workout_api.categorias.models import CategoriaModel
from workout_api.centro_treinamento.models import CentroTreinamentoModel
from workout_api.contrib.dependencies import DatabaseDependency


router = APIRouter()

# @router.post(
#         '/', 
#         summary='Criar novo atleta',
#         status_code=status.HTTP_201_CREATED,
#         response_model=AtletaOut
#     )
# async def post(
#     db_session: DatabaseDependency, 
#     atleta_in: AtletaIn = Body(...)
#     ):
    
#     categoria_nome = atleta_in.categoria.nome
#     centro_treinamento_nome = atleta_in.centro_treinamento.nome

#     categoria = (await db_session.execute(
#         select(CategoriaModel).filter_by(nome=categoria_nome))
#         ).scalars().first()
    
#     if not categoria:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST, 
#                 detail=f'A categoria {categoria_nome} não foi encontrada'
#             )
    
#     centro_treinamento = (await db_session.execute(
#         select(CentroTreinamentoModel).filter_by(nome=centro_treinamento_nome))
#         ).scalars().first()
    
#     if not centro_treinamento:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST, 
#                 detail=f'O Centro de Treinamento {centro_treinamento_nome} não foi encontrado'
#             )

#     try:
#         atleta_out = AtletaOut(id=uuid4(), created_at=datetime.now(timezone.utc), **atleta_in.model_dump())

#         atleta_model = AtletaModel(**atleta_out.model_dump(exclude={'categoria', 'centro_treinamento'}))
#         atleta_model.categoria_id = categoria.pk_id
#         atleta_model.centro_treinamento_id = centro_treinamento.pk_id

#         db_session.add(atleta_model)
#         await db_session.commit()
#     except Exception:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail='Ocorreu um erro ao isnerir os dados no banco'
#         )

#     return atleta_out

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

    categoria = (await db_session.execute(
        select(CategoriaModel).filter_by(nome=categoria_nome))
    ).scalars().first()

    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'A categoria {categoria_nome} não foi encontrada'
        )

    centro_treinamento = (await db_session.execute(
        select(CentroTreinamentoModel).filter_by(nome=centro_treinamento_nome))
    ).scalars().first()

    if not centro_treinamento:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'O Centro de Treinamento {centro_treinamento_nome} não foi encontrado'
        )

    # Criar ORM
    atleta_model = AtletaModel(
        id=uuid4(),
        nome=atleta_in.nome,
        cpf=atleta_in.cpf,
        idade=atleta_in.idade,
        peso=atleta_in.peso,
        altura=atleta_in.altura,
        sexo=atleta_in.sexo,
        created_at=datetime.now(timezone.utc),
        categoria_id=categoria.pk_id,
        centro_treinamento_id=centro_treinamento.pk_id
    )

    db_session.add(atleta_model)

    try:
        await db_session.commit()
    except IntegrityError:
        await db_session.rollback()  # desfazer a transação
        raise HTTPException(
            status_code=303,
            detail=f"Já existe um atleta cadastrado com o cpf: {atleta_in.cpf}"
        )

    await db_session.refresh(atleta_model)
    return AtletaOut.model_validate(atleta_model)



# @router.get(
#     '/',
#     summary='Consultar todos os atletas',
#     response_model=list[AtletaOut],
# )
# async def get_atletas(
#     db_session: DatabaseDependency,
#     nome: str | None = Query(None, description="Filtrar por nome do atleta"),
#     cpf: str | None = Query(None, description="Filtrar por CPF do atleta")
# ):
#     query = select(AtletaModel)

#     if nome:
#         query = query.filter(AtletaModel.nome.ilike(f"%{nome}%"))  # busca parcial, case-insensitive
#     if cpf:
#         query = query.filter(AtletaModel.cpf == cpf)  # busca exata

#     result = await db_session.execute(query)
#     atletas = result.scalars().all()
    
#     return [AtletaOut.model_validate(atleta) for atleta in atletas]

@router.get(
    '/',
    summary='Consultar todos os atletas com paginação',
    response_model=Page[dict],  # paginação com lista de dicionários
)
async def get_atletas(
    db_session: DatabaseDependency,
    nome: str | None = Query(None, description="Filtrar por nome do atleta"),
    cpf: str | None = Query(None, description="Filtrar por CPF do atleta")
):
    query = select(AtletaModel).options(
        selectinload(AtletaModel.categoria),
        selectinload(AtletaModel.centro_treinamento)
    )

    if nome:
        query = query.filter(AtletaModel.nome.ilike(f"%{nome}%"))
    if cpf:
        query = query.filter(AtletaModel.cpf == cpf)

    result = await db_session.execute(query)
    atletas = result.scalars().all()

    # Montar lista customizada
    response = [
        {
            "nome": atleta.nome,
            "categoria": atleta.categoria.nome if atleta.categoria else None,
            "centro_treinamento": atleta.centro_treinamento.nome if atleta.centro_treinamento else None
        }
        for atleta in atletas
    ]

    # Paginar a resposta
    return paginate(response)


@router.get(
        '/{id}', 
        summary='Consultar um atleta pelo id',
        status_code=status.HTTP_200_OK,
        response_model=AtletaOut,
    )
async def get(id:UUID4, db_session: DatabaseDependency) -> AtletaOut:
        atleta: AtletaOut = (await db_session.execute(select(AtletaModel).filter_by(id=id))).scalars().first()

        if not atleta:
            raise HTTPException(
                  status_code=status.HTTP_404_NOT_FOUND, 
                  detail=f'atleta não encontrada no id: {id}'
                )
        
        return atleta


@router.patch(
        '/{id}', 
        summary='Editar um atleta pelo id',
        status_code=status.HTTP_200_OK,
        response_model=AtletaOut,
    )
async def get(id:UUID4, db_session: DatabaseDependency, atleta_up: AtletaUpdate = Body(...)) -> AtletaOut:
        atleta: AtletaOut = (await db_session.execute(select(AtletaModel).filter_by(id=id))).scalars().first()

        if not atleta:
            raise HTTPException(
                  status_code=status.HTTP_404_NOT_FOUND, 
                  detail=f'atleta não encontrada no id: {id}'
                )
        
        atleta_update = atleta_up.model_dump(exclude_unset=True)
        for key, value in atleta_update.items():
            setattr(atleta, key, value)

        await db_session.commit()
        await db_session.refresh(atleta)
        
        return atleta


@router.delete(
        '/{id}', 
        summary='Deletar um atleta pelo id',
        status_code=status.HTTP_204_NO_CONTENT
    )
async def get(id:UUID4, db_session: DatabaseDependency) -> None:
        atleta: AtletaOut = (await db_session.execute(select(AtletaModel).filter_by(id=id))).scalars().first()

        if not atleta:
            raise HTTPException(
                  status_code=status.HTTP_404_NOT_FOUND, 
                  detail=f'atleta não encontrada no id: {id}'
                )
        
        await db_session.delete(atleta)
        await db_session.commit()