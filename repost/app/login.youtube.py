
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent

PASTA_CONTAS = (
    BASE_DIR
    / "data"
    / "contas"
    / "youtube"
)

PASTA_CONTAS.mkdir(parents=True, exist_ok=True)


def login_youtube():

    print("\n===== CAM - LOGIN YOUTUBE =====")

    try:
        numero = int(
            input("Qual conta deseja conectar? (1 a 10): ")
        )
    except ValueError:
        print("Digite um número válido.")
        return

    if not 1 <= numero <= 10:
        print("Escolha um número de 1 a 10.")
        return

    pasta_sessao = (
        PASTA_CONTAS / f"conta_{numero:02d}"
    )

    pasta_sessao.mkdir(
        parents=True,
        exist_ok=True
    )

    with sync_playwright() as p:

        navegador = p.chromium.launch_persistent_context(
            user_data_dir=str(pasta_sessao),
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
            "https://accounts.google.com/",
            wait_until="domcontentloaded",
            timeout=60000
        )

        print("\nFaça login na Conta Google.")
        print("Conclua as verificações solicitadas.")
        print("Depois, volte ao terminal.")

        input(
            "\nPressione ENTER para salvar e fechar..."
        )

        navegador.close()

    print(f"\nConta {numero:02d} conectada.")
    print(f"Sessão salva em: {pasta_sessao}")


if __name__ == "__main__":
    login_youtube()