
from postarinsta import postar_instagram
from postartiktok import postar_tiktok

from pathlib import Path
import random
import time


# ======================================================
# CONFIGURAÇÕES
# ======================================================

INTERVALO_CICLO = 60 * 60  # 60 minutos

PASTA_PROJETO = Path(
    r"C:\Users\marqu\OneDrive\Desktop\AUTOMACOES LUIZ\AUTOREDESOCIAL\copy"
)

ARQUIVO_LEGENDAS = (
    PASTA_PROJETO
    / "data"
    / "legendas.txt"
)

PASTA_VIDEOS = (
    PASTA_PROJETO
    / "data"
    / "videos"
    / "refeitos"
)

EXTENSOES_VIDEO = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
}


# ======================================================
# ESCOLHER LEGENDA ALEATORIAMENTE
# ======================================================

def escolher_legenda():

    if not ARQUIVO_LEGENDAS.exists():
        raise FileNotFoundError(
            f"Arquivo de legendas não encontrado:\n"
            f"{ARQUIVO_LEGENDAS}"
        )

    with open(
        ARQUIVO_LEGENDAS,
        "r",
        encoding="utf-8"
    ) as arquivo:
        conteudo = arquivo.read()

    legendas = [
        legenda.strip()
        for legenda in conteudo.split("###")
        if legenda.strip()
    ]

    if not legendas:
        raise ValueError(
            "Nenhuma legenda encontrada em:\n"
            f"{ARQUIVO_LEGENDAS}"
        )

    return random.choice(legendas)


# ======================================================
# ESCOLHER VÍDEO ALEATORIAMENTE
# ======================================================

def escolher_video():

    if not PASTA_VIDEOS.exists():
        raise FileNotFoundError(
            f"Pasta de vídeos não encontrada:\n"
            f"{PASTA_VIDEOS}"
        )

    videos = [
        arquivo
        for arquivo in PASTA_VIDEOS.iterdir()
        if arquivo.is_file()
        and arquivo.suffix.lower() in EXTENSOES_VIDEO
    ]

    if not videos:
        raise FileNotFoundError(
            "Nenhum vídeo compatível encontrado na pasta:\n"
            f"{PASTA_VIDEOS}"
        )

    return random.choice(videos)


# ======================================================
# MAIN
# ======================================================

def main():

    print("\n===================================")
    print("       AUTOMACAO TIKTOK")
    print("===================================")

    while True:

        inicio_ciclo = time.time()

        print("\n===================================")
        print("          NOVO CICLO")
        print("===================================\n")

        try:

            # ==============================================
            # 1. ESCOLHER LEGENDA
            # ==============================================

            legenda = escolher_legenda()

            print("-----------------------------------")
            print("LEGENDA ESCOLHIDA:")
            print(legenda)
            print("-----------------------------------")

            # ==============================================
            # 2. ESCOLHER VÍDEO
            # ==============================================

            arquivo = escolher_video()

            print("\n-----------------------------------")
            print("VÍDEO ESCOLHIDO:")
            print(arquivo.name)
            print(f"Caminho: {arquivo}")
            print("-----------------------------------")

        except Exception as erro:

            print("\nERRO AO PREPARAR O CICLO:")
            print(erro)

        else:

           # ==============================================
            # 3. POSTAR EM TODAS AS CONTAS
            # ==============================================

            for numero_conta in range(1, 11):

                print("\n" + "=" * 45)
                print(f"INICIANDO CONTA {numero_conta:02d}")
                print("=" * 45)

                # ==========================================
                # TIKTOK DA CONTA ATUAL
                # ==========================================

                try:

                    print(
                        f"\nIniciando TikTok - conta "
                        f"{numero_conta:02d}...\n"
                    )

                    resultado_tiktok = postar_tiktok(
                        caminho_video=str(arquivo),
                        descricao=legenda,
                        numero_conta=numero_conta
                    )

                    if resultado_tiktok:
                        print(
                            f"TikTok {numero_conta:02d}: "
                            "publicação concluída."
                        )
                    else:
                        print(
                            f"TikTok {numero_conta:02d}: "
                            "falha ao publicar."
                        )

                except Exception as erro:

                    print(
                        f"ERRO NO TIKTOK {numero_conta:02d}:"
                    )
                    print(erro)

                # ==========================================
                # INSTAGRAM DA MESMA CONTA
                # ==========================================

                try:

                    print(
                        f"\nIniciando Instagram - conta "
                        f"{numero_conta:02d}...\n"
                    )

                    resultado_instagram = postar_instagram(
                        numero_conta=numero_conta,
                        caminho_video=str(arquivo),
                        legenda=legenda
                    )

                    if resultado_instagram:
                        print(
                            f"Instagram {numero_conta:02d}: "
                            "publicação concluída."
                        )
                    else:
                        print(
                            f"Instagram {numero_conta:02d}: "
                            "falha ao publicar."
                        )

                except Exception as erro:

                    print(
                        f"ERRO NO INSTAGRAM {numero_conta:02d}:"
                    )
                    print(erro)

                print(
                    f"\nCONTA {numero_conta:02d} FINALIZADA."
                )

        # ==============================================

        # ==============================================
        # 5. ESPERAR ATÉ COMPLETAR O INTERVALO
        # ==============================================

        tempo_passado = time.time() - inicio_ciclo
        tempo_restante = INTERVALO_CICLO - tempo_passado

        if tempo_restante > 0:

            minutos = int(tempo_restante // 60)
            segundos = int(tempo_restante % 60)

            print("\n===================================")
            print("       CICLO FINALIZADO")
            print("===================================")
            print(
                f"Próximo ciclo em: "
                f"{minutos} min {segundos} seg"
            )
            print("===================================\n")

            time.sleep(tempo_restante)

        else:

            print("\nO ciclo ultrapassou 60 minutos.")
            print("Iniciando o próximo ciclo imediatamente.")


# ======================================================
# EXECUÇÃO
# ======================================================

if __name__ == "__main__":
    main()
