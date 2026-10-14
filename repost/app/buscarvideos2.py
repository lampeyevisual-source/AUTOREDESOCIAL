
import os
import re
import random
from urllib.parse import urlencode, urljoin

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


# =====================================================
# CONFIGURAÇÕES
# =====================================================

URL_BUSCA = "https://www.youtube.com/results"

PASTA_VIDEOS = os.path.join("data", "videos", "youtube")

ARQUIVO_PROCESSADOS = os.path.join(
    PASTA_VIDEOS,
    "processados_youtube.txt",
)

# Mais de 100 visualizações
VISUALIZACOES_MINIMAS = 100_000

# Número máximo de rolagens na pesquisa
ROLAGENS_MAXIMAS = 15

CATEGORIAS = [
    "Histórias",
    "Anime e quadrinhos",
    "Jogos",
    "Sociedade",
    "Comida",
    "Drama",
    "Educação",
    "Tecnologia",
]


# =====================================================
# PREPARAR ARQUIVOS
# =====================================================

def preparar_arquivo():

    os.makedirs(PASTA_VIDEOS, exist_ok=True)

    if not os.path.exists(ARQUIVO_PROCESSADOS):
        with open(
            ARQUIVO_PROCESSADOS,
            "w",
            encoding="utf-8",
        ):
            pass


# =====================================================
# CARREGAR VÍDEOS PROCESSADOS
# =====================================================

def carregar_processados():

    preparar_arquivo()

    with open(
        ARQUIVO_PROCESSADOS,
        "r",
        encoding="utf-8",
    ) as arquivo:

        return {
            linha.strip()
            for linha in arquivo
            if linha.strip()
        }


# =====================================================
# REGISTRAR VÍDEO PROCESSADO
# =====================================================

def registrar_processado(url_video):

    with open(
        ARQUIVO_PROCESSADOS,
        "a",
        encoding="utf-8",
    ) as arquivo:

        arquivo.write(url_video + "\n")


# =====================================================
# CONVERTER VISUALIZAÇÕES PARA NÚMERO
# =====================================================

def converter_visualizacoes(texto):

    if not texto:
        return 0

    texto = (
        texto.lower()
        .replace("\u00a0", " ")
        .strip()
    )

    # Exemplos:
    # 610 mil
    # 1,2 mi
    # 1.5M
    # 2 bilhões
    padrao_unidades = re.compile(
        r"(\d[\d.,]*)\s*"
        r"(bilhões|bilhoes|bilhão|bilhao|bi|"
        r"milhões|milhoes|milhão|milhao|mi|"
        r"mil|k|m)\b",
        re.IGNORECASE,
    )

    correspondencia = padrao_unidades.search(texto)

    if correspondencia:

        numero_texto = correspondencia.group(1)
        unidade = correspondencia.group(2).lower()

        # Interpreta decimal brasileiro e internacional.
        if "," in numero_texto:
            numero_texto = numero_texto.replace(".", "")
            numero_texto = numero_texto.replace(",", ".")
        elif "." in numero_texto:
            partes = numero_texto.split(".")

            if (
                len(partes[-1]) == 3
                and len(partes) > 1
            ):
                numero_texto = numero_texto.replace(".", "")

        try:
            numero = float(numero_texto)
        except ValueError:
            return 0

        if unidade in ("mil", "k"):
            return int(numero * 1_000)

        if unidade in (
            "mi", "m", "milhão", "milhao",
            "milhões", "milhoes",
        ):
            return int(numero * 1_000_000)

        if unidade in (
            "bi", "bilhão", "bilhao",
            "bilhões", "bilhoes",
        ):
            return int(numero * 1_000_000_000)

    # Exemplos:
    # 610 visualizações
    # 1.234 visualizações
    # 1,234 views
    correspondencia = re.search(
        r"(\d[\d.,]*)\s*(?:visualiza\w*|views?)",
        texto,
        re.IGNORECASE,
    )

    if correspondencia:

        numero_texto = correspondencia.group(1)

        # Sem unidade, o número é tratado como contagem inteira.
        numero_limpo = re.sub(r"[^\d]", "", numero_texto)

        return int(numero_limpo) if numero_limpo else 0

    # Não tenta adivinhar se só houver números sem contexto.
    return 0


# =====================================================
# EXTRAIR VISUALIZAÇÕES DOS MODELOS ANTIGO E NOVO
# =====================================================

