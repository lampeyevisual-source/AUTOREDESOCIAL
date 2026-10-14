import os
import re
import time

from urllib.parse import urlparse

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError
)


# =====================================================
# CONFIGURAÇÕES
# =====================================================

URL_SSTIK = "https://ssstik.io/ptn"

PASTA_BAIXADOS = os.path.join(
    "data",
    "videos",
    "baixados"
)

# Número máximo de sessões completas
# caso o SSSTik realmente trave.
MAX_REINICIOS = 3

# Quantas vezes tentaremos clicar no download
# caso o anúncio substitua o SSSTik.
MAX_TENTATIVAS_DOWNLOAD = 4


# =====================================================
# PREPARA PASTA
# =====================================================

def preparar_pasta():

    os.makedirs(
        PASTA_BAIXADOS,
        exist_ok=True
    )


# =====================================================
# EXTRAI ID DO VÍDEO
# =====================================================

def extrair_id_video(url):

    resultado = re.search(
        r"/video/(\d+)",
        url
    )

    if resultado:
        return resultado.group(1)

    partes = urlparse(
        url
    ).path.strip("/").split("/")

    if partes:
        return partes[-1]

    return "video"


# =====================================================
# VERIFICA SE A PÁGINA AINDA É O SSTIK
# =====================================================

def pagina_e_sstik(page):

    try:

        url = page.url.lower()

        if "ssstik.io" in url:
            return True

        return False

    except Exception:

        return False


# =====================================================
# TENTA FECHAR ANÚNCIOS / POPUPS
# =====================================================

def tentar_fechar_anuncio(page):

    print(
        "Procurando anúncio..."
    )

    seletores_fechar = [

        # Botões comuns
        '[aria-label="Fechar"]',
        '[aria-label="Close"]',

        'button[aria-label="Fechar"]',
        'button[aria-label="Close"]',

        # Textos
        'text=Fechar',
        'text=Close',

        # Possíveis containers
        '.close',
        '.close-button',
        '.close-btn',

        '[class*="close"]',
        '[class*="Close"]',

        '[id*="close"]',
        '[id*="Close"]',

        # Alguns anúncios utilizam X
        'button:has-text("×")',
        'button:has-text("✕")',
        'button:has-text("X")',
    ]

    for seletor in seletores_fechar:

        try:

            elementos = page.locator(
                seletor
            )

            quantidade = elementos.count()

            if quantidade == 0:
                continue

            for i in range(quantidade):

                try:

                    elemento = elementos.nth(i)

                    if not elemento.is_visible(
                        timeout=500
                    ):
                        continue

                    print(
                        f"Possível botão de anúncio encontrado: {seletor}"
                    )

                    # ---------------------------------
                    # TENTA CLICAR
                    # ---------------------------------

                    try:

                        elemento.click(
                            timeout=1000,
                            force=True
                        )

                        print(
                            "Anúncio fechado."
                        )

                        return True

                    except Exception:
                        pass

                    # ---------------------------------
                    # TENTA O PAI
                    # ---------------------------------

                    try:

                        pai = elemento.locator(
                            ".."
                        )

                        if pai.is_visible(
                            timeout=500
                        ):

                            pai.click(
                                timeout=1000,
                                force=True
                            )

                            print(
                                "Anúncio fechado pelo elemento pai."
                            )

                            return True

                    except Exception:
                        pass

                except Exception:
                    continue

        except Exception:
            continue

    print(
        "Nenhum botão de fechamento identificado."
    )

    return False


# =====================================================
# ESPERA PELO LINK SEM MARCA D'ÁGUA
# =====================================================

def esperar_link_download(page):

    print(
        "Aguardando link sem marca d'água..."
    )

    seletor = (
        "a.download_link.without_watermark"
    )

    try:

        page.locator(
            seletor
        ).wait_for(
            state="attached",
            timeout=45000
        )

        print(
            "Link de download encontrado."
        )

        return page.locator(
            seletor
        )

    except PlaywrightTimeoutError:

        print(
            "Link de download não apareceu."
        )

        return None


# =====================================================
# RECUPERA URL DO DOWNLOAD
# =====================================================

def obter_url_download(page, link_download):

    try:

        url = link_download.get_attribute(
            "href"
        )

        if url:

            print(
                "URL direta do download encontrada."
            )

            return url

    except Exception:
        pass

    return None


# =====================================================
# VOLTA PARA O SSTIK
# =====================================================

def voltar_para_sstik(page):

    try:

        print(
            "Anúncio substituiu o SSSTik. Voltando..."
        )

        page.go_back(
            wait_until="domcontentloaded",
            timeout=10000
        )

        page.wait_for_timeout(
            1500
        )

        if pagina_e_sstik(page):

            print(
                "SSSTik recuperado."
            )

            return True

    except Exception as erro:

        print(
            f"Erro ao voltar para o SSSTik: {erro}"
        )

    return False


