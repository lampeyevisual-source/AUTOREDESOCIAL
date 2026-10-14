
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
# PASTA PRINCIPAL DO PROJETO
# ============================================================

PASTA_PROJETO = Path(__file__).resolve().parent

PASTA_CONTAS = (
    PASTA_PROJETO
    / "data"
    / "contas"
    / "tiktok"
)

PASTA_CONTAS.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# OBTER PASTA DA CONTA
# ============================================================

def obter_pasta_conta(numero):

    if not 1 <= numero <= 10:
        raise ValueError("Escolha uma conta de 1 a 10.")

    pasta = PASTA_CONTAS / f"conta_{numero:02d}"

    pasta.mkdir(
        parents=True,
        exist_ok=True
    )

    return pasta


# ============================================================
# ABRIR TIKTOK
# ============================================================

def abrir_tiktok(numero):

    if not 1 <= numero <= 10:
        raise ValueError("Conta deve estar entre 1 e 10.")

    if not CHROME_EXE.is_file():
        raise FileNotFoundError(
            f"Google Chrome não encontrado: {CHROME_EXE}"
        )

    pasta_sessao = obter_pasta_conta(numero)

    # Porta exclusiva para cada conta: 9322 até 9331
    porta = 9321 + numero

    print()
    print("=" * 45)
    print(f" ABRINDO TIKTOK - CONTA {numero:02d}")
    print("=" * 45)
    print(f"Perfil: {pasta_sessao}")
    print(f"Porta CDP: {porta}")
    print()

    # ========================================================
    # ABRIR CHROME MAXIMIZADO
    # ========================================================

    processo = subprocess.Popen([
        str(CHROME_EXE),
        f"--user-data-dir={pasta_sessao.resolve()}",
        f"--remote-debugging-port={porta}",
        "--no-first-run",
        "--no-default-browser-check",
        "--new-window",
        "--start-maximized",
        "https://www.tiktok.com/"
    ])

    playwright = None
    navegador = None

    try:
        # ====================================================
        # CONECTAR AO CHROME
        # ====================================================

        playwright = sync_playwright().start()

        endereco_cdp = f"http://127.0.0.1:{porta}"

        # Aguarda o Chrome disponibilizar a porta CDP
        for tentativa in range(20):
            try:
                navegador = playwright.chromium.connect_over_cdp(
                    endereco_cdp,
                    timeout=3000
                )
                break
            except Exception:
                time.sleep(1)

        if navegador is None:
            raise RuntimeError(
                "Não foi possível conectar ao Chrome. "
                "Verifique se o navegador iniciou corretamente."
            )

        # ====================================================
        # OBTER ABA
        # ====================================================

        contexto = navegador.contexts[0]

        if contexto.pages:
            page = contexto.pages[0]
        else:
            page = contexto.new_page()

        # Garantir que a página esteja no TikTok
        if "tiktok.com" not in page.url:
            page.goto(
                "https://www.tiktok.com/",
                wait_until="domcontentloaded",
                timeout=60000
            )

        print(f"TikTok aberto - conta {numero:02d}.")
        print("Faça login manualmente se necessário.")
        print("Não abra o mesmo perfil em outro Chrome.")
        print()

        return playwright, navegador, page

    except Exception:
        if navegador is not None:
            try:
                navegador.close()
            except Exception:
                pass

        if playwright is not None:
            playwright.stop()

        raise


# ============================================================
# FECHAR CONEXÃO DO PLAYWRIGHT
# ============================================================

def fechar_tiktok(playwright, navegador):

    try:
        if navegador is not None:
            navegador.close()
    finally:
        if playwright is not None:
            playwright.stop()


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    try:
        numero = int(
            input("Qual conta deseja abrir? (1 a 10): ")
        )

        playwright, navegador, page = abrir_tiktok(numero)

        input(
            "\nQuando terminar, pressione ENTER "
            "para encerrar a conexão do Playwright..."
        )

        fechar_tiktok(playwright, navegador)

    except ValueError as erro:
        print(f"Entrada inválida: {erro}")

    except Exception as erro:
        print(f"ERRO: {erro}")

    input("\nPressione ENTER para sair...")
