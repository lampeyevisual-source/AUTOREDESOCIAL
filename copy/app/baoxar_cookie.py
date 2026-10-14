
from pathlib import Path
from playwright.sync_api import sync_playwright

# =====================================================
# CONFIGURAÇÕES
# =====================================================

# Arquivo atual: AUTOREDESOCIAL/copy/app/baoxar_cookie.py
PASTA_PROJETO = Path(__file__).resolve().parents[2]

# Perfil separado, exclusivo para esta automação
PASTA_CHROME = (
    PASTA_PROJETO
    / "data"
    / "contas"
    / "youtube_cookies"
)

ARQUIVO_COOKIES = PASTA_PROJETO / "cookies.txt"

DOMINIOS = (
    "youtube.com",
    "google.com",
    "googleusercontent.com",
)


def pertence_aos_dominios(dominio):
    dominio = dominio.lstrip(".").lower()

    return any(
        dominio == permitido
        or dominio.endswith("." + permitido)
        for permitido in DOMINIOS
    )


def puxar_cookies():
    PASTA_CHROME.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        print("Abrindo o Chrome com perfil exclusivo...")

        contexto = p.chromium.launch_persistent_context(
            user_data_dir=str(PASTA_CHROME),
            channel="chrome",
            headless=False,
            no_viewport=True,
        )

        try:
            pagina = (
                contexto.pages[0]
                if contexto.pages
                else contexto.new_page()
            )

            print("Abrindo o YouTube...")

            pagina.goto(
                "https://www.youtube.com/",
                wait_until="domcontentloaded",
                timeout=60000,
            )

            print("YouTube aberto.")

            input(
                "\nConfira se está conectado à sua conta do YouTube. "
                "Se precisar, faça login nessa janela. "
                "Depois, volte aqui e pressione ENTER para salvar os cookies..."
            )

            cookies = contexto.cookies()

            cookies = [
                cookie
                for cookie in cookies
                if pertence_aos_dominios(cookie["domain"])
            ]

            if not cookies:
                print(
                    "Nenhum cookie dos domínios esperados foi encontrado."
                )
                return

            with ARQUIVO_COOKIES.open(
                "w",
                encoding="utf-8",
                newline="\n",
            ) as arquivo:
                arquivo.write(
                    "# Netscape HTTP Cookie File\n"
                )

                for cookie in cookies:
                    dominio = cookie["domain"]
                    incluir_subdominios = dominio.startswith(".")
                    caminho = cookie.get("path", "/")
                    seguro = "TRUE" if cookie.get("secure") else "FALSE"
                    expiracao = int(cookie.get("expires", 0))

                    if expiracao < 0:
                        expiracao = 0

                    nome = cookie["name"]
                    valor = cookie["value"]

                    arquivo.write(
                        f"{dominio}\t"
                        f"{'TRUE' if incluir_subdominios else 'FALSE'}\t"
                        f"{caminho}\t"
                        f"{seguro}\t"
                        f"{expiracao}\t"
                        f"{nome}\t"
                        f"{valor}\n"
                    )

            print(f"\nCookies salvos em: {ARQUIVO_COOKIES}")
            print(f"Quantidade de cookies: {len(cookies)}")

        finally:
            contexto.close()


if __name__ == "__main__":
    puxar_cookies()
