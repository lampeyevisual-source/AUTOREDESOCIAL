import ctypes
import os
import time

from datetime import datetime, timedelta

from repost.app.instagram import (
    abrir_instagram,
    fechar_instagram
)

from ctypes import wintypes


user32 = ctypes.windll.user32
WM_SETTEXT = 0x000C
BM_CLICK = 0x00F5


# =====================================================
# CONFIGURAÇÕES
# =====================================================

INTERVALO_ESPERA = 5

TEMPO_CARREGAMENTO = 5000

TEMPO_APOS_PROGRAMAR = 10000


# =====================================================
# HORÁRIOS DE PUBLICAÇÃO
#
# Publicações a cada 30 minutos:
# 09:27
# 09:57
# 10:27
# 10:57
# =====================================================

def proximo_horario_publicacao():

    agora = datetime.now()

    candidatos = []

    for deslocamento in range(0, 5):

        hora_base = (
            agora.replace(
                minute=0,
                second=0,
                microsecond=0
            )
            + timedelta(hours=deslocamento)
        )

        candidatos.append(
            hora_base.replace(minute=27)
        )

        candidatos.append(
            hora_base.replace(minute=57)
        )

    for horario in candidatos:

        if horario > agora:
            return horario

    return candidatos[-1]


# =====================================================
# AGUARDAR HORÁRIO
# =====================================================

def aguardar_ate(horario):

    while True:

        agora = datetime.now()

        restante = (
            horario - agora
        ).total_seconds()

        if restante <= 0:
            break

        print(
            f"\rAguardando publicação: "
            f"{int(restante)} segundos restantes",
            end="",
            flush=True
        )

        time.sleep(
            min(
                restante,
                INTERVALO_ESPERA
            )
        )

    print("\nHorário atingido.")


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
def fechar_popup_notificacoes(page):
    try:
        popup = page.locator('h2').filter(
            has_text="Ativar notificações"
        ).first

        if popup.is_visible(timeout=2000):
            print("Popup 'Ativar notificações' encontrado.")

            agora_nao = page.get_by_role(
                "button",
                name="Agora não",
                exact=True
            ).first

            agora_nao.click(force=True)

            print("Popup de notificações fechado.")

            page.wait_for_timeout(500)

    except:
        # Popup não apareceu → continua normalmente
        pass

def fechar_aviso_reels(page):
    try:
        botao_ok = page.get_by_role(
            "button",
            name="OK",
            exact=True
        ).first

        if botao_ok.is_visible(timeout=2000):
            print("Aviso 'Agora os posts de vídeo são compartilhados como reels' encontrado.")
            botao_ok.click(force=True)
            print("Aviso de Reels fechado.")
            page.wait_for_timeout(500)

    except Exception:
        pass

def clicar_criar(page):
    print("Procurando botão 'Novo post'...")

    novo_post = page.locator(
        'a:has(svg[aria-label="Novo post"]), '
        'button:has(svg[aria-label="Novo post"])'
    ).first

    novo_post.wait_for(state="visible", timeout=10000)

    print("Botão 'Novo post' encontrado.")

    novo_post.click()

    print("Clique em 'Novo post' realizado.")

    page.wait_for_timeout(1000)

    print("Procurando opção 'Postar'...")

    # O Instagram coloca "Postar" dentro de um <a role="link">
    botao_postar = page.locator(
        'a[role="link"]'
    ).filter(
        has_text="Postar"
    ).first

    botao_postar.wait_for(
        state="visible",
        timeout=10000
    )

    print("Opção 'Postar' encontrada.")

    botao_postar.click()

    print("Clique em 'Postar' realizado.")

    page.wait_for_timeout(1000)

    return True

# =====================================================
# SELECIONAR VÍDEO
# =====================================================
# =====================================================
# SELECIONAR VÍDEO
# =====================================================

