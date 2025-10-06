from sqlalchemy import Column, Integer, String
from app.database import Base
from sqlalchemy import Enum
import enum


class STATUS(enum.Enum):
    PENDENTE = 1
    PROCESSADO = 2


class Configurations(Base):
    __tablename__ = 'configurations'
    id = Column(Integer, primary_key=True)
    prompt = Column(String(2048))
    api_url=  Column(String(256))
    api_key=  Column(String(256))
    llm_model=  Column(String(128))

class Item(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True)
    task = Column(String(256))


class Invoice(Base):
    __tablename__ = 'invoices'
    id = Column(Integer, primary_key=True)
    tipo_despesa = Column(String(20))
    cnpj = Column(String(20))
    data_emissao = Column(String(10))
    valor_total = Column(String(64))
    status = Column(String(10), default="PENDENTE")  # PENDENTE / CONFERIDO
    imagem_hash = Column(String(64), unique=True)


# https://dennisivy.com/fast-api-crud
# https://www.sqlalchemy.org/
# https://docs.sqlalchemy.org/en/20/tutorial/orm_data_manipulation.html
