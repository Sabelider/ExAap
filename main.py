import os
import json
import uuid
import re
import pytz
import unicodedata
import shutil
import time
import jwt
import unicodedata
from datetime import datetime, timedelta, timezone
from collections import OrderedDict
from urllib.parse import unquote

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, UploadFile, File, Body, Query, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.status import HTTP_303_SEE_OTHER
from typing import List, Optional

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from fpdf import FPDF
from pydantic import BaseModel

# --- Load environment ---
load_dotenv()

# --- Firebase ---
firebase_json = os.environ.get("FIREBASE_KEY")
if firebase_json and not firebase_admin._apps:
    try:
        firebase_info = json.loads(firebase_json)
        if "private_key" in firebase_info:
            firebase_info["private_key"] = firebase_info["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(firebase_info)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
    except Exception as e:
        raise RuntimeError(f"Erro ao inicializar Firebase: {e}")
else:
    db = None  

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFESSORES_JSON = os.path.join(BASE_DIR, "professores.json")
ALUNOS_JSON = os.path.join(BASE_DIR, "alunos.json")

# --- FastAPI app ---
app = FastAPI(title="SabApp + 100ms")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- CORS (opcional) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # alterar em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def carregar_professores_local():
    if os.path.exists(PROFESSORES_JSON):
        with open(PROFESSORES_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def salvar_professores_local(professores):
    with open(PROFESSORES_JSON, "w", encoding="utf-8") as f:
        json.dump(professores, f, ensure_ascii=False, indent=4)

def carregar_professores_firebase():
    return [doc.to_dict() for doc in db.collection("professores").stream()]

def salvar_professor_firebase(professor: dict):
    bi = professor.get("bi")
    if bi:
        db.collection("professores").document(bi).set(professor)

def excluir_professor_firebase(bi: str):
    db.collection("professores").document(bi).delete()

def gerar_html_professores():
    professores = carregar_professores_local()
    conteudo = """
    <!DOCTYPE html><html lang="pt"><head><meta charset="UTF-8">
    <title>Professores Registrados</title><link rel="stylesheet" href="/static/style.css">
    <style>body{font-family:Arial,sans-serif;background:#f8f9fa;padding:20px;}h1{text-align:center;color:#343a40;}
    table{width:100%;border-collapse:collapse;background:#fff;box-shadow:0 0 10px rgba(0,0,0,0.1);margin-top:20px;}
    th,td{padding:12px;border:1px solid #dee2e6;text-align:left;}th{background:#343a40;color:#fff;}
    tr:nth-child(even){background:#f1f1f1;}img{max-width:80px;border-radius:8px;}</style></head><body>
    <h1>Lista de Professores Registrados</h1><table>
    <tr><th>Foto</th><th>Nome</th><th>Idade</th><th>Pai</th><th>Mãe</th><th>Morada</th>
    <th>Referência</th><th>BI</th><th>Email</th><th>Telefone</th><th>Localização</th></tr>
    """
    for p in professores:
        foto = f'<img src="{p.get("doc_foto","")}" alt="Foto">' if p.get("doc_foto") else "N/A"
        conteudo += f"""<tr><td>{foto}</td><td>{p.get('nome','')}</td><td>{p.get('idade','')}</td>
        <td>{p.get('nome_pai','')}</td><td>{p.get('nome_mae','')}</td><td>{p.get('morada_atual','')}</td>
        <td>{p.get('ponto_referencia','')}</td><td>{p.get('bi','')}</td><td>{p.get('email','')}</td>
        <td>{p.get('telefone','')}</td><td>{p.get('localizacao','')}</td></tr>"""
    conteudo += "</table></body></html>"
    with open("templates/pro-info.html", "w", encoding="utf-8") as f:
        f.write(conteudo)

# Carrega inicial
if not os.path.exists(PROFESSORES_JSON):
    salvar_professores_local([])
gerar_html_professores()

# ============================
# 🔹 CONTAS 100MS
# ============================
CONTAS_100MS = [
    {
        "ACCESS_KEY": "68e12ac3bd0dab5f9a013f93",
        "SECRET": "4agaGFjtDBN9VtVehvbZDt7mNMHWSeoN05Q_SfzjAs0sTwhDbmkH4SFaxVqYFIcgcDCoBCgDBLofpmog6VUlwNmzkxi3PWQ9N3KZYYHNRZYItsxETK0qU_mfeA4ita1-OVzrq9m37nf6Ns-C-KBGWaLV3S45ZvhsxOHTzK-5A4g=",
        "TEMPLATE": "68e132db74147bd574bb494a",
        "SUBDOMAIN": "sabe-videoconf-1518"
    },
    {
        "ACCESS_KEY": "68e8c88cbd0dab5f9a01409d",
        "SECRET": "rI932W7abnwd9NC5vTY54e_DSfG8UNFxxgz5JD7_6stDWSbnOevqsaeeyaRfDitue4-IkmlgAR7c7fr_n42Wx0pKw4fhofXEGa3fj5R9Q3xcdxQJvHjMD6sM-VP9XL-HLKEFT7X1lK8hZAxh0DsCKrjaU2o5Bk2UoVN9pRQNnTc=",
        "TEMPLATE": "691af3a4033903926e62a61a",
        "SUBDOMAIN": "arrikson-videoconf-1105"
    },
    {
        "ACCESS_KEY": "691b1920145cb4e8449b1ad5",
        "SECRET": "y3Uk__pTuLXY2xYP_7QMw_rL7021SA3v7nAqLujr-pQ2Ree9fnYbLizd46OZ2K__53YEzH1hit8dw9ctDP0hEAP_q5Ca_kAp-bLa8gUSWgb1jeUpgETWFiUU4DzOnctm8iFueoZk8v_sb3HaN2vTSxUuj1-eI60W7RzAMObAxw0=",
        "TEMPLATE": "691b1965033903926e62a68e",
        "SUBDOMAIN": "mb-videoconf-1347"
    },
    {
        "ACCESS_KEY": "691c423fbd0dab5f9a0147ee",
        "SECRET": "VQpwHMexPStIBd3tB8UP7uXSdI4JzaGCUOX79M-YEUPhne3dh7tSIeGq9vobErsf0h4xMzjrTtvgimBca-89Oi7g5eBibRu6heKdqO10XzK3v4YrBaW0sENcTSMnwgmBwi4I7tGLYXrdP-G6xp2J_k0LoNZHX97A6Tzjm0SAA5I=",
        "TEMPLATE": "691c42b774147bd574bbb7e6",
        "SUBDOMAIN": "lcio-videoconf-1056"
    },
    {
        "ACCESS_KEY": "691b1f5c145cb4e8449b1ada",
        "SECRET": "WfQpeZTfOX2QcFRwmSg_t-vHH7Vd1x687DCp4IvLAyRhD2zWfgEt38M5gFNerlJKYBWgb_mhg5-0Y4MQCns5ANgDvTfVoejzwULFcAf3aY6m-FfFs_L5B2Naf3pRoeEvpdVeUMxeNLyEbGt1qp4n6sFtbcytzEr73lEGS0kD8t8=",
        "TEMPLATE": "691b1f6e74147bd574bbb5ce",
        "SUBDOMAIN": "rafael-videoconf-1413"
    },
    {
        "ACCESS_KEY": "691c4cf8bd0dab5f9a0147f6",
        "SECRET": "QFhzYgzrLpmawfPtPxlgn75UYRNfeNiCTha3YXDbmD3zeQVIsqEavBytDgk6jxnqr4ePjybhV_AR1zWphCkXf8A7UfS64vsuYr_QJymSsoE_BvdUanN3zXP16lU2XmjeCkA1uriETzhrsp1ruj498dgVpFNnV6QV9W67ybyACQA=",
        "TEMPLATE": "691c4d09033903926e62a8a0",
        "SUBDOMAIN": "rafael-videoconf-1140"
    },
    {
        "ACCESS_KEY": "691c4f0dbd0dab5f9a0147fb",
        "SECRET": "jMOUaFZLjtyNWLlhAUgFosGEfwTm5syNtb7NKnc33yWKipD-tDCQHD7Swjq9gOJlAoSoiU0wS9D2rUi8aQcpQhBkEag2VwbJrpDOMHRDp6m9JsLNk99BN0PvguvMvH4IVkHIkCRwgJ23fv2kksKEtzAXYOEOdcD9aNOh8Tm3usQ=",
        "TEMPLATE": "691c4f1b74147bd574bbb7ea",
        "SUBDOMAIN": "carlene100ms-videoconf-1148"
    },
    {
        "ACCESS_KEY": "691eaf0f145cb4e8449b1b80",
        "SECRET": "ktRPCNeqFjSdK8hp9UyH7ujxvrWM_oHmZd7fq5AfyjlInQWGKjBs32s_ZnpD2nvKe1gki_nrTDcbe_l6Jrj9Vb8dgJJjMN8V7Holkeq0mtCTFW6uD6uWoEXtUWhOG7XKfrLXW9D_4Aq5qNF2dqjxY3j4ro0Bz5Kq7837KeJDgyk=",
        "TEMPLATE": "691eaf26033903926e62ad5c",
        "SUBDOMAIN": "xoco-videoconf-703"
    },
]

# ============================
# 🔹 Inicializar CONTAS_100MS no Firebase (corrigido)
# ============================
def init_contas_100ms():
    ref = db.collection("CONTAS_100MS").document("contador")
    doc = ref.get()
    if not doc.exists:
        # 🔹 Converter índices para string
        usos = {str(i): 0 for i in range(len(CONTAS_100MS))}
        data = {
            "conta_atual": 0,
            "usos": usos
        }
        ref.set(data)
        print("🔥 Documento 'CONTAS_100MS/contador' criado automaticamente no Firebase.")

# Chamar na inicialização da aplicação
init_contas_100ms()

# ============================
# 🔹 FUNÇÕES DE CONTROLE DE CONTA
# ============================
async def get_current_account():
    ref = db.collection("CONTAS_100MS").document("contador")
    doc = ref.get()
    data = doc.to_dict() if doc.exists else None

    if not data:
        usos = {str(i): 0 for i in range(len(CONTAS_100MS))}
        data = {"conta_atual": 0, "usos": usos}
        ref.set(data)
        print("🔥 Documento 'contador' criado automaticamente no Firebase.")

    # 🔹 garante que todas as chaves de 'usos' sejam strings
    usos = {str(k): v for k, v in data["usos"].items()}
    return data["conta_atual"], usos


async def rotate_account():
    ref = db.collection("CONTAS_100MS").document("contador")
    doc = ref.get()
    data = doc.to_dict() if doc.exists else None

    if not data:
        usos = {str(i): 0 for i in range(len(CONTAS_100MS))}
        data = {"conta_atual": 0, "usos": usos}
        ref.set(data)
        print("🔥 Documento 'contador' criado automaticamente no Firebase.")

    conta = data["conta_atual"]
    usos = {str(k): v for k, v in data["usos"].items()}  # 🔹 chaves como string

    conta_str = str(conta)
    if usos.get(conta_str, 0) >= 10:
        conta = (conta + 1) % len(CONTAS_100MS)
        conta_str = str(conta)
        usos[conta_str] = 0

    ref.update({"conta_atual": conta, "usos": usos})
    return conta


async def incrementar_uso():
    ref = db.collection("CONTAS_100MS").document("contador")
    doc = ref.get()
    data = doc.to_dict() if doc.exists else None

    if not data:
        usos = {str(i): 0 for i in range(len(CONTAS_100MS))}
        data = {"conta_atual": 0, "usos": usos}
        ref.set(data)
        print("🔥 Documento 'contador' criado automaticamente no Firebase.")

    conta = data["conta_atual"]
    usos = {str(k): v for k, v in data["usos"].items()}  # 🔹 chaves como string

    conta_str = str(conta)
    usos[conta_str] = usos.get(conta_str, 0) + 1  # 🔹 seguro, evita KeyError
    ref.update({"usos": usos})

    await rotate_account()


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
    

class VinculoIn(BaseModel): 
    professor_email: str
    aluno_nome: str


def vinculo_existe(prof_email: str, aluno_nome: str) -> bool:
    prof_normalizado = prof_email.strip().lower()
    aluno_normalizado = aluno_nome.strip().lower()

    docs = db.collection('alunos_professor') \
             .where("professor", "==", prof_normalizado) \
             .where("aluno", "==", aluno_normalizado) \
             .limit(1).stream()

    return next(docs, None) is not None


@app.post('/vincular-aluno', status_code=201)
async def vincular_aluno(item: VinculoIn):
    try:
        prof = item.professor_email.strip().lower()
        aluno_nome_input = item.aluno_nome.strip().lower()

        # Buscar aluno pelo nome normalizado
        alunos = db.collection("alunos").stream()
        aluno_doc = None
        for doc in alunos:
            dados = doc.to_dict()
            nome_banco = dados.get("nome", "").strip().lower()
            if nome_banco == aluno_nome_input:
                aluno_doc = doc
                break

        if not aluno_doc:
            raise HTTPException(status_code=404, detail="Aluno não encontrado")

        if vinculo_existe(prof, aluno_nome_input):
            raise HTTPException(status_code=409, detail="Vínculo já existe")

        dados_aluno = aluno_doc.to_dict()

        # Remove campos sensíveis que não devem ir para alunos_professor
        for campo in ['senha']:
            dados_aluno.pop(campo, None)

        # Criação do documento com os dados do aluno + vínculo
        db.collection('alunos_professor').add({
            'professor': prof,
            'aluno': aluno_nome_input,
            'dados_aluno': {
                'nome': dados_aluno.get('nome', ''),
                'disciplina': dados_aluno.get('disciplina', ''),
                'progresso_ingles': dados_aluno.get('progresso_ingles', 0),
                'provincia': dados_aluno.get('provincia', '').strip(),
                'municipio': dados_aluno.get('municipio', '').strip(),
                'bairro': dados_aluno.get('bairro', '').strip(),
                'telefone': dados_aluno.get('telefone', '').strip(),
            },
            'vinculado_em': datetime.now(timezone.utc).isoformat(),
            'online': True,
            'notificacao': False,
            'aulas_dadas': 0,
            'total_aulas': 12,
            'aulas': [],
            'horario': {},        
            'datas_aulas': []      
        })

        # Atualiza o campo vinculado no documento do aluno
        db.collection("alunos").document(aluno_doc.id).update({
            "vinculado": True
        })

        return {"message": "Vínculo criado com sucesso"}

    except HTTPException:
        raise
    except Exception as e:
        print('Erro interno ao vincular aluno:', e)
        return JSONResponse(
            status_code=500,
            content={'detail': 'Erro interno ao criar vínculo. Verifique os dados e tente novamente.'}
        )


@app.get("/perfil_prof", response_class=HTMLResponse)
async def get_perfil_prof(request: Request, email: str):
    """
    Exibe o perfil do professor com base no email fornecido.
    Esse email normalmente virá da sessão de login ou como query param após login.
    """
    professores_ref = db.collection("professores_online")
    query = professores_ref.where("email", "==", email).limit(1).stream()
    prof_doc = next(query, None)

    if not prof_doc:
        return templates.TemplateResponse("erro.html", {"request": request, "mensagem": "Professor não encontrado"})

    prof_data = prof_doc.to_dict()
    prof_data["id"] = prof_doc.id  # armazenar ID do documento para atualização posterior

    # Pega o saldo atual ou assume 0.0
    saldo = prof_data.get("saldo", 0.0)
    try:
        saldo_float = float(saldo)
    except (ValueError, TypeError):
        saldo_float = 0.0

    # Formata o saldo como Kz 1.000,00
    saldo_formatado = f"{saldo_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    return templates.TemplateResponse("perfil_prof.html", {
        "request": request,
        "professor": prof_data,
        "saldo_atual": saldo_formatado
    })


@app.post("/perfil_prof", response_class=HTMLResponse)
async def post_perfil_prof(
    request: Request,
    email: str = Form(...),
    descricao: str = Form(...)
):
    """
    Atualiza apenas o campo "descricao" do professor logado.
    """
    professores_ref = db.collection("professores_online")
    query = professores_ref.where("email", "==", email).limit(1).stream()
    prof_doc = next(query, None)

    if not prof_doc:
        return templates.TemplateResponse("erro.html", {"request": request, "mensagem": "Professor não encontrado para atualização."})

    # Atualizar o campo descrição
    db.collection("professores_online").document(prof_doc.id).update({
        "descricao": descricao
    })

    # Redireciona de volta ao perfil com confirmação
    return RedirectResponse(url=f"/perfil_prof?email={email}", status_code=303)
    
@app.get('/alunos-disponiveis/{prof_email}')
async def alunos_disponiveis(prof_email: str):
    prof_docs = db.collection('professores_online') \
                  .where('email', '==', prof_email.strip()).limit(1).stream()
    prof = next(prof_docs, None)
    if not prof:
        raise HTTPException(status_code=404, detail='Professor não encontrado')

    prof_data = prof.to_dict()
    area = prof_data.get('area_formacao', '').strip()
    if not area:
        return []

    # Lista apenas os alunos que ainda não estão vinculados
    alunos = db.collection('alunos') \
               .where('disciplina', '==', area) \
               .where('vinculado', '==', False).stream()

    disponiveis = []
    for aluno in alunos:
        aluno_data = aluno.to_dict()
        disponiveis.append({
            'nome': aluno_data.get('nome', ''),
            'disciplina': aluno_data.get('disciplina', ''),
            'progresso_ingles': aluno_data.get('progresso_ingles', 0),
            'provincia': aluno_data.get('provincia', '').strip(),
            'municipio': aluno_data.get('municipio', '').strip(),
            'bairro': aluno_data.get('bairro', '').strip(),
            'telefone': aluno_data.get('telefone', '').strip()
        })

    return disponiveis

@app.get('/meus-alunos/{prof_email}')
async def meus_alunos(prof_email: str):
    try:
        docs = db.collection('alunos_professor') \
                 .where('professor', '==', prof_email.strip()).stream()

        alunos = []
        for doc in docs:
            data = doc.to_dict()
            dados_aluno = data.get('dados_aluno', {})
            aluno = {
                'nome': dados_aluno.get('nome', ''),
                'disciplina': dados_aluno.get('disciplina', ''),
                'bairro': dados_aluno.get('bairro', ''),
                'municipio': dados_aluno.get('municipio', ''),
                'provincia': dados_aluno.get('provincia', ''),
                'nome_pai': dados_aluno.get('nome_pai', ''),
                'nome_mae': dados_aluno.get('nome_mae', ''),
                'outra_disciplina': dados_aluno.get('outra_disciplina', ''),
                'vinculado_em': data.get('vinculado_em', '')
            }
            alunos.append(aluno)

        return JSONResponse(content=alunos)

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'detail': 'Erro ao buscar alunos vinculados', 'erro': str(e)}
        )


# 🔹 Modelo da mensagem
class MensagemInfo(BaseModel):
    aluno: str
    professor: str
    mensagem: str
    remetente: str  # "aluno" ou "professor"