def selecionar_video(page, caminho_video):

    caminho_video = os.path.abspath(
        caminho_video
    )

    if not os.path.isfile(caminho_video):

        raise FileNotFoundError(
            f"Vídeo não encontrado: {caminho_video}"
        )

    # ---------------------------------------------
    # GUARDA AS PÁGINAS EXISTENTES
    # ---------------------------------------------

    paginas_antes = list(
        page.context.pages
    )

    page.wait_for_timeout(
        10000
    )

    # ---------------------------------------------
    # BOTÃO SELECIONAR DO COMPUTADOR
    # ---------------------------------------------

    botao_selecionar = page.get_by_role(
        "button",
        name="Selecionar do computador"
    )

    botao_selecionar.wait_for(
        state="visible",
        timeout=30000
    )

    print(
        "Botão 'Selecionar do computador' encontrado."
    )

    # ---------------------------------------------
    # CLICAR NO BOTÃO
    # ---------------------------------------------

    botao_selecionar.click()

    print(
        "Botão 'Selecionar do computador' clicado."
    )

    # ---------------------------------------------
    # PREENCHE A JANELA NATIVA "ABRIR"
    # ---------------------------------------------

    print(
        "Preenchendo janela 'Abrir'..."
    )

    resultado = preencher_abrir_em_segundo_plano(
        caminho_video
    )

    if not resultado:

        raise RuntimeError(
            "Não foi possível selecionar o vídeo "
            "na janela 'Abrir' do Windows."
        )

    print(
        "Vídeo selecionado pela janela 'Abrir'."
    )

    # ---------------------------------------------
    # GARANTIR QUE O INSTAGRAM CONTINUA
    # ---------------------------------------------

    try:

        page.bring_to_front()

    except Exception:

        pass

    page.wait_for_timeout(
        10000
    )

    # ---------------------------------------------
    # AGUARDAR UPLOAD
    # ---------------------------------------------

    print(
        "Aguardando upload e processamento..."
    )

    page.wait_for_timeout(
        10000
    )

    page.wait_for_timeout(
        10000
    )

    print(
        "Upload e processamento aguardados."
    )
    
# =====================================================
# SELECIONAR FORMATO 9:16
# =====================================================

def selecionar_formato_vertical(page):

    print("Procurando botão 'Selecionar corte'...")

    # ---------------------------------------------
    # BOTÃO SELECIONAR CORTE
    # ---------------------------------------------

    botao_corte = page.locator(
        'svg[aria-label="Selecionar corte"]'
    ).first

    botao_corte.wait_for(
        state="visible",
        timeout=30000
    )

    print(
        "Botão 'Selecionar corte' encontrado."
    )

    # ---------------------------------------------
    # ABRIR MENU DE FORMATOS
    # ---------------------------------------------

    botao_corte.click()

    print(
        "Menu de formatos aberto."
    )

    # ---------------------------------------------
    # AGUARDAR MENU FICAR VISÍVEL
    # ---------------------------------------------

    menu = page.locator(
        'div[aria-hidden="false"]'
    ).filter(
        has_text="9:16"
    ).last

    menu.wait_for(
        state="visible",
        timeout=10000
    )

    print(
        "Menu de formatos confirmado."
    )

    # ---------------------------------------------
    # LOCALIZAR O ITEM 9:16
    # ---------------------------------------------

    formato = menu.get_by_text(
        "9:16",
        exact=True
    )

    formato.wait_for(
        state="visible",
        timeout=10000
    )

    print(
        "Opção 9:16 encontrada."
    )

    # ---------------------------------------------
    # CLICAR EM 9:16
    # ---------------------------------------------

    formato.click()

    print(
        "Formato 9:16 selecionado."
    )

    page.wait_for_timeout(
        2000
    )

# =====================================================
# BOTÃO AVANÇAR
# =====================================================

def clicar_avancar(page):

    botao_avancar = page.get_by_role(
        "button",
        name="Avançar",
        exact=True
    )

    botao_avancar.wait_for(
        state="visible",
        timeout=30000
    )

    botao_avancar.click()

    print("Avançar clicado.")

    page.wait_for_timeout(3000)


# =====================================================
# PREENCHER LEGENDA
# =====================================================

def preencher_legenda(
    page,
    legenda
):

    campo_legenda = page.locator(
        '[contenteditable="true"]'
        '[aria-label="Adicione uma legenda..."]'
    )

    campo_legenda.wait_for(
        state="visible",
        timeout=30000
    )

    campo_legenda.fill(
        legenda
    )

    print("Legenda preenchida.")

    campo_legenda.press("Tab")

    page.wait_for_timeout(500)

