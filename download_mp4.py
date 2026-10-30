
from pathlib import Path
import yt_dlp

# =====================================================
# CONFIGURAÇÕES
# =====================================================

BASE_DIR = Path(__file__).resolve().parent
PASTA_DESTINO = BASE_DIR / "videos"
PASTA_DESTINO.mkdir(parents=True, exist_ok=True)


# =====================================================
# RECEBER URL E BAIXAR EM MP4
# =====================================================

def download_mp4(url):
    """
    Recebe a URL de um vídeo do YouTube.
    Baixa vídeo e áudio e gera um arquivo MP4.
    Retorna o caminho do arquivo ou None em caso de erro.
    """

    if not isinstance(url, str) or not url.strip():
        print("ERRO: URL não informada.")
        return None

    url = url.strip()

    if not url.startswith("https://"):
        print("ERRO: informe uma URL HTTPS válida.")
        return None

    opcoes = {
        "format": "bestvideo*+bestaudio/best",
        "merge_output_format": "mp4",
        "recode_video": "mp4",
        "outtmpl": str(
            PASTA_DESTINO / "%(title).150s [%(id)s].%(ext)s"
        ),
        "noplaylist": True,
        "quiet": False,
    }

    try:
        with yt_dlp.YoutubeDL(opcoes) as ydl:
            info = ydl.extract_info(url, download=True)
            arquivo = Path(ydl.prepare_filename(info))
            arquivo_mp4 = arquivo.with_suffix(".mp4")

            if arquivo_mp4.exists():
                print(f"Download concluído: {arquivo_mp4}")
                return str(arquivo_mp4)

            if arquivo.exists():
                print(f"Arquivo baixado: {arquivo}")
                return str(arquivo)

            print("ERRO: arquivo final não encontrado.")
            return None

    except Exception as erro:
        print(f"ERRO NO DOWNLOAD: {erro}")
        return None
