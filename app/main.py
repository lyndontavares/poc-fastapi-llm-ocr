import os
from dotenv import load_dotenv
import json
from fastapi import Depends, FastAPI, HTTPException, UploadFile, File, Form  
from fastapi.responses import JSONResponse
import google.generativeai as genai
from app.database import Base, engine, SessionLocal
from sqlalchemy.orm import Session 
from app.schemas import ChatRequest, ChatResponse, ConfigurationRequest, ConfigurationResponse, InvoiceRequest, InvoiceResponse, PromptRequest
from app.models import Configurations, Invoice
import logging
from app.hash_util import gerar_hash_imagem # <-- Import logging
from fastapi.middleware.cors import CORSMiddleware
import requests  # Certo!
from requests.exceptions import RequestException  # Importa a exceção corretamente
from PIL import Image
import pytesseract


# --- Logging Setup ---
logger = logging.getLogger(__name__)

load_dotenv()

# --- Configuração do Google Gemini API ---
# API_KEY = "SUA_CHAVE_DA_API_GOOGLE_AQUI"
API_KEY = os.getenv("GOOGLE_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_API_URL=os.getenv("MISTRAL_API_URL")

if not API_KEY:
    raise ValueError(
        "A variável de ambiente 'GOOGLE_API_KEY' não está definida. "
        "Por favor, defina sua chave de API do Google Gemini."
    )

genai.configure(api_key=API_KEY)
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_PRO_VISION_MODEL = "gemini-1.5-flash" # Modelo para processamento de imagem  gemini-pro-vision gemini-1.5-flash

Base.metadata.create_all(engine)
def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

origins = [
        "http://localhost:4200",  # frontend URL
]

app = FastAPI(
    title="API METAMIND - Extração Inteligente ",
    description="Extração inteligente de dados.",
    version="1.0.0",
    openapi_tags=[
    {
        "name": "Interação com LLM",
        "description": "Interação com LLM.",
    },
    {
         "name": "Crud",
         "description": "Operações de CRUD.",
    }]
)

app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        #allow_credentials=True,
        allow_methods=["*"],  # Allows all HTTP methods
        allow_headers=["*"],  # Allows all headers
)

# --- Endpoint da API ---

@app.post("/chat/mistral", response_model=ChatResponse,tags=["Interação com LLM"])
def chat_with_mistral(request_data: ChatRequest):
    """
    Endpoint que recebe uma requisição de chat e encaminha para a API do Mistral. (https://mistral.ai/)
    
    Exemplo:

        {
            "model": "mistral-medium",
            "messages": [
                {
                "role": "system",
                "content": "Você é um assistente útil."
                },
                {
                "role": "user",
                "content": "Explique a teoria da relatividade em termos simples."
                }
            ],
            "temperature": 0.7,
            "top_p": 1,
            "max_tokens": 256,
            "stream": false
        }

    """
    url = MISTRAL_API_URL 
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = request_data.dict()
    
    try:
        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erro na requisição para a API do Mistral: {e}")
    
    data = resp.json()
    return ChatResponse(response=data)


@app.post("/invoices/extract/mistral",tags=["Interação com LLM"]) # , response_model=InvoiceResponse
async def extract_invoice_data_with_mistral(
    file: UploadFile = File(...),
):
    """
    Recebe uma imagem de nota fiscal, extrai CNPJ, data e valor total e grava na base de notas.
    """    
    # Salvar temporariamente
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    # Abrir imagem com Pillow e extrair texto via pytesseract
    image = Image.open(temp_path)

    logger.warning(">>> Salvou  imagem")

    texto_ocr = pytesseract.image_to_string(image, lang="por")

    # gera hash imagem
    # hash = gerar_hash_imagem(image)

    os.remove(temp_path)

    logger.warning(">>> Feito OCR")

    # Prompt para LLM
    prompt = f"""
        Você é um assistente para extração de dados de notas fiscais brasileiras.

        Texto extraído via OCR:
        ---
        {texto_ocr}
        ---

        Extraia os seguintes campos em formato JSON:

        {{
        "cnpj": "somente números",
        "data": "DD/MM/AAAA",
        "valor": número decimal com ponto (ex: 123.45)
        }}

        Se um campo não for encontrado, use null. Retorne apenas o JSON.
        """

    payload = {
        "model": "mistral-medium",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 400
    }

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(MISTRAL_API_URL, headers=headers, json=payload)

    if response.status_code != 200:
        return JSONResponse(status_code=500, content={"erro": "Falha no modelo", "detalhe": response.text})

    content = response.json()["choices"][0]["message"]["content"]



    # Tenta extrair o JSON da resposta do LLM
    json_data = {}
    raw_llm_response = content
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
    
    invoiceNew = Invoice(
        cnpj=json_data.get('cnpj'), 
        data_emissao=json_data.get('data'), 
        valor_total=json_data.get('valor'),
        #imagem_hash=hash,
        status="CHECKING"
    )

    return invoiceNew
 
    # try:
    #     return JSONResponse(content=eval(content))
    # except Exception:
    #     return {"resposta_nao_tratada": content}



@app.post("/chat/gemini",tags=["Interação com LLM"])
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

# --- Endpoint da API ---

@app.post("/invoices/extract/save" ,tags=["Interação com LLM"] ) # , response_model=InvoiceResponse
async def extract_invoice_data_with_gemini_and_save(file: UploadFile = File(...), session = Depends(get_session)):
    """
    Recebe uma imagem de nota fiscal, extrai CNPJ, data e valor total e grava na base de notas.
    """
    return await extract_invoice_data(file,True,session)