# =====================================================
# TENTA REALIZAR O DOWNLOAD
# =====================================================

def realizar_download(
    page,
    link_download,
    caminho_arquivo
):

    # =================================================
    # PRIMEIRO: PEGA A URL DO LINK
    # =================================================

    url_download = obter_url_download(
        page,
        link_download
    )

    # =================================================
    # TENTATIVA DIRETA
    # =================================================

    if url_download:

        print(
            "Tentando download direto..."
        )

        try:

            resposta = page.request.get(
                url_download,
                timeout=120000
            )

            if resposta.ok:

                with open(
                    caminho_arquivo,
                    "wb"
                ) as arquivo:

                    arquivo.write(
                        resposta.body()
                    )

                tamanho = os.path.getsize(
                    caminho_arquivo
                )

                if tamanho > 0:

                    print(
                        "Download direto concluído."
                    )

                    print(
                        f"Tamanho: {tamanho:,} bytes"
                    )

                    return True

        except Exception as erro:

            print(
                f"Download direto falhou: {erro}"
            )

    # =================================================
    # SEGUNDA OPÇÃO:
    # CLICA NO LINK E CAPTURA DOWNLOAD
    # =================================================

    for tentativa in range(
        1,
        MAX_TENTATIVAS_DOWNLOAD + 1
    ):

        print()
        print(
            f"Tentativa de download "
            f"{tentativa}/{MAX_TENTATIVAS_DOWNLOAD}"
        )

        # ---------------------------------------------
        # GARANTE QUE ESTAMOS NO SSTIK
        # ---------------------------------------------

        if not pagina_e_sstik(page):

            if not voltar_para_sstik(page):

                print(
                    "Não foi possível retornar ao SSSTik."
                )

                continue

        # ---------------------------------------------
        # LOCALIZA NOVAMENTE O LINK
        # ---------------------------------------------

        try:

            link_download = page.locator(
                "a.download_link.without_watermark"
            )

            link_download.wait_for(
                state="visible",
                timeout=10000
            )

        except Exception:

            print(
                "Link não está disponível."
            )

            continue

        # ---------------------------------------------
        # TENTA CAPTURAR DOWNLOAD
        # ---------------------------------------------

        try:

            print(
                "Clicando no download sem marca d'água..."
            )

            with page.expect_download(
                timeout=8000
            ) as download_info:

                link_download.click(
                    timeout=5000,
                    force=True
                )

            download = download_info.value

            download.save_as(
                caminho_arquivo
            )

            print(
                "Download capturado com sucesso."
            )

            return True

        except PlaywrightTimeoutError:

            # -----------------------------------------
            # O ANÚNCIO PROVAVELMENTE SUBSTITUIU
            # O SSTIK.
            # -----------------------------------------

            print(
                "O download não foi iniciado."
            )

            page.wait_for_timeout(
                1000
            )

            # -----------------------------------------
            # VERIFICA SE O SSTIK FOI SUBSTITUÍDO
            # -----------------------------------------

            if not pagina_e_sstik(page):

                print(
                    "Anúncio detectado na mesma aba."
                )

                if voltar_para_sstik(page):

                    continue

            # -----------------------------------------
            # MESMO URL, MAS A PÁGINA CONTINUA SSTIK
            # -----------------------------------------

            print(
                "Tentando novamente..."
            )

        except Exception as erro:

            print(
                f"Erro durante o clique: {erro}"
            )

            if not pagina_e_sstik(page):

                voltar_para_sstik(
                    page
                )

    return False


# =====================================================
# BAIXA UM VÍDEO
# =====================================================

