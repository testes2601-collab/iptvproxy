# -*- coding: utf-8 -*-
"""
===============================================================================
SERVIDOR PROXY IPTV PREMIUM - VERSÃO 21 (Filtro MPEG-TS Corrigido & Suporte Hugging Face / Render)
===============================================================================
Recursos da versão v21:
1. Correção no filtro Byte-a-Byte (chunk_bytes[0] == 0x47): Validação correta de pacotes MPEG-TS.
2. Pool completo de 17 contas IP Direto e Domínios.
3. Compatibilidade total com Docker / Hugging Face / Render / Koyeb.
===============================================================================
"""

import os
import re
import time
import logging
import urllib3
import requests
from flask import Flask, Response, request

# Desativa alertas de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = Flask(__name__)

# =============================================================================
# POOL COMPLETO DE CONTAS M3U
# =============================================================================
LISTA_CONTAS_POOL = [
    # --- SERVIDORES COM IP DIRETO (MAIOR ESTABILIDADE CONTRA CLOUDFLARE) ---
    {
        "id": "ip_103_01",
        "nome": "Servidor IP 103 (Conta 1)",
        "host": "http://103.176.90.186:80",
        "user": "e0828d9135",
        "pass": "e91802270546"
    },
    {
        "id": "ip_103_02",
        "nome": "Servidor IP 103 (Conta 2)",
        "host": "http://103.176.90.186:80",
        "user": "7b559c1042",
        "pass": "11de4cebb4"
    },
    {
        "id": "ono_79_01",
        "nome": "Servidor ONO IP 79",
        "host": "http://79.127.243.145:80",
        "user": "723015",
        "pass": "VfGrmD"
    },
    {
        "id": "ono_85_01",
        "nome": "Servidor ONO IP 85 (Otavio)",
        "host": "http://85.137.49.157.dyn.user.ono.com:80",
        "user": "Otaviodeledove",
        "pass": "9Dh5R8uAu5"
    },
    {
        "id": "ono_85_02",
        "nome": "Servidor ONO IP 85 (Tatiana)",
        "host": "http://85.137.49.157.dyn.user.ono.com:80",
        "user": "tatiana9944",
        "pass": "Ta994a"
    },
    # --- SERVIDORES DOMÍNIO MEUSRV ---
    {
        "id": "meusrv_01",
        "nome": "MeuSrv 955",
        "host": "http://meusrv.top:80",
        "user": "955823677",
        "pass": "798597634"
    },
    {
        "id": "meusrv_02",
        "nome": "MeuSrv 744",
        "host": "http://meusrv.top:80",
        "user": "74468590",
        "pass": "448420959"
    },
    {
        "id": "meusrv_03",
        "nome": "MeuSrv 567",
        "host": "http://meusrv.top:80",
        "user": "567689135",
        "pass": "965722522"
    },
    {
        "id": "meusrv_04",
        "nome": "MeuSrv 361",
        "host": "http://meusrv.top:80",
        "user": "361811331",
        "pass": "252766314"
    },
    # --- SERVIDORES DOMÍNIO XYZ E DEMAIS ---
    {
        "id": "xyz_332_01",
        "nome": "XYZ 332 (988)",
        "host": "http://332nr7hbfu.xyz:80",
        "user": "988060",
        "pass": "zd7YEw"
    },
    {
        "id": "xyz_332_02",
        "nome": "XYZ 332 (Constancio)",
        "host": "http://332nr7hbfu.xyz:80",
        "user": "constancio79",
        "pass": "Wagner@79"
    },
    {
        "id": "xyz_332_03",
        "nome": "XYZ 332 (Casa na Praia)",
        "host": "http://332nr7hbfu.xyz:80",
        "user": "Casanapraia10",
        "pass": "Tvfuturo2"
    },
    {
        "id": "z2mu_54_01",
        "nome": "54z2mu Pro",
        "host": "http://54z2mu.pro:80",
        "user": "jT63beuY",
        "pass": "F11Gkd"
    },
    {
        "id": "fftq_49_01",
        "nome": "49fftq Live",
        "host": "http://49fftq.live:80",
        "user": "WellgtonSilva35",
        "pass": "991DNEubv"
    },
    {
        "id": "vector_61_01",
        "nome": "Vector CDN 61",
        "host": "http://61701-vector.cdn-o2.me:80",
        "user": "4df74cf07e",
        "pass": "9d49be6b44bc"
    },
    {
        "id": "given_11_01",
        "nome": "Given CDN 11",
        "host": "http://11359-given.cdn-o2.me:80",
        "user": "4af01daf4f",
        "pass": "7e3498490571"
    },
    {
        "id": "biturl_play_01",
        "nome": "Biturl Play",
        "host": "http://play.biturl.vip:80",
        "user": "5181603291",
        "pass": "m23bm8a1nup"
    }
]

