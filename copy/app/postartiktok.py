 
import os
import time

from tiktok import abrir_tiktok, fechar_tiktok


# =====================================================
# CONFIGURAÇÕES
# =====================================================

URL_TIKTOK_STUDIO = (
    "https://www.tiktok.com/tiktokstudio/upload"
    "?from=creator_center&tab=video"
)

import ctypes
import time
from ctypes import wintypes


user32 = ctypes.windll.user32

WM_SETTEXT = 0x000C
BM_CLICK = 0x00F5

# =====================================================
# MAXIMIZAR JANELA DO WINDOWS
# =====================================================

SW_MAXIMIZE = 3

user32.ShowWindow.argtypes = [
    wintypes.HWND,
    ctypes.c_int,
]

user32.ShowWindow.restype = wintypes.BOOL


def maximizar_janela(hwnd):

    if hwnd:
        user32.ShowWindow(
            hwnd,
            SW_MAXIMIZE,
        )

def encontrar_janela_abrir():
    resultado = []

    @ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM
    )
    def callback(hwnd, lparam):

        if not user32.IsWindowVisible(hwnd):
            return True

        tamanho = user32.GetWindowTextLengthW(hwnd)

        if tamanho == 0:
            return True

        texto = ctypes.create_unicode_buffer(tamanho + 1)

        user32.GetWindowTextW(
            hwnd,
            texto,
            tamanho + 1
        )

        titulo = texto.value.lower()

        if titulo in ("abrir", "open"):

            resultado.append(hwnd)
            return False

        return True

    user32.EnumWindows(
        callback,
        0
    )

    if resultado:
        return resultado[0]

    return None


def encontrar_controles(hwnd_pai):

    controles = []

    @ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM
    )
    def callback(hwnd, lparam):

        classe_buffer = ctypes.create_unicode_buffer(256)
        titulo_buffer = ctypes.create_unicode_buffer(256)

        user32.GetClassNameW(
            hwnd,
            classe_buffer,
            256
        )

        user32.GetWindowTextW(
            hwnd,
            titulo_buffer,
            256
        )

        controles.append({
            "hwnd": hwnd,
            "classe": classe_buffer.value,
            "titulo": titulo_buffer.value
        })

        return True

    user32.EnumChildWindows(
        hwnd_pai,
        callback,
        0
    )

    return controles


def preencher_abrir_em_segundo_plano(caminho_video):

    print("Procurando janela 'Abrir'...")

    janela = None

    for _ in range(50):

        janela = encontrar_janela_abrir()

        if janela:
            break

        time.sleep(0.1)

    if not janela:

        print("Janela 'Abrir' não encontrada.")
        return False

    print("Janela 'Abrir' encontrada.")

    controles = encontrar_controles(janela)

    campo_nome = None
    botao_abrir = None

    print("Controles encontrados:")

    for controle in controles:

        print(
            f"  HWND={controle['hwnd']} | "
            f"CLASSE={controle['classe']} | "
            f"TITULO={controle['titulo']}"
        )

        titulo = controle["titulo"].strip().lower()
        classe = controle["classe"].lower()

        # Campo de nome
        if classe == "edit" and campo_nome is None:
            campo_nome = controle["hwnd"]

        # Botão Abrir
        if (
            classe == "button"
            and titulo in (
                "abrir",
                "open",
                "&abrir",
                "&open"
            )
        ):
            botao_abrir = controle["hwnd"]

    if not campo_nome:

        print("Campo Nome não encontrado.")
        return False

    # =====================================================
    # COLOCA O CAMINHO NO CAMPO NOME
    # =====================================================

    print("Preenchendo caminho do vídeo...")

    caminho_video = str(caminho_video)

    user32.SendMessageW(
        campo_nome,
        WM_SETTEXT,
        0,
        caminho_video
    )

    time.sleep(0.5)

    # =====================================================
    # SE ENCONTROU O BOTÃO
    # =====================================================

    if botao_abrir:

        print("Botão Abrir encontrado.")

        user32.SendMessageW(
            botao_abrir,
            BM_CLICK,
            0,
            0
        )

        time.sleep(1)

        print("Janela 'Abrir' fechada.")

        return True

    # =====================================================
    # BOTÃO NÃO ENCONTRADO
    # TENTA O COMANDO PADRÃO DA CAIXA DE DIÁLOGO
    # =====================================================

    print(
        "Botão Abrir não identificado."
    )

    print(
        "Tentando confirmar o arquivo pela janela..."
    )

    # ID padrão do botão OK/Abrir em diálogos Windows
    IDOK = 1

    resultado = user32.SendMessageW(
        janela,
        0x0111,  # WM_COMMAND
        IDOK,
        0
    )

    time.sleep(1)

    # Verifica se a janela ainda existe
    if not user32.IsWindow(janela):

        print(
            "Janela 'Abrir' fechada pelo comando padrão."
        )

        return True

    print(
        "Não foi possível fechar a janela 'Abrir'."
    )

    return False
