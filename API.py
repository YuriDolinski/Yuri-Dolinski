from fastapi import FastAPI, File, UploadFile, Form
import os

# Criar o app FastAPI
app = FastAPI()

# Diretório onde os arquivos serão armazenados
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload/")
async def upload_file(
    file: UploadFile = File(...),  # Arquivo enviado
    repositorio: str = Form(...),  # Metadados do arquivo
    tipo: str = Form(...),
    vinculo: str = Form(...),
    numero_processo: str = Form(None)  # Pode ser opcional
):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    # Salvar o arquivo localmente
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    return {
        "mensagem": "Arquivo enviado com sucesso!",
        "nome_arquivo": file.filename,
        "repositorio": repositorio,
        "tipo": tipo,
        "vinculo": vinculo,
        "numero_processo": numero_processo
    }

# Para rodar a API:
# uvicorn nome_do_arquivo:app --reload