def obter_visualizacoes(card):

    # 1. Modelo antigo do YouTube
    seletores = [
        "#dismissible #metadata-line .inline-metadata-item",
        "#metadata-line .inline-metadata-item",
        ".inline-metadata-item",
    ]

    for seletor in seletores:
        try:
            metadados = card.locator(seletor)

            for indice in range(metadados.count()):
                texto = metadados.nth(indice).inner_text(
                    timeout=2000
                ).strip()

                visualizacoes = converter_visualizacoes(texto)

                if visualizacoes > 0:
                    return visualizacoes

        except Exception:
            pass

    # 2. Modelo novo: lê todo o texto do card
    # Exemplo: "2,4 mi de visualizações"
    try:
        texto_card = card.inner_text(timeout=3000)

        visualizacoes = converter_visualizacoes(texto_card)

        if visualizacoes > 0:
            return visualizacoes

    except Exception:
        pass

    # 3. Modelo antigo: atributo aria-label do título
    try:
        titulo = card.locator(
            "a#video-title"
        ).first

        aria_label = titulo.get_attribute("aria-label") or ""

        visualizacoes = converter_visualizacoes(aria_label)

        if visualizacoes > 0:
            return visualizacoes

    except Exception:
        pass

    return 0


# =====================================================
# EXTRAIR LINK DO SHORT
# =====================================================

def extrair_link_short(card):

    seletores = [
        '#dismissible a#thumbnail[href*="/shorts/"]',
        '#dismissible a#video-title[href*="/shorts/"]',
        'a#thumbnail[href*="/shorts/"]',
        'a#video-title[href*="/shorts/"]',
    ]

    for seletor in seletores:

        try:

            links = card.locator(seletor)

            for indice in range(links.count()):

                href = links.nth(indice).get_attribute("href")

                if not href:
                    continue

                url = urljoin(
                    "https://www.youtube.com",
                    href,
                )

                url = url.split("?")[0].rstrip("/")

                if re.search(
                    r"youtube\.com/shorts/[^/]+$",
                    url,
                ):
                    return url

        except Exception:
            continue

    return None


# =====================================================
# EXTRAIR TÍTULO DO SHORT
# =====================================================

def extrair_titulo(card):

    try:

        elemento = card.locator(
            "a#video-title"
        ).first

        titulo = (
            elemento.get_attribute("title")
            or elemento.inner_text()
        ).strip()

        if titulo:
            return titulo

    except Exception:
        pass

    return "Título não identificado"


# =====================================================
# PROCURAR O PRIMEIRO SHORT APROVADO
# =====================================================

def coletar_primeiro_short(page, processados):

    while True:

        vistos_nesta_busca = set()

        for numero_rolagem in range(ROLAGENS_MAXIMAS):

            print(
                f"\nPesquisando resultados: "
                f"{numero_rolagem + 1}/{ROLAGENS_MAXIMAS}",
                flush=True
            )

            # Procura links de Shorts nos modelos antigo e novo.
            links = page.locator('a[href*="/shorts/"]')

            try:
                links.first.wait_for(
                    state="attached",
                    timeout=5000
                )
            except Exception:
                print(
                    "Ainda não há links de Shorts visíveis.",
                    flush=True
                )

            total = links.count()

            print(f"Links encontrados: {total}", flush=True)

            for indice in range(total):

                link = links.nth(indice)

                try:
                    href = link.get_attribute("href")

                    if not href or "/shorts/" not in href:
                        continue

                    url_video = (
                        "https://www.youtube.com" + href
                        if href.startswith("/")
                        else href.split("&")[0]
                    )

                    # Normaliza a URL para evitar duplicatas por parâmetros.
                    url_video = url_video.split("?")[0].rstrip("/")

                    if url_video in processados:
                        continue

                    if url_video in vistos_nesta_busca:
                        continue

                    vistos_nesta_busca.add(url_video)

                    # O HTML enviado possui o título no atributo title.
                    titulo = link.get_attribute("title") or ""

                    if not titulo:
                        try:
                            titulo = link.inner_text(timeout=1500).strip()
                        except Exception:
                            titulo = ""

                    if not titulo:
                        try:
                            titulo = link.locator(
                                "xpath=ancestor::*[self::ytd-video-renderer "
                                "or self::ytm-shorts-lockup-view-model-v2 "
                                "or self::ytm-shorts-lockup-view-model][1]"
                            ).inner_text(timeout=1500).strip()
                        except Exception:
                            titulo = "Título não identificado"

                    # Procura visualizações no card que contém o link.
                    visualizacoes = 0

                    try:
                        card = link.locator(
                            "xpath=ancestor::*[self::ytd-video-renderer "
                            "or self::ytm-shorts-lockup-view-model-v2 "
                            "or self::ytm-shorts-lockup-view-model][1]"
                        )

                        visualizacoes = obter_visualizacoes(card)

                    except Exception as erro:
                        print(
                            f"Não foi possível ler visualizações: {erro}",
                            flush=True
                        )

                    print(f"\nTítulo: {titulo}", flush=True)
                    print(f"URL: {url_video}", flush=True)
                    print(
                        f"Visualizações: {visualizacoes:,}",
                        flush=True
                    )

                    if visualizacoes <= VISUALIZACOES_MINIMAS:
                        print(
                            "Ignorado: não ultrapassa "
                            f"{VISUALIZACOES_MINIMAS:,} visualizações.",
                            flush=True
                        )
                        continue

                    print("\nShort aprovado!", flush=True)

                    return {
                        "titulo": titulo,
                        "visualizacoes": visualizacoes,
                        "url_video": url_video,
                    }

                except Exception as erro:
                    print(
                        f"Erro ao analisar link: {erro}",
                        flush=True
                    )

            # Rola para carregar mais resultados.
            if numero_rolagem < ROLAGENS_MAXIMAS - 1:
                page.evaluate(
                    "window.scrollTo(0, document.documentElement.scrollHeight)"
                )
                page.wait_for_timeout(1500)

        print(
            "\n15 rolagens concluídas. Recarregando a pesquisa...",
            flush=True
        )

        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
