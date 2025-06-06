from pydantic import BaseModel

# --- corpo da requisição ---
class PromptRequest(BaseModel):
    prompt: str

# --- Dados de Nota Fiscal ---
class InvoiceResponse(BaseModel):
    id: int | None = None
    cnpj: str | None = None
    data_emissao: str | None = None
    valor_total: float | None = None
    observacao: str = "Dados extraídos. A precisão depende da qualidade da imagem e do modelo LLM."
    #nome_arquivo_imagem: str | None = None # Novo campo para o nome do arquivo da imagem
    status: str| None = None # Novo campo para o status da persistência

    
# --- Dados de Nota Fiscal ---
class InvoiceRequest(BaseModel):
    id: int | None = None
    cnpj: str | None = None
    data_emissao: str | None = None
    valor_total: float | None = None
    status: str| None = None # Novo campo para o status da persistência
