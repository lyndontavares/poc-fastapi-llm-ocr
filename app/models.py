from sqlalchemy import Column, Integer, String
from app.database import Base
from sqlalchemy import Enum
import enum

class STATUS(enum.Enum):
    PENDENTE = 1
    PROCESSADO = 2

class Item(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True)
    task = Column(String(256))


class Invoice(Base):
    __tablename__ = 'invoices'
    id = Column(Integer, primary_key=True)
    cnpj = Column(String(20))
    data_emissao = Column(String(10))
    valor_total = Column(String(64))
    status = Column(String(10),default="PENDENTE") # PENDENTE / CONFERIDO


# https://dennisivy.com/fast-api-crud
# https://www.sqlalchemy.org/
# https://docs.sqlalchemy.org/en/20/tutorial/orm_data_manipulation.html