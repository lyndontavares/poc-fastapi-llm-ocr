from typing import List
from pydantic import BaseModel

# --- corpo da requisição ---


class PromptRequest(BaseModel):
    prompt: str


class ConfigurationRequest(BaseModel):
    prompt: str


class ConfigurationResponse(BaseModel):
    prompt: str

# --- Dados de Nota Fiscal ---


class InvoiceResponse(BaseModel):
    id: int | None = None
    tipo_despesa: str | None = None
    cnpj: str | None = None
    data_emissao: str | None = None
    valor_total: float | None = None
    imagem_hash: str | None = None
    # observacao: str = "Dados extraídos. A precisão depende da qualidade da imagem e do modelo LLM."
    # nome_arquivo_imagem: str | None = None # Novo campo para o nome do arquivo da imagem
    status: str | None = None  # Novo campo para o status da persistência


# --- Dados de Nota Fiscal ---
class InvoiceRequest(BaseModel):
    id: int | None = None
    tipo_despesa: str | None = None
    cnpj: str | None = None
    data_emissao: str | None = None
    valor_total: float | None = None
    imagem_hash: str | None = None
    status: str | None = None  # Novo campo para o status da persistência

# Esquemas para a requisição e resposta


class Message(BaseModel):
    role: str  # Ex: "system", "user", "assistant"
    content: str


class ChatRequest(BaseModel):
    model: str = "mistral-medium"
    messages: List[Message]
    temperature: float = 0.7
    max_tokens: int = 300
    stream: bool = False


class ChatResponse(BaseModel):
    response: dict