# =====================================================
# 1. ABRIR TIKTOK STUDIO
# =====================================================

def abrir_pagina_upload(page):

    page.goto(
        URL_TIKTOK_STUDIO,
        wait_until="domcontentloaded"
    )

    page.wait_for_timeout(5000)

    print("TikTok Studio aberto.")
    page.wait_for_timeout(20000)



# =====================================================
# 2. SELECIONAR VÍDEO
# =====================================================

def selecionar_video(page, caminho_video):

    caminho_video = os.path.abspath(
        caminho_video
    )

    if not os.path.isfile(caminho_video):
        raise FileNotFoundError(
            f"Vídeo não encontrado: {caminho_video}"
        )

    # Guarda as páginas existentes antes de selecionar
    paginas_antes = list(
        page.context.pages
    )
    page.wait_for_timeout(10000)

    # ---------------------------------------------
    # BOTÃO SELECIONAR VÍDEO
    # ---------------------------------------------

    botao_selecionar = page.locator(
        'button[data-e2e="select_video_button"]'
    )

    botao_selecionar.wait_for(
        state="visible",
        timeout=30000
    )

    botao_selecionar.click()
    page.wait_for_timeout(10000)

    # Preenche e confirma a janela "Abrir"
    preencher_abrir_em_segundo_plano(
        caminho_video
    )

    # ---------------------------------------------
    # GARANTIR QUE A PÁGINA DO TIKTOK CONTINUA
    # ---------------------------------------------

    try:

        page.bring_to_front()

    except Exception:
        pass
    page.wait_for_timeout(10000)

    # ---------------------------------------------
    # AGUARDAR UPLOAD
    # ---------------------------------------------

    botoes_ads = page.locator(
        'button:has-text("Entendi")'
    )

    quantidade_ads = botoes_ads.count()

    if quantidade_ads > 0:

        print(
            f"Botões 'Entendi' encontrados: {quantidade_ads}"
        )

        # Tenta clicar no segundo, se existir
        if quantidade_ads > 1:

            try:

                botoes_ads.nth(1).click(
                    timeout=1000
                )

                print(
                    "Botão 'Entendi' fechado."
                )

            except Exception:

                print(
                    "Segundo 'Entendi' não pôde ser clicado. Continuando..."
                )

        else:

            # Se existir apenas um
            try:

                botoes_ads.nth(0).click(
                    timeout=1000
                )

                print(
                    "Botão 'Entendi' fechado."
                )

            except Exception:

                print(
                    "Botão 'Entendi' não pôde ser clicado. Continuando..."
                )

    else:

        print(
            "Nenhum botão 'Entendi' encontrado. Continuando..."
        )


    print(
        "Aguardando upload e processamento..."
    )

    page.wait_for_timeout(
        10000
    )

    page.wait_for_timeout(
        10000
    )
# =====================================================
# 3. PREENCHER DESCRIÇÃO
# =====================================================

def preencher_descricao(page, descricao):

    # Campo DraftEditor enviado pelo usuário
    campo_descricao = page.locator(
        '[data-e2e="caption_container"] '
        '[contenteditable="true"][role="combobox"]'
    )

    campo_descricao.wait_for(
        state="visible",
        timeout=30000
    )

    campo_descricao.click()

    # Substitui o texto que já estiver no campo
    campo_descricao.fill(
        descricao
    )

    print("Descrição preenchida.")
    page.wait_for_timeout(20000)

# =====================================================
# 4. ABRIR PAINEL DE SONS
# =====================================================

def abrir_painel_sons(page):

    # Botão Sons enviado pelo usuário
    botao_sons = page.locator(
        'button[data-button-name="sounds"]'
    )

    botao_sons.wait_for(
        state="visible",
        timeout=30000
    )

    botao_sons.click()

    print("Painel de sons aberto.")

    page.wait_for_timeout(3000)


# =====================================================
# 5. SELECIONAR O PRIMEIRO SOM
# =====================================================

def selecionar_primeiro_som(page):

    # Localiza os itens de música
    itens_som = page.locator(
        'div[class*="MusicPanelMusicItem__container"]'
    )

    itens_som.first.wait_for(
        state="visible",
        timeout=30000
    )

    quantidade = itens_som.count()

    if quantidade == 0:
        raise Exception(
            "Nenhum som encontrado no painel."
        )

    # Sempre seleciona o primeiro item da lista
    primeiro_som = itens_som.first

    # Botão de adicionar som dentro do primeiro item
    botao_adicionar = primeiro_som.locator(
        'button:has([data-testid="PlusBold"])'
    )

    botao_adicionar.wait_for(
        state="visible",
        timeout=20000
    )

    botao_adicionar.click()

    print("Primeiro som adicionado.")

    page.wait_for_timeout(3000)

