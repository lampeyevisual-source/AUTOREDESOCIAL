
from pathlib import Path
from playwright.sync_api import sync_playwright
import sys


# =====================================================
# CAMINHO PRINCIPAL DO PROJETO
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent

PASTA_CONTAS = (
    BASE_DIR
    / "app"
    / "data"
    / "contas"
    / "instagram"
)


# =====================================================
# ESCOLHER CONTA
# =====================================================

try:
    numero = int(input("Qual conta deseja abrir? (1 a 10): "))
except ValueError:
    print("ERRO: digite um número válido.")
    input("Pressione ENTER para sair...")
    sys.exit(1)

if not 1 <= numero <= 10:
    print("ERRO: escolha um número de 1 a 10.")
    input("Pressione ENTER para sair...")
    sys.exit(1)


# =====================================================
# LOCALIZAR A PASTA DA CONTA
# =====================================================

pasta_sessao = PASTA_CONTAS / f"conta_{numero:02d}"

print()
print("=" * 45)
print(f" ABRINDO INSTAGRAM - CONTA {numero:02d}")
print("=" * 45)
print()
print(f"Pasta da sessão:\n{pasta_sessao}")
print()

if not pasta_sessao.is_dir():
    print("ERRO: a pasta da conta não existe.")
    print(f"Caminho verificado: {pasta_sessao}")
    input("Pressione ENTER para sair...")
    sys.exit(1)


# =====================================================
# ABRIR CHROME
# =====================================================

playwright = None
navegador = None

try:
    playwright = sync_playwright().start()

    navegador = playwright.chromium.launch_persistent_context(
        user_data_dir=str(pasta_sessao.resolve()),
        channel="chrome",
        headless=False,
        no_viewport=True
    )

    # =================================================
    # ABRIR INSTAGRAM
    # =================================================

    page = (
        navegador.pages[0]
        if navegador.pages
        else navegador.new_page()
    )

    page.goto(
        "https://www.instagram.com/",
        wait_until="domcontentloaded",
        timeout=60000
    )

    print()
    print("Instagram aberto com o perfil selecionado.")
    print("Se necessário, faça login manualmente.")
    print("Feche o navegador normalmente para salvar a sessão.")
    print()

    input("Pressione ENTER aqui para encerrar...")

except Exception as erro:
    print()
    print(f"ERRO AO ABRIR A CONTA: {erro}")
    input("Pressione ENTER para sair...")

finally:
    if navegador is not None:
        navegador.close()

    if playwright is not None:
        playwright.stop()
