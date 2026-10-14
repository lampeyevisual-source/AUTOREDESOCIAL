from repost.app.buscarvideos2 import buscar_video_youtube
from repost.app.baixarvideos2 import baixar_video
from repost.app.postarinsta import postar_instagram
from repost.app.postartiktok import postar_tiktok

from pathlib import Path
import random
import time


# ======================================================
# CONFIGURAÇÕES
# ======================================================

INTERVALO_CICLO = 60 * 60  # 60 minutos

BASE_DIR = Path(__file__).resolve().parent.parent

ARQUIVO_LEGENDAS = (
    BASE_DIR
    / "data"
    / "legendas.txt"
)


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
            "Nenhuma legenda encontrada em "
            "data/legendas.txt"
        )

    return random.choice(legendas)


# ======================================================
# MAIN
# ======================================================

def main():

    print("\n===================================")
    print("       AUTOMACAO TIKTOK")
    print("===================================\n")

    while True:

        # ==================================================
        # INÍCIO DO CICLO
        # ==================================================

        inicio_ciclo = time.time()

        print("\n===================================")
        print("          NOVO CICLO")
        print("===================================\n")


        # ==================================================
        # 1. ESCOLHER LEGENDA
        # ==================================================

        try:

            legenda = escolher_legenda()

            print("-----------------------------------")
            print("Legenda escolhida:")
            print(legenda)
            print("-----------------------------------")

        except Exception as erro:

            print("\nERRO AO CARREGAR LEGENDA:")
            print(erro)

            
            # ==================================================
            # 4. POSTAR NO TIKTOK
            # ==================================================

            print("\nIniciando postagem no TikTok...\n")

            resultado_tiktok = postar_tiktok(
                caminho_video=arquivo,
                descricao=legenda
            )

            if resultado_tiktok:

                print("\n-----------------------------------")
                print("Vídeo publicado no TikTok.")
                print("-----------------------------------")

            else:

                print("\nFalha ao postar no TikTok.")


            # ==================================================
            # 5. POSTAR NO INSTAGRAM
            # ==================================================

            print("\nIniciando postagem no Instagram...\n")

            resultado_instagram = postar_instagram(
                numero_conta=1,
                caminho_video=arquivo,
                legenda=legenda
            )

            if resultado_instagram:

                print("\n-----------------------------------")
                print("Vídeo programado no Instagram.")
                print("-----------------------------------")

            else:

                print("\nFalha ao postar no Instagram.")


        # ==================================================
        # 6. CALCULAR TEMPO DO CICLO
        # ==================================================

        tempo_passado = time.time() - inicio_ciclo

        tempo_restante = (
            INTERVALO_CICLO
            - tempo_passado
        )


        # ==================================================
        # 7. ESPERAR ATÉ COMPLETAR 27 MINUTOS
        # ==================================================

        if tempo_restante > 0:

            minutos = int(
                tempo_restante // 60
            )

            segundos = int(
                tempo_restante % 60
            )

            print("\n===================================")
            print("       CICLO FINALIZADO")
            print("===================================")

            print(
                f"Próximo ciclo em: "
                f"{minutos} min {segundos} seg"
            )

            print("===================================\n")

            time.sleep(
                tempo_restante
            )

        else:

            print("\n===================================")
            print("O ciclo demorou mais de 27 minutos.")
            print("Iniciando próximo ciclo imediatamente.")
            print("===================================\n")


# ======================================================
# EXECUÇÃO
# ======================================================

if __name__ == "__main__":

    main()