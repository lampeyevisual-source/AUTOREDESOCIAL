
from buscarvideos2 import (
    buscar_video_youtube,
    CATEGORIAS,
)
from baixarvideos3 import baixar_video


# ======================================================
# CONFIGURAÇÕES
# ======================================================

VIDEOS_POR_CATEGORIA = 10
MAX_FALHAS_CONSECUTIVAS = 8


# ======================================================
# MAIN — SOMENTE PESQUISAR E BAIXAR
# ======================================================

def main():

    total_baixados = 0
    total_falhas = 0

    print("\n==============================================")
    print(" CAM - PESQUISADOR E BAIXADOR DE SHORTS")
    print("==============================================")
    print("Modo: somente downloads")
    print(f"Meta: {VIDEOS_POR_CATEGORIA} vídeos por categoria")
    print(f"Categorias: {len(CATEGORIAS)}")
    print("Publicações: desativadas")
    print("==============================================")

    for categoria in CATEGORIAS:

        baixados_categoria = 0
        falhas_consecutivas = 0
        videos_tentados = set()

        print("\n")
        print("==============================================")
        print(f"CATEGORIA: {categoria}")
        print("==============================================")

        while baixados_categoria < VIDEOS_POR_CATEGORIA:

            print(
                f"\nProgresso: {baixados_categoria}/"
                f"{VIDEOS_POR_CATEGORIA} vídeos baixados"
            )

            print(f"Pesquisando na categoria: {categoria}")

            # ------------------------------------------
            # 1. PESQUISAR SHORT NA CATEGORIA ATUAL
            # ------------------------------------------

            try:
                resultados = buscar_video_youtube(
                    categoria=categoria
                )

            except Exception as erro:
                print(f"Erro ao pesquisar: {erro}")
                total_falhas += 1
                falhas_consecutivas += 1

                if falhas_consecutivas >= MAX_FALHAS_CONSECUTIVAS:
                    print("Muitas falhas. Passando para a próxima categoria.")
                    break

                continue

            if not resultados:
                print(
                    f"Nenhum Short encontrado nesta tentativa "
                    f"para a categoria '{categoria}'."
                )

                total_falhas += 1
                falhas_consecutivas += 1

                if falhas_consecutivas >= MAX_FALHAS_CONSECUTIVAS:
                    print(
                        f"Limite de {MAX_FALHAS_CONSECUTIVAS} falhas consecutivas "
                        f"atingido na categoria '{categoria}'."
                    )
                    print("Encerrando esta categoria.")
                    break

                print(
                    f"Tentando pesquisar novamente "
                    f"({falhas_consecutivas}/{MAX_FALHAS_CONSECUTIVAS})..."
                )
                continue

            video = resultados[0]

            # ------------------------------------------
            # 2. CONFERIR A CATEGORIA E O LINK
            # ------------------------------------------

            categoria_video = video.get("categoria", categoria)

            if categoria_video != categoria:
                print(
                    "Resultado ignorado: a categoria retornada "
                    f"foi '{categoria_video}', mas a pesquisa atual "
                    f"é '{categoria}'."
                )
                total_falhas += 1
                falhas_consecutivas += 1

                if falhas_consecutivas >= MAX_FALHAS_CONSECUTIVAS:
                    break

                continue

            url_video = video.get("link_compartilhamento")

            if not url_video:
                print("Resultado sem link de compartilhamento.")
                total_falhas += 1
                falhas_consecutivas += 1

                if falhas_consecutivas >= MAX_FALHAS_CONSECUTIVAS:
                    break

                continue

            if url_video in videos_tentados:
                print("Esse link já foi tentado nesta categoria.")
                print("Tentando encontrar outro vídeo.")

                total_falhas += 1
                falhas_consecutivas += 1

                if falhas_consecutivas >= MAX_FALHAS_CONSECUTIVAS:
                    print(
                        f"Limite de {MAX_FALHAS_CONSECUTIVAS} falhas consecutivas "
                        f"atingido na categoria '{categoria}'."
                    )
                    break

                continue
            videos_tentados.add(url_video)

            print(f"Título: {video.get('titulo', 'Sem título')}")
            print(f"Categoria: {categoria_video}")
            print(f"Link: {url_video}")

            # ------------------------------------------
            # 3. BAIXAR NA PASTA DA CATEGORIA
            # ------------------------------------------

            print("\nIniciando download...")

            try:
                arquivo = baixar_video(
                    url_video,
                    categoria=categoria_video
                )

            except Exception as erro:
                print(f"Erro no download: {erro}")
                arquivo = None

            if not arquivo:
                print("Download não concluído.")
                total_falhas += 1
                falhas_consecutivas += 1

                if falhas_consecutivas >= MAX_FALHAS_CONSECUTIVAS:
                    print("Muitas falhas. Passando para a próxima categoria.")
                    break

                continue

            # ------------------------------------------
            # 4. REGISTRAR SUCESSO
            # ------------------------------------------

            print("\nDownload concluído!")
            print(f"Categoria: {categoria_video}")
            print(f"Arquivo salvo: {arquivo}")

            baixados_categoria += 1
            total_baixados += 1
            falhas_consecutivas = 0

        print("\n----------------------------------------------")
        print(f"Categoria finalizada: {categoria}")
        print(
            f"Downloads concluídos: {baixados_categoria}/"
            f"{VIDEOS_POR_CATEGORIA}"
        )
        print("----------------------------------------------")

    # ==================================================
    # RESUMO FINAL
    # ==================================================

    print("\n==============================================")
    print(" PROCESSO FINALIZADO")
    print("==============================================")
    print(f"Total baixado: {total_baixados}")
    print(f"Total de falhas: {total_falhas}")
    print("Publicações realizadas: 0")
    print("O programa será encerrado.")
    print("==============================================")


# ======================================================
# EXECUÇÃO
# ======================================================

if __name__ == "__main__":
    main()
