from pydantic import Field
from pydantic_settings import BaseSettings

class Seetings(BaseSettings):
    DB_URL: str = Field(default='postgresql+asyncpg://workout:workout@localhost:5432/workout') 

settings = Seetings()