# =====================================================
# PROGRAMAR PUBLICAÇÃO + RÓTULO DE IA
# =====================================================
def clicar_programar(page, horario):

    print("\nVerificando opções da publicação...")

    # =================================================
    # 1. ADICIONAR RÓTULO DE IA, SE DISPONÍVEL
    # =================================================

    try:
        rotulo_ia = page.get_by_text(
            "Adicionar rótulo de IA",
            exact=True
        ).last

        rotulo_ia.wait_for(
            state="visible",
            timeout=3000
        )

        container_ia = rotulo_ia.locator(
            "xpath=../../.."
        )

        switch_ia = container_ia.locator(
            'input[role="switch"][type="checkbox"]'
        )

        if switch_ia.count() == 1:

            switch_ia = switch_ia.first

            estado_ia = switch_ia.get_attribute(
                "aria-checked"
            )

            print(
                f"Estado inicial do rótulo de IA: {estado_ia}"
            )

            if estado_ia != "true":
                switch_ia.check(force=True)
                page.wait_for_timeout(500)

            estado_ia = switch_ia.get_attribute(
                "aria-checked"
            )

            if estado_ia == "true":
                print("Rótulo de IA ativado.")
            else:
                print(
                    "Não foi possível confirmar "
                    "a ativação do rótulo de IA."
                )

        else:
            print(
                "Switch de IA não identificado. "
                "Continuando sem alterar esse controle."
            )

    except Exception:
        print(
            "Opção de rótulo de IA indisponível. "
            "Continuando..."
        )

    # =================================================
    # 2. VERIFICAR SE A CONTA POSSUI PROGRAMAÇÃO
    # =================================================

    print("\nVerificando programação...")

    rotulo_programar = page.get_by_text(
        "Programar conteúdo",
        exact=True
    ).last

    try:
        rotulo_programar.wait_for(
            state="visible",
            timeout=5000
        )

        possui_programacao = True

    except Exception:
        possui_programacao = False

    # =================================================
    # 3. CONTA SEM OPÇÃO DE PROGRAMAÇÃO
    #    TENTAR PUBLICAR COM COMPARTILHAR
    # =================================================

    if not possui_programacao:

        print(
            "Esta conta não apresenta a opção "
            "'Programar conteúdo'."
        )

        print(
            "Procurando o botão Compartilhar..."
        )

        botao_compartilhar = page.get_by_role(
            "button",
            name="Compartilhar",
            exact=True
        ).last

        try:
            botao_compartilhar.wait_for(
                state="visible",
                timeout=10000
            )

            if not botao_compartilhar.is_enabled():
                print(
                    "O botão Compartilhar está desabilitado."
                )
                return False

            botao_compartilhar.click()

            print(
                "Botão Compartilhar clicado. "
                "Publicação imediata solicitada."
            )

            page.wait_for_timeout(
                TEMPO_APOS_PROGRAMAR
            )

            return True

        except Exception as erro:
            print(
                "Não foi possível clicar em Compartilhar: "
                f"{erro}"
            )
            return False

    # =================================================
    # 4. LOCALIZAR O SWITCH DE PROGRAMAÇÃO
    # =================================================

    container_programar = rotulo_programar.locator(
        "xpath=../../.."
    )

    switch_programar = container_programar.locator(
        'input[role="switch"][type="checkbox"]'
    )

    if switch_programar.count() != 1:
        print(
            "Não foi possível identificar o switch "
            "de programação."
        )
        return False

    switch_programar = switch_programar.first

    estado = switch_programar.get_attribute(
        "aria-checked"
    )

    print(
        f"Estado inicial da programação: {estado}"
    )

    if estado != "true":

        try:
            switch_programar.check(force=True)
            page.wait_for_timeout(800)

        except Exception as erro:
            print(
                f"Erro ao ativar a programação: {erro}"
            )
            return False

    estado = switch_programar.get_attribute(
        "aria-checked"
    )

    if estado != "true":
        print(
            "O Instagram não confirmou a ativação "
            "da programação."
        )
        return False

    print("Programação ativada.")

    # =================================================
    # 5. VERIFICAR OS CAMPOS DE HORÁRIO
    # =================================================

    campo_hora = page.locator(
        'input[aria-label="Hours"]'
    ).last

    campo_minuto = page.locator(
        'input[aria-label="Minutes"]'
    ).last

    if (
        campo_hora.count() == 0
        or campo_minuto.count() == 0
    ):
        print(
            "Campos de hora ou minuto não encontrados."
        )
        return False

    try:
        campo_hora.wait_for(
            state="visible",
            timeout=5000
        )

        campo_minuto.wait_for(
            state="visible",
            timeout=5000
        )

    except Exception:
        print("Campos de horário indisponíveis.")
        return False

    # =================================================
    # 6. PREENCHER HORÁRIO
    # =================================================

    hora = horario.strftime("%H")
    minuto = horario.strftime("%M")

    try:
        campo_hora.fill(hora)
        campo_minuto.fill(minuto)

        page.wait_for_timeout(1000)

        print(
            f"Horário preenchido: {hora}:{minuto}"
        )

    except Exception as erro:
        print(
            f"Erro ao preencher o horário: {erro}"
        )
        return False

    # =================================================
    # 7. CLICAR NO BOTÃO FINAL DE PROGRAMAR
    # =================================================

    botao_programar_final = page.get_by_role(
        "button",
        name="Programar",
        exact=True
    ).last

    try:
        botao_programar_final.wait_for(
            state="visible",
            timeout=10000
        )

        if not botao_programar_final.is_enabled():
            print(
                "Botão final de programação desabilitado."
            )
            return False

        botao_programar_final.click()

        print(
            "Botão final de programação clicado."
        )

        page.wait_for_timeout(
            TEMPO_APOS_PROGRAMAR
        )

        print(
            "Solicitação de programação enviada para "
            f"{horario.strftime('%d/%m/%Y %H:%M')}."
        )

        return True

    except Exception as erro:
        print(
            f"Erro ao finalizar a programação: {erro}"
        )
        return False