# 🔹 Atualiza coleção e garante campos obrigatórios
@app.get("/meus-alunos-status/{prof_email}")
async def meus_alunos_status(prof_email: str):
    try:
        docs = db.collection('alunos_professor') \
                 .where('professor', '==', prof_email.strip().lower()).stream()

        alunos = []
        for doc in docs:
            d = doc.to_dict()
            atualizacoes = {}

            # Garante campos obrigatórios
            if 'dados_aluno' not in d:
                atualizacoes['dados_aluno'] = {}
            if 'mensagens' not in d:  # 🔹 agora padronizado
                atualizacoes['mensagens'] = []

            if atualizacoes:
                db.collection('alunos_professor').document(doc.id).update(atualizacoes)

            dados = d.get('dados_aluno', {})
            alunos.append({
                'nome': dados.get('nome', d.get('aluno', '')),
                'disciplina': dados.get('disciplina', ''),
                'telefone': dados.get('telefone', ''),
                'provincia': dados.get('provincia', ''),
                'municipio': dados.get('municipio', ''),
                'bairro': dados.get('bairro', ''),
                'nivel_ingles': dados.get('nivel_ingles', ''),
                'online': d.get('online', False)
            })

        return alunos

    except Exception as e:
        print("❌ Erro em /meus-alunos-status:", e)
        return JSONResponse(status_code=500, content={"detail": str(e)})


# 🔹 Enviar mensagem (aluno → professor ou professor → aluno)
@app.post("/enviar-mensagem")
async def enviar_mensagem(request: Request):
    try:
        data = await request.json()
        aluno = data.get("aluno", "").strip().lower()
        professor = data.get("professor", "").strip().lower()
        mensagem = data.get("mensagem", "").strip()
        remetente = data.get("remetente", "").strip().lower()

        print(f"📨 Tentando enviar mensagem de '{remetente}' | Aluno: '{aluno}' | Prof: '{professor}'")

        if not aluno or not professor or not mensagem:
            return JSONResponse(status_code=400, content={"detail": "Dados incompletos"})

        # Buscar vínculo entre aluno e professor
        query = db.collection("alunos_professor") \
                  .where("aluno", "==", aluno) \
                  .where("professor", "==", professor) \
                  .limit(1).stream()

        docs = list(query)
        if not docs:
            print("⚠️ Nenhum vínculo encontrado!")
            return JSONResponse(status_code=404, content={"detail": "Vínculo não encontrado"})

        vinculo_doc = docs[0]
        doc_ref = db.collection("alunos_professor").document(vinculo_doc.id)

        nova_mensagem = {
            "remetente": remetente,
            "mensagem": mensagem,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Atualiza o array de mensagens com segurança
        doc_ref.update({
            "mensagens": firestore.ArrayUnion([nova_mensagem])
        })

        print("✅ Mensagem enviada com sucesso:", nova_mensagem)
        return {"status": "sucesso", "mensagem": nova_mensagem}

    except Exception as e:
        print("❌ Erro ao enviar mensagem:", e)
        return JSONResponse(status_code=500, content={"detail": str(e)})


# 🔹 Buscar mensagens trocadas entre professor e aluno
@app.get("/buscar-mensagens/{professor}/{aluno}")
async def buscar_mensagens(professor: str, aluno: str):
    try:
        aluno_normalizado = aluno.strip().lower()
        professor_normalizado = professor.strip().lower()

        print(f"🗂️ Buscando mensagens entre '{professor_normalizado}' e '{aluno_normalizado}'")

        query = db.collection("alunos_professor") \
                  .where("aluno", "==", aluno_normalizado) \
                  .where("professor", "==", professor_normalizado) \
                  .limit(1).stream()

        docs = list(query)
        if not docs:
            print("⚠️ Nenhum vínculo encontrado para carregar mensagens.")
            return []

        vinculo_doc = docs[0]
        data = vinculo_doc.to_dict()
        mensagens = data.get("mensagens", [])

        mensagens_formatadas = []
        for m in mensagens:
            msg = {
                "mensagem": m.get("mensagem"),
                "remetente": m.get("remetente"),
            }

            timestamp = m.get("timestamp")
            if not timestamp:
                timestamp = datetime.utcnow()
            elif hasattr(timestamp, "to_datetime"):
                timestamp = timestamp.to_datetime()

            msg["timestamp"] = (
                timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp)
            )

            mensagens_formatadas.append(msg)

        # Ordena as mensagens pelo timestamp
        mensagens_formatadas.sort(key=lambda x: x["timestamp"])

        print(f"💬 {len(mensagens_formatadas)} mensagens encontradas.")
        return mensagens_formatadas

    except Exception as e:
        print("❌ Erro ao buscar mensagens:", e)
        return JSONResponse(status_code=500, content={"detail": str(e)})


# 🔹 Status completo com last_seen
@app.get("/alunos-status-completo/{prof_email}")
async def alunos_status_completo(prof_email: str):
    try:
        docs = db.collection('alunos_professor') \
                 .where('professor', '==', prof_email.strip().lower()).stream()

        alunos = []
        for doc in docs:
            data = doc.to_dict()
            nome = data.get("aluno")

            aluno_query = db.collection("alunos").where("nome", "==", nome).limit(1).stream()
            aluno_doc = next(aluno_query, None)

            if aluno_doc and aluno_doc.exists:
                aluno_data = aluno_doc.to_dict()
                alunos.append({
                    "nome": nome,
                    "online": aluno_data.get("online", False),
                    "last_seen": aluno_data.get("last_seen", "Desconhecido")
                })
            else:
                alunos.append({
                    "nome": nome,
                    "online": False,
                    "last_seen": "Desconhecido"
                })

        return alunos

    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": "Erro ao buscar status dos alunos", "erro": str(e)})


@app.get("/ver-professor/{aluno_nome}")
async def ver_professor(aluno_nome: str):
    try:
        aluno_normalizado = aluno_nome.strip().lower().replace(" ", "_")

        # Procurar vínculo do aluno
        docs = db.collection("alunos_professor") \
                 .where("aluno", "==", aluno_normalizado) \
                 .limit(1).stream()

        doc = next(docs, None)
        if not doc:
            raise HTTPException(status_code=404, detail="Aluno não possui professor vinculado")

        dados = doc.to_dict()
        professor_email = dados.get("professor")

        return {
            "aluno": aluno_normalizado,
            "professor": professor_email
        }

    except HTTPException:
        raise
    except Exception as e:
        print("Erro ao buscar professor vinculado:", e)
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno ao buscar professor"}
        )
        
@app.get("/alunos-status-completo/{prof_email}")
async def alunos_status_completo(prof_email: str):
    try:
        docs = db.collection('alunos_professor') \
                 .where('professor', '==', prof_email.strip()).stream()

        alunos = []
        for doc in docs:
            data = doc.to_dict()
            nome = data.get("aluno")

            # Buscar o documento na coleção "alunos"
            aluno_query = db.collection("alunos").where("nome", "==", nome).limit(1).stream()
            aluno_doc = next(aluno_query, None)

            if aluno_doc and aluno_doc.exists:
                aluno_data = aluno_doc.to_dict()
                alunos.append({
                    "nome": nome,
                    "online": aluno_data.get("online", False),
                    "last_seen": aluno_data.get("last_seen", "Desconhecido")
                })
            else:
                alunos.append({
                    "nome": nome,
                    "online": False,
                    "last_seen": "Desconhecido"
                })

        return alunos

    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": "Erro ao buscar status dos alunos", "erro": str(e)})


@app.put("/atualizar-status/{aluno_nome}/{status}")
async def atualizar_status_online(aluno_nome: str, status: bool):
    try:
        query = db.collection("alunos") \
                  .where("nome", "==", aluno_nome.strip()).stream()

        atualizado = False
        for doc in query:
            doc.reference.update({
                "online": status,
                "last_seen": datetime.now(timezone.utc).isoformat()
            })
            atualizado = True

        if not atualizado:
            raise HTTPException(status_code=404, detail="Aluno não encontrado na coleção 'alunos'")

        return {"message": f"Status do aluno '{aluno_nome}' atualizado para {status}"}

    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": "Erro ao atualizar status", "erro": str(e)})

@app.get("/buscar-professor/{nome_aluno}")
async def buscar_professor(nome_aluno: str):
    try:
        query = db.collection("alunos_professor") \
                  .where("aluno", "==", nome_aluno.strip()) \
                  .limit(1).stream()
        doc = next(query, None)

        if not doc:
            return JSONResponse(status_code=404, content={"professor": None, "disciplina": None})

        data = doc.to_dict()
        professor_email = data.get("professor")

        if not professor_email:
            return {"professor": "Desconhecido", "disciplina": "Desconhecida"}

        prof_query = db.collection("professores_online") \
                       .where("email", "==", professor_email.strip()) \
                       .limit(1).stream()
        prof_doc = next(prof_query, None)

        if not prof_doc:
            return {"professor": "Desconhecido", "disciplina": "Desconhecida"}

        prof_data = prof_doc.to_dict()
        return {
            "professor": prof_data.get("nome_completo", "Desconhecido"),
            "disciplina": prof_data.get("area_formacao", "Desconhecida")
        }

    except Exception as e:
        print("Erro ao buscar professor:", e)
        return JSONResponse(status_code=500, content={"detail": "Erro interno ao buscar professor"})

@app.get("/criar-conta", response_class=HTMLResponse)
async def criar_conta(request: Request):
    return templates.TemplateResponse("criar-conta.html", {"request": request})

@app.post("/criar-conta")
async def criar_conta_post(
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...)
):
    # Coleção: alunos_sabilider
    dados = {
        "nome": nome,
        "email": email,
        "senha": senha,
        "data_criacao": datetime.utcnow().isoformat()
    }
    db.collection("alunos_sabilider").add(dados)
    return RedirectResponse(url="/criar-conta", status_code=303)

@app.get("/quero-aulas", response_class=HTMLResponse)
async def quero_aulas(request: Request):
    return templates.TemplateResponse("quero-aulas.html", {"request": request})

@app.get("/precos", response_class=HTMLResponse)
async def ver_precos(request: Request):
    return templates.TemplateResponse("precos.html", {"request": request})

@app.get("/aulaonline", response_class=HTMLResponse)
async def aula_online(request: Request):
    return templates.TemplateResponse("aulaonline.html", {"request": request})

@app.get("/info-p.html", response_class=HTMLResponse)
async def mostrar_professores(request: Request):
    professores = carregar_professores_local()
    return templates.TemplateResponse("info-p.html", {"request": request, "professores": professores})

@app.post("/excluir-professor/{bi}")
async def excluir_professor(bi: str):
    profs = carregar_professores_local()
    profs = [p for p in profs if p.get("bi") != bi]
    salvar_professores_local(profs)
    excluir_professor_firebase(bi)
    gerar_html_professores()
    return RedirectResponse(url="/info-p.html", status_code=303)

@app.get("/editar-professor/{bi}", response_class=HTMLResponse)
async def editar_professor_form(bi: str, request: Request):
    profs = carregar_professores_local()
    professor = next((p for p in profs if p.get("bi") == bi), None)
    if not professor:
        return HTMLResponse("Professor não encontrado", status_code=404)
    return templates.TemplateResponse("editar-professor.html", {"request": request, "professor": professor})

@app.get("/dados-professor.html", response_class=HTMLResponse)
async def dados_professor(request: Request):
    return templates.TemplateResponse("dados-professor.html", {"request": request})

@app.post("/api/professores", response_class=JSONResponse)
async def receber_professor_api(professor: dict = Body(...)):
    profs = carregar_professores_local()
    profs.append(professor)
    salvar_professores_local(profs)
    gerar_html_professores()
    salvar_professor_firebase(professor)
    return {"message": "Professor registrado com sucesso"}

@app.get("/api/professores")
async def listar_professores():
    return JSONResponse(content=carregar_professores_local())

@app.get("/api/firebase-professores")
async def listar_professores_firebase():
    return JSONResponse(content=carregar_professores_firebase())

from firebase_admin import firestore

@app.post("/registrar-professor", response_class=HTMLResponse)
async def registrar_professor(
    request: Request,
    nome: str = Form(...), idade: str = Form(...), nome_pai: str = Form(...),
    nome_mae: str = Form(...), morada_atual: str = Form(...), ponto_referencia: str = Form(...),
    bi: str = Form(...), disciplinas: List[str] = Form([]), outras_disciplinas: Optional[str] = Form(""),
    telefone: str = Form(...), email: str = Form(...), latitude: str = Form(...),
    longitude: str = Form(...), doc_foto: UploadFile = File(...), doc_pdf: UploadFile = File(...)
):
    os.makedirs("static/docs", exist_ok=True)
    foto_path = f"static/docs/{doc_foto.filename}"
    pdf_path = f"static/docs/{doc_pdf.filename}"

    with open(foto_path, "wb") as buff:
        shutil.copyfileobj(doc_foto.file, buff)

    with open(pdf_path, "wb") as buff:
        shutil.copyfileobj(doc_pdf.file, buff)

    novo = {
        "nome": nome,
        "idade": idade,
        "nome_pai": nome_pai,
        "nome_mae": nome_mae,
        "morada_atual": morada_atual,
        "ponto_referencia": ponto_referencia,
        "bi": bi,
        "disciplinas": disciplinas,
        "outras_disciplinas": outras_disciplinas,
        "telefone": telefone,
        "email": email,
        "localizacao": f"Latitude: {latitude}, Longitude: {longitude}",
        "doc_foto": "/" + foto_path,
        "doc_pdf": "/" + pdf_path
    }

    # Salvar localmente
    profs = carregar_professores_local()
    profs.append(novo)
    salvar_professores_local(profs)
    gerar_html_professores()

    # Salvar na coleção antiga
    salvar_professor_firebase(novo)

    # ✅ Também salvar na nova coleção "professores_online2"
    db = firestore.client()
    db.collection("professores_online2").document(email).set(novo)

    return RedirectResponse(url="/pro-info.html", status_code=303)


@app.get("/gerar-pdf", response_class=FileResponse)
async def gerar_pdf():
    professores = carregar_professores_local()
    os.makedirs("static/docs", exist_ok=True)
    pdf_path = "static/docs/lista_professores.pdf"
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    y = height - 80

    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 50, "Novos alunos Registrados")
    data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 50, height - 30, f"Data: {data_hoje}")

    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import Image as RLImage

    for i, p in enumerate(professores):
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.darkblue)
        c.drawString(50, y, f"{i+1}. {p.get('nome','Sem nome')}")
        y -= 20
        c.setFont("Helvetica", 11)
        c.setFillColor(colors.black)

        for label, valor in [
            ("Idade", p.get("idade","")), ("Nome do Pai", p.get("nome_pai","")),
            ("Nome da Mãe", p.get("nome_mae","")), ("Morada Atual", p.get("morada_atual","")),
            ("Ponto de Referência", p.get("ponto_referencia","")), ("BI", p.get("bi","")),
            ("Disciplinas", ", ".join(p.get("disciplinas",[]))), ("Outras Disciplinas", p.get("outras_disciplinas","")),
            ("Telefone", p.get("telefone","")), ("Email", p.get("email","")),
            ("Localização", p.get("localizacao",""))
        ]:
            if valor:
                c.drawString(60, y, f"{label}: {valor}")
                y -= 15

        foto = p.get("doc_foto","").lstrip("/")
        if foto and os.path.exists(foto):
            try:
                c.drawImage(foto, width-6.5*cm, y-5*cm, width=5.5*cm, height=5.5*cm)
            except:
                c.drawString(60, y, "Erro ao carregar imagem.")
        y -= 100
        c.setStrokeColor(colors.grey)
        c.setLineWidth(0.5)
        c.line(50, y, width-50, y)
        y -= 30
        if y < 150:
            c.showPage()
            y = height - 80
            c.setFont("Helvetica-Bold", 18)
            c.drawCentredString(width/2, height-50, "Novos Professores Registrados")
            c.setFont("Helvetica", 10)
            c.drawRightString(width-50, height-30, f"Data: {data_hoje}")

    c.save()
    return FileResponse(pdf_path, media_type="application/pdf", filename="lista_professores.pdf")

@app.get("/cadastro-aluno", response_class=HTMLResponse)
async def exibir_formulario(request: Request):
    return templates.TemplateResponse("cadastro-aluno.html", {"request": request, "erro": None})
    
@app.post("/cadastro-aluno")
async def cadastrar_aluno(
    request: Request,
    nome: str = Form(...),
    nome_mae: str = Form(...),
    nome_pai: str = Form(...),
    senha: str = Form(...),
    provincia: str = Form(...),
    municipio: str = Form(...),
    bairro: str = Form(...),
    latitude: str = Form(...),
    longitude: str = Form(...),
    telefone: str = Form(...),
    disciplina: str = Form(...),
    bilhete: str = Form(...),
    outra_disciplina: str = Form(None),
    nivel_ingles: str = Form(...)
):
    alunos_ref = db.collection("alunos")
    nome_normalizado = nome.strip().lower()

    # 🔎 Verifica se já existe aluno com esse nome normalizado
    existente = alunos_ref.where("nome_normalizado", "==", nome_normalizado).get()
    if existente:
        return templates.TemplateResponse("cadastro-aluno.html", {
            "request": request,
            "erro": "Este nome já está cadastrado. Tente outro."
        })

    # 🔄 Busca histórico de pagamentos na coleção alunos_professor (com base no NOME, não no normalizado)
    paga_passado = []
    vinculo_query = db.collection("alunos_professor") \
        .where("aluno", "==", nome.strip().lower()) \
        .limit(1).stream()
    vinculo_doc = next(vinculo_query, None)
    if vinculo_doc:
        vinculo_data = vinculo_doc.to_dict()
        paga_passado = vinculo_data.get("paga_passado", [])

    # ✅ Gera ID único para o aluno
    aluno_id = str(uuid.uuid4())
    dados = {
        "nome": nome,
        "nome_normalizado": nome_normalizado,
        "nome_mae": nome_mae,
        "nome_pai": nome_pai,
        "senha": senha,
        "provincia": provincia,
        "municipio": municipio,
        "bairro": bairro,
        "localizacao": {
            "latitude": latitude,
            "longitude": longitude
        },
        "telefone": telefone,
        "disciplina": disciplina,
        "outra_disciplina": outra_disciplina,
        "bilhete": bilhete,
        "nivel_ingles": nivel_ingles,
        "progresso_ingles": 0,
        "online": False,
        "notificacao": False,
        "vinculado": False,
        "horario": {},
        "paga_passado": paga_passado  # ✅ agora usa dados de alunos_professor se existir
    }

    # Salva novo aluno
    db.collection("alunos").document(aluno_id).set(dados)

    # 🔄 Atualiza alunos antigos sem campo "paga_passado"
    alunos_antigos = alunos_ref.stream()
    for aluno in alunos_antigos:
        dados_aluno = aluno.to_dict()
        if "paga_passado" not in dados_aluno:
            paga_passado_antigo = []
            # busca também pelo NOME do aluno em alunos_professor
            vinculo_query = db.collection("alunos_professor") \
                .where("aluno", "==", dados_aluno.get("nome", "").strip().lower()) \
                .limit(1).stream()
            vinculo_doc = next(vinculo_query, None)
            if vinculo_doc:
                paga_passado_antigo = vinculo_doc.to_dict().get("paga_passado", [])
            alunos_ref.document(aluno.id).update({"paga_passado": paga_passado_antigo})

    return RedirectResponse(url="/login?sucesso=1", status_code=HTTP_303_SEE_OTHER)


@app.get("/login", response_class=HTMLResponse)
async def exibir_login(request: Request, sucesso: int = 0):
    return templates.TemplateResponse("login.html", {
        "request": request,
        "sucesso": sucesso,
        "erro": None
    })

