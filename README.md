# poc-fastapi-llm
POC Fastapi com Gemini. Criado para o segundo trabalho do curso da I1A2 em Junho de 2025.

## Run

```
fastapi run app/main.py --port 8000

```

## Live reload

```
uvicorn app.main:app --reload --port 8000
```

## LLM Mistral 

para testar endpoit invoices/extract/mistral, instale:

```
sudo apt update
sudo apt install tesseract-ocr -y
sudo apt install tesseract-ocr-por
```
## Acessar Swagger

```
http://127.0.0.1:8000/docs#/
```

## API Swagger

<div align="center">

![](notas-fiscais/api.png)

</div>

## Teste

### teste no swagger

<div align="center">

![](notas-fiscais/teste1.PNG)

![](notas-fiscais/teste1b.PNG)

</div>

### Nota utilizada

<div align="center">

![](notas-fiscais/nota1.PNG) 

</div>
