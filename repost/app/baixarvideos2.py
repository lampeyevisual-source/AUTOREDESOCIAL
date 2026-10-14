

import os
import re
import time
from urllib.parse import urlparse

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


# =====================================================
# CONFIGURAÇÕES
# =====================================================

URL_YTULTRA = (
    "https://www.ytultra.com/pt/youtube-shorts-downloader/"
)

PASTA_BAIXADOS = os.path.join(
    "data",
    "videos",
    "baixados",
)

MAX_REINICIOS = 3
TIMEOUT_DOWNLOAD = 120000


# =====================================================
# PREPARAR PASTA
# =====================================================

def preparar_pasta():
    os.makedirs(PASTA_BAIXADOS, exist_ok=True)


# =====================================================
# EXTRAIR ID DO SHORT
# =====================================================

def extrair_id_video(url):
    url = url.strip()

    partes = urlparse(url).path.strip("/").split("/")

    if "shorts" in partes:
        indice = partes.index("shorts")

        if indice + 1 < len(partes):
            return partes[indice + 1]

    if "watch" in partes:
        from urllib.parse import parse_qs

        parametros = parse_qs(urlparse(url).query)
        video_id = parametros.get("v", [None])[0]

        if video_id:
            return video_id

    # Também aceita um ID informado diretamente.
    if re.fullmatch(r"[A-Za-z0-9_-]{6,}", url):
        return url

    return "youtube_short"


# =====================================================
# LOCALIZAR CAMPO DE URL
# =====================================================

def localizar_campo_url(page):
    seletores = [
        'input[placeholder*="URL do YouTube Shorts"]',
        'input[placeholder*="ID do vídeo"]',
        'input[placeholder*="YouTube"]',
        'input[type="url"]',
    ]

    for seletor in seletores:
        campo = page.locator(seletor).first

        try:
            campo.wait_for(
                state="visible",
                timeout=5000,
            )

            return campo

        except PlaywrightTimeoutError:
            continue

    raise Exception(
        "Não encontrei o campo para inserir "
        "o link do YouTube."
    )


# =====================================================
# LOCALIZAR LINK BAIXAR AGORA
# =====================================================

def localizar_baixar_agora(page):
    seletor = 'a:has-text("Baixar agora")'

    links = page.locator(seletor)

    links.first.wait_for(
        state="visible",
        timeout=90000,
    )

    # Prioriza MP4 720p.
    for indice in range(links.count()):
        link = links.nth(indice)

        try:
            if not link.is_visible():
                continue

            texto = link.locator(
                "xpath=.."
            ).inner_text().lower()

            if "mp4" in texto and "720p" in texto:
                return link

        except Exception:
            continue

    # Alternativa: primeiro link visível.
    for indice in range(links.count()):
        link = links.nth(indice)

        try:
            if link.is_visible():
                return link

        except Exception:
            continue

    raise Exception(
        "Não encontrei um link de download visível."
    )


# =====================================================
# LOCALIZAR URL DIRETA DO VÍDEO
# =====================================================

def localizar_url_mp4(pagina, timeout_segundos=30):
    limite = time.time() + timeout_segundos

    while time.time() < limite:
        try:
            if pagina.is_closed():
                return None

            # URL dentro de <video><source src="...">
            source = pagina.locator(
                "video source[src]"
            ).first

            if source.count() > 0:
                endereco = source.get_attribute("src")

                if endereco and endereco.startswith("http"):
                    return endereco

            # Algumas páginas usam <video src="...">
            video = pagina.locator(
                "video[src]"
            ).first

            if video.count() > 0:
                endereco = video.get_attribute("src")

                if endereco and endereco.startswith("http"):
                    return endereco

        except Exception:
            pass

        time.sleep(0.5)

    return None


# =====================================================
# BAIXAR O MP4 PELA REQUISIÇÃO DO NAVEGADOR
# =====================================================

def salvar_mp4(contexto, url_mp4, pagina_video, caminho_arquivo):
    print("Baixando o arquivo MP4...")

    resposta = contexto.request.get(
        url_mp4,
        headers={
            "Referer": pagina_video.url,
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/154.0.0.0 Safari/537.36"
            ),
        },
        timeout=TIMEOUT_DOWNLOAD,
    )

    try:
        if not resposta.ok:
            raise Exception(
                f"Servidor respondeu HTTP {resposta.status}."
            )

        conteudo = resposta.body()

        if not conteudo or len(conteudo) < 12:
            raise Exception(
                "O arquivo recebido está vazio ou incompleto."
            )

        # Assinatura típica de arquivo MP4: ftyp.
        if conteudo[4:8] != b"ftyp":
            tipo = resposta.headers.get(
                "content-type",
                "desconhecido",
            )

            raise Exception(
                "A resposta recebida não parece ser um MP4. "
                f"Content-Type: {tipo}"
            )

        with open(caminho_arquivo, "wb") as arquivo:
            arquivo.write(conteudo)

    finally:
        resposta.dispose()

    tamanho = os.path.getsize(caminho_arquivo)

    if tamanho == 0:
        os.remove(caminho_arquivo)

        raise Exception(
            "O arquivo salvo ficou vazio."
        )

    print("\n======================================")
    print("DOWNLOAD CONCLUÍDO")
    print(f"Arquivo: {caminho_arquivo}")
    print(f"Tamanho: {tamanho:,} bytes")
    print("======================================")

    return caminho_arquivo


# =====================================================
# BAIXAR UM SHORT
# =====================================================