# =====================================================
# SELECIONAR FILTRO SHORTS
# =====================================================

def selecionar_shorts(page):

    print("Procurando o filtro Shorts...")

    seletores = [
        "yt-chip-cloud-chip-renderer",
        "yt-chip-cloud-chip-renderer #text",
        "div.ytChipShapeChip",
    ]

    for seletor in seletores:

        elementos = page.locator(seletor)

        try:

            for indice in range(elementos.count()):

                elemento = elementos.nth(indice)

                try:

                    if not elemento.is_visible():
                        continue

                    texto = elemento.inner_text().strip().lower()

                    if texto != "shorts":
                        continue

                    elemento.click(timeout=3000)

                    page.wait_for_timeout(2000)

                    print("Filtro Shorts selecionado.")

                    return True

                except Exception:
                    continue

        except Exception:
            continue

    print(
        "Filtro Shorts não encontrado. "
        "A pesquisa continuará usando os links /shorts/."
    )

    return False


# =====================================================
# ABRIR SHORT E CAPTURAR LINK DE COMPARTILHAMENTO
# =====================================================

def pegar_link_compartilhamento(page, url_video):

    try:

        print(f"\nAbrindo Short aprovado: {url_video}")

        page.goto(
            url_video,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        page.wait_for_timeout(1500)

        
        # -----------------------------------------
        # LOCALIZAR BOTÃO COMPARTILHAR DO YOUTUBE
        # -----------------------------------------

        seletor_botao = (
            'label.ytSpecButtonShapeWithLabelHost '
            'button[aria-label="Compartilhar"]'
        )

        botao = page.locator(seletor_botao).first

        try:
            botao.wait_for(
                state="visible",
                timeout=15000,
            )

            botao.scroll_into_view_if_needed(
                timeout=5000
            )

            botao.click(
                timeout=10000
            )

            print(
                "Compartilhar clicado. "
                "Aguardando a janela..."
            )

            page.wait_for_timeout(1500)

        except PlaywrightTimeoutError:
            print(
                "Botão Compartilhar não apareceu "
                "na página do Short."
            )
            return None

        except Exception as erro:
            print(
                f"Erro ao clicar em Compartilhar: {erro}"
            )
            return None


        # -----------------------------------------
        # LER LINK DA JANELA DE COMPARTILHAMENTO
        # -----------------------------------------

        seletores_link = [
            'ytd-unified-share-panel-renderer input#share-url',
            'yt-share-panel-renderer input#share-url',
            'input#share-url',
        ]

        for seletor in seletores_link:

            campo = page.locator(seletor).first

            try:

                campo.wait_for(
                    state="visible",
                    timeout=7000,
                )

                link = campo.input_value().strip()

                if link:
                    print(f"Link de compartilhamento: {link}")
                    return link

            except PlaywrightTimeoutError:
                continue

        # -----------------------------------------
        # ALTERNATIVA: TEXTO DO CAMPO DE COMPARTILHAR
        # -----------------------------------------

        try:

            campos = page.locator(
                'input[readonly]'
            )

            for indice in range(campos.count()):

                campo = campos.nth(indice)

                if not campo.is_visible():
                    continue

                valor = (
                    campo.input_value().strip()
                )

                if (
                    "youtu.be/" in valor
                    or "youtube.com/shorts/" in valor
                ):
                    print(
                        f"Link de compartilhamento: {valor}"
                    )
                    return valor

        except Exception:
            pass

        print(
            "A janela abriu, mas não encontrei o link. "
            "Confira o HTML atual da janela de compartilhamento."
        )

        return None

    except PlaywrightTimeoutError:

        print(
            "Tempo esgotado ao abrir o Short "
            "ou localizar os controles de compartilhamento."
        )

        return None

    except Exception as erro:

        print(f"Erro ao capturar compartilhamento: {erro}")

        return None


# =====================================================
# BUSCAR, ABRIR E CAPTURAR UM SHORT
# =====================================================

def buscar_video_youtube():

    preparar_arquivo()

    processados = carregar_processados()

    categoria = random.choice(CATEGORIAS)

    print("\n======================================")
    print("CAM - BUSCADOR DE SHORTS DO YOUTUBE")
    print("======================================")

    print(f"Categoria: {categoria}")
    print(
        f"Filtro: mais de "
        f"{VISUALIZACOES_MINIMAS} visualizações"
    )

    url_busca = (
        f"{URL_BUSCA}?"
        f"{urlencode({'search_query': categoria})}"
    )

    with sync_playwright() as playwright:

        navegador = playwright.chromium.launch(
            headless=False,
            args=["--start-maximized"],
        )

        contexto = navegador.new_context(
            no_viewport=True,
        )

        page = contexto.new_page()

        try:

            # -----------------------------------------
            # ABRIR PESQUISA
            # -----------------------------------------

            print("\nAbrindo pesquisa do YouTube...")

            page.goto(
                url_busca,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            page.wait_for_timeout(2500)

            # -----------------------------------------
            # FILTRAR SHORTS
            # -----------------------------------------

            selecionar_shorts(page)

            # -----------------------------------------
            # ENCONTRAR O PRIMEIRO SHORT APROVADO
            # -----------------------------------------

            video = coletar_primeiro_short(
                page,
                processados,
            )

            if not video:
                return []

            # -----------------------------------------
            # ABRIR E COPIAR LINK DE COMPARTILHAMENTO
            # -----------------------------------------

            link_compartilhamento = (
                pegar_link_compartilhamento(
                    page,
                    video["url_video"],
                )
            )

            if not link_compartilhamento:

                print(
                    "\nLink não capturado. "
                    "Vídeo não será marcado como processado."
                )

                return []

            # -----------------------------------------
            # REGISTRAR APÓS CAPTURAR O LINK
            # -----------------------------------------

            registrar_processado(video["url_video"])

            print("\n======================================")
            print("SHORT PROCESSADO COM SUCESSO")
            print("======================================")
            print(f"Título: {video['titulo']}")
            print(
                f"Visualizações: "
                f"{video['visualizacoes']:,}"
            )
            print(f"URL original: {video['url_video']}")
            print(
                f"URL compartilhada: "
                f"{link_compartilhamento}"
            )

            return [{
                "titulo": video["titulo"],
                "visualizacoes": video["visualizacoes"],
                "url_video": video["url_video"],
                "link_compartilhamento": link_compartilhamento,
            }]

        finally:

            navegador.close()


# =====================================================
# EXECUÇÃO DIRETA
# =====================================================

if __name__ == "__main__":

    try:

        resultados = buscar_video_youtube()

        if resultados:

            video = resultados[0]

            print("\nRESULTADO FINAL")
            print(f"Título: {video['titulo']}")
            print(
                f"Visualizações: "
                f"{video['visualizacoes']:,}"
            )
            print(
                "Link para usar no downloader: "
                f"{video['link_compartilhamento']}"
            )

        else:

            print(
                "\nNenhum link foi capturado nesta execução."
            )

    except KeyboardInterrupt:

        print("\nExecução interrompida pelo usuário.")

    except Exception as erro:

        print(f"\nErro geral: {erro}")