HEADERS_CLIENTE = {
    "User-Agent": "TiviMate/4.6.1 (Android TV; BRAVIA 4K UR3)",
    "Accept": "*/*",
    "Connection": "keep-alive"
}


# =============================================================================
# FUNÇÕES DE VALIDAÇÃO E FILTRAGEM ANTI-CLOUDFLARE
# =============================================================================

def extrair_stream_id_real(conta_info):
    """ Baixa a lista M3U em segundo plano para capturar o ID numérico exato do Premiere 1. """
    url_m3u = f"{conta_info['host']}/get.php?username={conta_info['user']}&password={conta_info['pass']}&type=m3u_plus"
    try:
        res = requests.get(url_m3u, headers=HEADERS_CLIENTE, timeout=4, verify=False)
        if res.status_code == 200 and "#EXTM3U" in res.text:
            linhas = res.text.splitlines()
            for idx, linha in enumerate(linhas):
                l_up = linha.upper()
                if "PREMIERE 1" in l_up or "PREMIERE FC 1" in l_up or "PREMIERE HD" in l_up:
                    if idx + 1 < len(linhas):
                        prox = linhas[idx + 1].strip()
                        if prox and not prox.startswith("#"):
                            m = re.search(r'/(\d+)\.(ts|m3u8)', prox)
                            if m:
                                return m.group(1)
    except Exception as e:
        logging.warning(f"Erro ao buscar ID numérico na conta {conta_info['id']}: {e}")
    return "premiere1"


def validar_se_e_video_mpegts(chunk_bytes):
    """
    Inspeção Byte-a-Byte: Todo pacote MPEG-TS de IPTV começa com o byte de sincronização 0x47 (71 em decimal).
    Se contiver texto HTML ou marcas da Cloudflare, rejeita imediatamente.
    """
    if not chunk_bytes or len(chunk_bytes) < 188:
        return False
    
    # Valida se o primeiro byte é 0x47 (71 em decimal)
    if chunk_bytes[0] != 0x47:
        return False

    amostra = chunk_bytes[:1024].lower()
    termos_invalidos = [b"<html", b"<!doctype", b"cloudflare", b"restricted", b"access denied", b"error 1020"]
    for termo in termos_invalidos:
        if termo in amostra:
            return False

    return True


def tentar_conectar_stream(conta_info):
    """ Tenta obter o fluxo da conta e valida se é sinal de vídeo real. """
    stream_id = extrair_stream_id_real(conta_info)
    target_url = f"{conta_info['host']}/live/{conta_info['user']}/{conta_info['pass']}/{stream_id}.ts"
    
    try:
        res = requests.get(target_url, headers=HEADERS_CLIENTE, stream=True, timeout=5, verify=False)
        if res.status_code == 200:
            iterador = res.iter_content(chunk_size=32768)
            primeiro_chunk = next(iterador, None)
            
            if primeiro_chunk and validar_se_e_video_mpegts(primeiro_chunk):
                def gerador_stream():
                    yield primeiro_chunk
                    for chunk in iterador:
                        if chunk:
                            yield chunk
                return gerador_stream()
    except Exception as err:
        logging.error(f"Erro na conexão com {conta_info['id']}: {err}")
        
    return None


def adicionar_cors(resposta):
    resposta.headers["Access-Control-Allow-Origin"] = "*"
    resposta.headers["Access-Control-Allow-Headers"] = "*"
    resposta.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS, HEAD"
    return resposta


