

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