def baixar_video(
    link_tiktok,
    tentativa=1
):

    preparar_pasta()

    playwright = None
    navegador = None
    contexto = None

    try:

        # =================================================
        # ID DO VÍDEO
        # =================================================

        id_video = extrair_id_video(
            link_tiktok
        )

        nome_arquivo = (
            f"{id_video}.mp4"
        )

        caminho_arquivo = os.path.join(
            PASTA_BAIXADOS,
            nome_arquivo
        )

        # =================================================
        # VERIFICA SE JÁ EXISTE
        # =================================================

        if os.path.exists(
            caminho_arquivo
        ):

            tamanho = os.path.getsize(
                caminho_arquivo
            )

            if tamanho > 0:

                print(
                    "Vídeo já existe na pasta de baixados."
                )

                return caminho_arquivo

        # =================================================
        # INÍCIO
        # =================================================

        print()
        print(
            "================================"
        )
        print(
            f"Iniciando downloader - tentativa "
            f"{tentativa}/{MAX_REINICIOS}"
        )
        print(
            f"Vídeo: {link_tiktok}"
        )
        print(
            "================================"
        )

        # =================================================
        # PLAYWRIGHT
        # =================================================

        playwright = sync_playwright().start()

        navegador = playwright.chromium.launch(
            headless=False
        )

        contexto = navegador.new_context(
            accept_downloads=True
        )

        page = contexto.new_page()

        # =================================================
        # ABRE SSTIK
        # =================================================

        print(
            "Acessando SSSTik..."
        )

        page.goto(
            URL_SSTIK,
            wait_until="domcontentloaded",
            timeout=60000
        )

        # Pequena espera para a interface carregar.
        page.wait_for_timeout(
            1500
        )

        # =================================================
        # PREENCHE LINK
        # =================================================

        campo_link = page.locator(
            "#main_page_text"
        )

        campo_link.wait_for(
            state="visible",
            timeout=30000
        )

        campo_link.fill(
            link_tiktok
        )

        print(
            "Link preenchido."
        )

        # =================================================
        # CLICA EM BAIXAR
        # =================================================

        botao_baixar = page.locator(
            "#submit"
        )

        botao_baixar.wait_for(
            state="visible",
            timeout=30000
        )

        botao_baixar.click(
            timeout=10000
        )

        print(
            "Processamento iniciado."
        )

        # =================================================
        # NÃO ESPERA 20 SEGUNDOS FIXOS
        # =================================================
        #
        # O código agora espera pelo elemento real.
        # =================================================

        link_download = esperar_link_download(
            page
        )

        if not link_download:

            raise Exception(
                "SSSTik não disponibilizou o link de download."
            )

        # =================================================
        # TENTA FECHAR ALGUM POPUP EXISTENTE
        # =================================================

        tentar_fechar_anuncio(
            page
        )

        # =================================================
        # DOWNLOAD
        # =================================================

        print()
        print(
            "Iniciando processo de download..."
        )

        sucesso = realizar_download(
            page,
            link_download,
            caminho_arquivo
        )

        if not sucesso:

            raise Exception(
                "Não foi possível realizar o download após "
                f"{MAX_TENTATIVAS_DOWNLOAD} tentativas."
            )

        # =================================================
        # VERIFICA ARQUIVO
        # =================================================

        if not os.path.exists(
            caminho_arquivo
        ):

            raise Exception(
                "O download terminou, mas o arquivo não foi encontrado."
            )

        tamanho = os.path.getsize(
            caminho_arquivo
        )

        if tamanho <= 0:

            try:

                os.remove(
                    caminho_arquivo
                )

            except Exception:
                pass

            raise Exception(
                "O arquivo baixado está vazio."
            )

        # =================================================
        # SUCESSO
        # =================================================

        print()
        print(
            "================================"
        )
        print(
            "DOWNLOAD CONCLUÍDO"
        )
        print(
            f"Vídeo salvo: {caminho_arquivo}"
        )
        print(
            f"Tamanho: {tamanho:,} bytes"
        )
        print(
            "================================"
        )

        return caminho_arquivo

    # =====================================================
    # TIMEOUT
    # =====================================================

    except PlaywrightTimeoutError as erro:

        print()
        print(
            f"Tempo limite excedido: {erro}"
        )

    # =====================================================
    # OUTRO ERRO
    # =====================================================

    except Exception as erro:

        print()
        print(
            f"Erro na tentativa {tentativa}: {erro}"
        )

    finally:

        # =================================================
        # FECHA CONTEXTO
        # =================================================

        if contexto:

            try:
                contexto.close()
            except Exception:
                pass

        # =================================================
        # FECHA NAVEGADOR
        # =================================================

        if navegador:

            try:
                navegador.close()
            except Exception:
                pass

        # =================================================
        # PARA PLAYWRIGHT
        # =================================================

        if playwright:

            try:
                playwright.stop()
            except Exception:
                pass

        print(
            "Sessão do downloader encerrada."
        )

    # =====================================================
    # REINICIA AUTOMATICAMENTE
    # =====================================================

    if tentativa < MAX_REINICIOS:

        print()
        print(
            "================================"
        )
        print(
            "REINICIANDO DOWNLOADER..."
        )
        print(
            f"Nova tentativa: "
            f"{tentativa + 1}/{MAX_REINICIOS}"
        )
        print(
            "================================"
        )

        time.sleep(
            3
        )

        return baixar_video(
            link_tiktok,
            tentativa + 1
        )

    # =====================================================
    # ESGOTOU TENTATIVAS
    # =====================================================

    print()
    print(
        "================================"
    )
    print(
        "NÚMERO MÁXIMO DE TENTATIVAS ATINGIDO."
    )
    print(
        "Download não concluído."
    )
    print(
        "================================"
    )

    return None


# =====================================================
# TESTE DIRETO
# =====================================================

if __name__ == "__main__":

    link = input(
        "Cole o link do TikTok: "
    ).strip()

    if link:

        arquivo = baixar_video(
            link
        )

        if arquivo:

            print()
            print(
                f"Download concluído: {arquivo}"
            )

        else:

            print()
            print(
                "Não foi possível baixar o vídeo."
            )