@app.post("/invoices/extract/check" ,tags=["Interação com LLM"] ) # , response_model=InvoiceResponse
async def extract_invoice_data_with_gemini_for_checking(file: UploadFile = File(...), session = Depends(get_session)):
    """
    Recebe uma imagem de nota fiscal, extrai CNPJ, data e valor total. Não grava em base de dados.
    """
    return await extract_invoice_data(file,False,session)

async def extract_invoice_data(file: UploadFile, save: bool, session):
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

        itemObject = session.query(Configurations).first()

        prompt = ""
        if itemObject and itemObject.prompt:
            logger.warning("usando config...")
            prompt = itemObject.prompt
        else:
            prompt = "Analise esta imagem de nota fiscal. Extraia as seguintes informações e formate-as como um objeto JSON. Se um dado não for encontrado, use `null`. Não adicione nenhum texto antes ou depois do JSON. Certifique-se de que o JSON é válido: {\"cnpj\":[CNPJ ou NPJ ou IPJ ou PJ ou P depois do :, com 14 números ou mais], \"data\":[Data da emissão no formato DD/MM/AAAA], \"valor\":[Valor total pago da nota fiscal, em formato numérico com ponto como separador decimal, ex: 123.45]} "
            logger.warning("usando default...")
           
        prompt_parts =  [prompt, "Imagem:", image_parts[0] ]
 
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
        
        # gera hash imagem
        hash = gerar_hash_imagem(image_data)
 
 
        # persistência
        
        #logger.warning("Verificando Hash existe: "+hash)
        encontrou = session.query(Invoice).filter_by(imagem_hash=hash).all()
        #logger.warning(encontrou)

        status="CHECKING"

        if encontrou:
            status=encontrou[0].status
        else:
            if save:
                status="PEDENTE"

        if save and encontrou:
            raise HTTPException(status_code=400, detail="O arquivo enviado já está cadastrado.")

        invoiceNew = Invoice(
            cnpj=json_data.get('cnpj'), 
            data_emissao=json_data.get('data'), 
            valor_total=json_data.get('valor'),
            imagem_hash=hash,
            status=status
        )

        if save:
            session.add(invoiceNew)
            session.commit()
            session.refresh(invoiceNew)

        return invoiceNew
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao processar a imagem da nota fiscal: {str(e)}"
        )

 
@app.get("/invoices",tags=["Crud"])
def get_invoices(session: Session = Depends(get_session)):
    """
    Retorna lista de documentos extraidos.
    """
    items = session.query(Invoice).all()

    return items

@app.get("/invoices/{id}",tags=["Crud"])
def get_invoice(id:int, session: Session = Depends(get_session)):
    """
    Retorna um documento a parti do id.
    """
    item = session.query(Invoice).get(id)
    return item

@app.post("/invoices/add",tags=["Crud"])
def create_invoice(invoice:InvoiceRequest, session = Depends(get_session)):
    """
    Adiciona um novo documento.
    """
    logger.warning(">>>")
    logger.warning(invoice)

    itemObject = Invoice(
        cnpj= invoice.cnpj,
        data_emissao= invoice.data_emissao, 
        valor_total= invoice.valor_total, 
        imagem_hash= invoice.imagem_hash, 
        status= "PROCESSADO"
    )
    session.add(itemObject)
    session.commit()
    session.refresh(itemObject)
    return itemObject

@app.put("/invoices/{id}",tags=["Crud"])
def update_invoice(id:int, invoice:InvoiceRequest, session = Depends(get_session)):
    """
    Atualiza um documento parcialmente.
    """
    itemObject = session.query(Invoice).get(id)
    itemObject.cnpj = invoice.cnpj 
    itemObject.data_emissao = invoice.data_emissao 
    itemObject.valor_total = invoice.valor_total 
    itemObject.status = invoice.status 
    session.commit()
    return itemObject

@app.delete("/invoices/{id}",tags=["Crud"])
def delete_invoice(id:int, session = Depends(get_session)):
    """
    Exclue um documento a partir do ID.
    """
    itemObject = session.query(Invoice).get(id)
    session.delete(itemObject)
    session.commit()
    session.close()
    return 'Documento removido permanentemente.'


@app.put("/configuration",tags=["Configuração"])
def update_configuration(config:ConfigurationRequest, session = Depends(get_session)):
    """
    Atualiza Prompt de extração de dados. Prompt default: Analise esta imagem de nota fiscal. Extraia as seguintes informações e formate-as como um objeto JSON. Se um dado não for encontrado, use `null`. Não adicione nenhum texto antes ou depois do JSON. Certifique-se de que o JSON é válido: {\\\\"cnpj\\\\":[CNPJ da empresa emissora, apenas números], \\\\"data\\\\":[Data da emissão no formato DD/MM/AAAA], \\\\"valor\\\\":[Valor total pago da nota fiscal, em formato numérico com ponto como separador decimal, ex: 123.45]} 
    """
    configUpdated = session.query(Configurations).first()

    if configUpdated:
        configUpdated.prompt = config.prompt 
        logger.warning("Encontrou:"+configUpdated.prompt)
    else:   
        configUpdated = Configurations(prompt=config.prompt)
        logger.warning("Novo:"+configUpdated.prompt)

    session.add(configUpdated)
    session.commit()
    session.refresh(configUpdated)

    return configUpdated

@app.get("/configuration",tags=["Configuração"])
def get_configuration(session = Depends(get_session)):
    """
    Retorna prompt de extração de dados.
    """
    config = session.query(Configurations).first()
    #configResponse = ConfigurationResponse(prompt=config.prompt)
    #session.close()

    return config