def deixar_audio_mudo(page):

    botoes_volume = page.locator(
        'button:has([data-testid="VolumeUp"])'
    )

    botoes_volume.nth(1).wait_for(
        state="visible",
        timeout=30000
    )

    botoes_volume.nth(1).click()

    print("Áudio original colocado no mudo.")

    page.wait_for_timeout(2000)

# =====================================================
# 7. CLICAR EM SALVAR
# =====================================================

def clicar_salvar(page):

    # ---------------------------------------------
    # SALVAR
    # ---------------------------------------------

    botao_salvar = page.get_by_role(
        "button",
        name="Salvar",
        exact=True
    )

    botao_salvar.wait_for(
        state="visible",
        timeout=30000
    )

    botao_salvar.click()

    print("Botão 'Salvar' clicado.")

    page.wait_for_timeout(5000)

  
# =====================================================
# 8. FUNÇÃO PRINCIPAL DE POSTAGEM
# =====================================================

def postar_tiktok(
    caminho_video,
    descricao="",
    numero_conta=1
):

    playwright = None
    navegador = None

    try:

        # ---------------------------------------------
        # VERIFICAR VÍDEO
        # ---------------------------------------------

        caminho_video = os.path.abspath(
            caminho_video
        )

        if not os.path.isfile(caminho_video):

            print(
                f"Vídeo não encontrado: {caminho_video}"
            )

            return False

        print("\nIniciando postagem no TikTok...")

        # ---------------------------------------------
        # ABRIR TIKTOK
        # ---------------------------------------------

        playwright, navegador, page = abrir_tiktok(numero_conta)

        print(
            f"TikTok aberto com a conta "
            f"{numero_conta:02d}."
        )
        # ---------------------------------------------
        # ABRIR STUDIO
        # ---------------------------------------------

        abrir_pagina_upload(page)

        # ---------------------------------------------
        # SELECIONAR VÍDEO
        # ---------------------------------------------

        selecionar_video(
            page,
            caminho_video
        )

        # ---------------------------------------------
        # PREENCHER DESCRIÇÃO
        # ---------------------------------------------

        preencher_descricao(
            page,
            descricao
        )

        # ---------------------------------------------
        # ABRIR SONS
        # ---------------------------------------------

        abrir_painel_sons(page)

        # ---------------------------------------------
        # ADICIONAR PRIMEIRO SOM
        # ---------------------------------------------

        selecionar_primeiro_som(page)

        # ---------------------------------------------
        # DEIXAR MUDO
        # ---------------------------------------------

        deixar_audio_mudo(page)

        # ---------------------------------------------
        # SALVAR
        # ---------------------------------------------

        # SALVAR CONFIGURAÇÕES DO SOM
        clicar_salvar(page)

        # PUBLICAR VÍDEO
        clicar_publicar(page)

        print(
            "\nPublicação enviada ao TikTok."
        )

        return True
    
    except Exception as erro:

        print(
            f"\nErro ao postar no TikTok: {erro}"
        )

        return False

    finally:

        if playwright and navegador:

            fechar_tiktok(
                playwright,
                navegador
            )

# =====================================================
# 8. CLICAR NO BOTÃO PUBLICAR
# =====================================================

def clicar_publicar(page):

    botao_publicar = page.locator(
        'button[data-e2e="post_video_button"]'
    )

    botao_publicar.wait_for(
        state="visible",
        timeout=30000
    )

    # Aguarda o botão estar habilitado
    botao_publicar.wait_for(
        state="attached",
        timeout=30000
    )

    if botao_publicar.get_attribute("aria-disabled") == "true":
        raise Exception(
            "O botão Publicar está desabilitado."
        )

    botao_publicar.click()

    print("Botão Publicar clicado.")

    # Aguarda o TikTok processar a publicação
    page.wait_for_timeout(10000)

    # ---------------------------------------------
    # PUBLICAR AGORA — OPCIONAL
    # ---------------------------------------------

    botao_publicar2 = page.get_by_role(
        "button",
        name="Publicar agora",
        exact=True
    )

    try:

        botao_publicar2.wait_for(
            state="visible",
            timeout=10000
        )

        botao_publicar2.click()

        print("Botão 'Publicar agora' clicado.")

        page.wait_for_timeout(5000)

    except Exception:

        print(
            "Botão 'Publicar agora' não apareceu. "
            "Continuando normalmente..."
        )

# =====================================================
# TESTE DIRETO
# =====================================================

if __name__ == "__main__":

    VIDEO = (
        "data/videos/baixados/video.mp4"
    )

    DESCRICAO = (
        "Confira este conteúdo!\n"
        "#brasil #videos #tiktok"
    )

    postar_tiktok(
        caminho_video=VIDEO,
        descricao=DESCRICAO
    )