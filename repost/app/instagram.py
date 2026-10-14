
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent

PASTA_CONTAS = (
    BASE_DIR
    / "data"
    / "contas"
    / "instagram"
)

# ============================================================
# ABRIR INSTAGRAM MAXIMIZADO
# ============================================================

def abrir_instagram(numero):

    if not 1 <= numero <= 10:
        raise ValueError("Conta deve estar entre 1 e 10.")

    pasta_sessao = (
        PASTA_CONTAS / f"conta_{numero:02d}"
    )

    if not pasta_sessao.exists():
        raise FileNotFoundError(
            f"Conta {numero:02d} ainda não foi conectada."
        )

    playwright = sync_playwright().start()

    navegador = playwright.chromium.launch_persistent_context(
        user_data_dir=str(pasta_sessao),
        channel="chrome",
        headless=False,
        no_viewport=True,
        args=["--start-maximized"],
    )

    if navegador.pages:
        page = navegador.pages[0]
    else:
        page = navegador.new_page()

    page.goto(
        "https://www.instagram.com/",
        wait_until="domcontentloaded",
        timeout=60000,
    )

    return playwright, navegador, page


# ============================================================
# FECHAR INSTAGRAM
# ============================================================

def fechar_instagram(playwright, navegador):

    try:
        navegador.close()
    finally:
        playwright.stop()