# =====================================================
# AGUARDAR CONFIRMAÇÃO DA PUBLICAÇÃO NO INSTAGRAM
# E CLICAR NO BOTÃO CONCLUIR
# =====================================================

def aguardar_confirmacao_compartilhamento(page):

    print("\nAguardando confirmação da publicação...")

    try:
        # =============================================
        # 1. AGUARDAR A JANELA DE CONFIRMAÇÃO
        # =============================================

        janela = page.locator(
            'div[role="dialog"][aria-label="Post compartilhado"]'
        )

        janela.wait_for(
            state="visible",
            timeout=30000
        )

        print("Janela 'Post compartilhado' detectada.")

        # =============================================
        # 2. CONFIRMAR A MENSAGEM DE SUCESSO
        # =============================================

        mensagem = janela.get_by_text(
            "Seu post foi compartilhado.",
            exact=True
        )

        mensagem.wait_for(
            state="visible",
            timeout=10000
        )

        print(
            "Instagram confirmou que o post "
            "foi compartilhado."
        )
        # =============================================
        # 3. LOCALIZAR O BOTÃO CONCLUIR
        # =============================================

        botao_concluir = janela.get_by_role(
            "button",
            name="Concluir",
            exact=True
        )

        botao_concluir.wait_for(
            state="visible",
            timeout=15000
        )

        print("Botão Concluir encontrado.")

        # =============================================
        # 4. CLICAR NO BOTÃO CONCLUIR
        # =============================================

        botao_concluir.click(
            timeout=15000,
            force=True
        )

        print("Botão Concluir clicado.")

        # =============================================
        # 5. AGUARDAR A JANELA FECHAR
        # =============================================

        janela.wait_for(
            state="hidden",
            timeout=15000
        )

        print(
            "Janela de confirmação fechada "
            "com sucesso."
        )

        return True

    except Exception as erro:

        print(
            "Erro ao confirmar ou finalizar "
            "a publicação no Instagram: "
            f"{erro}"
        )

        return False
# =====================================================
# PUBLICAR NO INSTAGRAM
# =====================================================

