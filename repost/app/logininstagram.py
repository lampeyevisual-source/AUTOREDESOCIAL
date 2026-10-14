
from pathlib import Path
from playwright.sync_api import sync_playwright
import re

# ==========================================
# CONFIGURAÇÕES
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

PASTA_CONTAS = (
    BASE_DIR
    / "data"
    / "contas"
    / "instagram"
)

PASTA_CONTAS.mkdir(parents=True, exist_ok=True)


def obter_pasta_conta(numero):

    if not 1 <= numero <= 10:
        raise ValueError("Escolha uma conta de 1 a 10.")

    nome_pasta = f"conta_{numero:02d}"

    pasta = PASTA_CONTAS / nome_pasta

    pasta.mkdir(parents=True, exist_ok=True)

    return pasta


def login_instagram():

    print("\n==============================")
    print("     CAM - LOGIN INSTAGRAM")
    print("==============================\n")

    try:
        numero = int(
            input("Qual conta deseja conectar? (1 a 10): ")
        )
    except ValueError:
        print("Digite um número válido.")
        return

    if numero < 1 or numero > 10:
        print("Escolha um número entre 1 e 10.")
        return

    pasta_sessao = obter_pasta_conta(numero)

    print(f"\nConta selecionada: {numero:02d}")
    print(f"Perfil: {pasta_sessao}")

    print("\nAbrindo o Chrome...")

    with sync_playwright() as p:

        navegador = p.chromium.launch_persistent_context(
            user_data_dir=str(pasta_sessao),
            channel="chrome",
            headless=False,
            no_viewport=True
        )

        if navegador.pages:
            page = navegador.pages[0]
        else:
            page = navegador.new_page()

        page.goto(
            "https://www.instagram.com/",
            wait_until="domcontentloaded",
            timeout=60000
        )

        print("\nFaça o login manualmente no Instagram.")
        print("Conclua qualquer verificação solicitada.")

        input(
            "\nQuando estiver dentro da conta, "
            "pressione ENTER aqui para fechar..."
        )

        navegador.close()

    print("\nSessão da conta salva.")
    print(f"Conta: {numero:02d}")
    print(f"Pasta: {pasta_sessao}")


if __name__ == "__main__":
    login_instagram()