@app.post("/login")
async def login(request: Request, nome: str = Form(...), senha: str = Form(...)):
    alunos_ref = db.collection("alunos")

    # Normaliza os valores digitados
    nome_digitado = nome.strip().lower()
    senha_digitada = senha.strip().lower()

    # Busca todos os alunos para fazer comparação segura
    alunos = alunos_ref.stream()

    for aluno in alunos:
        dados = aluno.to_dict()
        nome_banco = dados.get("nome", "").strip().lower()
        senha_banco = dados.get("senha", "").strip().lower()

        if nome_banco == nome_digitado and senha_banco == senha_digitada:
            aluno.reference.update({"online": True})
            return RedirectResponse(url=f"/perfil/{dados.get('nome')}", status_code=303)

    return templates.TemplateResponse("login.html", {
        "request": request,
        "erro": "Nome de usuário ou senha inválidos",
        "sucesso": 0
    })


@app.get("/perfil/{nome}", response_class=HTMLResponse)
async def profil(request: Request, nome: str):
    try:
        nome_normalizado = nome.strip().lower()
        print(f"🔍 Buscando dados do aluno: {nome_normalizado}")

        # Buscar aluno na coleção "alunos" pelo nome_normalizado
        query = db.collection("alunos") \
            .where("nome_normalizado", "==", nome_normalizado) \
            .limit(1) \
            .stream()

        aluno = None
        doc_id = None

        for doc in query:
            dados = doc.to_dict()
            aluno = {
                "nome": dados.get("nome", nome),  # nome real do aluno
                "bilhete": dados.get("bilhete", "Não informado"),
                "nivel_ingles": dados.get("nivel_ingles", "N/A"),
                "telefone": dados.get("telefone", "N/A"),
                "disciplina": dados.get("disciplina", "N/A")
            }
            doc_id = doc.id
            break

        if not aluno or not doc_id:
            return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

        # Atualizar status online
        db.collection("alunos").document(doc_id).update({
            "online": True,
            "ultimo_ping": datetime.utcnow().isoformat()
        })


        total_gasto = 0
        aulas_dadas = 0
        vinculo_id = None

        # 1) Buscar o vínculo em alunos_professor pelo nome_normalizado
        alunos_prof_ref = db.collection("alunos_professor") \
            .where("aluno", "==", nome_normalizado) \
            .limit(1) \
            .stream()

        for vinculo_doc in alunos_prof_ref:
            vinculo_data = vinculo_doc.to_dict()
            try:
                aulas_dadas = int(vinculo_data.get("aulas_dadas", 0) or 0)
            except Exception:
                aulas_dadas = 0
            vinculo_id = vinculo_doc.id
            break

        # 2) Buscar valor_total em comprovativos_pagamento/{nome_com_underscore}
        valor_total = 0
        doc_id_comprovativo = nome_normalizado.replace(" ", "_")
        comp_doc = db.collection("comprovativos_pagamento").document(doc_id_comprovativo).get()
        if comp_doc.exists:
            comp_data = comp_doc.to_dict() or {}
            mensalidade = comp_data.get("mensalidade") or {}
            raw_valor_total = mensalidade.get("valor_total", 0)

            try:
                valor_total = int(raw_valor_total)
            except Exception:
                try:
                    valor_total = int(float(raw_valor_total))
                except Exception:
                    valor_total = 0

        # 3) Calcular saldo
        total_gasto = valor_total - (aulas_dadas * 1250)
        if total_gasto < 0:
            total_gasto = 0

        # 4) Atualizar campo auxiliar no vínculo (se existir)
        if vinculo_id:
            db.collection("alunos_professor").document(vinculo_id).update({
                "valor_mensal_aluno": total_gasto
            })


        return templates.TemplateResponse("perfil.html", {
            "request": request,
            "aluno": aluno,
            "total_gasto": total_gasto
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return HTMLResponse(content=f"Erro ao carregar perfil: {str(e)}", status_code=500)

        
from slugify import slugify


def slug(texto):
    return slugify(texto.strip().lower())


def professor_possui_alunos(prof_email: str) -> bool:
    prof_email = prof_email.strip().lower()
    docs = db.collection('alunos_professor') \
             .where('professor', '==', prof_email) \
             .limit(1).stream()
    return next(docs, None) is not None


def buscar_professor_por_email(email: str):
    email = email.strip().lower()
    professores = db.collection("professores_online2") \
                    .where("email", "==", email) \
                    .limit(1).stream()
    for prof in professores:
        return prof.to_dict()
    return None

# ✅ Verifica se o vínculo entre aluno e professor existe
def vinculo_existe(prof_email: str, aluno_nome: str) -> Optional[dict]:
    prof_email = prof_email.strip().lower()
    aluno_nome = aluno_nome.strip().lower()

    docs = db.collection("alunos_professor") \
             .where("professor", "==", prof_email) \
             .where("aluno", "==", aluno_nome) \
             .limit(1).stream()
    return next(docs, None)


@app.get("/sala_virtual_professor", response_class=HTMLResponse)
async def get_sala_virtual_professor(
    request: Request,
    email: Optional[str] = Query(default=None),
    aluno: Optional[str] = Query(default=None)
):
    if not email:
        return HTMLResponse("<h2 style='color:red'>Erro: email não fornecido na URL.</h2>", status_code=400)

    try:
        email = email.strip().lower()
        aluno_normalizado = aluno.strip().lower() if aluno else None

        # 🔍 Busca o documento do professor
        doc_ref = db.collection("professores_online2").document(email)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(status_code=404, detail="Professor não encontrado.")

        professor = doc.to_dict()

        # 🧪 Valida vínculo com o aluno, se fornecido
        if aluno:
            # Buscar todos os documentos do professor na coleção alunos_professor
            docs = db.collection('alunos_professor') \
                .where('professor', '==', email).stream()

            vinculo_encontrado = False
            for d in docs:
                data = d.to_dict()
                dados_aluno = data.get("dados_aluno", {})
                nome_no_banco = dados_aluno.get("nome", "").strip().lower()
                if nome_no_banco == aluno_normalizado:
                    vinculo_encontrado = True
                    break

            if not vinculo_encontrado:
                return HTMLResponse(
                    "<h2 style='color:red'>Vínculo entre professor e aluno não encontrado.</h2>",
                    status_code=403
                )

        # 🔑 Gera ID da sala
        def slug(texto):
            return slugify(texto)

        sala_id = f"{slug(email)}-{slug(aluno_normalizado)}" if aluno else slug(email)

        return templates.TemplateResponse("sala_virtual_professor.html", {
            "request": request,
            "email": email,
            "aluno": aluno,
            "professor": professor,
            "sala_id": sala_id
        })

    except Exception as e:
        return HTMLResponse(f"<h2 style='color:red'>Erro ao abrir sala do professor: {str(e)}</h2>", status_code=500)

@app.get("/sala_virtual_aluno", response_class=HTMLResponse)
async def get_sala_virtual_aluno(
    request: Request,
    email: Optional[str] = Query(default=None),
    aluno: Optional[str] = Query(default=None)
):
    if not email or not aluno:
        return HTMLResponse("<h2 style='color:red'>Erro: Parâmetros faltando.</h2>", status_code=400)

    email_normalizado = email.strip().lower()
    aluno_normalizado = aluno.strip().lower()

    # Verifica se o aluno está vinculado ao professor
    aluno_data = vinculo_existe(email_normalizado, aluno_normalizado)
    if not aluno_data:
        return HTMLResponse("<h2 style='color:red'>Aluno não encontrado ou não vinculado ao professor.</h2>", status_code=403)

    # Verifica se o professor existe
    professor = buscar_professor_por_email(email_normalizado)
    if not professor:
        return HTMLResponse("<h2 style='color:red'>Professor não encontrado.</h2>", status_code=404)

    return templates.TemplateResponse("sala_virtual_aluno.html", {
        "request": request,
        "aluno": aluno.strip(),  
        "professor": email_normalizado
    })


import logging

MAX_TENTATIVAS = 3

def verificar_pagamento_existente(nome_comprovativo: str, aluno_nome: str) -> bool:
    """Verifica se o comprovativo já existe para o aluno no Firebase."""
    doc_ref = db.collection("comprovativos_pagamento").document(aluno_nome)
    doc = doc_ref.get()
    if doc.exists:
        comprovativos = doc.to_dict().get("comprovativos", [])
        return nome_comprovativo in comprovativos
    return False


def registrar_comprovativo_pagamento(nome_comprovativo: str, aluno_nome: str):
    """Registra o comprovativo no Firebase (somente nome)."""
    try:
        doc_ref = db.collection("comprovativos_pagamento").document(aluno_nome)
        doc = doc_ref.get()

        if doc.exists:
            dados = doc.to_dict()
            comprovativos = dados.get("comprovativos", [])
            comprovativos.append(nome_comprovativo)
            doc_ref.update({"comprovativos": comprovativos})
        else:
            doc_ref.set({"comprovativos": [nome_comprovativo]})

    except Exception as e:
        logging.error(f"Erro ao registrar comprovativo no Firebase: {e}")
        raise HTTPException(status_code=500, detail="Erro ao registrar comprovativo no Firebase.")


def atualizar_status_conta(aluno_nome: str, status: str):
    """Ativa ou desativa a conta do aluno na coleção 'alunos'."""
    alunos_ref = db.collection("alunos")
    docs = alunos_ref.stream()
    for doc in docs:
        dados = doc.to_dict()
        nome_banco = dados.get("nome", "").strip().lower()
        if nome_banco == aluno_nome:
            alunos_ref.document(doc.id).update({"ativacao_conta": status})


def registrar_pagamento_mensal(aluno_nome: str):
    """Armazena o pagamento na coleção 'alunos_professor' e zera valor_mensal_aluno."""
    docs = db.collection("alunos_professor").where("aluno", "==", aluno_nome).stream()
    for doc in docs:
        ref = db.collection("alunos_professor").document(doc.id)
        dados = doc.to_dict()
        valor_atual = dados.get("valor_mensal_aluno", 0)
        
        paga_passado = dados.get("paga_passado", {})
        proximo_indice = str(len(paga_passado))
        now = datetime.now(timezone.utc)
        paga_passado[proximo_indice] = {
            "ano": now.year,
            "mes": now.month,
            "data_pagamento": now.strftime("%Y-%m-%d"),
            "hora_pagamento": now.strftime("%H:%M:%S"),
            "valor_pago": valor_atual
        }
        
        ref.update({
            "valor_mensal_aluno": 0,
            "paga_passado": paga_passado
        })


import logging

MAX_TENTATIVAS = 3


@app.post("/upload_comprovativo", response_class=HTMLResponse)
async def upload_comprovativo(
    request: Request,
    aluno_nome: str = Form(...),
    banco: str = Form(...),
    meses: int = Form(...),
    comprovativo: UploadFile = File(...),
    tentativas: int = Form(default=0)
):
    try:
        aluno_normalizado = aluno_nome.strip().lower().replace(" ", "_")
        banco_norm = banco.strip().lower()

        # Limites de tamanho
        limites = {"bai": 32, "bni": 32, "bpc": 31, "multicaixa express": 33}
        if banco_norm not in limites:
            raise HTTPException(status_code=400, detail="Banco inválido.")

        # Validar tipo PDF
        if comprovativo.content_type != "application/pdf":
            return HTMLResponse("<h3>Apenas PDFs são aceites.</h3>", status_code=400)

        conteudo = await comprovativo.read()
        tamanho_kb = len(conteudo) / 1024

        if banco_norm == "multicaixa express":
            if tamanho_kb < 24 or tamanho_kb > 33:
                raise HTTPException(status_code=400, detail="Comprovativo inválido para Multicaixa Express.")
        elif tamanho_kb > limites[banco_norm]:
            raise HTTPException(status_code=400, detail=f"O comprovativo excede o limite para {banco.upper()}.")

        await comprovativo.close()
        nome_comprovativo = comprovativo.filename

        # Cálculo financeiro
        valor_mensal = 15000
        desconto_por_mes = 100
        desconto_total = meses * desconto_por_mes
        valor_total = (meses * valor_mensal) - desconto_total

        # Registrar no Firebase (mantive tua lógica)
        doc_ref = db.collection("comprovativos_pagamento").document(aluno_normalizado)
        if not doc_ref.get().exists:
            doc_ref.set({"comprovativos": []})

        if verificar_pagamento_existente(nome_comprovativo, aluno_normalizado):
            tentativas += 1
            if tentativas >= MAX_TENTATIVAS:
                atualizar_status_conta(aluno_normalizado, "Desativada")
                return HTMLResponse("<h3>Comprovativo já existe. Conta desativada.</h3>", status_code=403)
            return HTMLResponse(f"<h3>Comprovativo já existe. Tentativas restantes: {MAX_TENTATIVAS - tentativas}</h3>", status_code=400)

        registrar_comprovativo_pagamento(nome_comprovativo, aluno_normalizado)
        registrar_pagamento_mensal(aluno_normalizado)
        atualizar_status_conta(aluno_normalizado, "Ativada")

        doc_ref.update({
            "mensalidade": {
                "meses": meses,
                "valor_total": valor_total,
                "valor_mensal": valor_mensal,
                "desconto_total": desconto_total
            }
        })

        # Criar PDF no servidor
        pdf_path = f"static/recibo_{aluno_normalizado}.pdf"
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        styles = getSampleStyleSheet()
        elementos = []

        elementos.append(Paragraph("<b>Sabi Lider</b> - N.I.F nº 5002232529", styles["Title"]))
        elementos.append(Spacer(1, 12))
        elementos.append(Paragraph("<b>Recibo de Pagamento</b>", styles["Heading2"]))
        elementos.append(Spacer(1, 20))

        dados = [
            ["Aluno", aluno_nome],
            ["Banco", banco.upper()],
            ["Meses", str(meses)],
            ["Mensalidade", f"{valor_mensal:,.0f} Kz"],
            ["Desconto", f"{desconto_total:,.0f} Kz"],
            ["Valor Total", f"{valor_total:,.0f} Kz"],
            ["Comprovativo", nome_comprovativo],
        ]

        tabela = Table(dados, hAlign="LEFT")
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.grey),
            ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
            ("ALIGN", (0,0), (-1,-1), "LEFT"),
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("BACKGROUND", (0,1), (-1,-1), colors.beige),
        ]))

        elementos.append(tabela)
        doc.build(elementos)

        # Retornar HTML com botão de download
        html_content = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Recibo Gerado</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background: #f4f4f8;
                    padding: 20px;
                    text-align: center;
                }}
                .btn {{
                    padding: 12px 20px;
                    border-radius: 8px;
                    font-size: 16px;
                    text-decoration: none;
                    margin: 10px;
                    display: inline-block;
                }}
                .download {{
                    background: #28a745;
                    color: white;
                }}
                .perfil {{
                    background: #007bff;
                    color: white;
                }}
                @media(max-width:600px) {{
                    body {{
                        padding: 10px;
                    }}
                    .btn {{
                        width: 100%;
                        font-size: 14px;
                    }}
                }}
            </style>
        </head>
        <body>
            <h2>✅ Recibo Gerado com Sucesso!</h2>
            <a href="/static/recibo_{aluno_normalizado}.pdf" class="btn download" download>📄 Baixar Recibo PDF</a>
            <a href="/perfil/{aluno_normalizado}" class="btn perfil">🔙 Voltar ao Perfil</a>
        </body>
        </html>
        """

        return HTMLResponse(content=html_content)

    except Exception as e:
        logging.error(f"Erro inesperado: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar comprovativo: {str(e)}")


@app.get("/enviar_comprovativo", response_class=HTMLResponse)
async def enviar_comprovativo(request: Request, aluno_nome: str):
    aluno_normalizado = aluno_nome.strip().lower()
    return templates.TemplateResponse(
        "enviar_comprovativo.html",
        {"request": request, "aluno_nome": aluno_nome, "aluno_normalizado": aluno_normalizado}
    )


@app.get("/sala_virtual_aluno/{sala}")
async def redirecionar_para_sala_aluno(sala: str):
    decoded = unquote(sala)

    if "-" not in decoded or decoded.count("-") < 1:
        return HTMLResponse(
            "<h2 style='color:red'>Formato inválido: esperado 'email-do-professor-nome-do-aluno'</h2>",
            status_code=400
        )

    try:
        professor_email, aluno_nome = decoded.split("-", 1)
    except Exception as e:
        return HTMLResponse(f"<h2 style='color:red'>Erro ao processar os dados da sala: {str(e)}</h2>", status_code=400)

    return RedirectResponse(
        url=f"/sala_virtual_aluno?email={professor_email}&aluno={aluno_nome}"
    )


def vinculo_existe(prof_email: str, aluno_nome: str) -> dict:
    """
    Verifica se o aluno está vinculado ao professor (normalizando os dados dos dois lados).
    """
    prof_email = prof_email.strip().lower()
    aluno_nome = aluno_nome.strip().lower()

    try:
        docs = db.collection("alunos_professor") \
                 .where("professor", "==", prof_email) \
                 .stream()

        for doc in docs:
            data = doc.to_dict()
            nome_banco = data.get("aluno", "").strip().lower()

            if nome_banco == aluno_nome:
                return data

        return None
    except Exception as e:
        print(f"❌ Erro ao verificar vínculo: {e}")
        return None

@app.post("/solicitar_entrada")
async def solicitar_entrada(
    nome_aluno: str = Form(...),
    senha_aluno: str = Form(...),
    peer_id_aluno: str = Form(...),
    id_professor: str = Form(...)
):
    try:
        aluno_info = vinculo_existe(id_professor, nome_aluno)

        if not aluno_info:
            return JSONResponse(
                status_code=403,
                content={"autorizado": False, "motivo": "Aluno não está vinculado ao professor."}
            )

        if aluno_info.get("senha") != senha_aluno:
            return JSONResponse(
                status_code=403,
                content={"autorizado": False, "motivo": "Senha incorreta."}
            )

        print(f"✅ Solicitação autorizada: {nome_aluno} para professor {id_professor} com PeerID {peer_id_aluno}")
        return JSONResponse(content={"autorizado": True})

    except Exception as e:
        print(f"Erro ao verificar solicitação: {e}")
        return JSONResponse(
            status_code=500,
            content={"autorizado": False, "erro": "Erro interno ao verificar vínculo."}
        )

@app.get("/logout/{nome}")
async def logout(nome: str):
    db = firestore.client()
    alunos_ref = db.collection("alunos")
    query = alunos_ref.where("nome", "==", nome).stream()
    for aluno in query:
        aluno.reference.update({"online": False})
    return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)
    
@app.post("/logout")
async def logout(request: Request):
    data = await request.json()
    nome = data.get("nome")
    db = firestore.client()
    alunos_ref = db.collection("alunos")
    query = alunos_ref.where("nome", "==", nome).stream()
    for aluno in query:
        aluno.reference.update({"online": False})
    return RedirectResponse(url="/", status_code=303)

@app.post("/alterar-senha/{nome}")
async def alterar_senha(
    request: Request,
    nome: str,
    senha_antiga: str = Form(...),
    nova_senha: str = Form(...),
    confirmar_senha: str = Form(...)
):
    aluno_docs = db.collection("alunos").where("nome", "==", nome).get()
    if not aluno_docs:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    aluno_ref = aluno_docs[0].reference
    aluno_data = aluno_docs[0].to_dict()

    if senha_antiga != aluno_data.get("senha"):
        return templates.TemplateResponse("perfil.html", {
            "request": request,
            "aluno": aluno_data,
            "erro_senha": "Senha antiga incorreta!"
        })

    if nova_senha != confirmar_senha:
        return templates.TemplateResponse("perfil.html", {
            "request": request,
            "aluno": aluno_data,
            "erro_senha": "As novas senhas não coincidem!"
        })

    aluno_ref.update({"senha": nova_senha})
    aluno_data["senha"] = nova_senha  # para manter os dados atualizados na recarga

    return templates.TemplateResponse("perfil.html", {
        "request": request,
        "aluno": aluno_data,
        "sucesso_senha": "Senha alterada com sucesso!"
    })


@app.post("/ping-online")
async def ping_online(payload: dict = Body(...)):
    nome = payload.get("nome")
    if not nome:
        return {"status": "erro", "mensagem": "Nome não fornecido"}

    aluno_ref = db.collection("alunos").where("nome", "==", nome).get()
    if aluno_ref:
        doc = aluno_ref[0]
        db.collection("alunos").document(doc.id).update({
            "online": True,
            "ultimo_ping": datetime.utcnow().isoformat()
        })
        return {"status": "ok"}
    else:
        return {"status": "erro", "mensagem": "Aluno não encontrado"}

@app.post("/atualizar-perfil/{nome}")
async def atualizar_perfil(
    request: Request,
    nome: str,
    telefone: str = Form(...),
    bairro: str = Form(...),
    municipio: str = Form(...),
    provincia: str = Form(...),
    disciplina: str = Form(...),
    outra_disciplina: str = Form(None)
):
    aluno_docs = db.collection("alunos").where("nome", "==", nome).get()
    if not aluno_docs:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    aluno_ref = aluno_docs[0].reference
    dados_atuais = aluno_docs[0].to_dict()

    atualizacoes = {
        "telefone": telefone,
        "bairro": bairro,
        "municipio": municipio,
        "provincia": provincia,
        "disciplina": disciplina,
    }

    if outra_disciplina:
        disciplinas_existentes = dados_atuais.get("outras_disciplinas", [])
        disciplinas_existentes.append(outra_disciplina)
        atualizacoes["outras_disciplinas"] = disciplinas_existentes

    aluno_ref.update(atualizacoes)
    return RedirectResponse(url=f"/perfil/{nome}", status_code=HTTP_303_SEE_OTHER)


@app.post("/verificar-aluno")
async def verificar_aluno(
    nome_aluno: str = Form(...),
    senha: str = Form(...),
    professor_id: str = Form(...)
):
    try:
        # Simula verificação de senha – você pode melhorar isso futuramente
        # Aqui consideramos apenas o nome e a presença dele na lista
        ref = db.collection("lista_de_alunos").document(professor_id)
        doc = ref.get()

        if doc.exists and nome_aluno in doc.to_dict().get("alunos", []):
            return JSONResponse({"status": "autorizado", "mensagem": "Acesso liberado para aula."})
        else:
            return JSONResponse({"status": "nao_autorizado", "mensagem": "Faça a sua solicitação ao professor."})

    except Exception as e:
        return JSONResponse({"status": "erro", "mensagem": str(e)})

@app.post("/verificar-aluno")
async def verificar_aluno(
    nome_aluno: str = Form(...),
    senha: str = Form(...),
    professor_id: str = Form(...)
):
    try:
        # Pega o documento da lista de alunos do professor
        ref_lista = db.collection("lista_de_alunos").document(professor_id)
        doc_lista = ref_lista.get()

        # Verifica se o aluno está na lista do professor
        if doc_lista.exists and nome_aluno in doc_lista.to_dict().get("alunos", []):
            # Pega os dados do aluno na coleção 'alunos'
            ref_aluno = db.collection("alunos").document(nome_aluno)
            doc_aluno = ref_aluno.get()

            if doc_aluno.exists:
                dados_aluno = doc_aluno.to_dict()
                senha_registrada = dados_aluno.get("senha")

                if senha == senha_registrada:
                    return JSONResponse({"status": "autorizado", "mensagem": "Acesso liberado para aula."})
                else:
                    return JSONResponse({"status": "erro", "mensagem": "Senha incorreta."})
            else:
                return JSONResponse({"status": "erro", "mensagem": "Aluno não encontrado no sistema."})
        else:
            return JSONResponse({"status": "nao_autorizado", "mensagem": "Você ainda não foi autorizado para essa aula."})

    except Exception as e:
        return JSONResponse({"status": "erro", "mensagem": str(e)})

@app.get("/professores_online", response_class=HTMLResponse)
async def get_cadastro(request: Request):
    return templates.TemplateResponse("professores_online.html", {"request": request, "success": False})

@app.post("/professores_online", response_class=HTMLResponse) 
async def post_cadastro(
    request: Request,
    nome_completo: str = Form(...),
    nome_mae: str = Form(...),
    nome_pai: str = Form(...),
    bilhete: str = Form(...),
    provincia: str = Form(...),
    municipio: str = Form(...),
    bairro: str = Form(...),
    residencia: str = Form(...),
    ponto_referencia: str = Form(...),
    localizacao: str = Form(...),
    telefone: str = Form(...),
    telefone_alternativo: str = Form(""),
    email: str = Form(...),
    nivel_ensino: str = Form(...),
    ano_faculdade: str = Form(""),
    area_formacao: str = Form(...),
    senha: str = Form(...)
):
    dados = {
        "nome_completo": nome_completo,
        "nome_mae": nome_mae,
        "nome_pai": nome_pai,
        "bilhete": bilhete,
        "provincia": provincia,
        "municipio": municipio,
        "bairro": bairro,
        "residencia": residencia,
        "ponto_referencia": ponto_referencia,
        "localizacao": localizacao,
        "telefone": telefone,
        "telefone_alternativo": telefone_alternativo,
        "email": email,
        "nivel_ensino": nivel_ensino,
        "ano_faculdade": ano_faculdade,
        "area_formacao": area_formacao,
        "senha": senha,
        "online": True
    }

    # ✅ Coleção original (mantém como está)
    db.collection("professores_online").add(dados)

    # ✅ Nova coleção: professores_online2 com email como ID
    try:
        db.collection("professores_online2").document(email).set(dados)
        print(f"✅ Salvo em professores_online2 com ID {email}")
    except Exception as e:
        print(f"❌ Erro ao salvar em professores_online2: {e}")

    return RedirectResponse(url="/login_prof", status_code=303)


@app.get("/login_prof", response_class=HTMLResponse)
async def login_prof_get(request: Request):
    return templates.TemplateResponse("login_prof.html", {"request": request, "erro": None})


@app.post("/login_prof", response_class=HTMLResponse)
async def login_prof_post(
    request: Request,
    nome_completo: str = Form(...),
    senha: str = Form(...)
):
    professores_ref = db.collection("professores_online").where("nome_completo", "==", nome_completo).stream()

    for prof in professores_ref:
        dados = prof.to_dict()
        if dados.get("senha") == senha:
            email = dados.get("email")

            # Atualiza o campo 'online' para True
            db.collection("professores_online").document(prof.id).update({
                "online": True
            })

            return RedirectResponse(url=f"/perfil_prof?email={email}", status_code=303)

    # ❌ Se não encontrou ou senha incorreta
    return templates.TemplateResponse("login_prof.html", {
        "request": request,
        "erro": "Nome completo ou senha incorretos."
    })

@app.post("/dados_professor", response_class=HTMLResponse)
async def dados_professor(request: Request, email: str = Form(...)):
    try:
        email = email.strip().lower()
        prof_query = db.collection("professores_online").where("email", "==", email).limit(1).stream()
        for prof_doc in prof_query:
            dados = prof_doc.to_dict()

            # Pegar salários se já estiverem salvos
            salario_info = dados.get("salario", {})
            saldo_atual = salario_info.get("saldo_atual", 0)
            salario_mensal = salario_info.get("mensal_estimado", 0)

            return templates.TemplateResponse("perfil_prof.html", {
                "request": request,
                "professor": dados,
                "saldo_atual": saldo_atual,
                "salario_mensal": salario_mensal,
                "total_aulas": 0,  # ou pegue do Firestore se necessário
                "valor_por_aula": 1250,
                "total_a_receber": saldo_atual
            })

        return HTMLResponse(content="Professor não encontrado.", status_code=404)
    except Exception as e:
        return HTMLResponse(content=f"Erro interno: {str(e)}", status_code=500)


@app.post("/logout_prof", response_class=HTMLResponse)
async def logout_prof(request: Request, email: str = Form(...)):
    professores_ref = db.collection("professores_online").where("email", "==", email).stream()

    for prof in professores_ref:
        db.collection("professores_online").document(prof.id).update({
            "online": False
        })
        break  # só precisa atualizar um documento

    return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)

@app.get("/meus-dados")
async def meus_dados(email: str = Query(...)):
    prof_ref = db.collection("professores_online").where("email", "==", email).limit(1).stream()
    prof_doc = next(prof_ref, None)

    if not prof_doc:
        return {"erro": "Professor não encontrado"}

    return prof_doc.to_dict()

@app.get("/aulas-dia")
async def aulas_dadas_no_dia(email: str = Query(...)):
    # Em produção, puxar do Firebase a agenda desse professor
    return {
        "professor": email,
        "data": "2025-06-08",
        "aulas": ["Matemática 10º Ano", "Física 11º Ano"],
        "quantidade": 2
    }

@app.get("/aulas-semana")
async def aulas_dadas_na_semana(email: str = Query(...)):
    return {
        "professor": email,
        "semana": "03 a 08 de Junho",
        "aulas": ["Matemática", "Física", "Química", "Inglês"],
        "quantidade": 7
    }

@app.get("/aulas-mes")
async def aulas_dadas_no_mes(email: str = Query(...)):
    return {
        "professor": email,
        "mes": "Junho",
        "quantidade": 28,
        "resumo": "Aulas ministradas com regularidade nas 4 semanas."
    }

@app.get("/sala_virtual", response_class=HTMLResponse)
async def sala_virtual(request: Request, email: str):
    """
    Página da sala de aula online do professor.
    O professor será identificado pelo email enviado via query string.
    """
    professores_ref = db.collection("professores_online")
    query = professores_ref.where("email", "==", email).limit(1).stream()
    prof_doc = next(query, None)

    if not prof_doc:
        return templates.TemplateResponse("erro.html", {"request": request, "mensagem": "Professor não encontrado para criar a sala."})

    prof_data = prof_doc.to_dict()
    prof_data["id"] = prof_doc.id

    return templates.TemplateResponse("inonline.html", {
        "request": request,
        "professor": prof_data
    })

@app.post("/verificar_aluno")
async def verificar_aluno(request: Request):
    dados = await request.json()
    nome = dados.get("nome")
    senha = dados.get("senha")

    with open("alunos.json", "r") as f:
        alunos = json.load(f)

    for aluno in alunos:
        if aluno["nome"] == nome and aluno["senha"] == senha:
            return {"ok": True}
    return JSONResponse(status_code=403, content={"erro": "Nome ou senha incorretos."})


@app.get("/professor-do-aluno/{nome_aluno}")
async def professor_do_aluno(nome_aluno: str):
    try:
        aluno_normalizado = nome_aluno.strip().lower()

        query = db.collection("alunos_professor") \
                  .where("aluno", "==", aluno_normalizado) \
                  .limit(1).stream()
        vinculo_doc = next(query, None)

        if not vinculo_doc:
            return JSONResponse(
                status_code=404,
                content={
                    "professor": None,
                    "disciplina": None,
                    "mensagem": f"Aluno '{aluno_normalizado}' não vinculado a nenhum professor"
                }
            )

        vinculo_data = vinculo_doc.to_dict()
        professor_email = vinculo_data.get("professor")

        if not professor_email:
            return {"professor": "Desconhecido", "disciplina": "Desconhecida"}

        prof_query = db.collection("professores_online") \
                       .where("email", "==", professor_email.strip().lower()) \
                       .limit(1).stream()
        prof_doc = next(prof_query, None)

        if not prof_doc:
            return {"professor": "Desconhecido", "disciplina": "Desconhecida"}

        prof_data = prof_doc.to_dict()

        return {
            "professor": prof_data.get("nome_completo", "Desconhecido"),
            "disciplina": prof_data.get("area_formacao", "Desconhecida"),
            "email": professor_email.strip().lower(),
            "mensagens": vinculo_data.get("mensagens", [])  # 🔹 já retorna as mensagens
        }

    except Exception as e:
        print("Erro ao buscar professor do aluno:", e)
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno ao buscar professor do aluno", "erro": str(e)}
        )


@app.get("/meu-professor-status/{nome_aluno}") 
async def meu_professor_status(nome_aluno: str):
    try:
        # Nome recebido da URL
        nome_original = nome_aluno.strip()

        # Normalizar para comparação (aceita underscores ou espaços)
        nome_aluno_input = nome_original.lower().replace("_", " ")

        # Procurar o aluno na coleção "alunos"
        alunos_ref = db.collection("alunos").stream()
        aluno_doc = None
        for doc in alunos_ref:
            dados = doc.to_dict()
            nome_banco = dados.get("nome", "").strip().lower()
            if nome_banco == nome_aluno_input:
                aluno_doc = doc
                break

        if not aluno_doc:
            return JSONResponse(content={
                "aluno": nome_original,
                "professor": "Aluno não encontrado",
                "online": False
            }, status_code=404)

        # Verificar vínculo na coleção "alunos_professor"
        vinculo_ref = db.collection("alunos_professor") \
                        .where("aluno", "==", nome_aluno_input) \
                        .limit(1) \
                        .stream()
        vinculo_doc = next(vinculo_ref, None)

        if not vinculo_doc:
            return JSONResponse(content={
                "aluno": nome_original,
                "professor": "Nenhum professor vinculado",
                "online": False
            }, status_code=404)

        dados_vinculo = vinculo_doc.to_dict()
        professor_nome = dados_vinculo.get("professor", "Professor não especificado")
        online_status = dados_vinculo.get("online", False)

        return JSONResponse(content={
            "aluno": nome_original,
            "professor": professor_nome,
            "online": online_status
        }, status_code=200)

    except Exception as e:
        print("Erro ao obter status do professor:", e)
        return JSONResponse(content={
            "erro": f"Erro interno: {str(e)}"
        }, status_code=500)


@app.post("/iniciar-aula")
async def iniciar_aula(payload: dict):
    aluno = payload.get("aluno", "").strip().lower()
    professor = payload.get("professor", "").strip().lower()
    sala = payload.get("sala", "")

    db.collection("chamadas_ao_vivo").document(aluno).set({
        "aluno": aluno,
        "professor": professor,
        "sala": sala,
        "status": "pendente",
        "timestamp": firestore.SERVER_TIMESTAMP
    })

    return {"mensagem": "Chamada enviada ao aluno"}

# 🔸 Verificar vínculo do aluno com o professor
@app.post('/verificar-vinculo')
async def verificar_vinculo(dados: dict):
    prof_email = dados.get('professor_email', '').strip().lower()
    aluno_nome = dados.get('aluno_nome', '').strip().lower()
    senha = dados.get('senha', '').strip()

    try:
        docs = db.collection('alunos_professor') \
                 .where('professor', '==', prof_email).stream()

        aluno_encontrado = False
        for doc in docs:
            data = doc.to_dict()
            dados_aluno = data.get('dados_aluno', {})
            nome_salvo = dados_aluno.get('nome', '').strip().lower()
            if nome_salvo == aluno_nome:
                aluno_encontrado = True
                break

        if not aluno_encontrado:
            raise HTTPException(status_code=404, detail="Vínculo com este aluno não encontrado.")

        aluno_docs = db.collection('alunos') \
                       .where('nome', '==', aluno_nome) \
                       .where('senha', '==', senha) \
                       .limit(1).stream()
        aluno_doc = next(aluno_docs, None)
        if not aluno_doc:
            raise HTTPException(status_code=403, detail="Senha incorreta.")

        return {"message": "Aluno autorizado."}

    except HTTPException:
        raise
    except Exception as e:
        print("Erro ao verificar vínculo:", e)
        raise HTTPException(status_code=500, detail="Erro interno.")

# 🔸 Verificar vínculo e professor do aluno
class VerificarAlunoInput(BaseModel):
    aluno_nome: str
    senha: str

@app.post("/verificar-aluno-vinculo")
async def verificar_aluno_vinculo(data: VerificarAlunoInput):
    try:
        aluno_nome = data.aluno_nome.strip().lower()
        senha = data.senha.strip()

        aluno_docs = db.collection('alunos') \
            .where('nome', '==', aluno_nome) \
            .limit(1).stream()

        aluno_doc = next(aluno_docs, None)
        if not aluno_doc:
            raise HTTPException(status_code=404, detail="Aluno não encontrado.")

        aluno_data = aluno_doc.to_dict()
        if aluno_data.get("senha") != senha:
            raise HTTPException(status_code=401, detail="Senha incorreta.")

        vinculo_docs = db.collection('alunos_professor') \
            .where('aluno', '==', aluno_nome) \
            .limit(1).stream()

        vinculo_doc = next(vinculo_docs, None)
        if not vinculo_doc:
            raise HTTPException(status_code=404, detail="Nenhum vínculo encontrado com professor.")

        vinculo_data = vinculo_doc.to_dict()
        professor_email = vinculo_data.get("professor", "").strip().lower()

        prof_docs = db.collection('professores_online') \
            .where('email', '==', professor_email) \
            .limit(1).stream()

        prof_doc = next(prof_docs, None)
        professor_nome = prof_doc.to_dict().get("nome_completo", "Professor") if prof_doc else "Professor"

        return {
            "professor_email": professor_email,
            "professor_nome": professor_nome
        }

    except HTTPException:
        raise
    except Exception as e:
        print("Erro interno:", e)
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno ao verificar vínculo do aluno."}
        )

class NotificacaoRequest(BaseModel):
    aluno: str

@app.post("/ativar-notificacao")
async def ativar_notificacao(data: NotificacaoRequest):
    try:
        aluno_nome = data.aluno.strip().lower()

        # Buscar o documento do aluno na coleção alunos_professor
        docs = db.collection("alunos_professor") \
                 .where("aluno", "==", aluno_nome) \
                 .limit(1).stream()
        doc = next(docs, None)

        if not doc:
            return JSONResponse(
                content={"msg": f"Aluno '{aluno_nome}' não encontrado."},
                status_code=404
            )

        db.collection("alunos_professor").document(doc.id).update({"notificacao": True})
        return {"msg": f"Notificação ativada para o aluno '{aluno_nome}'."}

    except Exception as e:
        return JSONResponse(
            content={"msg": f"Erro ao ativar notificação: {str(e)}"},
            status_code=500
        )


class AlunoInfo(BaseModel):
    aluno: str

@app.post("/desativar-notificacao")
async def desativar_notificacao(info: AlunoInfo):
    try:
        aluno = info.aluno.strip().lower()

        docs = db.collection("alunos_professor") \
                 .where("aluno", "==", aluno) \
                 .limit(1).stream()

        doc = next(docs, None)

        if not doc:
            return JSONResponse(
                content={"status": "erro", "mensagem": "Aluno não encontrado"},
                status_code=404
            )

        doc.reference.update({"notificacao": False})
        return {"status": "ok", "mensagem": "Notificação desativada"}

    except Exception as e:
        return JSONResponse(
            content={"status": "erro", "mensagem": f"Erro ao desativar notificação: {str(e)}"},
            status_code=500
        )


@app.post("/verificar-notificacao")
async def verificar_notificacao(request: Request):
    try:
        dados = await request.json()
        nome_aluno = str(dados.get("aluno", "")).strip().lower()

        if not nome_aluno:
            return JSONResponse(content={"erro": "Nome do aluno não fornecido"}, status_code=400)

        query = db.collection("alunos_professor") \
                  .where("aluno", "==", nome_aluno) \
                  .limit(1).stream()

        doc = next(query, None)

        if not doc:
            return JSONResponse(
                content={"notificacao": False, "mensagem": "Aluno não encontrado"},
                status_code=404
            )

        dados_aluno = doc.to_dict()
        notificacao = dados_aluno.get("notificacao", False)
        professor_email = dados_aluno.get("professor", "")

        return JSONResponse(content={
            "notificacao": notificacao,
            "professor_email": professor_email
        })

    except Exception as e:
        return JSONResponse(content={"erro": str(e)}, status_code=500)


from fastapi import Request
from fastapi.responses import JSONResponse

@app.post("/registrar-chamada")
async def registrar_chamada(request: Request):
    try:
        dados = await request.json()
        aluno_raw = dados.get("aluno")
        professor_raw = dados.get("professor")

        if not aluno_raw or not professor_raw:
            return JSONResponse(content={"erro": "Dados incompletos"}, status_code=400)

        # Normalização
        aluno_normalizado = str(aluno_raw).strip().lower().replace(" ", "")
        professor_normalizado = str(professor_raw).strip().lower()
        nome_sala = f"{professor_normalizado.replace(' ', '_')}-{aluno_normalizado}"

        # Verificar vínculo
        vinculo_docs = db.collection("alunos_professor") \
                         .where("professor", "==", professor_normalizado) \
                         .stream()

        vinculo_encontrado = False
        for doc in vinculo_docs:
            data = doc.to_dict()
            aluno_db = data.get("aluno", "").strip().lower().replace(" ", "")
            if aluno_db == aluno_normalizado:
                vinculo_encontrado = True
                break

        if not vinculo_encontrado:
            return JSONResponse(
                content={"erro": "Vínculo entre professor e aluno não encontrado."},
                status_code=403
            )

        # Verificar ou criar o documento de chamada
        doc_ref = db.collection("chamadas_ao_vivo").document(aluno_normalizado)
        doc = doc_ref.get()

        if not doc.exists:
            # 🔧 Se não existir, cria automaticamente com status 'aceito'
            doc_ref.set({
                "aluno": aluno_normalizado,
                "professor": professor_normalizado,
                "status": "aceito",
                "sala": nome_sala
            }, merge=True)

            return JSONResponse(
                content={
                    "mensagem": "Conexão autorizada - documento criado.",
                    "sala": nome_sala
                },
                status_code=200
            )

        # Verificar status existente
        dados_atuais = doc.to_dict() or {}
        status_atual = dados_atuais.get("status", "")

        if status_atual == "aceito":
            doc_ref.set({
                "aluno": aluno_normalizado,
                "professor": professor_normalizado,
                "sala": nome_sala
            }, merge=True)

            return JSONResponse(
                content={
                    "mensagem": "Conexão autorizada com status 'aceito'.",
                    "sala": nome_sala
                },
                status_code=200
            )

        elif status_atual == "pendente":
            return JSONResponse(
                content={"erro": "Aguardando o aluno aceitar a chamada..."},
                status_code=403
            )

        elif status_atual == "recusado":
            return JSONResponse(
                content={"erro": "O aluno recusou a chamada."},
                status_code=403
            )

        else:
            return JSONResponse(
                content={"erro": f"Status de chamada desconhecido: '{status_atual}'"},
                status_code=403
            )

    except Exception as e:
        print(f"❌ ERRO AO REGISTRAR CHAMADA: {str(e)}")
        return JSONResponse(
            content={"erro": f"Erro interno ao registrar chamada: {str(e)}"},
            status_code=500
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/verificar-transmissao/{professor_email}/{aluno_nome}")
def verificar_transmissao(professor_email: str, aluno_nome: str):
    professor_id = professor_email.strip().lower()
    aluno_id = aluno_nome.strip().lower().replace(" ", "_")

    doc_ref = db.collection("chamadas_ao_vivo").document(aluno_id)
    doc = doc_ref.get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Chamada não encontrada")

    dados = doc.to_dict()
    if dados.get("professor") != professor_id:
        raise HTTPException(status_code=400, detail="Professor não corresponde")

    status = dados.get("status", "")
    if status == "aceito":
        return {"status": "ok", "sala": f"{professor_id}-{aluno_id}"}
    elif status == "pendente":
        return {"status": "aguardando"}
    elif status == "rejeitado":
        return {"status": "rejeitado"}
    else:
        return {"status": "desconhecido"}

@app.post("/definir-status-ok")
def definir_status_ok(dados: dict):
    aluno = dados.get("aluno")
    if not aluno:
        raise HTTPException(status_code=400, detail="Aluno não informado")

    aluno_id = aluno.strip().lower().replace(" ", "_")
    ref = db.collection("chamadas_ao_vivo").document(aluno_id)
    ref.set({"status": "aceito"}, merge=True)

    return {"msg": "Status definido como aceito"}

@app.get("/verificar-status/{aluno_nome}")
def verificar_status(aluno_nome: str):
    try:
        if not aluno_nome:
            return JSONResponse(content={"erro": "Aluno não especificado"}, status_code=400)

        aluno_id = aluno_nome.strip().lower().replace(" ", "_")
        ref = db.collection("chamadas_ao_vivo").document(aluno_id)
        doc = ref.get()

        if doc.exists:
            status = doc.to_dict().get("status", "pendente")
            if status == "pendente":
                ref.update({"status": "aceito"})
                status = "aceito"
            return {"status": status}
        else:
            return {"status": "nao_encontrado"}

    except Exception as e:
        return JSONResponse(content={"erro": str(e)}, status_code=500)
        
@app.post("/ver-aulas")
async def ver_aulas(request: Request):
    try:
        dados = await request.json()
        aluno_raw = dados.get("aluno", "")
        if not aluno_raw:
            return JSONResponse(content={"erro": "Nome do aluno ausente"}, status_code=400)

        aluno_normalizado = str(aluno_raw).strip().lower().replace(" ", "")

        db_firestore = firestore.client()
        query = db_firestore.collection("alunos_professor").stream()

        aluno_encontrado = None
        for doc in query:
            dados_doc = doc.to_dict()
            aluno_db = dados_doc.get("aluno", "").strip().lower().replace(" ", "")
            if aluno_db == aluno_normalizado:
                aluno_encontrado = dados_doc
                break

        if not aluno_encontrado:
            return JSONResponse(content={"erro": "Aluno não encontrado"}, status_code=404)

        aulas = aluno_encontrado.get("aulas", [])
        total_dadas = aluno_encontrado.get("aulas_dadas", 0)
        total_previstas = aluno_encontrado.get("total_aulas", 24)
        restantes = max(0, total_previstas - total_dadas)

        return JSONResponse(content={
            "aulas_dadas": total_dadas,
            "restantes": restantes,
            "aulas": aulas
        })

    except Exception as e:
        print("Erro ao buscar aulas:", e)
        return JSONResponse(content={"erro": str(e)}, status_code=500)


@app.get("/listar-alunos")
async def listar_alunos():
    alunos_ref = db.collection("alunos").stream()
    alunos = []

    for doc in alunos_ref:
        dados = doc.to_dict()
        nome = dados.get("nome", "")
        disciplina = dados.get("disciplina", "")
        online = dados.get("online", False)
        vinculado = dados.get("vinculado", False)
        alunos.append({
            "nome": nome,
            "disciplina": disciplina,
            "online": online,
            "vinculado": vinculado
        })

    return alunos

@app.get("/listar-professores-online")
async def listar_professores_online():
    professores = db.collection("professores_online").stream()
    lista = []

    for prof in professores:
        dados = prof.to_dict()
        lista.append({
            "email": dados.get("email", ""),
            "nome": dados.get("nome_completo", ""),  # Novo campo incluído
            "online": dados.get("online", False)
        })

    return lista

@app.get("/listar-chamadas")
async def listar_chamadas():
    chamadas_ref = db.collection("chamadas_ao_vivo").stream()
    lista = []

    for ch in chamadas_ref:
        dados = ch.to_dict()
        lista.append({
            "aluno": dados.get("aluno", ""),
            "professor": dados.get("professor", ""),
            "status": dados.get("status", "")
        })

    return lista


@app.get("/relatorio-aulas")
async def relatorio_aulas():
    relatorio_ref = db.collection("alunos_professor").stream()
    resultado = []
    notificacoes = []

    for doc in relatorio_ref:
        dados = doc.to_dict()
        aulas_dadas = dados.get("aulas_dadas", 0)
        aluno_nome = dados.get("aluno", "")

        # Notificações baseadas no número de aulas
        if aulas_dadas == 12:
            notificacoes.append(f"O aluno {aluno_nome} já completou 12 aulas.")
        elif aulas_dadas == 72:
            notificacoes.append(f"O aluno {aluno_nome} já completou o curso de 72 aulas.")

        resultado.append({
            "professor": dados.get("professor", ""),
            "aluno": aluno_nome,
            "aulas_dadas": aulas_dadas
        })

    return {"relatorio": resultado, "notificacoes": notificacoes}

@app.get("/alunos-nao-vinculados")
async def listar_alunos_nao_vinculados():
    try:
        alunos_ref = db.collection("alunos") \
                       .where("vinculado", "==", False) \
                       .stream()

        alunos_disponiveis = []
        for doc in alunos_ref:
            dados = doc.to_dict()
            alunos_disponiveis.append({
                "nome": dados.get("nome", ""),
                "disciplina": dados.get("disciplina", ""),
                "bairro": dados.get("bairro", ""),
                "provincia": dados.get("provincia", ""),
                "online": dados.get("online", False)
            })

        return JSONResponse(content=alunos_disponiveis)

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"erro": "Erro ao buscar alunos não vinculados", "detalhes": str(e)}
        )


@app.post("/remover-aluno")
async def remover_aluno(request: Request):
    dados = await request.json()
    nome_raw = dados.get("nome", "")
    nome = str(nome_raw).strip()

    if not nome:
        return JSONResponse(content={"erro": "Nome do aluno ausente"}, status_code=400)

    print("🔍 Nome recebido:", nome)

    db = firestore.client()
    docs = db.collection("alunos").where("nome", "==", nome).stream()
    achou = False

    for doc in docs:
        print("📌 Documento encontrado:", doc.id)
        doc.reference.delete()
        achou = True

    if achou:
        return {"mensagem": f"Aluno {nome} removido com sucesso"}
    else:
        print("⚠️ Nenhum aluno encontrado com esse nome.")
        return JSONResponse(content={"erro": "Aluno não encontrado"}, status_code=404)


@app.post("/remover-professor")
async def remover_professor(request: Request):
    dados = await request.json()
    email_raw = dados.get("email", "")
    email = str(email_raw).strip().lower()

    if not email:
        return JSONResponse(content={"erro": "Email do professor ausente"}, status_code=400)

    print("🔍 Email recebido:", email_raw)
    print("🔍 Email normalizado:", email)

    db = firestore.client()
    docs = db.collection("professores_online").where("email", "==", email).stream()
    achou = False

    for doc in docs:
        print("📌 Documento encontrado:", doc.id)
        doc.reference.delete()
        achou = True

    # Também remove da coleção professores_online2, onde o email é o ID
    try:
        db.collection("professores_online2").document(email).delete()
        print("🗑️ Removido de professores_online2")
    except Exception as e:
        print("⚠️ Erro ao remover de professores_online2:", e)

    if achou:
        return {"mensagem": f"Professor {email_raw} removido com sucesso"}
    else:
        return JSONResponse(content={"erro": "Professor não encontrado"}, status_code=404)


@app.post("/enviar-mensagem-professor")
async def enviar_mensagem_professor(request: Request):
    dados = await request.json()
    destino = dados.get("email", "").strip().lower()
    texto = dados.get("mensagem", "").strip()

    if not destino or not texto:
        return {"erro": "Email e mensagem são obrigatórios"}

    db_firestore = firestore.client()
    doc_ref = db_firestore.collection("mensagens_professores").document(destino)

    # Buscar mensagens anteriores (se existirem)
    doc = doc_ref.get()
    mensagens = doc.to_dict().get("mensagens", []) if doc.exists else []

    # Adicionar nova mensagem com data
    nova_mensagem = {
        "texto": texto,
        "data": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    mensagens.append(nova_mensagem)

    # Atualizar no Firestore
    doc_ref.set({"mensagens": mensagens})

    return {"mensagem": "Mensagem enviada com sucesso"}

@app.get("/mensagens-professor/{email}")
async def mensagens_professor(email: str):
    email = email.strip().lower()
    db_firestore = firestore.client()
    doc_ref = db_firestore.collection("mensagens_professores").document(email)
    doc = doc_ref.get()
    if doc.exists:
        return {"mensagens": doc.to_dict().get("mensagens", [])}
    return {"mensagens": []}


# Data base fixa: Domingo, 3 de agosto de 2025, às 11h10
data_base = datetime(2025, 8, 3, 11, 10)  # Domingo

dias_map = {
    0: "Dom",  # 0 = Domingo
    1: "Seg",
    2: "Ter",
    3: "Qua",
    4: "Qui",
    5: "Sex",
    6: "Sab"
}

dias_traduzidos = {
    "Seg": "Segunda-feira",
    "Ter": "Terça-feira",
    "Qua": "Quarta-feira",
    "Qui": "Quinta-feira",
    "Sex": "Sexta-feira",
    "Sab": "Sábado",
    "Dom": "Domingo"
}

@app.post("/aulas_do_dia")
async def aulas_do_dia(request: Request):
    try:
        dados = await request.json()
        professor_email = dados.get("professor_email", "").strip().lower()

        if not professor_email:
            return JSONResponse(content={"erro": "E-mail do professor é obrigatório."}, status_code=400)

        # Calcular o número de dias passados desde a data base
        dias_passados = (datetime.now() - data_base).days

        # Dia da semana (Domingo = 0, Segunda = 1, ..., Sábado = 6)
        dia_semana_index = (0 + dias_passados) % 7
        dia_abreviado = dias_map[dia_semana_index]

        aulas = []
        docs = db.collection("alunos_professor") \
                 .where("professor", "==", professor_email).stream()

        for doc in docs:
            data = doc.to_dict()
            aluno_nome = data.get("aluno", "").strip().lower()

            aluno_docs = db.collection("alunos") \
                .where("nome_normalizado", "==", aluno_nome).limit(1).stream()

            for aluno_doc in aluno_docs:
                aluno_data = aluno_doc.to_dict()
                horarios = aluno_data.get("horario", {}).get(dia_abreviado, [])
                if horarios:
                    aulas.append({
                        "aluno": aluno_data.get("nome", aluno_nome),
                        "horarios": horarios,
                        "preco": "1.500 Kz"
                    })

        return JSONResponse(content={"aulas": aulas})
    except Exception as e:
        return JSONResponse(status_code=500, content={"erro": f"Erro interno: {str(e)}"})


@app.post("/aulas_da_semana")
async def aulas_da_semana(request: Request):
    try:
        dados = await request.json()
        professor_email = dados.get("professor_email", "").strip().lower()

        if not professor_email:
            return JSONResponse(content={"erro": "E-mail do professor é obrigatório."}, status_code=400)

        # ✅ OrderedDict garante a ordem
        resultado = OrderedDict({
            "Domingo": [],
            "Segunda-feira": [],
            "Terça-feira": [],
            "Quarta-feira": [],
            "Quinta-feira": [],
            "Sexta-feira": [],
            "Sábado": []
        })

        # Buscar os alunos vinculados ao professor
        docs = db.collection("alunos_professor") \
                 .where("professor", "==", professor_email).stream()

        for doc in docs:
            data = doc.to_dict()
            aluno_nome = data.get("aluno", "").strip().lower()

            aluno_docs = db.collection("alunos") \
                .where("nome_normalizado", "==", aluno_nome).limit(1).stream()

            for aluno_doc in aluno_docs:
                aluno_data = aluno_doc.to_dict()
                horarios_por_dia = aluno_data.get("horario", {})

                for dia_abrev, horarios in horarios_por_dia.items():
                    dia_completo = dias_traduzidos.get(dia_abrev)
                    if dia_completo and dia_completo in resultado:
                        resultado[dia_completo].append({
                            "aluno": aluno_data.get("nome", aluno_nome),
                            "horarios": horarios,
                            "preco": "1.500 Kz"
                        })

        return JSONResponse(content={"aulas": resultado})

    except Exception as e:
        return JSONResponse(status_code=500, content={"erro": f"Erro interno: {str(e)}"})

@app.post("/ultimas-aulas")
async def ultimas_aulas(request: Request):
    try:
        dados = await request.json()
        professor_email = dados.get("professor_email", "").strip().lower()
        skip = int(dados.get("skip", 0))
        limit = int(dados.get("limit", 5))

        if not professor_email:
            return JSONResponse(
                status_code=400,
                content={"erro": "E-mail do professor é obrigatório."}
            )

        documentos = db.collection("alunos_professor") \
                       .where("professor", "==", professor_email).stream()

        lista_aulas = []

        for doc in documentos:
            doc_dict = doc.to_dict()
            nome_aluno = doc_dict.get("aluno", "Aluno desconhecido")
            aulas = doc_dict.get("aulas", [])

            for aula in aulas:
                lista_aulas.append({
                    "nome": nome_aluno,
                    "data": aula.get("data", ""),
                    "horario": aula.get("horario", "")
                })

        # Ordenar por data + horário em ordem decrescente
        def parse_datetime(aula):
            try:
                return datetime.strptime(f"{aula['data']} {aula['horario']}", "%Y-%m-%d %H:%M")
            except:
                return datetime.min

        lista_aulas.sort(key=parse_datetime, reverse=True)

        return {
            "ultimas_aulas": lista_aulas[skip:skip+limit],
            "total": len(lista_aulas)
        }

    except Exception as e:
        print("Erro ao buscar últimas aulas:", e)
        return JSONResponse(
            status_code=500,
            content={"erro": "Erro interno ao buscar últimas aulas"}
        )

        
class HorarioEnvio(BaseModel):
    aluno_nome: str
    professor_email: str
    horario: dict

@app.post("/enviar-horario")
async def enviar_horario(request: Request):
    try:
        dados = await request.json()
        aluno_nome = dados.get("aluno_nome", "").strip().lower()
        professor_email = dados.get("professor_email", "").strip().lower()
        horario = dados.get("horario")  # dict esperado

        if not aluno_nome or not professor_email or not horario:
            return JSONResponse(status_code=400, content={"detail": "Dados incompletos."})

        doc_id = f"{aluno_nome}_{professor_email}"

        print(f"🟢 Vai gravar EM alunos → nome_normalizado: {aluno_nome} | Dados: {horario}")

        # ✅ Atualiza o campo 'horario' na coleção 'alunos' usando 'nome_normalizado'
        alunos_query = db.collection("alunos") \
            .where("nome_normalizado", "==", aluno_nome) \
            .limit(1) \
            .stream()

        aluno_found = False
        for aluno_doc in alunos_query:
            aluno_doc.reference.update({"horario": horario})
            aluno_found = True
            print(f"✅ Horário atualizado na coleção alunos → ID: {aluno_doc.id}")
            break

        if not aluno_found:
            print("⚠️ Aluno não encontrado na coleção alunos para atualizar horário.")

        # Atualizar também o campo horario na coleção alunos_professor
        query = db.collection("alunos_professor") \
            .where("professor", "==", professor_email) \
            .where("aluno", "==", aluno_nome) \
            .limit(1) \
            .stream()

        doc_found = False
        for doc in query:
            doc.reference.update({"horario": horario})
            doc_found = True
            print(f"✅ Horário também atualizado em alunos_professor → ID: {doc.id}")
            break

        if not doc_found:
            print("⚠️ Vínculo não encontrado na coleção alunos_professor para atualizar horário.")

        return {"mensagem": "Horário enviado e atualizado com sucesso."}

    except Exception as e:
        print("🔴 Erro ao enviar horário:", e)
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.get("/ver-horario-aluno/{nome}")
async def ver_horario_aluno(nome: str):
    try:
        nome = nome.strip()
        query = db.collection("alunos").where("nome", "==", nome).limit(1).stream()
        for doc in query:
            dados = doc.to_dict()
            if "horario" in dados:
                horario = dados["horario"]

                # Tradução dos dias
                dias_traduzidos = {
                    "Seg": "Segunda-feira",
                    "Ter": "Terça-feira",
                    "Qua": "Quarta-feira",
                    "Qui": "Quinta-feira",
                    "Sex": "Sexta-feira",
                    "Sab": "Sábado",
                    "Dom": "Domingo"
                }

                horario_traduzido = {}
                for dia, horarios in horario.items():
                    nome_completo = dias_traduzidos.get(dia, dia)
                    horario_traduzido[nome_completo] = horarios

                return {"horario": horario_traduzido}
            else:
                return {"erro": "Horário não encontrado para este aluno."}
        return {"erro": "Aluno não encontrado."}
    except Exception as e:
        return {"erro": f"Erro ao buscar horário: {str(e)}"}


@app.get("/custos-aluno/{nome}", response_class=HTMLResponse)
async def ver_custos_aluno(request: Request, nome: str):
    try:
        nome_normalizado = nome.strip().lower()
        print(f"🔍 Verificando custos do aluno: {nome_normalizado}")

        # Buscar os vínculos do aluno na coleção alunos_professor
        vinculos = db.collection("alunos_professor").where(
            "aluno", "==", nome_normalizado
        ).stream()

        valor_por_aula = 1250
        total_aulas_previstas = 0
        total_aulas_dadas = 0
        detalhes_aulas = []

        for doc in vinculos:
            dados = doc.to_dict()
            try:
                professor = dados.get("professor", "Desconhecido")
                qtd_total = int(dados.get("total_aulas", 0))
                qtd_dadas = int(dados.get("aulas_dadas", 0))

                total_aulas_previstas += qtd_total
                total_aulas_dadas += qtd_dadas

                datas = dados.get("datas_aulas", [])
                for d in datas:
                    detalhes_aulas.append({
                        "data": d,
                        "professor": professor,
                        "disciplina": dados.get("dados_aluno", {}).get("disciplina", "N/A")
                    })

            except Exception as e:
                print(f"⚠️ Erro ao processar vínculo do aluno: {e}")
                continue

        total_gasto = total_aulas_dadas * valor_por_aula
        total_pacote = total_aulas_previstas * valor_por_aula

        return templates.TemplateResponse("custos_aluno.html", {
            "request": request,
            "nome_aluno": nome_normalizado.title(),
            "total_gasto": total_gasto,
            "valor_por_aula": valor_por_aula,
            "total_aulas_dadas": total_aulas_dadas,
            "total_aulas_previstas": total_aulas_previstas,
            "total_pacote": total_pacote,
            "aulas": detalhes_aulas
        })

    except Exception as e:
        print(f"❌ Erro ao calcular custos do aluno: {e}")
        return HTMLResponse(content=f"Erro ao calcular os custos: {str(e)}", status_code=500)

@app.get("/saldo-atual")
async def obter_saldo_atual(request: Request):
    try:
        email = request.query_params.get("email")
        if not email:
            return JSONResponse(content={"erro": "Email não informado"}, status_code=400)

        email = email.strip().lower()

        # Função para tratar valores "Undefined" e None
        def safe_value(val, default=""):
            if str(type(val)).endswith("Undefined'>"):  # evita precisar importar Undefined
                return default
            if val is None:
                return default
            return val

        prof_ref = db.collection("professores_online").where(
            filter=FieldFilter("email", "==", email)
        ).limit(1).stream()

        for doc in prof_ref:
            professor = doc.to_dict() or {}
            salario_info = safe_value(professor.get("salario"), {}) or {}
            saldo_atual = int(safe_value(salario_info.get("saldo_atual"), 0))
            return JSONResponse(content={"saldo_atual": saldo_atual})

        return JSONResponse(content={"erro": "Professor não encontrado"}, status_code=404)

    except Exception as e:
        print(f"❌ Erro ao obter saldo: {e}")
        return JSONResponse(content={"erro": str(e)}, status_code=500)
        
@app.post("/inserir-perguntas")
def inserir_perguntas():
    total = 0
    perguntas_por_nivel = obter_perguntas_ingles()  # <-- Correto agora!
    for nivel, perguntas in perguntas_por_nivel.items():
        for i, p in enumerate(perguntas):
            doc_id = f"{nivel}_{i+1}"
            db.collection("perguntas_ingles").document(doc_id).set({
                "pergunta": p["pergunta"],
                "resposta": p["resposta"],
                "nivel": nivel
            })
            total += 1
    return {"mensagem": f"✅ {total} perguntas inseridas na coleção 'perguntas_ingles' com sucesso!"}


@app.get("/inserir-perguntas")
def inserir_perguntas_get():
    return inserir_perguntas()  # Reaproveita a lógica do POST


# ✅ Corrigido: função com nome diferente da variável
def obter_perguntas_ingles():
    return {
        "iniciante": [
            {"pergunta": "You ___ a student.", "resposta": "are"},
            {"pergunta": "I ___ happy.", "resposta": "am"},
            {"pergunta": "He ___ a doctor.", "resposta": "is"},
            {"pergunta": "She ___ my friend.", "resposta": "is"},
            {"pergunta": "We ___ ready.", "resposta": "are"},
            {"pergunta": "They ___ teachers.", "resposta": "are"},
            {"pergunta": "It ___ a cat.", "resposta": "is"},
            {"pergunta": "I ___ from Angola.", "resposta": "am"},
            {"pergunta": "He ___ not here.", "resposta": "is"},
            {"pergunta": "She ___ beautiful.", "resposta": "is"},
            {"pergunta": "They ___ playing football.", "resposta": "are"},
            {"pergunta": "We ___ in the classroom.", "resposta": "are"},
            {"pergunta": "It ___ raining.", "resposta": "is"},
            {"pergunta": "You ___ very kind.", "resposta": "are"},
            {"pergunta": "I ___ tired.", "resposta": "am"},
            {"pergunta": "My name ___ John.", "resposta": "is"},
            {"pergunta": "They ___ not at home.", "resposta": "are"},
            {"pergunta": "We ___ hungry.", "resposta": "are"},
            {"pergunta": "This ___ my book.", "resposta": "is"},
            {"pergunta": "Those ___ my shoes.", "resposta": "are"}
        ],
        "intermediario": [
            {"pergunta": "She ___ to school every day.", "resposta": "goes"},
            {"pergunta": "We ___ dinner at 7 PM.", "resposta": "have"},
            {"pergunta": "They ___ in Luanda last year.", "resposta": "were"},
            {"pergunta": "He ___ not like coffee.", "resposta": "does"},
            {"pergunta": "I ___ playing the guitar now.", "resposta": "am"},
            {"pergunta": "What ___ you doing?", "resposta": "are"},
            {"pergunta": "We ___ been to Brazil.", "resposta": "have"},
            {"pergunta": "He ___ watching TV when I arrived.", "resposta": "was"},
            {"pergunta": "She ___ already eaten.", "resposta": "has"},
            {"pergunta": "___ you ever traveled alone?", "resposta": "have"},
            {"pergunta": "They ___ working since morning.", "resposta": "have been"},
            {"pergunta": "I ___ my homework before dinner.", "resposta": "did"},
            {"pergunta": "She ___ a new phone yesterday.", "resposta": "bought"},
            {"pergunta": "Where ___ you go on vacation?", "resposta": "did"},
            {"pergunta": "He ___ English fluently.", "resposta": "speaks"}
        ],
        "avancado": [
            {"pergunta": "If I ___ more time, I would travel.", "resposta": "had"},
            {"pergunta": "She would have come if she ___ invited.", "resposta": "had been"},
            {"pergunta": "He ___ finished the work by now.", "resposta": "should have"},
            {"pergunta": "I wish I ___ taller.", "resposta": "were"},
            {"pergunta": "By next year, they ___ graduated.", "resposta": "will have"},
            {"pergunta": "He acts as if he ___ the boss.", "resposta": "were"},
            {"pergunta": "No sooner ___ I arrived than it started to rain.", "resposta": "had"},
            {"pergunta": "Had I known, I ___ helped you.", "resposta": "would have"},
            {"pergunta": "She demanded that he ___ on time.", "resposta": "be"},
            {"pergunta": "It’s essential that she ___ informed immediately.", "resposta": "be"},
            {"pergunta": "Hardly ___ he left when the phone rang.", "resposta": "had"},
            {"pergunta": "He ___ rather stay home than go out.", "resposta": "would"},
            {"pergunta": "Were I rich, I ___ travel the world.", "resposta": "would"},
            {"pergunta": "If only I ___ spoken up earlier.", "resposta": "had"},
            {"pergunta": "She speaks as though she ___ everything.", "resposta": "knew"}
        ],
        "fluente": [
            {"pergunta": "Not only ___ he smart, but also kind.", "resposta": "is"},
            {"pergunta": "Scarcely ___ I sat down when she arrived.", "resposta": "had"},
            {"pergunta": "Little ___ they know about the truth.", "resposta": "do"},
            {"pergunta": "Rarely ___ we see such talent.", "resposta": "do"},
            {"pergunta": "So beautiful ___ the painting that everyone stopped to look.", "resposta": "was"},
            {"pergunta": "No sooner ___ the meeting started than he left.", "resposta": "had"},
            {"pergunta": "Were it not for her help, I ___ failed.", "resposta": "would have"},
            {"pergunta": "Under no circumstances ___ you open that door.", "resposta": "must"},
            {"pergunta": "Only after the rain stopped ___ we leave the house.", "resposta": "did"},
            {"pergunta": "Seldom ___ a mistake like that.", "resposta": "does he make"},
            {"pergunta": "Hardly ever ___ such a mistake occur.", "resposta": "does"},
            {"pergunta": "Had it not been for the traffic, I ___ on time.", "resposta": "would have arrived"},
            {"pergunta": "Never before ___ I seen such a view.", "resposta": "have"},
            {"pergunta": "Not until she spoke ___ I realize the truth.", "resposta": "did"},
            {"pergunta": "Only by working hard ___ you succeed.", "resposta": "can"}
        ]
    }


@app.get("/ajustar-progresso-ingles")
async def ajustar_progresso_ingles():
    alunos_ref = db.collection("alunos").stream()
    count = 0

    for aluno_doc in alunos_ref:
        aluno_data = aluno_doc.to_dict()
        update_data = {}

        if "progresso_ingles" not in aluno_data:
            update_data["progresso_ingles"] = 0
        if "progresso_ingles1" not in aluno_data:
            update_data["progresso_ingles1"] = 0
        if "progresso_ingles2" not in aluno_data:
            update_data["progresso_ingles2"] = 0
        if "progresso_ingles3" not in aluno_data:
            update_data["progresso_ingles3"] = 0
        if "progresso_ingles4" not in aluno_data:
            update_data["progresso_ingles4"] = 0

        if update_data:
            aluno_doc.reference.update(update_data)
            count += 1

    # Dados das perguntas para as coleções separadas
    perguntas_ingles1 = [
        # nível iniciante (exemplo)
        {"pergunta": "What is your name?", "resposta": "my name is"},
        {"pergunta": "Where do you live?", "resposta": "i live in"},
        {"pergunta": "How old are you?", "resposta": "i am"},
        
    ]

    perguntas_ingles2 = [
        # nível intermediário
        {"pergunta": "She ___ to school every day.", "resposta": "goes"},
        {"pergunta": "We ___ dinner at 7 PM.", "resposta": "have"},
        {"pergunta": "They ___ in Luanda last year.", "resposta": "were"},
       
    ]

    perguntas_ingles3 = [
        # nível avançado
        {"pergunta": "If I ___ more time, I would travel.", "resposta": "had"},
        {"pergunta": "She would have come if she ___ invited.", "resposta": "had been"},
        {"pergunta": "He ___ finished the work by now.", "resposta": "should have"},
  
    ]

    perguntas_ingles4 = [
        # nível fluente
        {"pergunta": "Not only ___ he smart, but also kind.", "resposta": "is"},
        {"pergunta": "Scarcely ___ I sat down when she arrived.", "resposta": "had"},
        {"pergunta": "Little ___ they know about the truth.", "resposta": "do"},
       
    ]

    # Função para popular coleção, cuidando para não duplicar
    def popular_colecao(nome_colecao, perguntas):
        colecao_ref = db.collection(nome_colecao)
        docs = list(colecao_ref.stream())
        if docs:
            print(f"🛑 Coleção {nome_colecao} já populada, pulando inserção.")
            return  # já populado, evita duplicar
        batch = db.batch()
        for pergunta in perguntas:
            doc_ref = colecao_ref.document()  # gera ID automático
            batch.set(doc_ref, pergunta)
        batch.commit()
        print(f"✅ Coleção {nome_colecao} populada com {len(perguntas)} perguntas.")

    popular_colecao("perguntas_ingles1", perguntas_ingles1)
    popular_colecao("perguntas_ingles2", perguntas_ingles2)
    popular_colecao("perguntas_ingles3", perguntas_ingles3)
    popular_colecao("perguntas_ingles4", perguntas_ingles4)

    return {"mensagem": f"Campos criados/atualizados em {count} alunos e coleções de perguntas criadas."}


# Dicionário de níveis
proximo_nivel = {
    "iniciante": "intermediario",
    "intermediario": "avancado",
    "avancado": "fluente"
}

# Sinônimos de níveis
mapa_niveis = {
    "basico": "iniciante",
    "inicial": "iniciante",
    "intermedio": "intermediario",
    "medio": "intermediario",
    "avançado": "avancado",
    "fluente": "fluente"
}

# Mapas de níveis
mapa_niveis = {
    "basico": "iniciante",
    "inicial": "iniciante",
    "intermedio": "intermediario",
    "medio": "intermediario",
    "avancado": "avancado",
    "fluente": "fluente"
}

proximo_nivel = {
    "iniciante": "intermediario",
    "intermediario": "avancado",
    "avancado": "fluente"
}


import unicodedata

# 🔹 Função global para todas as rotas
def remover_acentos(texto: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

@app.get("/pergunta-ingles")
async def pergunta_ingles(nome: str, nivel: str = None):
    mapa_niveis = {
        "basico": "iniciante",
        "inicial": "iniciante",
        "intermedio": "intermediario",
        "medio": "intermediario",
        "avancado": "avancado",
        "fluente": "fluente"
    }

    proximo_nivel = {
        "iniciante": "intermediario",
        "intermediario": "avancado",
        "avancado": "fluente"
    }

    nome = remover_acentos(nome.strip().lower())

    # Busca aluno pelo nome
    aluno_ref = db.collection("alunos").where("nome_normalizado", "==", nome).limit(1).get()
    if not aluno_ref:
        return JSONResponse(status_code=404, content={"erro": "Aluno não encontrado"})

    doc = aluno_ref[0]
    aluno = doc.to_dict()

    # Define nível
    if nivel:
        nivel = mapa_niveis.get(nivel.strip().lower(), "iniciante")
    else:
        nivel_raw = aluno.get("nivel_ingles", "iniciante").strip().lower()
        nivel = mapa_niveis.get(nivel_raw, "iniciante")

    # Progresso do aluno
    progresso = aluno.get("progresso_ingles", 0)
    if not isinstance(progresso, int) or progresso < 0:
        progresso = 0

    # Busca perguntas do nível
    perguntas_ref = db.collection("perguntas_ingles") \
        .where("nivel", "==", nivel) \
        .order_by("pergunta") \
        .stream()
    perguntas = [{"id": p.id, **p.to_dict()} for p in perguntas_ref]

    # Caso tenha terminado as perguntas -> subir nível
    if progresso >= len(perguntas):
        if nivel in proximo_nivel:
            novo_nivel = proximo_nivel[nivel]
            doc.reference.update({
                "nivel_ingles": novo_nivel,
                "progresso_ingles": 0
            })
            print(f"🚀 {aluno.get('nome', nome)} subiu de {nivel.upper()} para {novo_nivel.upper()}.")

            prox_perguntas_ref = db.collection("perguntas_ingles") \
                .where("nivel", "==", novo_nivel) \
                .order_by("pergunta") \
                .stream()
            prox_perguntas = [{"id": p.id, **p.to_dict()} for p in prox_perguntas_ref]

            if prox_perguntas:
                primeira = prox_perguntas[0]
                return JSONResponse(content={
                    "mensagem": "Subiu de nível!",
                    "novo_nivel": novo_nivel,
                    "id": primeira["id"],
                    "pergunta": primeira["pergunta"],
                    "nivel": novo_nivel,
                    "numero": 0
                })
            else:
                return JSONResponse(content={"mensagem": "Subiu de nível, mas não há perguntas no próximo nível."})
        else:
            return JSONResponse(content={"status": "maximo", "mensagem": "Você já está no nível máximo!"})

    # Caso ainda tenha perguntas no nível
    if perguntas:
        pergunta_atual = perguntas[progresso]
        return JSONResponse(content={
            "id": pergunta_atual["id"],
            "pergunta": pergunta_atual["pergunta"],
            "nivel": nivel,
            "numero": progresso
        })

    return JSONResponse(content={"status": "sem-perguntas", "mensagem": "Nenhuma pergunta disponível para este nível."})


@app.post("/proxima-pergunta")
async def proxima_pergunta(data: dict = Body(...)):
    mapa_niveis = {
        "basico": "iniciante",
        "inicial": "iniciante",
        "intermedio": "intermediario",
        "medio": "intermediario",
        "avancado": "avancado",
        "fluente": "fluente"
    }

    nome = data.get("nome", "").strip()
    nome_normalizado = remover_acentos(nome.lower())

    aluno_ref = db.collection("alunos").where("nome_normalizado", "==", nome_normalizado).limit(1).get()
    if not aluno_ref:
        return JSONResponse(status_code=404, content={"erro": "Aluno não encontrado"})

    aluno_doc = aluno_ref[0]
    aluno = aluno_doc.to_dict()

    progresso = aluno.get("progresso_ingles", 0) + 1
    db.collection("alunos").document(aluno_doc.id).update({
        "progresso_ingles": progresso
    })

    nivel_raw = aluno.get("nivel_ingles", "iniciante").strip().lower()
    nivel = mapa_niveis.get(nivel_raw, "iniciante")

    perguntas_ref = db.collection("perguntas_ingles") \
        .where("nivel", "==", nivel) \
        .order_by("pergunta") \
        .stream()

    perguntas = [{"id": p.id, **p.to_dict()} for p in perguntas_ref]

    if progresso >= len(perguntas):
        return JSONResponse(content={"status": "final-nivel"})

    pergunta_atual = perguntas[progresso]

    return JSONResponse(content={
        "id": pergunta_atual["id"],
        "pergunta": pergunta_atual["pergunta"],
        "nivel": nivel,
        "numero": progresso
    })


@app.post("/verificar-resposta")
async def verificar_resposta(data: dict = Body(...)):
    nome = data.get("nome", "").strip().lower()
    resposta_user = remover_acentos(data.get("resposta", "").strip().lower())
    pergunta_id = data.get("pergunta_id", "").strip()

    aluno_ref = db.collection("alunos").where("nome_normalizado", "==", nome).limit(1).get()
    if not aluno_ref:
        return JSONResponse(status_code=404, content={"erro": "Aluno não encontrado"})

    doc = aluno_ref[0]
    aluno = doc.to_dict()

    pergunta_ref = db.collection("perguntas_ingles").document(pergunta_id).get()
    if not pergunta_ref.exists:
        return JSONResponse(status_code=404, content={"erro": "Pergunta não encontrada"})

    pergunta_data = pergunta_ref.to_dict()
    resposta_certa = remover_acentos(pergunta_data["resposta"].strip().lower())

    if resposta_user == resposta_certa:
        print(f"✔️ {aluno.get('nome', nome)} acertou a pergunta {pergunta_id}.")
        return JSONResponse(content={"acertou": True})
    else:
        print(f"❌ {aluno.get('nome', nome)} errou a pergunta {pergunta_id}.")
        return JSONResponse(content={"acertou": False})


@app.get("/pagamentos/{aluno_nome}", response_class=HTMLResponse)
async def pagina_pagamentos(aluno_nome: str, request: Request):
    """
    Serve a página de pagamentos para o aluno. Não faz fetchs servidor-side aqui —
    o JS da página vai chamar a API '/api/historico-pagamentos/{aluno_nome}'.
    """
    # passa o nome para o template (será injetado de forma segura)
    return templates.TemplateResponse("pagamentos.html", {"request": request, "aluno_nome": aluno_nome})


@app.get("/api/historico-pagamentos/{aluno_nome}")
async def historico_pagamentos_api(aluno_nome: str):
    aluno_normalizado = aluno_nome.strip().lower()

    # busca vinculo (aluno_professor)
    vinculos = db.collection("alunos_professor") \
                 .where("aluno", "==", aluno_normalizado) \
                 .limit(1).stream()
    vinculo_doc = next(vinculos, None)
    if not vinculo_doc:
        raise HTTPException(status_code=404, detail="Aluno/vínculo não encontrado")

    vinculo_data = vinculo_doc.to_dict()
    total_aulas = int(vinculo_data.get("total_aulas", 0))
    valor_mensal = total_aulas * 1250  # 1.250 Kz por aula

    # busca pagamentos já registados
    pagamentos_query = db.collection("pagamentos") \
                         .where("aluno", "==", aluno_normalizado) \
                         .stream()

    pagamentos = []
    seen = set()
    for doc in pagamentos_query:
        d = doc.to_dict()
        mes = int(d.get("mes", 0))
        ano = int(d.get("ano", 0))
        key = (ano, mes)
        if key in seen:
            continue
        seen.add(key)

        pagamentos.append({
            "mes": mes,
            "ano": ano,
            "valor": int(d.get("valor", valor_mensal)),
            "pago": bool(d.get("pago", False)),
            "data_registro": d.get("data_registro", None)
        })

    # garantir que o mês corrente esteja sempre presente (se não existir, adiciona como não pago)
    hoje = datetime.utcnow()
    mes_atual = hoje.month
    ano_atual = hoje.year
    if not any(p["mes"] == mes_atual and p["ano"] == ano_atual for p in pagamentos):
        pagamentos.append({
            "mes": mes_atual,
            "ano": ano_atual,
            "valor": valor_mensal,
            "pago": False,
            "data_registro": None
        })

    # ordenar por ano/mes descendente (mais recente primeiro)
    pagamentos.sort(key=lambda x: (x["ano"], x["mes"]), reverse=True)
    return JSONResponse(content=pagamentos)


class PagamentoIn(BaseModel): 
    aluno_nome: str
    mes: int  
    ano: int
    pago: bool


@app.post("/api/registrar-pagamento")
async def registrar_pagamento(data: PagamentoIn):
    aluno_normalizado = data.aluno_nome.strip().lower()

    # Buscar vínculo do aluno
    vinculos = db.collection("alunos_professor") \
                 .where("aluno", "==", aluno_normalizado) \
                 .limit(1).stream()
    vinculo_doc = next(vinculos, None)
    if not vinculo_doc:
        raise HTTPException(status_code=404, detail="Aluno/vínculo não encontrado")

    doc_ref = db.collection("alunos_professor").document(vinculo_doc.id)
    vinculo_data = vinculo_doc.to_dict()

    # Agora pega valor_mensal_aluno
    valor_mensal_aluno = vinculo_data.get("valor_mensal_aluno", 0)

    # Histórico de pagamentos
    paga_passado = vinculo_data.get("paga_passado", [])

    if data.pago:
        registro_pagamento = {
            "mes": data.mes,
            "ano": data.ano,
            "valor_pago": valor_mensal_aluno,
            "data_pagamento": datetime.utcnow().strftime("%Y-%m-%d"),
            "hora_pagamento": datetime.utcnow().strftime("%H:%M:%S")
        }
        paga_passado.append(registro_pagamento)

        # Atualiza histórico no documento
        doc_ref.update({
            "paga_passado": paga_passado
        })

    # ✅ Sempre zera o valor_mensal_aluno depois do registro
    doc_ref.update({
        "valor_mensal_aluno": 0
    })

    # Além disso, registrar em coleção de pagamentos individuais (opcional)
    doc_id = f"{aluno_normalizado}_{data.ano}_{data.mes}"
    db.collection("pagamentos").document(doc_id).set({
        "aluno": aluno_normalizado,
        "mes": data.mes,
        "ano": data.ano,
        "valor": valor_mensal_aluno,
        "pago": bool(data.pago),
        "data_registro": datetime.utcnow().isoformat()
    })

    return {"message": "Pagamento registrado com sucesso"}


@app.get("/salarios", response_class=HTMLResponse)
async def salarios(request: Request):
    try:
        email = request.query_params.get("email")
        if not email:
            return HTMLResponse(content="Email não informado", status_code=400)

        email = email.strip().lower()

        # Função para tratar valores "Undefined" e None
        def safe_value(val, default=""):
            if str(type(val)).endswith("Undefined'>"):
                return default
            if val is None:
                return default
            return val

        # Buscar no Firestore apenas o professor com o email informado
        prof_ref = db.collection("professores_online").where(
            filter=FieldFilter("email", "==", email)
        ).limit(1).stream()

        saldo_atual = 0
        nome_professor = ""
        pagamentos_list = []

        for doc in prof_ref:
            professor = doc.to_dict() or {}
            nome_professor = safe_value(professor.get("nome_completo") or professor.get("nome"), "")

            # Saldo atual
            salario_info = safe_value(professor.get("salario"), {}) or {}
            saldo_atual = int(safe_value(salario_info.get("saldo_atual"), 0))

            # Pagamentos
            pagamentos_info = professor.get("pagamentos", {}) or {}
            if isinstance(pagamentos_info, dict):
                for mes, pagamento in pagamentos_info.items():
                    if not isinstance(pagamento, dict):
                        pagamento = {}
                    pagamentos_list.append({
                        "mes": str(mes or ""),
                        "data_pagamento": str(pagamento.get("data_pagamento") or ""),
                        "valor_pago": float(pagamento.get("valor_pago") or 0),
                        "email_professor": str(pagamento.get("email_professor") or "")
                    })
            break  # só deve haver 1 professor

        # Renderiza o template passando saldo e histórico de pagamentos
        return templates.TemplateResponse("salarios.html", {
            "request": request,
            "nome": nome_professor,
            "saldo_atual": saldo_atual,
            "pagamentos": pagamentos_list
        })

    except Exception as e:
        print(f"❌ Erro ao carregar página de salário: {e}")
        return HTMLResponse(content=f"Erro: {str(e)}", status_code=500)


@app.get("/pagamentos", response_class=HTMLResponse)
async def pagamentos(request: Request):
    campos_obrigatorios = {
        "aluno": "",
        "preco_aula": 0,
        "total_aulas": 0,
        "valor_mensal": 0,
    }

    # Campos de mensalidades de alunos (12 meses)
    for i in range(1, 13):
        campos_obrigatorios[f"mensalidade{i}"] = False

    # Campos de mensalidades de professores (12 meses)
    for i in range(1, 13):
        campos_obrigatorios[f"mensapro{i}"] = False

    # Atualizar todos os documentos na coleção
    alunos_ref = db.collection("alunos_professor").stream()

    for doc in alunos_ref:
        data = doc.to_dict()
        atualizado = False
        novos_dados = {}

        for campo, valor_padrao in campos_obrigatorios.items():
            if campo not in data:
                novos_dados[campo] = valor_padrao
                atualizado = True

        if atualizado:
            db.collection("alunos_professor").document(doc.id).update(novos_dados)

    return templates.TemplateResponse("pagamentos.html", {"request": request})
    

ANGOLA_TZ = pytz.timezone("Africa/Luanda")

@app.post("/api/registrar-pagamento")
async def registrar_pagamento(data: dict = Body(...)):
    try:
        aluno = data.get("aluno", "").strip().lower()
        valor = data.get("valor", 0)

        if not aluno or valor <= 0:
            raise HTTPException(status_code=400, detail="Dados inválidos")

        agora = datetime.now(ANGOLA_TZ)

        # Nome do mês em português
        MESES_PT = {
            "January": "Janeiro", "February": "Fevereiro", "March": "Março",
            "April": "Abril", "May": "Maio", "June": "Junho",
            "July": "Julho", "August": "Agosto", "September": "Setembro",
            "October": "Outubro", "November": "Novembro", "December": "Dezembro"
        }
        mes_atual = f"{MESES_PT[agora.strftime('%B')]}/{agora.strftime('%Y')}"
        data_pagamento = agora.strftime("%Y-%m-%d")
        hora_pagamento = agora.strftime("%H:%M:%S")

        # Buscar vínculo em alunos_professor
        alunos_prof_ref = db.collection("alunos_professor") \
            .where("aluno", "==", aluno).limit(1).stream()

        vinculo_id = None
        vinculo_data = None
        for doc in alunos_prof_ref:
            vinculo_id = doc.id
            vinculo_data = doc.to_dict()
            break

        if not vinculo_id:
            raise HTTPException(status_code=404, detail="Aluno não encontrado em alunos_professor")

        # Montar registro do pagamento
        pagamento = {
            "mes": mes_atual,
            "valor_pago": valor,
            "data_pagamento": data_pagamento,
            "hora_pagamento": hora_pagamento
        }

        # Atualizar documento
        doc_ref = db.collection("alunos_professor").document(vinculo_id)
        updates = {}

        # Adicionar histórico no campo paga_passado
        paga_passado = vinculo_data.get("paga_passado", [])
        # Evita duplicar o mesmo mês
        if any(p["mes"] == mes_atual for p in paga_passado):
            raise HTTPException(status_code=400, detail=f"Pagamento para {mes_atual} já registrado")

        paga_passado.append(pagamento)
        updates["paga_passado"] = paga_passado

        # Garantir que Valor_mensal exista (fixo em 1250 se não houver)
        if "Valor_mensal" not in vinculo_data:
            updates["Valor_mensal"] = 1250

        # Zera o valor mensal do aluno após pagamento
        updates["Valor_mensal_aluno"] = 0

        doc_ref.update(updates)

        return {
            "status": "sucesso",
            "mensagem": f"Pagamento de {valor} kz registrado para {aluno} no mês {mes_atual}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/historico-pagamentos-prof/{prof_id}", response_class=HTMLResponse)
async def historico_pagamentos_prof(request: Request, prof_id: str):
    try:
        # Busca o professor no Firestore
        doc_ref = db.collection("professores_online").document(prof_id)
        doc = doc_ref.get()

        if not doc.exists:
            return templates.TemplateResponse(
                "historico_pagamentos.html",
                {"request": request, "professor": None, "historico": []}
            )

        dados_prof = doc.to_dict() or {}

        # Pega o histórico salvo no campo 'historico_pagamentos'
        historico = dados_prof.get("historico_pagamentos", [])

        # Ordena do mais recente para o mais antigo (se tiver data)
        historico.sort(key=lambda x: x.get("data", ""), reverse=True)

        return templates.TemplateResponse(
            "historico_pagamentos.html",
            {
                "request": request,
                "professor": dados_prof.get("nome", "Professor sem nome"),
                "historico": historico
            }
        )

    except Exception as e:
        print(f"Erro ao buscar histórico de pagamentos: {e}")
        return templates.TemplateResponse(
            "historico_pagamentos.html",
            {"request": request, "professor": None, "historico": []}
        )


@app.get("/detalhes-pagamento/{aluno_id}")
async def detalhes_pagamento(aluno_id: str):
    doc_ref = db.collection("alunos_professor").document(aluno_id).get()
    if not doc_ref.exists:
        return JSONResponse({"error": "Aluno não encontrado"}, status_code=404)

    data = doc_ref.to_dict()
    meses = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    lista_meses = []
    for i, mes in enumerate(meses, start=1):
        lista_meses.append({
            "mes": mes,
            "status": data.get(f"mensalidade{i}", False),
            "campo": f"mensalidade{i}"
        })

    return JSONResponse({
        "aluno": data.get("aluno", ""),
        "meses": lista_meses
    })


@app.post("/atualizar-pagamento-mes")
async def atualizar_pagamento_mes(payload: dict):
    aluno_id = payload.get("id")
    campo = payload.get("campo")
    status = payload.get("status")

    if not aluno_id or not campo:
        return JSONResponse({"error": "Dados incompletos"}, status_code=400)

    db.collection("alunos_professor").document(aluno_id).update({
        campo: status
    })
    return JSONResponse({"status": "ok"})


@app.get("/listar-pagamentos")
async def listar_pagamentos():
    alunos_ref = db.collection("alunos").stream()
    alunos_lista = []

    for doc in alunos_ref:
        dados = doc.to_dict()
        nome_banco = dados.get("nome", "").strip()
        nome_normalizado = nome_banco.lower()

        # Agora pega o histórico diretamente do campo 'paga_passado' do aluno
        paga_passado = dados.get("paga_passado", [])
        valor_mensal_aluno = 0
        total_gasto = 0

        # Se quiser, ainda pode buscar vínculo para pegar valor_mensal_aluno atualizado
        alunos_prof_ref = db.collection("alunos_professor") \
            .where("aluno", "==", nome_banco.lower()) \
            .limit(1).stream()

        for vinculo_doc in alunos_prof_ref:
            vinculo_data = vinculo_doc.to_dict()
            valor_mensal_aluno = vinculo_data.get("valor_mensal_aluno", 0)
            total_gasto = valor_mensal_aluno
            break

        alunos_lista.append({
            "id": doc.id,
            "nome": nome_banco,
            "mensalidade": dados.get("mensalidade", False),
            "divida": total_gasto,
            "valor_mensal_aluno": valor_mensal_aluno,
            "paga_passado": paga_passado  
        })

    return alunos_lista



@app.get("/ver-pagamentos/{nome_aluno}")
async def ver_pagamentos(nome_aluno: str):
    # Normaliza o nome do aluno
    nome_normalizado = nome_aluno.strip().lower()

    # Buscar aluno na coleção "alunos" pelo nome original
    alunos_ref = db.collection("alunos").stream()
    aluno_doc = None

    for doc in alunos_ref:
        dados = doc.to_dict()
        nome_banco = dados.get("nome", "").strip().lower()
        if nome_banco == nome_normalizado:
            aluno_doc = dados
            break

    if not aluno_doc:
        raise HTTPException(status_code=404, detail=f"Aluno '{nome_aluno}' não encontrado")

    # Pega o histórico de pagamentos do campo "paga_passado"
    pagamentos = aluno_doc.get("paga_passado", [])

    return JSONResponse(content={
        "aluno": aluno_doc.get("nome", nome_aluno),
        "historico_pagamentos": pagamentos
    })

    
@app.post("/atualizar-pagamento")
async def atualizar_pagamento(payload: dict):
    aluno_id = payload.get("id")
    mensalidade = payload.get("mensalidade")
    if aluno_id is None:
        return JSONResponse({"error": "ID não informado"}, status_code=400)
    
    db.collection("alunos_professor").document(aluno_id).update({
        "mensalidade": mensalidade
    })
    return JSONResponse({"status": "ok"})


class PagamentoProfIn(BaseModel):
    id: str
    mensapro1: bool
class PagamentoMesProfIn(BaseModel):
    id: str
    campo: str
    status: bool

@app.get("/listar-pagamentos-prof")
async def listar_pagamentos_prof():
    try:
        docs = db.collection("alunos_professor").stream()
        professores_dict = {}

        for doc in docs:
            dados = doc.to_dict()
            prof_email = dados.get("professor")
            if prof_email not in professores_dict:
                # Buscar o saldo atual do professor
                saldo_atual = 0
                pagamentos_list = []
                nome_professor = ""
                try:
                    prof_ref = db.collection("professores_online") \
                        .where(filter=FieldFilter("email", "==", prof_email.strip().lower())) \
                        .limit(1).stream()
                    
                    for prof_doc in prof_ref:
                        professor_data = prof_doc.to_dict() or {}
                        nome_professor = professor_data.get("nome_completo") or professor_data.get("nome") or ""
                        
                        # Saldo atual
                        salario_info = professor_data.get("salario", {}) or {}
                        saldo_atual = int(salario_info.get("saldo_atual", 0))
                        
                        # Pagamentos detalhados
                        pagamentos_info = professor_data.get("pagamentos", {}) or {}
                        if isinstance(pagamentos_info, dict):
                            for mes, pagamento in pagamentos_info.items():
                                if not isinstance(pagamento, dict):
                                    pagamento = {}
                                pagamentos_list.append({
                                    "mes": str(mes or ""),
                                    "data_pagamento": str(pagamento.get("data_pagamento") or ""),
                                    "valor_pago": float(pagamento.get("valor_pago") or 0),
                                    "email_professor": str(pagamento.get("email_professor") or "")
                                })
                        break
                except Exception as saldo_err:
                    print(f"⚠️ Erro ao buscar saldo do professor {prof_email}: {saldo_err}")

                # Checar o próximo mês a ser pago (primeiro False de mensapro1 → mensapro12)
                meses = [f"mensapro{i}" for i in range(1, 13)]
                proximo_mes = None
                for mes in meses:
                    if not dados.get(mes, False):
                        proximo_mes = mes
                        break
                if not proximo_mes:
                    proximo_mes = "mensapro1"

                professores_dict[prof_email] = {
                    "id": doc.id,
                    "professor": prof_email,
                    "nome": nome_professor,
                    "saldo_atual": saldo_atual,
                    "proximo_mes_a_pagar": proximo_mes,
                    "pagamentos": pagamentos_list
                }

        return list(professores_dict.values())

    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})
        
        
@app.get("/ver-pagamentos", response_class=HTMLResponse)
async def ver_pagamentos(request: Request, professor: str):
    """
    Exibe os registros da coluna pagamentos de um professor específico
    usando o email do professor como filtro.
    """
    try:
        professores_data = []
        
        # Busca apenas o professor específico pelo email (corrigido)
        doc_ref = db.collection("professores_online") \
                    .where("email", "==", professor.strip().lower()) \
                    .stream()
        
        for doc in doc_ref:
            dados = doc.to_dict()
            email_prof = dados.get("email", "Sem email")
            pagamentos = dados.get("pagamentos", {})

            # Itera sobre cada mês salvo na coluna pagamentos
            for mes, info in pagamentos.items():
                professores_data.append({
                    "email_professor": email_prof,
                    "mes": mes,
                    "data_pagamento": info.get("data_pagamento", ""),
                    "hora_pagamento": info.get("hora_pagamento", ""),
                    "valor_pago": info.get("valor_pago", 0),
                    "status": info.get("status", "N/A")
                })

        # Renderiza o HTML com apenas esse professor
        return templates.TemplateResponse(
            "pagamentos_dashboard.html",
            {
                "request": request,
                "pagamentos": professores_data,
                "professor": professor
            }
        )

    except Exception as e:
        return HTMLResponse(content=f"<h3>Erro: {str(e)}</h3>", status_code=500)


        
@app.post("/atualizar-pagamento-mes-prof")
async def atualizar_pagamento_mes_prof(item: PagamentoMesProfIn):
    try:
        db.collection("alunos_professor").document(item.id).update({
            item.campo: item.status
        })
        return {"message": "Pagamento mensal atualizado com sucesso"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


class AtualizarPagamentoProfIn(BaseModel):
    id: str
    professor: str  # email do professor

@app.post("/atualizar-pagamento-prof")
async def atualizar_pagamento_prof(item: AtualizarPagamentoProfIn):
    """
    Atualiza o pagamento do professor:
    - Busca saldo_atual em professores_online e usa como valor_pago.
    - Marca próximo mês como pago em alunos_professor.
    - Registra em pagamentos e na coluna pagamentos do professor.
    - Zera saldo_atual no final.
    """
    try:
        # Buscar professor em alunos_professor
        doc_ref = db.collection("alunos_professor").document(item.id)
        doc = doc_ref.get()
        if not doc.exists:
            return JSONResponse(status_code=404, content={"detail": "Professor não encontrado"})

        dados = doc.to_dict()
        meses = [f"mensapro{i}" for i in range(1, 13)]

        # Encontrar próximo mês não pago
        mes_atualizado = next((mes for mes in meses if not dados.get(mes, False)), None)
        if not mes_atualizado:
            doc_ref.update({mes: False for mes in meses})
            mes_atualizado = "mensapro1"

        # Marcar mês como pago
        doc_ref.update({mes_atualizado: True})

        # Nome do mês
        mes_num = int(mes_atualizado.replace("mensapro", ""))
        mes_nome = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ][mes_num - 1]

        # Data e hora atuais
        agora = datetime.now()
        data_pagamento = agora.strftime("%d/%m/%Y")
        hora_pagamento = agora.strftime("%H:%M:%S")

        # Buscar professor no professores_online e pegar saldo_atual
        professor_email = item.professor.strip().lower()
        prof_ref = db.collection("professores_online") \
            .where(filter=FieldFilter("email", "==", professor_email)) \
            .limit(1).stream()

        valor_pago = 0
        prof_id = None
        for prof_doc in prof_ref:
            prof_id = prof_doc.id
            prof_dados = prof_doc.to_dict()
            valor_pago = prof_dados.get("salario", {}).get("saldo_atual", 0)
            break

        if prof_id is None:
            return JSONResponse(status_code=404, content={"detail": "Professor não encontrado em professores_online"})

        # Determinar status
        status_pagamento = "PAGO" if valor_pago > 0 else "NÃO PAGO"

        # Atualizar coluna pagamentos no professores_online
        db.collection("professores_online").document(prof_id).update({
            f"pagamentos.{mes_nome}": {
                "data_pagamento": data_pagamento,
                "hora_pagamento": hora_pagamento,
                "valor_pago": valor_pago,
                "status": status_pagamento,
                "email_professor": professor_email
            },
            "salario.saldo_atual": 0
        })

        # Registrar na coleção pagamentos
        db.collection("pagamentos").add({
            "mes": mes_nome,
            "data_pagamento": data_pagamento,
            "hora_pagamento": hora_pagamento,
            "valor_pago": valor_pago,
            "status": status_pagamento,
            "email_professor": professor_email,
            "professor_id": prof_id,
            "timestamp": firestore.SERVER_TIMESTAMP
        })

        # Atualizar status no alunos_professor
        doc_ref.update({
            "salario.saldo_atual": 0,
            "salario.status": status_pagamento
        })

        return {"message": f"Pagamento de {valor_pago} registrado para {mes_nome}"}

    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})
        

        
@app.get("/admin", response_class=HTMLResponse)
async def painel_admin(request: Request):
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})

class EntradaItem(BaseModel):
    nome: str
    preco: float
    quantidade: int

class CustoItem(BaseModel):
    nome: str
    valor: float

class VendaItem(BaseModel):
    nome: str
    preco: float  # Preço de venda
    quantidade: int

@app.get("/ajustar-progresso-ingles")
async def ajustar_progresso_ingles():
    alunos_ref = db.collection("alunos").stream()
    count = 0

    for aluno_doc in alunos_ref:
        aluno_data = aluno_doc.to_dict()
        update_data = {}

        if "progresso_ingles" not in aluno_data:
            update_data["progresso_ingles"] = 0
        if "progresso_ingles1" not in aluno_data:
            update_data["progresso_ingles1"] = 0
        if "progresso_ingles2" not in aluno_data:
            update_data["progresso_ingles2"] = 0
        if "progresso_ingles3" not in aluno_data:
            update_data["progresso_ingles3"] = 0
        if "progresso_ingles4" not in aluno_data:
            update_data["progresso_ingles4"] = 0

        if update_data:
            aluno_doc.reference.update(update_data)
            count += 1

    return {"mensagem": f"Campos criados/atualizados em {count} alunos."}

@app.get("/info-pagamentos", response_class=HTMLResponse)
async def info_pagamentos(request: Request):
    return templates.TemplateResponse("info_pagamentos.html", {"request": request})

@app.post("/desvincular-aluno")
async def desvincular_aluno(data: dict):
    try:
        professor = data.get("professor", "").strip().lower()
        aluno = data.get("aluno", "").strip().lower()

        if not professor or not aluno:
            return JSONResponse(status_code=400, content={"detail": "Professor ou aluno inválido"})

        # 1️⃣ Remover vínculo na coleção alunos_professor
        query = db.collection("alunos_professor") \
                  .where("professor", "==", professor) \
                  .where("aluno", "==", aluno) \
                  .stream()

        for doc in query:
            db.collection("alunos_professor").document(doc.id).delete()

        # 2️⃣ Atualizar campo "vinculado" = false na coleção alunos
        aluno_query = db.collection("alunos") \
                        .where("nome", "==", aluno) \
                        .limit(1).stream()

        aluno_doc = next(aluno_query, None)
        if aluno_doc:
            db.collection("alunos").document(aluno_doc.id).update({"vinculado": False})

        return {"status": "success", "message": f"Aluno {aluno} desvinculado do professor {professor}"}

    except Exception as e:
        print("Erro ao desvincular aluno:", e)
        return JSONResponse(status_code=500, content={"detail": "Erro interno", "erro": str(e)})

# ============================
# CONFIG 100ms - DINÂMICA DE TROCA DE CONTA
# ============================
HMS_API_BASE = "https://api.100ms.live/v2"

# ============================
# SCHEMA DA REQUISIÇÃO
# ============================
class CreateRoomRequest(BaseModel):
    name: str

# ============================
# BUSCA CONTA ATIVA
# ============================
async def get_current_account():
    doc = db.collection("CONTAS_100MS").document("contador").get()
    data = doc.to_dict()

    # garante que todas as chaves do 'usos' são strings
    usos = {str(k): v for k, v in data["usos"].items()}

    return data["conta_atual"], usos


async def rotate_account():
    ref = db.collection("CONTAS_100MS").document("contador")
    doc = ref.get().to_dict()

    conta = doc["conta_atual"]
    usos = {str(k): v for k, v in doc["usos"].items()}  # converte chaves para string

    conta_str = str(conta)
    if usos.get(conta_str, 0) >= 10:  # limite de usos por conta
        conta = (conta + 1) % len(CONTAS_100MS)
        conta_str = str(conta)
        usos[conta_str] = 0  # reset da nova conta

    ref.update({
        "conta_atual": conta,
        "usos": usos
    })
    return conta


async def incrementar_uso():
    ref = db.collection("CONTAS_100MS").document("contador")
    doc = ref.get().to_dict()

    conta = doc["conta_atual"]
    usos = {str(k): v for k, v in doc["usos"].items()}  # garante chaves como string

    conta_str = str(conta)
    usos[conta_str] = usos.get(conta_str, 0) + 1  # incrementa o uso da conta atual

    ref.update({"usos": usos})
    await rotate_account()


# ============================
# GERA TOKEN 100ms (com permissão de management)
# ============================
async def generate_100ms_token():
    conta_atual, _ = await get_current_account()
    conta = CONTAS_100MS[conta_atual]

    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,  # válido por 1 hora
        "access_key": conta["ACCESS_KEY"],
        "type": "management",  # 🔥 ESSENCIAL para criar salas e room codes
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, conta["SECRET"], algorithm="HS256")


# ============================
# RETORNA HEADERS COM CONTA ATIVA
# ============================
async def get_headers():
    token = await generate_100ms_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

# ============================
# Normaliza nome da sala
# ============================
def normalize_room_name(name: str):
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^a-zA-Z0-9._:-]", "_", name)
    return name.strip("_").lower()

# ============================
# Cria sala 100ms (corrigido)
# ============================
@app.post("/create-room")
async def create_room(req: CreateRoomRequest):
    import asyncio
    async with httpx.AsyncClient(timeout=30.0) as client:
        normalized_name = normalize_room_name(req.name)
        print(f"🟦 Criando sala com nome normalizado: {normalized_name}")

        # 🔹 Busca conta ativa
        conta_atual, _ = await get_current_account()
        conta = CONTAS_100MS[conta_atual]
        template_id = conta["TEMPLATE"]
        subdomain = conta["SUBDOMAIN"]

        body = {"name": normalized_name, "template_id": template_id}

        # ====== Criação da sala ======
        headers = await get_headers()
        r = await client.post(f"{HMS_API_BASE}/rooms", json=body, headers=headers)
        print(f"📡 [100ms /rooms] STATUS: {r.status_code} | RESPOSTA: {r.text}")

        if r.status_code >= 400:
            raise HTTPException(status_code=500, detail=f"Erro ao criar sala: {r.status_code} - {r.text}")

        room = r.json()
        room_id = room.get("id")
        if not room_id:
            raise HTTPException(status_code=500, detail="⚠️ Sala criada, mas sem ID retornado.")

        print(f"✅ Sala criada com ID: {room_id}")

        await asyncio.sleep(1)

        # ====== Criação dos códigos (room-codes) ======
        body_codes = {"roles": ["host", "guest"]}
        r2 = await client.post(
            f"{HMS_API_BASE}/room-codes/room/{room_id}",
            json=body_codes,
            headers=headers,
        )
        print(f"📡 [100ms /room-codes/room/{room_id}] STATUS: {r2.status_code} | BODY ENVIADO: {body_codes} | RESPOSTA: {r2.text}")

        if r2.status_code >= 400:
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao gerar room codes: {r2.status_code} - {r2.text}"
            )

        data_codes = r2.json()
        codes = data_codes.get("data", [])
        if not codes:
            raise HTTPException(status_code=500, detail=f"⚠️ Nenhum room code retornado: {data_codes}")

        role_map = {c.get("role"): c.get("code") for c in codes}
        room_code_host = role_map.get("host")
        room_code_guest = role_map.get("guest")

        if not room_code_host or not room_code_guest:
            raise HTTPException(status_code=500, detail=f"⚠️ Room codes ausentes: {data_codes}")

        print(f"✅ Room codes criados com sucesso → Host={room_code_host}, Guest={room_code_guest}")

        # ====== Incrementa uso da conta ativa ======
        await incrementar_uso()

        return {
            "room_id": room_id,
            "room_code_host": room_code_host,
            "room_code_guest": room_code_guest,
            "prebuilt_links": {
                "host": f"https://{subdomain}.app.100ms.live/meeting/{room_code_host}",
                "guest": f"https://{subdomain}.app.100ms.live/meeting/{room_code_guest}",
            },
            "conta_usada": conta_atual  # ✅ retorna qual conta foi usada
        }

# -------------------------
# 3️⃣ PROFESSOR ENVIA room_code AO ALUNO
# -------------------------
# ✅ Modelo atualizado
class EnviarIdPayload(BaseModel):
    aluno: str
    professor: str
    room_id: str   # Recebe apenas o room_id (sem o link completo)


# ==============================
# Gerar token JWT via API 100ms
# ==============================
async def gerar_token(role: str, user_id: str, room_id: str):
    url = f"{HMS_ROOM_URL}/room/{room_id}/token"

    headers = {
        "Authorization": f"Bearer {HMS_API_KEY}",
        "Content-Type": "application/json"
    }

    body = {
        "user_id": user_id,
        "role": role
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=body)
        if response.status_code != 200:
            raise Exception(f"Erro ao gerar token: {response.text}")
        data = response.json()
        return data["token"]


# ==============================
# Enviar ID (com conta ativa)
# ==============================
from pydantic import BaseModel

ALUNO_ROOM = {}

class EnviarIdPayload(BaseModel):
    aluno: str
    professor: str
    room_id: str
    prebuilt_link: str   


# ===========================
# 🔹 Enviar ID e link da aula
# ===========================
@app.post("/enviar-id-aula")
async def enviar_id_aula(payload: EnviarIdPayload):
    aluno_norm = payload.aluno.strip().lower().replace(" ", "")
    professor_norm = payload.professor.strip().lower().replace(" ", "")

    # Buscar conta ativa para este envio
    conta_atual, _ = await get_current_account()
    conta = CONTAS_100MS[conta_atual]

    ALUNO_ROOM[aluno_norm] = {
        "room_id": payload.room_id,
        "professor": professor_norm,
        "prebuilt_link": payload.prebuilt_link,  
        "subdomain": conta["SUBDOMAIN"],        
        "template_id": conta["TEMPLATE"]        
    }

    return {
        "status": "ok",
        "message": "Link real da aula enviado ao aluno com sucesso!",
        "conta_usada": conta_atual  # ✅ retorna qual conta foi usada
    }


@app.get("/buscar-id-professor")
async def buscar_id_professor(aluno: str):
    aluno_norm = aluno.strip().lower().replace(" ", "")
    data = ALUNO_ROOM.get(aluno_norm)

    if not data:
        return {"room_id": None, "prebuilt_link": None}

    return {
        "room_id": data["room_id"],
        "prebuilt_link": data["prebuilt_link"]
    }


@app.post("/registrar-aula")
async def registrar_aula(data: dict = Body(...)):
    try:
        professor = data.get("professor", "").strip().lower()
        aluno = data.get("aluno", "").strip().lower()

        if not professor or not aluno:
            raise HTTPException(status_code=400, detail="Dados incompletos")

        # 🔹 Quando for chamada via /buscar-id-professor,
        # inicia o cronômetro de 60 minutos antes de registrar.
        print(f"⏳ Cronômetro iniciado para {aluno} - Professor: {professor} (60 minutos)")
        await asyncio.sleep(60 * 60)  # Espera 60 minutos (3600 segundos)

        print(f"🕒 Tempo concluído. Registrando aula de {aluno} com {professor}...")

        # 🔹 Busca vínculo aluno-professor
        query = db.collection("alunos_professor") \
                  .where("professor", "==", professor) \
                  .where("aluno", "==", aluno) \
                  .limit(1).stream()

        doc = next(query, None)
        if not doc:
            raise HTTPException(status_code=404, detail="Vínculo não encontrado")

        doc_ref = db.collection("alunos_professor").document(doc.id)
        doc_data = doc.to_dict()
        aulas_anteriores = doc_data.get("aulas_dadas", 0)
        lista_aulas = doc_data.get("aulas", [])
        aulas_passadas = doc_data.get("aulas_passadas", [])  
        valor_passado = doc_data.get("valor_passado", [])    

        agora = datetime.now()
        nova_aula = {
            "data": agora.strftime("%Y-%m-%d"),
            "horario": agora.strftime("%H:%M")
        }

        # Incrementa a aula
        novo_total = aulas_anteriores + 1
        valor_mensal = novo_total * 1250  # 💰 cálculo do valor acumulado

        update_data = {
            "aulas_dadas": novo_total,
            "aulas": lista_aulas + [nova_aula],
            "valor_mensal": valor_mensal
        }

        registro_passado = None
        registro_valor = None

        # 🔹 Quando completar 12 aulas -> transferir e zerar ciclo
        if novo_total >= 12:
            registro_passado = {
                "data_transferencia": agora.strftime("%Y-%m-%d %H:%M"),
                "mes": agora.strftime("%Y-%m"),
                "total_aulas": 12
            }

            registro_valor = {
                "data_transferencia": agora.strftime("%Y-%m-%d %H:%M"),
                "mes": agora.strftime("%Y-%m"),
                "valor_pago": valor_mensal,
                "pago": "Não Pago"
            }

            aulas_passadas.append(registro_passado)
            valor_passado.append(registro_valor)

            # Resetar contadores
            update_data["aulas_dadas"] = 0
            update_data["valor_mensal"] = 0
            update_data["aulas_passadas"] = aulas_passadas
            update_data["valor_passado"] = valor_passado

        # 🔹 Atualiza documento aluno-professor
        doc_ref.update(update_data)

        # 🔹 Atualiza saldo_atual do professor na coleção "professores_online"
        prof_ref = db.collection("professores_online").where(
            filter=FieldFilter("email", "==", professor)
        ).limit(1).stream()

        prof_doc = next(prof_ref, None)
        if prof_doc:
            prof_doc_ref = db.collection("professores_online").document(prof_doc.id)
            prof_data = prof_doc.to_dict() or {}
            salario_info = prof_data.get("salario", {})

            saldo_atual = int(salario_info.get("saldo_atual", 0)) + (valor_mensal if novo_total < 12 else 0)
            if novo_total >= 12:
                saldo_atual = int(salario_info.get("saldo_atual", 0)) + registro_valor["valor_pago"]

            prof_doc_ref.update({
                "salario.saldo_atual": saldo_atual
            })

        print(f"✅ Aula de {aluno} registrada automaticamente após 60 minutos.")
        return {
            "mensagem": f"Aula registrada automaticamente após 60 minutos. Total atual: {update_data['aulas_dadas']}",
            "nova_aula": nova_aula,
        }

    except Exception as e:
        print("Erro ao registrar aula:", e)
        raise HTTPException(status_code=500, detail="Erro ao registrar aula")


@app.get("/paginavendas", response_class=HTMLResponse)
async def paginavendas(request: Request):
    return templates.TemplateResponse("paginavendas.html", {"request": request})
