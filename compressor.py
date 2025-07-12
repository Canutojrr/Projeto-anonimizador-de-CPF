import os
import subprocess

def compress_pdf(input_path, output_path=None, quality='screen'):
    """
    Comprime um PDF usando Ghostscript.
    """
    # Aqui você pode colocar o caminho fixo para ghostscript portátil se quiser
    # Ou adaptar para ler config.json, mas para teste coloque o caminho direto

    gs_path = "ghostscript/gswin64c.exe"  # Ajuste conforme seu projeto

    if not os.path.isfile(gs_path):
        print("Executável do Ghostscript não encontrado em:", gs_path)
        return

    if not output_path:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_comprimido{ext}"

    gs_command = [
        gs_path,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS=/{quality}",
        "-dNOPAUSE", "-dQUIET", "-dBATCH",
        f"-sOutputFile={output_path}",
        input_path
    ]
    subprocess.call(gs_command)
    print(f"Compressão concluída: {output_path}")
