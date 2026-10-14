
import random
import re
import os

from repost.app.tiktok import abrir_tiktok, fechar_tiktok


URL_EXPLORAR = "https://www.tiktok.com/explore"

PASTA_VIDEOS = os.path.join("data", "videos")

ARQUIVO_PROCESSADOS = os.path.join(
    PASTA_VIDEOS,
    "processados.txt"
)

ROLAGENS_MAXIMAS = 15


# =========================
# PREPARA TXT
# =========================

def preparar_arquivo():

    os.makedirs(
        PASTA_VIDEOS,
        exist_ok=True
    )

    if not os.path.exists(ARQUIVO_PROCESSADOS):

        with open(
            ARQUIVO_PROCESSADOS,
            "w",
            encoding="utf-8"
        ):
            pass


# =========================
# CARREGA PROCESSADOS
# =========================

def carregar_processados():

    preparar_arquivo()

    with open(
        ARQUIVO_PROCESSADOS,
        "r",
        encoding="utf-8"
    ) as arquivo:

        return {
            linha.strip()
            for linha in arquivo
            if linha.strip()
        }


# =========================
# REGISTRA LINK
# =========================

def registrar_processado(url):

    processados = carregar_processados()

    if url in processados:
        return False

    with open(
        ARQUIVO_PROCESSADOS,
        "a",
        encoding="utf-8"
    ) as arquivo:

        arquivo.write(url + "\n")

    return True


# =========================
# CONVERTE CURTIDAS
# =========================

def converter_curtidas(texto):

    texto = texto.strip().upper()
    texto = texto.replace(",", ".")

    try:

        if "K" in texto:

            return int(
                float(texto.replace("K", "")) * 1000
            )

        if "M" in texto:

            return int(
                float(texto.replace("M", "")) * 1000000
            )

        numeros = re.sub(
            r"[^\d]",
            "",
            texto
        )

        return int(numeros or 0)

    except (ValueError, TypeError):

        return 0


# =========================
# COLETA OS CARDS
# =========================

def coletar_links(page):

    # =========================
    # SELECIONA CATEGORIA ALEATÓRIA
    # =========================

    categorias = [
        "Anime e quadrinhos",
        "Jogos",
        "Sociedade",
        "Comida",
        "Drama",
        "Educação",
        "Tecnologia"
    ]

    categoria_escolhida = random.choice(categorias)

    print()
    print("================================")
    print(f"Categoria escolhida: {categoria_escolhida}")
    print("================================")

    chips = page.locator(
        'div[data-e2e="explore-category-chip"]'
    )

    quantidade_categorias = chips.count()

    for i in range(quantidade_categorias):

        chip = chips.nth(i)

        try:
            texto = chip.locator(
                '[data-testid="tux-web-text"]'
            ).inner_text().strip()

            if texto.lower() == categoria_escolhida.lower():

                print(
                    f"Selecionando categoria: {texto}"
                )

                chip.scroll_into_view_if_needed()

                chip.locator(
                'div[data-testid="tux-web-interaction-container"]'
                ).click(
                    timeout=10000
                )

                page.wait_for_timeout(2000)

                print(
                    f"Categoria selecionada: {texto}"
                )

                break

        except Exception as erro:

            print(
                f"Erro ao verificar categoria: {erro}"
            )
            
    videos = []

    lista = page.locator(
        "#explore-item-list"
    )

    if lista.count() == 0:

        print(
            "Lista do Explorar não encontrada."
        )

        return videos

    cards = lista.locator(
        '[data-e2e="explore-item"]'
    )

    quantidade = cards.count()

    print(
        f"Cards encontrados: {quantidade}"
    )

    for i in range(quantidade):

        try:

            card = cards.nth(i)

            # Link do vídeo
            link = card.locator(
                'a[href*="/video/"]'
            ).first

            url = link.get_attribute("href")

            if not url:
                continue

            url = url.split("?")[0].rstrip("/")

            # Curtidas do card
            curtidas_elemento = card.locator(
                '[data-e2e="explore-card-like-container"] span'
            )

            curtidas_texto = ""

            if curtidas_elemento.count() > 0:

                curtidas_texto = (
                    curtidas_elemento.first.inner_text()
                )

            curtidas = converter_curtidas(
                curtidas_texto
            )

            videos.append({

                "url": url,

                "curtidas": curtidas

            })

        except Exception as erro:

            print(
                f"Erro ao ler card {i}: {erro}"
            )

    return videos


# =========================
# BUSCA UM VÍDEO
# =========================

def buscar_videos():

    playwright = None
    navegador = None

    try:

        processados = carregar_processados()

        playwright, navegador, page = abrir_tiktok()

        page.goto(
            URL_EXPLORAR,
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(5000)

        for rodada in range(
            ROLAGENS_MAXIMAS + 1
        ):

            print(
                f"Verificando cards: {rodada + 1}"
            )

            videos = coletar_links(page)

            # Só considera vídeos que ainda não foram processados
            novos = [
                video for video in videos
                if video["url"] not in processados
            ]

            if novos:

                # Seleciona o vídeo com mais curtidas
                # entre os cards carregados e ainda não processados
                novos.sort(
                    key=lambda video: video["curtidas"],
                    reverse=True
                )

                escolhido = novos[0]

                url = escolhido["url"]

                print(
                    f"Vídeo selecionado: {url}"
                )

                print(
                    f"Curtidas: {escolhido['curtidas']}"
                )

                if registrar_processado(url):

                    return url

                return None

            # Nenhum novo: rola para carregar mais cards
            if rodada < ROLAGENS_MAXIMAS:

                page.mouse.wheel(
                    0,
                    2000
                )

                page.wait_for_timeout(3000)

        print(
            "Nenhum vídeo novo encontrado."
        )

        return None

    except Exception as erro:

        print(
            f"Erro na busca: {erro}"
        )

        return None

    finally:

        print("Encerrando TikTok...")

        try:

            if page:

                try:
                    page.close()
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

            print("TikTok encerrado.")

        except Exception as erro:

            print(
                f"Erro ao fechar TikTok: {erro}"
            )