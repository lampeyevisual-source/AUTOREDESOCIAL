
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent

PASTA_CONTAS = (
    BASE_DIR
    / "data"
    / "contas"
    / "youtube"
)


def abrir_youtube(numero):

    if not 1 <= numero <= 10:
        raise ValueError("Escolha de 1 a 10.")

    pasta = PASTA_CONTAS / f"conta_{numero:02d}"

    if not pasta.exists():
        raise FileNotFoundError(
            f"Conta {numero:02d} não conectada."
        )

    playwright = sync_playwright().start()

    navegador = p.chromium.launch_persistent_context(
        user_data_dir=str(pasta),
        channel="chrome",
        headless=False,
        no_viewport=True
    )

    page = (
        navegador.pages[0]
        if navegador.pages
        else navegador.new_page()
    )

    page.goto(
        "https://www.youtube.com/",
        wait_until="domcontentloaded"
    )

    return playwright, navegador, page


def fechar_youtube(playwright, navegador):

    navegador.close()
    playwright.stop()