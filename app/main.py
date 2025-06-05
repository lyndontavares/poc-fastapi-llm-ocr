import os
from typing import Union
from fastapi import FastAPI, HTTPException, UploadFile, File, Form  
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv
import json

load_dotenv()

app = FastAPI()

# --- Configuração do Google Gemini API ---
# É ALTAMENTE RECOMENDADO usar variáveis de ambiente para sua API Key
# Exemplo (Linux/macOS): export GOOGLE_API_KEY="SUA_CHAVE_AQUI"
# Exemplo (Windows CMD): set GOOGLE_API_KEY="SUA_CHAVE_AQUI"
# Exemplo (Windows PowerShell): $env:GOOGLE_API_KEY="SUA_CHAVE_AQUI"
# Ou coloque diretamente, mas NÃO faça isso em produção:
# API_KEY = "SUA_CHAVE_DA_API_GOOGLE_AQUI"
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError(
        "A variável de ambiente 'GOOGLE_API_KEY' não está definida. "
        "Por favor, defina sua chave de API do Google Gemini."
    )

genai.configure(api_key=API_KEY)
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_PRO_VISION_MODEL = "gemini-1.5-flash" # Modelo para processamento de imagem  gemini-pro-vision gemini-1.5-flash



# --- Modelo Pydantic para o corpo da requisição ---
class PromptRequest(BaseModel):
    prompt: str

# --- Endpoint da API ---
@app.post("/chat")
async def chat_with_gemini(request: PromptRequest):
    """
    Recebe um prompt de texto, interage com o modelo Google Gemini e retorna a resposta.
    """
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        # Gera o conteúdo usando o modelo
        response = model.generate_content(request.prompt)
        
        # Verifica se a resposta contém texto
        if response.parts:
            # Concatena todas as partes da resposta
            full_response_text = "".join([part.text for part in response.parts if hasattr(part, 'text')])
            return {"response": full_response_text}
        else:
            # Lida com casos onde a resposta pode ser vazia ou não ter texto
            return {"response": "Não foi possível gerar uma resposta para o prompt."}

    except Exception as e:
        # Captura erros da API ou outros problemas
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao interagir com o modelo Gemini: {str(e)}"
        )

# --- NOVO ENDPOINT: Extração de Dados de Nota Fiscal ---
class InvoiceData(BaseModel):
    cnpj: str | None = None
    data_emissao: str | None = None
    valor_total: float | None = None
    observacao: str = "Dados extraídos. A precisão depende da qualidade da imagem e do modelo LLM."

@app.post("/extract-invoice-data", response_model=InvoiceData)
async def extract_invoice_data(file: UploadFile = File(...)):
    """
    Recebe uma imagem de nota fiscal, extrai CNPJ, data e valor total.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="O arquivo enviado não é uma imagem.")

    try:
        # Carrega a imagem para o formato que o Gemini espera
        image_data = await file.read()
        image_parts = [
            {
                "mime_type": file.content_type,
                "data": image_data
            }
        ]

        # Prepara o modelo Gemini Vision
        model_vision = genai.GenerativeModel(GEMINI_PRO_VISION_MODEL)

        # Prompt de engenharia para extração de dados em JSON
        # É crucial pedir o formato JSON e instruir para usar 'null' se o dado não for encontrado.
        prompt_parts = [
            "Analise esta imagem de nota fiscal. Extraia as seguintes informações e formate-as como um objeto JSON. Se um dado não for encontrado, use `null`. Não adicione nenhum texto antes ou depois do JSON. Certifique-se de que o JSON é válido.",
            "",
            "```json",
            "{",
            "  \"cnpj\": \"[CNPJ da empresa emissora, apenas números]\",",
            "  \"data\": \"[Data da emissão no formato DD/MM/AAAA]\",",
            "  \"valor\": [Valor total psgo da nota fiscal, em formato numérico com ponto como separador decimal, ex: 123.45]",
            "}",
            "```",
            "Imagem:",
            image_parts[0] # Anexa a imagem aqui
        ]
        
        # Gera o conteúdo
        response = model_vision.generate_content(prompt_parts)
        
        # O Gemini pode retornar texto em partes. Juntamos tudo.
        raw_llm_response = "".join([part.text for part in response.parts if hasattr(part, 'text')])

        # Tenta extrair o JSON da resposta do LLM
        json_data = {}
        try:
            # Tenta encontrar o bloco JSON na resposta
            start_index = raw_llm_response.find("```json")
            end_index = raw_llm_response.find("```", start_index + 1)
            
            if start_index != -1 and end_index != -1:
                json_string = raw_llm_response[start_index + len("```json"):end_index].strip()
                json_data = json.loads(json_string)
            else:
                # Se não encontrar o bloco ```json```, tenta parsear a resposta completa
                json_data = json.loads(raw_llm_response.strip())

        except json.JSONDecodeError as e:
            print(f"Não foi possível parsear o JSON da resposta do LLM: {raw_llm_response}. Erro: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao parsear a resposta do modelo. Resposta recebida: {raw_llm_response.strip()}"
            )

        # Converte o valor para float se não for nulo
        if 'valor' in json_data and json_data['valor'] is not None:
            try:
                json_data['valor'] = float(json_data['valor'])
            except ValueError:
                json_data['valor'] = None # Ou manter como string se a conversão falhar

        # Cria a resposta com o modelo Pydantic, garantindo que os campos existam
        return InvoiceData(
            cnpj=json_data.get('cnpj'),
            data_emissao=json_data.get('data'),
            valor_total=json_data.get('valor')
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao processar a imagem da nota fiscal: {str(e)}"
        )


@app.get("/")
def read_root():
    return {"Hello": "World"}