def postar_instagram(
    numero_conta,
    caminho_video,
    legenda=""
):

    playwright = None
    navegador = None
    page= None

    try:

        # ---------------------------------------------
        # 1. VERIFICAR ARQUIVO
        # ---------------------------------------------

        caminho_video = os.path.abspath(
            caminho_video
        )

        if not os.path.isfile(caminho_video):

            print(
                f"Vídeo não encontrado: {caminho_video}"
            )

            return False

        # ---------------------------------------------
        # 2. DEFINIR HORÁRIO
        # ---------------------------------------------

        horario = proximo_horario_publicacao()

        print(
            f"\nConta Instagram: {numero_conta}"
        )

        print(
            f"Vídeo: {caminho_video}"
        )

        print(
            f"Horário previsto: "
            f"{horario.strftime('%d/%m/%Y %H:%M:%S')}"
        )

        # 2. DEFINIR HORÁRIO

        horario = proximo_horario_publicacao()

        print(
            f"\nHorário previsto: "
            f"{horario.strftime('%d/%m/%Y %H:%M:%S')}"
        )
      
        # ---------------------------------------------
        # 3. ABRIR CONTA
        # ---------------------------------------------

        numero_conta = 2

        playwright, navegador, page = abrir_instagram(numero_conta)

        print(f"Instagram aberto com a conta {numero_conta:02d}.")

        page.wait_for_timeout(TEMPO_CARREGAMENTO)

        # ---------------------------------------------
        # FECHAR POPUP DE NOTIFICAÇÕES
        # ---------------------------------------------

        fechar_popup_notificacoes(page)
        
        # ---------------------------------------------
        # 4. CRIAR PUBLICAÇÃO
        # ---------------------------------------------

        clicar_criar(page)

        # ---------------------------------------------
        # 5. SELECIONAR VÍDEO
        # ---------------------------------------------

        selecionar_video(
            page,
            caminho_video
        )


        fechar_aviso_reels(page)
        # ---------------------------------------------
        # 6. FORMATO 9:16
        # ---------------------------------------------

        selecionar_formato_vertical(page)

        # ---------------------------------------------
        # 7. AVANÇAR PARA EDIÇÃO
        # ---------------------------------------------

        clicar_avancar(page)

        # ---------------------------------------------
        # 8. AVANÇAR PARA LEGENDA
        # ---------------------------------------------

        clicar_avancar(page)

        # ---------------------------------------------
        # 9. PREENCHER LEGENDA
        # ---------------------------------------------

        preencher_legenda(
            page,
            legenda
        )
        # ---------------------------------------------
        # 10. CONFERIR SE O HORÁRIO NÃO PASSOU
        # ---------------------------------------------

        agora = datetime.now()

        if agora >= horario:

            horario = proximo_horario_publicacao()

            print(
                f"\nO horário anterior passou."
                f"\nNovo horário: "
                f"{horario.strftime('%d/%m/%Y %H:%M:%S')}"
            )

        # ---------------------------------------------
        # 11. HORÁRIO DEFINIDO PARA A PUBLICAÇÃO
        # ---------------------------------------------

        print(
            f"\nHorário que será programado: "
            f"{horario.strftime('%d/%m/%Y %H:%M:%S')}"
        )

        # ---------------------------------------------
        # 12. CLICAR EM PROGRAMAR
        # ---------------------------------------------

        clicar_programar(
            page, horario
        )

        print(
            "\nProcesso concluído."
        )

        # ---------------------------------------------
        # 12.1 AGUARDAR CONFIRMAÇÃO DO COMPARTILHAMENTO
        # ---------------------------------------------

        confirmacao_ok = aguardar_confirmacao_compartilhamento(
            page
        )

        if not confirmacao_ok:
            print(
                "\nNão foi possível confirmar "
                "o compartilhamento."
            )
            return False

        print("\nProcesso concluído.")

        page.wait_for_timeout(30000)

        return True

    finally:

        # ---------------------------------------------
        # 13. FECHAR NAVEGADOR
        # ---------------------------------------------

        if playwright and navegador:

            fechar_instagram(
                playwright,
                navegador
            )


# =====================================================
# TESTE DIRETO DO ARQUIVO
# =====================================================

if __name__ == "__main__":

    VIDEO = r"data/videos/baixados/video.mp4"

    LEGENDA = (
        "Confira este conteúdo!\n"
        "#videos #reels #brasil"
    )

    postar_instagram(
        numero_conta=1,
        caminho_video=VIDEO,
        legenda=LEGENDA
    )