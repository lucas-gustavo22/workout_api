import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Importar seu BaseModel e todas as models aqui
from workout_api.contrib.models import BaseModel
from workout_api.categorias.models import CategoriaModel
from workout_api.atleta.models import AtletaModel
from workout_api.centro_treinamento.models import CentroTreinamentoModel

# Config do Alembic
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# metadata do SQLAlchemy que Alembic vai usar
target_metadata = BaseModel.metadata

# Rodar migrations offline
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# Função de execução sincronizada dentro do async
def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


# Rodar migrations online (async)
async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# Executa de acordo com o modo offline/online
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