def baixar_video(link_youtube, tentativa=1):
    preparar_pasta()

    navegador = None
    contexto = None
    playwright = None

    link_youtube = link_youtube.strip()
    id_video = extrair_id_video(link_youtube)

    caminho_arquivo = os.path.join(
        PASTA_BAIXADOS,
        f"{id_video}.mp4",
    )

    try:
        # ---------------------------------------------
        # VERIFICAR SE JÁ EXISTE
        # ---------------------------------------------

        if os.path.isfile(caminho_arquivo):
            if os.path.getsize(caminho_arquivo) > 0:
                print(
                    f"Vídeo já baixado: {caminho_arquivo}"
                )

                return caminho_arquivo

        print("\n======================================")
        print(
            f"DOWNLOAD DO YOUTUBE - "
            f"TENTATIVA {tentativa}/{MAX_REINICIOS}"
        )
        print(f"URL: {link_youtube}")
        print("======================================")

        # ---------------------------------------------
        # ABRIR NAVEGADOR MAXIMIZADO
        # ---------------------------------------------

        playwright = sync_playwright().start()

        navegador = playwright.chromium.launch(
            headless=False,
            args=["--start-maximized"],
        )

        contexto = navegador.new_context(
            accept_downloads=True,
            no_viewport=True,
        )

        page = contexto.new_page()

        # ---------------------------------------------
        # ABRIR YTULTRA
        # ---------------------------------------------

        print("Abrindo YTUltra...")

        page.goto(
            URL_YTULTRA,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        campo = localizar_campo_url(page)

        # ---------------------------------------------
        # INSERIR LINK
        # ---------------------------------------------

        campo.fill(link_youtube)

        print("Link inserido.")

        campo.press("Enter")

        print(
            "Enter pressionado. "
            "Aguardando resultados..."
        )

        # ---------------------------------------------
        # AGUARDAR OPÇÕES DE DOWNLOAD
        # ---------------------------------------------

        link_baixar = localizar_baixar_agora(page)

        print("Opção de download encontrada.")

        # ---------------------------------------------
        # CLICAR E DETECTAR A PÁGINA DO VÍDEO
        # ---------------------------------------------

        print("Clicando em Baixar agora...")

        paginas_antes = list(contexto.pages)
        url_antes = page.url

        link_baixar.click(timeout=15000)

        pagina_video = None
        url_mp4 = None

        limite = time.time() + 30

        while time.time() < limite:
            paginas_atuais = list(contexto.pages)

            # Prioriza páginas abertas depois do clique.
            novas_paginas = [
                p for p in paginas_atuais
                if p not in paginas_antes
            ]

            # Procura primeiro nas novas abas.
            for candidata in reversed(novas_paginas):
                try:
                    if candidata.is_closed():
                        continue

                    endereco = localizar_url_mp4(
                        candidata,
                        timeout_segundos=1,
                    )

                    if endereco:
                        pagina_video = candidata
                        url_mp4 = endereco
                        break

                except Exception:
                    continue

            if url_mp4:
                break

            # O site também pode navegar na própria aba.
            try:
                if not page.is_closed():
                    if page.url != url_antes or page.locator(
                        "video"
                    ).count() > 0:

                        endereco = localizar_url_mp4(
                            page,
                            timeout_segundos=1,
                        )

                        if endereco:
                            pagina_video = page
                            url_mp4 = endereco
                            break

            except Exception:
                pass

            time.sleep(0.5)

        if not url_mp4:
            print("Não encontrei a URL direta do vídeo.")

            # Diagnóstico das páginas abertas.
            for indice, pagina in enumerate(contexto.pages):
                try:
                    print(
                        f"Aba {indice}: {pagina.url}"
                    )
                except Exception:
                    pass

            raise Exception(
                "O YTUltra não apresentou uma URL de vídeo "
                "em video source[src] ou video[src]."
            )

        print("Página do vídeo identificada.")
        print("URL direta do vídeo encontrada.")

        # ---------------------------------------------
        # BAIXAR E SALVAR
        # ---------------------------------------------

        arquivo = salvar_mp4(
            contexto,
            url_mp4,
            pagina_video,
            caminho_arquivo,
        )

        return arquivo

    except Exception as erro:
        print(f"\nErro no download: {erro}")

        # Remove somente arquivo incompleto.
        if os.path.isfile(caminho_arquivo):
            try:
                if os.path.getsize(caminho_arquivo) == 0:
                    os.remove(caminho_arquivo)
            except Exception:
                pass

    finally:
        if contexto:
            try:
                contexto.close()
            except Exception:
                pass

        if navegador:
            try:
                navegador.close()
            except Exception:
                pass

        if playwright:
            try:
                playwright.stop()
            except Exception:
                pass

    # ---------------------------------------------
    # NOVA TENTATIVA EM CASO DE FALHA
    # ---------------------------------------------

    if tentativa < MAX_REINICIOS:
        print(
            "Aguardando antes de tentar novamente..."
        )

        time.sleep(3)

        return baixar_video(
            link_youtube,
            tentativa + 1,
        )

    print("Número máximo de tentativas atingido.")

    return None


# =====================================================
# TESTE DIRETO
# =====================================================

if __name__ == "__main__":
    link = input(
        "Cole o link do YouTube Shorts: "
    ).strip()

    if link:
        arquivo = baixar_video(link)

        if arquivo:
            print(
                f"\nVídeo salvo em: {arquivo}"
            )
        else:
            print(
                "\nNão foi possível baixar o vídeo."
            )