# =============================================================================
# ROTAS FLASK (COM SUPORTE A DUPLA BARRA)
# =============================================================================

@app.route("/")
def home():
    html_home = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Servidor Proxy IPTV - Premiere 1 (v21)</title>
        <style>
            body { font-family: Arial, sans-serif; background-color: #121212; color: #fff; text-align: center; padding: 40px; }
            .card { background-color: #1e1e1e; padding: 30px; border-radius: 12px; display: inline-block; max-width: 650px; }
            h1 { color: #00e676; }
            .btn { display: inline-block; background-color: #00e676; color: #000; padding: 12px 24px; margin: 10px; border-radius: 6px; font-weight: bold; text-decoration: none; }
            .btn:hover { background-color: #00c853; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>⚽ Servidor Proxy IPTV Premiere 1 (v21)</h1>
            <p>Servidor ativo com Filtro MPEG-TS de Sinal Limpo e Web Player mpegts.js!</p>
            <br>
            <a href="/debug" class="btn">📊 Painel de Diagnóstico (/debug)</a>
            <a href="/watch" class="btn">📺 Web Player Chrome (/watch)</a>
            <a href="/playlist.m3u" class="btn">📋 Baixar Lista M3U (/playlist.m3u)</a>
        </div>
    </body>
    </html>
    """
    return adicionar_cors(Response(html_home, content_type="text/html; charset=utf-8"))


@app.route("/debug")
@app.route("/debug/")
def debug():
    inicio_tempo = time.time()
    linhas_tabela = []
    total_contas = len(LISTA_CONTAS_POOL)
    contas_online = 0
    contas_offline = 0

    for conta in LISTA_CONTAS_POOL:
        url_teste = f"{conta['host']}/live/{conta['user']}/{conta['pass']}/premiere1.ts"
        try:
            r = requests.get(url_teste, headers=HEADERS_CLIENTE, stream=True, timeout=4, verify=False)
            if r.status_code == 200:
                amostra = next(r.iter_content(chunk_size=512), None)
                if amostra and validar_se_e_video_mpegts(amostra):
                    status_txt = "ONLINE (HTTP 200 - Sinal MPEG-TS Limpo)"
                    cor_status = "#00e676"
                    contas_online += 1
                else:
                    status_txt = "BLOQUEADO / CLOUDFLARE (Falso HTTP 200)"
                    cor_status = "#ff5252"
                    contas_offline += 1
            else:
                status_txt = f"RESPOSTA ANÔMALA (HTTP {r.status_code})"
                cor_status = "#ffb74d"
                contas_offline += 1
        except Exception as ex:
            status_txt = f"OFFLINE ({str(ex)})"
            cor_status = "#ff5252"
            contas_offline += 1

        linha = f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #333;"><b>{conta['nome']}</b></td>
            <td style="padding: 10px; border-bottom: 1px solid #333;"><code>{conta['host']}</code></td>
            <td style="padding: 10px; border-bottom: 1px solid #333; color: {cor_status}; font-weight: bold;">{status_txt}</td>
        </tr>
        """
        linhas_tabela.append(linha)

    tempo = round(time.time() - inicio_tempo, 2)

    html_debug = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Diagnóstico do Servidor Proxy IPTV (v21)</title>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #121212; color: #fff; padding: 20px; }}
            .container {{ max-width: 900px; margin: 0 auto; background-color: #1e1e1e; padding: 25px; border-radius: 10px; }}
            h2 {{ color: #00e676; border-bottom: 2px solid #00e676; padding-bottom: 10px; }}
            .summary {{ display: flex; justify-content: space-between; background: #2a2a2a; padding: 15px; border-radius: 6px; margin-bottom: 20px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ background-color: #2c2c2c; color: #00e676; padding: 12px; text-align: left; }}
            .btn-voltar {{ display: inline-block; margin-top: 20px; padding: 10px 15px; background-color: #29b6f6; color: #000; font-weight: bold; text-decoration: none; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>📊 Relatório de Saúde do Pool de Servidores M3U (v21)</h2>
            <div class="summary">
                <div><b>Total Mapeado:</b> {total_contas}</div>
                <div><b style="color: #00e676;">Contas Online (Sinal MPEG-TS):</b> {contas_online}</div>
                <div><b style="color: #ff5252;">Contas Inativas/Cloudflare:</b> {contas_offline}</div>
                <div><b>Tempo:</b> {tempo}s</div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Nome do Servidor</th>
                        <th>Endereço do Host</th>
                        <th>Status do Sinal</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(linhas_tabela)}
                </tbody>
            </table>
            <br>
            <a href="/" class="btn-voltar">← Voltar para o Início</a>
        </div>
    </body>
    </html>
    """
    return adicionar_cors(Response(html_debug, content_type="text/html; charset=utf-8"))


@app.route("/watch")
@app.route("/watch/")
def watch():
    """ Web Player com biblioteca mpegts.js para suporte total a .ts no Chrome. """
    html_watch = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Web Player Chrome - Premiere 1 FHD</title>
        <script src="https://cdn.jsdelivr.net/npm/mpegts.js@1.7.3/dist/mpegts.min.js"></script>
        <style>
            body { font-family: Arial, sans-serif; background-color: #0a0a0a; color: #fff; text-align: center; margin: 0; padding: 20px; }
            .player-box { max-width: 900px; margin: 20px auto; background-color: #161616; padding: 20px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.8); }
            h1 { color: #00e676; }
            video { width: 100%; height: 500px; background-color: #000; border-radius: 8px; }
            .badge { background-color: #ff1744; color: #fff; padding: 4px 10px; border-radius: 4px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="player-box">
            <h1>⚽ Premiere 1 FHD <span class="badge">AO VIVO</span></h1>
            <p>Decodificação MPEG-TS em tempo real via HTML5 (mpegts.js)</p>
            <video id="videoElement" controls autoplay muted></video>
        </div>
        <script>
            if (mpegts.getFeatureList().isSupported) {
                var videoElement = document.getElementById('videoElement');
                var player = mpegts.createPlayer({
                    type: 'mse',
                    isLive: true,
                    url: '/live/premiere1.ts'
                });
                player.attachMediaElement(videoElement);
                player.load();
                player.play();
            } else {
                alert('Seu navegador não possui suporte ao mpegts.js.');
            }
        </script>
    </body>
    </html>
    """
    return adicionar_cors(Response(html_watch, content_type="text/html; charset=utf-8"))


@app.route("/playlist.m3u")
def playlist():
    host_base = request.host_url.rstrip("/")
    m3u_txt = f"""#EXTM3U
#EXTINF:-1 tvg-id="Premiere1.br" tvg-name="Premiere 1 FHD" tvg-logo="https://i.imgur.com/8Q9Z3v1.png" group-title="ESPORTES",Premiere 1 FHD
{host_base}/live/premiere1.ts
"""
    return adicionar_cors(Response(m3u_txt, content_type="application/x-mpegURL"))


@app.route("/live/premiere1.ts")
@app.route("/live/premiere.m3u8")
def stream_premiere():
    for conta in LISTA_CONTAS_POOL:
        fluxo = tentar_conectar_stream(conta)
        if fluxo:
            logging.info(f"Sinal MPEG-TS limpo entregue com a conta: {conta['id']}")
            return adicionar_cors(Response(fluxo, content_type="video/mp2t"))

    msg_erro = "Nenhum sinal válido encontrado. Todas as contas foram bloqueadas pela Cloudflare ou estão offline."
    return adicionar_cors(Response(msg_erro, status=503, content_type="text/plain; charset=utf-8"))


@app.errorhandler(404)
def erro_404(e):
    msg = """
    <h2>⚠️ Página Não Encontrada (Erro 404)</h2>
    <p>O endereço acessado não existe neste servidor.</p>
    <ul>
        <li><a href="/">Página Inicial</a></li>
        <li><a href="/debug">Painel de Diagnóstico (/debug)</a></li>
        <li><a href="/watch">Web Player (/watch)</a></li>
        <li><a href="/playlist.m3u">Lista M3U (/playlist.m3u)</a></li>
    </ul>
    """
    return adicionar_cors(Response(msg, status=404, content_type="text/html; charset=utf-8"))


if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=porta, debug=False)
