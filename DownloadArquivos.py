from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import os
import zipfile
import rarfile
import requests
from typing import List
import tempfile
import shutil


app = FastAPI()

# Configuração da API de destino
API_URL = "http://127.0.0.1:8000/upload/"

# Pasta para uploads temporários
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def upload_interface():
    return """
    <html>
        <head>
            <title>Upload de Arquivos</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                h1 { color: #333; }
                .container { background: #f5f5f5; padding: 20px; border-radius: 5px; }
                .result { margin-top: 20px; padding: 15px; background: #e9e9e9; border-radius: 5px; }
            </style>
        </head>
        <body>
            <h1>Enviar Arquivo Compactado</h1>
            <div class="container">
                <form action="/upload" method="post" enctype="multipart/form-data" id="uploadForm">
                    <input type="file" name="file" accept=".zip,.rar" required>
                    <button type="submit">Enviar</button>
                </form>
                <div id="result" class="result"></div>
            </div>
            <script>
                document.getElementById('uploadForm').addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const formData = new FormData(e.target);
                    const response = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });
                    const result = await response.json();
                    document.getElementById('result').innerHTML = 
                        result.map(item => `<p>${item}</p>`).join('');
                });
            </script>
        </body>
    </html>
    """

async def process_archive(filepath: str) -> List[dict]:
    """Processa arquivo ZIP ou RAR e retorna lista de arquivos"""
    dados = []
    
    if filepath.endswith(".zip"):
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            for arquivo in zip_ref.namelist():
                if not arquivo.endswith('/'):
                    dados.append({
                        "nome_arquivo": os.path.basename(arquivo),
                        "pasta_origem": os.path.dirname(arquivo),
                        "caminho_completo": arquivo
                    })
    
    elif filepath.endswith(".rar"):
        with rarfile.RarFile(filepath, 'r') as rar_ref:
            for arquivo in rar_ref.infolist():
                if not arquivo.isdir():
                    dados.append({
                        "nome_arquivo": os.path.basename(arquivo.filename),
                        "pasta_origem": os.path.dirname(arquivo.filename),
                        "caminho_completo": arquivo.filename
                    })
    
    return dados

async def send_to_api(file_info: dict, archive_path: str) -> str:
    """Envia um arquivo individual para a API"""
    temp_dir = tempfile.mkdtemp()
    temp_file = os.path.join(temp_dir, file_info["nome_arquivo"])
    
    try:
        # Extrair arquivo
        if archive_path.endswith(".zip"):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                with zip_ref.open(file_info["caminho_completo"]) as source, open(temp_file, 'wb') as target:
                    shutil.copyfileobj(source, target)
        
        elif archive_path.endswith(".rar"):
            with rarfile.RarFile(archive_path, 'r') as rar_ref:
                with rar_ref.open(file_info["caminho_completo"]) as source, open(temp_file, 'wb') as target:
                    shutil.copyfileobj(source, target)
        
        # Enviar para API
        with open(temp_file, 'rb') as f:
            files = {'file': (file_info["nome_arquivo"], f)}
            data = {
                'pasta_origem': file_info["pasta_origem"],
                'caminho_completo': file_info["caminho_completo"]
            }
            
            response = requests.post(API_URL, files=files, data=data)
            
            if response.status_code == 200:
                return f"✅ {file_info['nome_arquivo']} enviado com sucesso!"
            return f"❌ Erro ao enviar {file_info['nome_arquivo']}: {response.text}"
    
    except Exception as e:
        return f"⚠️ Erro ao processar {file_info['nome_arquivo']}: {str(e)}"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(('.zip', '.rar')):
        raise HTTPException(400, "Apenas arquivos ZIP ou RAR são permitidos")
    
    # Salvar arquivo temporariamente
    file_location = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Processar arquivo
        files_info = await process_archive(file_location)
        
        # Enviar arquivos para API
        results = []
        for file_info in files_info:
            result = await send_to_api(file_info, file_location)
            results.append(result)
        
        return JSONResponse(content=results)
    
    finally:
        # Limpar arquivo temporário
        os.remove(file_location)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)