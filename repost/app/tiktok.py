from pathlib import Path
import subprocess
import time

from playwright.sync_api import sync_playwright


# ============================================================
# CAMINHO DO GOOGLE CHROME
# ============================================================

CHROME_EXE = Path(
    r"C:\Program Files\Google\Chrome\Application\chrome.exe"
)


# ============================================================
# PERFIL EXCLUSIVO DO TIKTOK
# ============================================================

PASTA_PROJETO = Path(__file__).resolve().parent

PASTA_SESSAO = (
    PASTA_PROJETO
    / "data"
    / "contas"
    / "tiktok"
    / "conta_cam_nova"
)

PASTA_SESSAO.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# ABRIR TIKTOK
# ============================================================

def abrir_tiktok(numero_conta=1):

    if not 1 <= numero_conta <= 10:
        raise ValueError(
            "O número da conta deve estar entre 1 e 10."
        )

    if not CHROME_EXE.exists():
        raise FileNotFoundError(
            f"Google Chrome não encontrado: {CHROME_EXE}"
        )

    # ========================================================
    # PASTA DA CONTA SELECIONADA
    # ========================================================

    pasta_sessao = (
        PASTA_PROJETO
        / "data"
        / "contas"
        / "tiktok"
        / f"conta_{numero_conta:02d}"
    )

    pasta_sessao.mkdir(
        parents=True,
        exist_ok=True
    )

    print(
        f"Abrindo TikTok - conta {numero_conta:02d}"
    )

    print(f"Pasta da sessão: {pasta_sessao}")

    # ========================================================
    # ABRIR CHROME
    # ========================================================

    subprocess.Popen([
        str(CHROME_EXE),
        f"--user-data-dir={pasta_sessao}",
        "--remote-debugging-port=9222",
        "--no-first-run",
        "--no-default-browser-check",
        "--new-window",
        "--start-maximized",
        "https://www.tiktok.com/"
    ])

    time.sleep(5)

    # ========================================================
    # CONECTAR PLAYWRIGHT
    # ========================================================

    playwright = sync_playwright().start()

    try:
        navegador = playwright.chromium.connect_over_cdp(
            "http://127.0.0.1:9222"
        )

        contexto = navegador.contexts[0]

        if contexto.pages:
            page = contexto.pages[0]
        else:
            page = contexto.new_page()

        return playwright, navegador, page

    except Exception:
        playwright.stop()
        raise
# ============================================================
# FECHAR TIKTOK
# ============================================================

def fechar_tiktok(playwright, navegador):

    try:

        navegador.close()

    except Exception:
        pass


    try:

        playwright.stop()

    except Exception:
        pass