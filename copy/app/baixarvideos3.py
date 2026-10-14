
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


# =====================================================
# CONFIGURAÇÕES
# =====================================================

URL_VIDSSAVE = "https://br.vidssave.com/home"

PASTA_BAIXADOS = os.path.join(
    "copy",
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
# CRIAR PASTA ESPECÍFICA PARA CADA CATEGORIA
# =====================================================

def obter_pasta_categoria(categoria):
    categoria = (categoria or "sem_categoria").strip()

    nome_pasta = re.sub(
        r'[<>:"/\\|?*]',
        "_",
        categoria,
    ).strip(" .")

    if not nome_pasta:
        nome_pasta = "sem_categoria"

    pasta_categoria = os.path.join(
        PASTA_BAIXADOS,
        nome_pasta,
    )

    os.makedirs(
        pasta_categoria,
        exist_ok=True,
    )

    return pasta_categoria


# =====================================================
# EXTRAIR ID DO SHORT
# =====================================================

def extrair_id_video(url):
    url = url.strip()
    partes_url = urlparse(url)
    partes = partes_url.path.strip("/").split("/")

    if "shorts" in partes:
        indice = partes.index("shorts")

        if indice + 1 < len(partes):
            return partes[indice + 1]

    if "watch" in partes:
        return parse_qs(
            partes_url.query
        ).get("v", [None])[0] or "youtube_short"

    if "youtu.be" in partes_url.netloc.lower():
        return partes[0] if partes and partes[0] else "youtube_short"

    if re.fullmatch(r"[A-Za-z0-9_-]{6,}", url):
        return url

    return "youtube_short"


# =====================================================
# VALIDAR MP4
# =====================================================

def validar_video_mp4(caminho):
    try:
        arquivo = Path(caminho)

        if not arquivo.is_file():
            return False

        if arquivo.suffix.lower() != ".mp4":
            return False

        if arquivo.stat().st_size < 1024:
            return False

        with arquivo.open("rb") as f:
            cabecalho = f.read(64)

        return b"ftyp" in cabecalho

    except OSError:
        return False


# =====================================================
# BAIXAR MP4 PELO VIDSSAVE
# =====================================================

def clicar_opcao_mp4_480p(page, caminho_arquivo):
    destino = Path(caminho_arquivo)
    destino.parent.mkdir(parents=True, exist_ok=True)

    contexto = page.context

    # A mesma sequência é aplicada a ambas as resoluções.
    for resolucao in ("480P", "360P"):
        print(f"\nProcurando opção MP4 {resolucao}...")

        try:
            texto_resolucao = page.get_by_text(
                re.compile(
                    rf"MP4\s*{re.escape(resolucao)}",
                    re.IGNORECASE,
                ),
                exact=False,
            ).first

            texto_resolucao.wait_for(
                state="visible",
                timeout=30000,
            )

            linha = texto_resolucao.locator(
                "xpath=ancestor::*[.//*[normalize-space()='Baixar']][1]"
            )

            botao = linha.get_by_text(
                "Baixar",
                exact=True,
            ).last

            botao.wait_for(
                state="visible",
                timeout=15000,
            )

            # -------------------------------------------------
            # 1. TENTAR DOWNLOAD DIRETO
            # -------------------------------------------------

            try:
                with page.expect_download(
                    timeout=15000
                ) as evento:
                    botao.click(timeout=10000)

                download = evento.value
                download.save_as(str(destino))

                if validar_video_mp4(destino):
                    print(
                        f"Download {resolucao} concluído."
                    )
                    return str(destino)

                if destino.exists():
                    destino.unlink()

                print(
                    "O arquivo recebido não passou "
                    "na validação MP4."
                )

            except PlaywrightTimeoutError:
                print(
                    "O download direto não começou. "
                    "Verificando as janelas alternativas..."
                )

            # -------------------------------------------------
            # 2. PROCURAR LINK DIRETO E "BAIXAR AGORA"
            # -------------------------------------------------

            limite = time.monotonic() + 60

            while time.monotonic() < limite:
                links_encontrados = False

                # Examina todas as páginas abertas no contexto.
                for pagina_link in list(contexto.pages):
                    if pagina_link.is_closed():
                        continue

                    try:
                        links = pagina_link.locator(
                            'a[href*="download_redirect"], '
                            'a:has-text("Baixar agora"), '
                            'a:has-text("Clique para baixar o vídeo diretamente")'
                        )

                        quantidade = links.count()

                    except Exception:
                        continue

                    for indice in range(quantidade):
                        link = links.nth(indice)

                        try:
                            if not link.is_visible():
                                continue

                            href = link.get_attribute("href") or ""
                            texto = link.inner_text(
                                timeout=2000
                            ).strip().lower()

                            eh_link_direto = (
                                "download_redirect" in href
                                or "clique para baixar" in texto
                            )

                            eh_baixar_agora = (
                                "baixar agora" in texto
                            )

                            if not (
                                eh_link_direto
                                or eh_baixar_agora
                            ):
                                continue

                            links_encontrados = True

                            if eh_link_direto:
                                print(
                                    f"Link direto da opção "
                                    f"{resolucao} encontrado."
                                )
                            else:
                                print(
                                    "Janela de vídeo pronto: "
                                    "botão Baixar agora encontrado."
                                )

                            # Evita abrir outra aba quando o link
                            # estiver marcado com target="_blank".
                            try:
                                link.evaluate(
                                    """el => el.setAttribute(
                                        'target',
                                        '_self'
                                    )"""
                                )
                            except Exception:
                                pass

                            try:
                                with pagina_link.expect_download(
                                    timeout=15000
                                ) as evento:
                                    link.click(timeout=10000)

                                download = evento.value
                                download.save_as(str(destino))

                                if validar_video_mp4(destino):
                                    print(
                                        f"Download {resolucao} "
                                        "confirmado pelo link alternativo."
                                    )
                                    return str(destino)

                                if destino.exists():
                                    destino.unlink()

                            except PlaywrightTimeoutError:
                                print(
                                    "O clique não iniciou um download "
                                    "detectável nessa página."
                                )

                        except Exception as erro_link:
                            print(
                                f"Não foi possível usar o link: "
                                f"{erro_link}"
                            )

                # Se os links ainda não apareceram, aguarda.
                page.wait_for_timeout(500)

            print(
                f"Não foi possível concluir o download "
                f"em {resolucao}."
            )

        except PlaywrightTimeoutError:
            print(
                f"A opção MP4 {resolucao} não apareceu "
                "dentro do tempo limite."
            )

        except Exception as erro:
            print(
                f"Erro na tentativa {resolucao}: {erro}"
            )

        if destino.exists() and not validar_video_mp4(destino):
            try:
                destino.unlink()
            except OSError:
                pass

    raise RuntimeError(
        "Não foi possível baixar um MP4 válido em 480P ou 360P."
    )


# =====================================================
# BAIXAR UM SHORT
# =====================================================

def baixar_video(
    link_youtube,
    tentativa=1,
    categoria="sem_categoria",
):
    preparar_pasta()

    pasta_categoria = obter_pasta_categoria(categoria)

    link_youtube = link_youtube.strip()
    id_video = extrair_id_video(link_youtube)

    caminho_arquivo = os.path.join(
        pasta_categoria,
        f"{id_video}.mp4",
    )

    # -------------------------------------------------
    # VERIFICAR SE JÁ EXISTE UM MP4 VÁLIDO
    # -------------------------------------------------

    if validar_video_mp4(caminho_arquivo):
        print(f"Vídeo já baixado: {caminho_arquivo}")
        return caminho_arquivo

    if os.path.exists(caminho_arquivo):
        try:
            os.remove(caminho_arquivo)
        except OSError as erro:
            print(f"Não foi possível remover arquivo inválido: {erro}")
            return None

    # -------------------------------------------------
    # TENTATIVAS CONTROLADAS, SEM RECURSÃO
    # -------------------------------------------------

    for numero_tentativa in range(
        tentativa,
        MAX_REINICIOS + 1,
    ):
        playwright = None
        navegador = None
        contexto = None

        try:
            print("\n======================================")
            print(
                f"DOWNLOAD DO YOUTUBE - "
                f"TENTATIVA {numero_tentativa}/{MAX_REINICIOS}"
            )
            print(f"URL: {link_youtube}")
            print("======================================")

            # Esta versão usa a API síncrona.
            # Execute o arquivo diretamente pelo PowerShell,
            # sem chamá-lo de dentro de um loop asyncio.
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
            page.set_default_timeout(30000)

            # -------------------------------------------------
            # ABRIR VIDSSAVE
            # -------------------------------------------------

            print("Abrindo Vidssave...")

            page.goto(
                URL_VIDSSAVE,
                wait_until="domcontentloaded",
                timeout=TIMEOUT_DOWNLOAD,
            )

            # -------------------------------------------------
            # INSERIR O LINK DO YOUTUBE
            # -------------------------------------------------

            campo = page.locator(
                "#url-input-wrapper"
            )

            campo.wait_for(
                state="visible",
                timeout=30000,
            )

            campo.fill(link_youtube)

            print("Link inserido no Vidssave.")

            # -------------------------------------------------
            # CLICAR EM BAIXAR
            # -------------------------------------------------

            botao_inicial = page.get_by_text(
                "Baixar",
                exact=True,
            ).first

            botao_inicial.wait_for(
                state="visible",
                timeout=30000,
            )

            botao_inicial.click()

            print(
                "Aguardando opções de resolução..."
            )

            # -------------------------------------------------
            # ESPERAR AS OPÇÕES MP4
            # -------------------------------------------------

            limite = time.monotonic() + 60
            opcoes_prontas = False

            while time.monotonic() < limite:
                try:
                    opcoes = page.get_by_text(
                        re.compile(
                            r"MP4\s*480P",
                            re.IGNORECASE,
                        ),
                        exact=False,
                    )

                    if opcoes.count() > 0:
                        opcoes_prontas = True
                        break

                except Exception:
                    pass

                page.wait_for_timeout(500)

            if not opcoes_prontas:
                raise RuntimeError(
                    "O Vidssave não apresentou as opções MP4."
                )

            # -------------------------------------------------
            # EXECUTAR FLUXO 480P E DEPOIS 360P
            # -------------------------------------------------

            resultado = clicar_opcao_mp4_480p(
                page,
                caminho_arquivo,
            )

            if resultado and validar_video_mp4(resultado):
                print("\n======================================")
                print("DOWNLOAD CONCLUÍDO")
                print(f"Arquivo: {resultado}")
                print("======================================")

                return resultado

            raise RuntimeError(
                "O download não produziu um MP4 válido."
            )

        except Exception as erro:
            print(f"\nErro no download: {erro}")

        finally:
            # Cada tentativa fecha os recursos antes da próxima.
            if contexto is not None:
                try:
                    contexto.close()
                except Exception:
                    pass

            if navegador is not None:
                try:
                    navegador.close()
                except Exception:
                    pass

            if playwright is not None:
                try:
                    playwright.stop()
                except Exception:
                    pass

        if numero_tentativa < MAX_REINICIOS:
            print("Nova tentativa em 3 segundos...")
            time.sleep(3)

    print("Número máximo de tentativas atingido.")
    return None


# =====================================================
# RECEPÇÃO DO LINK
# =====================================================

if __name__ == "__main__":
    link = input(
        "Cole o link do YouTube Shorts: "
    ).strip()

    if link:
        arquivo = baixar_video(link)

        if arquivo:
            print(f"\nVídeo salvo em: {arquivo}")
        else:
            print("\nO download não foi concluído.")

import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


# =====================================================
# CONFIGURAÇÕES
# =====================================================

URL_VIDSSAVE = "https://br.vidssave.com/home"

PASTA_BAIXADOS = os.path.join(
    "copy",
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
# CRIAR PASTA ESPECÍFICA PARA CADA CATEGORIA
# =====================================================

def obter_pasta_categoria(categoria):
    categoria = (categoria or "sem_categoria").strip()

    nome_pasta = re.sub(
        r'[<>:"/\\|?*]',
        "_",
        categoria,
    ).strip(" .")

    if not nome_pasta:
        nome_pasta = "sem_categoria"

    pasta_categoria = os.path.join(
        PASTA_BAIXADOS,
        nome_pasta,
    )

    os.makedirs(
        pasta_categoria,
        exist_ok=True,
    )

    return pasta_categoria


# =====================================================
# EXTRAIR ID DO SHORT
# =====================================================

def extrair_id_video(url):
    url = url.strip()
    partes_url = urlparse(url)
    partes = partes_url.path.strip("/").split("/")

    if "shorts" in partes:
        indice = partes.index("shorts")

        if indice + 1 < len(partes):
            return partes[indice + 1]

    if "watch" in partes:
        return parse_qs(
            partes_url.query
        ).get("v", [None])[0] or "youtube_short"

    if "youtu.be" in partes_url.netloc.lower():
        return partes[0] if partes and partes[0] else "youtube_short"

    if re.fullmatch(r"[A-Za-z0-9_-]{6,}", url):
        return url

    return "youtube_short"


# =====================================================
# VALIDAR MP4
# =====================================================

def validar_video_mp4(caminho):
    try:
        arquivo = Path(caminho)

        if not arquivo.is_file():
            return False

        if arquivo.suffix.lower() != ".mp4":
            return False

        if arquivo.stat().st_size < 1024:
            return False

        with arquivo.open("rb") as f:
            cabecalho = f.read(64)

        return b"ftyp" in cabecalho

    except OSError:
        return False


# =====================================================
# BAIXAR MP4 PELO VIDSSAVE
# =====================================================

def clicar_opcao_mp4_480p(page, caminho_arquivo):
    destino = Path(caminho_arquivo)
    destino.parent.mkdir(parents=True, exist_ok=True)

    contexto = page.context

    # A mesma sequência é aplicada a ambas as resoluções.
    for resolucao in ("480P", "360P"):
        print(f"\nProcurando opção MP4 {resolucao}...")

        try:
            texto_resolucao = page.get_by_text(
                re.compile(
                    rf"MP4\s*{re.escape(resolucao)}",
                    re.IGNORECASE,
                ),
                exact=False,
            ).first

            texto_resolucao.wait_for(
                state="visible",
                timeout=30000,
            )

            linha = texto_resolucao.locator(
                "xpath=ancestor::*[.//*[normalize-space()='Baixar']][1]"
            )

            botao = linha.get_by_text(
                "Baixar",
                exact=True,
            ).last

            botao.wait_for(
                state="visible",
                timeout=15000,
            )

            # -------------------------------------------------
            # 1. TENTAR DOWNLOAD DIRETO
            # -------------------------------------------------

            try:
                with page.expect_download(
                    timeout=15000
                ) as evento:
                    botao.click(timeout=10000)

                download = evento.value
                download.save_as(str(destino))

                if validar_video_mp4(destino):
                    print(
                        f"Download {resolucao} concluído."
                    )
                    return str(destino)

                if destino.exists():
                    destino.unlink()

                print(
                    "O arquivo recebido não passou "
                    "na validação MP4."
                )

            except PlaywrightTimeoutError:
                print(
                    "O download direto não começou. "
                    "Verificando as janelas alternativas..."
                )

            # -------------------------------------------------
            # 2. PROCURAR LINK DIRETO E "BAIXAR AGORA"
            # -------------------------------------------------

            limite = time.monotonic() + 60

            while time.monotonic() < limite:
                links_encontrados = False

                # Examina todas as páginas abertas no contexto.
                for pagina_link in list(contexto.pages):
                    if pagina_link.is_closed():
                        continue

                    try:
                        links = pagina_link.locator(
                            'a[href*="download_redirect"], '
                            'a:has-text("Baixar agora"), '
                            'a:has-text("Clique para baixar o vídeo diretamente")'
                        )

                        quantidade = links.count()

                    except Exception:
                        continue

                    for indice in range(quantidade):
                        link = links.nth(indice)

                        try:
                            if not link.is_visible():
                                continue

                            href = link.get_attribute("href") or ""
                            texto = link.inner_text(
                                timeout=2000
                            ).strip().lower()

                            eh_link_direto = (
                                "download_redirect" in href
                                or "clique para baixar" in texto
                            )

                            eh_baixar_agora = (
                                "baixar agora" in texto
                            )

                            if not (
                                eh_link_direto
                                or eh_baixar_agora
                            ):
                                continue

                            links_encontrados = True

                            if eh_link_direto:
                                print(
                                    f"Link direto da opção "
                                    f"{resolucao} encontrado."
                                )
                            else:
                                print(
                                    "Janela de vídeo pronto: "
                                    "botão Baixar agora encontrado."
                                )

                            # Evita abrir outra aba quando o link
                            # estiver marcado com target="_blank".
                            try:
                                link.evaluate(
                                    """el => el.setAttribute(
                                        'target',
                                        '_self'
                                    )"""
                                )
                            except Exception:
                                pass

                            try:
                                with pagina_link.expect_download(
                                    timeout=15000
                                ) as evento:
                                    link.click(timeout=10000)

                                download = evento.value
                                download.save_as(str(destino))

                                if validar_video_mp4(destino):
                                    print(
                                        f"Download {resolucao} "
                                        "confirmado pelo link alternativo."
                                    )
                                    return str(destino)

                                if destino.exists():
                                    destino.unlink()

                            except PlaywrightTimeoutError:
                                print(
                                    "O clique não iniciou um download "
                                    "detectável nessa página."
                                )

                        except Exception as erro_link:
                            print(
                                f"Não foi possível usar o link: "
                                f"{erro_link}"
                            )

                # Se os links ainda não apareceram, aguarda.
                page.wait_for_timeout(500)

            print(
                f"Não foi possível concluir o download "
                f"em {resolucao}."
            )

        except PlaywrightTimeoutError:
            print(
                f"A opção MP4 {resolucao} não apareceu "
                "dentro do tempo limite."
            )

        except Exception as erro:
            print(
                f"Erro na tentativa {resolucao}: {erro}"
            )

        if destino.exists() and not validar_video_mp4(destino):
            try:
                destino.unlink()
            except OSError:
                pass

    raise RuntimeError(
        "Não foi possível baixar um MP4 válido em 480P ou 360P."
    )


# =====================================================
# BAIXAR UM SHORT
# =====================================================

def baixar_video(
    link_youtube,
    tentativa=1,
    categoria="sem_categoria",
):
    preparar_pasta()

    pasta_categoria = obter_pasta_categoria(categoria)

    link_youtube = link_youtube.strip()
    id_video = extrair_id_video(link_youtube)

    caminho_arquivo = os.path.join(
        pasta_categoria,
        f"{id_video}.mp4",
    )

    # -------------------------------------------------
    # VERIFICAR SE JÁ EXISTE UM MP4 VÁLIDO
    # -------------------------------------------------

    if validar_video_mp4(caminho_arquivo):
        print(f"Vídeo já baixado: {caminho_arquivo}")
        return caminho_arquivo

    if os.path.exists(caminho_arquivo):
        try:
            os.remove(caminho_arquivo)
        except OSError as erro:
            print(f"Não foi possível remover arquivo inválido: {erro}")
            return None

    # -------------------------------------------------
    # TENTATIVAS CONTROLADAS, SEM RECURSÃO
    # -------------------------------------------------

    for numero_tentativa in range(
        tentativa,
        MAX_REINICIOS + 1,
    ):
        playwright = None
        navegador = None
        contexto = None

        try:
            print("\n======================================")
            print(
                f"DOWNLOAD DO YOUTUBE - "
                f"TENTATIVA {numero_tentativa}/{MAX_REINICIOS}"
            )
            print(f"URL: {link_youtube}")
            print("======================================")

            # Esta versão usa a API síncrona.
            # Execute o arquivo diretamente pelo PowerShell,
            # sem chamá-lo de dentro de um loop asyncio.
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
            page.set_default_timeout(30000)

            # -------------------------------------------------
            # ABRIR VIDSSAVE
            # -------------------------------------------------

            print("Abrindo Vidssave...")

            page.goto(
                URL_VIDSSAVE,
                wait_until="domcontentloaded",
                timeout=TIMEOUT_DOWNLOAD,
            )

            # -------------------------------------------------
            # INSERIR O LINK DO YOUTUBE
            # -------------------------------------------------

            campo = page.locator(
                "#url-input-wrapper"
            )

            campo.wait_for(
                state="visible",
                timeout=30000,
            )

            campo.fill(link_youtube)

            print("Link inserido no Vidssave.")

            # -------------------------------------------------
            # CLICAR EM BAIXAR
            # -------------------------------------------------

            botao_inicial = page.get_by_text(
                "Baixar",
                exact=True,
            ).first

            botao_inicial.wait_for(
                state="visible",
                timeout=30000,
            )

            botao_inicial.click()

            print(
                "Aguardando opções de resolução..."
            )

            # -------------------------------------------------
            # ESPERAR AS OPÇÕES MP4
            # -------------------------------------------------

            limite = time.monotonic() + 60
            opcoes_prontas = False

            while time.monotonic() < limite:
                try:
                    opcoes = page.get_by_text(
                        re.compile(
                            r"MP4\s*480P",
                            re.IGNORECASE,
                        ),
                        exact=False,
                    )

                    if opcoes.count() > 0:
                        opcoes_prontas = True
                        break

                except Exception:
                    pass

                page.wait_for_timeout(500)

            if not opcoes_prontas:
                raise RuntimeError(
                    "O Vidssave não apresentou as opções MP4."
                )

            # -------------------------------------------------
            # EXECUTAR FLUXO 480P E DEPOIS 360P
            # -------------------------------------------------

            resultado = clicar_opcao_mp4_480p(
                page,
                caminho_arquivo,
            )

            if resultado and validar_video_mp4(resultado):
                print("\n======================================")
                print("DOWNLOAD CONCLUÍDO")
                print(f"Arquivo: {resultado}")
                print("======================================")

                return resultado

            raise RuntimeError(
                "O download não produziu um MP4 válido."
            )

        except Exception as erro:
            print(f"\nErro no download: {erro}")

        finally:
            # Cada tentativa fecha os recursos antes da próxima.
            if contexto is not None:
                try:
                    contexto.close()
                except Exception:
                    pass

            if navegador is not None:
                try:
                    navegador.close()
                except Exception:
                    pass

            if playwright is not None:
                try:
                    playwright.stop()
                except Exception:
                    pass

        if numero_tentativa < MAX_REINICIOS:
            print("Nova tentativa em 3 segundos...")
            time.sleep(3)

    print("Número máximo de tentativas atingido.")
    return None


# =====================================================
# RECEPÇÃO DO LINK
# =====================================================

if __name__ == "__main__":
    link = input(
        "Cole o link do YouTube Shorts: "
    ).strip()

    if link:
        arquivo = baixar_video(link)

        if arquivo:
            print(f"\nVídeo salvo em: {arquivo}")
        else:
            print("\nO download não foi concluído.")

import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


# =====================================================
# CONFIGURAÇÕES
# =====================================================

URL_VIDSSAVE = "https://br.vidssave.com/home"

PASTA_BAIXADOS = os.path.join(
    "copy",
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
# CRIAR PASTA ESPECÍFICA PARA CADA CATEGORIA
# =====================================================

def obter_pasta_categoria(categoria):
    categoria = (categoria or "sem_categoria").strip()

    nome_pasta = re.sub(
        r'[<>:"/\\|?*]',
        "_",
        categoria,
    ).strip(" .")

    if not nome_pasta:
        nome_pasta = "sem_categoria"

    pasta_categoria = os.path.join(
        PASTA_BAIXADOS,
        nome_pasta,
    )

    os.makedirs(
        pasta_categoria,
        exist_ok=True,
    )

    return pasta_categoria


# =====================================================
# EXTRAIR ID DO SHORT
# =====================================================

def extrair_id_video(url):
    url = url.strip()
    partes_url = urlparse(url)
    partes = partes_url.path.strip("/").split("/")

    if "shorts" in partes:
        indice = partes.index("shorts")

        if indice + 1 < len(partes):
            return partes[indice + 1]

    if "watch" in partes:
        return parse_qs(
            partes_url.query
        ).get("v", [None])[0] or "youtube_short"

    if "youtu.be" in partes_url.netloc.lower():
        return partes[0] if partes and partes[0] else "youtube_short"

    if re.fullmatch(r"[A-Za-z0-9_-]{6,}", url):
        return url

    return "youtube_short"


# =====================================================
# VALIDAR MP4
# =====================================================

def validar_video_mp4(caminho):
    try:
        arquivo = Path(caminho)

        if not arquivo.is_file():
            return False

        if arquivo.suffix.lower() != ".mp4":
            return False

        if arquivo.stat().st_size < 1024:
            return False

        with arquivo.open("rb") as f:
            cabecalho = f.read(64)

        return b"ftyp" in cabecalho

    except OSError:
        return False


# =====================================================
# BAIXAR MP4 PELO VIDSSAVE
# =====================================================

def clicar_opcao_mp4_480p(page, caminho_arquivo):
    destino = Path(caminho_arquivo)
    destino.parent.mkdir(parents=True, exist_ok=True)

    contexto = page.context

    # A mesma sequência é aplicada a ambas as resoluções.
    for resolucao in ("480P", "360P"):
        print(f"\nProcurando opção MP4 {resolucao}...")

        try:
            texto_resolucao = page.get_by_text(
                re.compile(
                    rf"MP4\s*{re.escape(resolucao)}",
                    re.IGNORECASE,
                ),
                exact=False,
            ).first

            texto_resolucao.wait_for(
                state="visible",
                timeout=30000,
            )

            linha = texto_resolucao.locator(
                "xpath=ancestor::*[.//*[normalize-space()='Baixar']][1]"
            )

            botao = linha.get_by_text(
                "Baixar",
                exact=True,
            ).last

            botao.wait_for(
                state="visible",
                timeout=15000,
            )

            # -------------------------------------------------
            # 1. TENTAR DOWNLOAD DIRETO
            # -------------------------------------------------

            try:
                with page.expect_download(
                    timeout=15000
                ) as evento:
                    botao.click(timeout=10000)

                download = evento.value
                download.save_as(str(destino))

                if validar_video_mp4(destino):
                    print(
                        f"Download {resolucao} concluído."
                    )
                    return str(destino)

                if destino.exists():
                    destino.unlink()

                print(
                    "O arquivo recebido não passou "
                    "na validação MP4."
                )

            except PlaywrightTimeoutError:
                print(
                    "O download direto não começou. "
                    "Verificando as janelas alternativas..."
                )

            # -------------------------------------------------
            # 2. PROCURAR LINK DIRETO E "BAIXAR AGORA"
            # -------------------------------------------------

            limite = time.monotonic() + 60

            while time.monotonic() < limite:
                links_encontrados = False

                # Examina todas as páginas abertas no contexto.
                for pagina_link in list(contexto.pages):
                    if pagina_link.is_closed():
                        continue

                    try:
                        links = pagina_link.locator(
                            'a[href*="download_redirect"], '
                            'a:has-text("Baixar agora"), '
                            'a:has-text("Clique para baixar o vídeo diretamente")'
                        )

                        quantidade = links.count()

                    except Exception:
                        continue

                    for indice in range(quantidade):
                        link = links.nth(indice)

                        try:
                            if not link.is_visible():
                                continue

                            href = link.get_attribute("href") or ""
                            texto = link.inner_text(
                                timeout=2000
                            ).strip().lower()

                            eh_link_direto = (
                                "download_redirect" in href
                                or "clique para baixar" in texto
                            )

                            eh_baixar_agora = (
                                "baixar agora" in texto
                            )

                            if not (
                                eh_link_direto
                                or eh_baixar_agora
                            ):
                                continue

                            links_encontrados = True

                            if eh_link_direto:
                                print(
                                    f"Link direto da opção "
                                    f"{resolucao} encontrado."
                                )
                            else:
                                print(
                                    "Janela de vídeo pronto: "
                                    "botão Baixar agora encontrado."
                                )

                            # Evita abrir outra aba quando o link
                            # estiver marcado com target="_blank".
                            try:
                                link.evaluate(
                                    """el => el.setAttribute(
                                        'target',
                                        '_self'
                                    )"""
                                )
                            except Exception:
                                pass

                            try:
                                with pagina_link.expect_download(
                                    timeout=15000
                                ) as evento:
                                    link.click(timeout=10000)

                                download = evento.value
                                download.save_as(str(destino))

                                if validar_video_mp4(destino):
                                    print(
                                        f"Download {resolucao} "
                                        "confirmado pelo link alternativo."
                                    )
                                    return str(destino)

                                if destino.exists():
                                    destino.unlink()

                            except PlaywrightTimeoutError:
                                print(
                                    "O clique não iniciou um download "
                                    "detectável nessa página."
                                )

                        except Exception as erro_link:
                            print(
                                f"Não foi possível usar o link: "
                                f"{erro_link}"
                            )

                # Se os links ainda não apareceram, aguarda.
                page.wait_for_timeout(500)

            print(
                f"Não foi possível concluir o download "
                f"em {resolucao}."
            )

        except PlaywrightTimeoutError:
            print(
                f"A opção MP4 {resolucao} não apareceu "
                "dentro do tempo limite."
            )

        except Exception as erro:
            print(
                f"Erro na tentativa {resolucao}: {erro}"
            )

        if destino.exists() and not validar_video_mp4(destino):
            try:
                destino.unlink()
            except OSError:
                pass

    raise RuntimeError(
        "Não foi possível baixar um MP4 válido em 480P ou 360P."
    )


# =====================================================
# BAIXAR UM SHORT
# =====================================================

def baixar_video(
    link_youtube,
    tentativa=1,
    categoria="sem_categoria",
):
    preparar_pasta()

    pasta_categoria = obter_pasta_categoria(categoria)

    link_youtube = link_youtube.strip()
    id_video = extrair_id_video(link_youtube)

    caminho_arquivo = os.path.join(
        pasta_categoria,
        f"{id_video}.mp4",
    )

    # -------------------------------------------------
    # VERIFICAR SE JÁ EXISTE UM MP4 VÁLIDO
    # -------------------------------------------------

    if validar_video_mp4(caminho_arquivo):
        print(f"Vídeo já baixado: {caminho_arquivo}")
        return caminho_arquivo

    if os.path.exists(caminho_arquivo):
        try:
            os.remove(caminho_arquivo)
        except OSError as erro:
            print(f"Não foi possível remover arquivo inválido: {erro}")
            return None

    # -------------------------------------------------
    # TENTATIVAS CONTROLADAS, SEM RECURSÃO
    # -------------------------------------------------

    for numero_tentativa in range(
        tentativa,
        MAX_REINICIOS + 1,
    ):
        playwright = None
        navegador = None
        contexto = None

        try:
            print("\n======================================")
            print(
                f"DOWNLOAD DO YOUTUBE - "
                f"TENTATIVA {numero_tentativa}/{MAX_REINICIOS}"
            )
            print(f"URL: {link_youtube}")
            print("======================================")

            # Esta versão usa a API síncrona.
            # Execute o arquivo diretamente pelo PowerShell,
            # sem chamá-lo de dentro de um loop asyncio.
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
            page.set_default_timeout(30000)

            # -------------------------------------------------
            # ABRIR VIDSSAVE
            # -------------------------------------------------

            print("Abrindo Vidssave...")

            page.goto(
                URL_VIDSSAVE,
                wait_until="domcontentloaded",
                timeout=TIMEOUT_DOWNLOAD,
            )

            # -------------------------------------------------
            # INSERIR O LINK DO YOUTUBE
            # -------------------------------------------------

            campo = page.locator(
                "#url-input-wrapper"
            )

            campo.wait_for(
                state="visible",
                timeout=30000,
            )

            campo.fill(link_youtube)

            print("Link inserido no Vidssave.")

            # -------------------------------------------------
            # CLICAR EM BAIXAR
            # -------------------------------------------------

            botao_inicial = page.get_by_text(
                "Baixar",
                exact=True,
            ).first

            botao_inicial.wait_for(
                state="visible",
                timeout=30000,
            )

            botao_inicial.click()

            print(
                "Aguardando opções de resolução..."
            )

            # -------------------------------------------------
            # ESPERAR AS OPÇÕES MP4
            # -------------------------------------------------

            limite = time.monotonic() + 60
            opcoes_prontas = False

            while time.monotonic() < limite:
                try:
                    opcoes = page.get_by_text(
                        re.compile(
                            r"MP4\s*480P",
                            re.IGNORECASE,
                        ),
                        exact=False,
                    )

                    if opcoes.count() > 0:
                        opcoes_prontas = True
                        break

                except Exception:
                    pass

                page.wait_for_timeout(500)

            if not opcoes_prontas:
                raise RuntimeError(
                    "O Vidssave não apresentou as opções MP4."
                )

            # -------------------------------------------------
            # EXECUTAR FLUXO 480P E DEPOIS 360P
            # -------------------------------------------------

            resultado = clicar_opcao_mp4_480p(
                page,
                caminho_arquivo,
            )

            if resultado and validar_video_mp4(resultado):
                print("\n======================================")
                print("DOWNLOAD CONCLUÍDO")
                print(f"Arquivo: {resultado}")
                print("======================================")

                return resultado

            raise RuntimeError(
                "O download não produziu um MP4 válido."
            )

        except Exception as erro:
            print(f"\nErro no download: {erro}")

        finally:
            # Cada tentativa fecha os recursos antes da próxima.
            if contexto is not None:
                try:
                    contexto.close()
                except Exception:
                    pass

            if navegador is not None:
                try:
                    navegador.close()
                except Exception:
                    pass

            if playwright is not None:
                try:
                    playwright.stop()
                except Exception:
                    pass

        if numero_tentativa < MAX_REINICIOS:
            print("Nova tentativa em 3 segundos...")
            time.sleep(3)

    print("Número máximo de tentativas atingido.")
    return None


# =====================================================
# RECEPÇÃO DO LINK
# =====================================================

if __name__ == "__main__":
    link = input(
        "Cole o link do YouTube Shorts: "
    ).strip()

    if link:
        arquivo = baixar_video(link)

        if arquivo:
            print(f"\nVídeo salvo em: {arquivo}")
        else:
            print("\nO download não foi concluído.")
