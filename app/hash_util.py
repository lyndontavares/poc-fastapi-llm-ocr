import hashlib
import io
from typing import Union

def gerar_hash_imagem(image_data: Union[bytes, io.BytesIO]) -> str:
    """
    Gera o hash MD5 de uma imagem.

    Args:
        image_data: Os dados binários da imagem (bytes) ou um objeto BytesIO.

    Returns:
        Uma string hexadecimal representando o hash MD5 da imagem.
    """
    # Se for BytesIO, precisamos ler o conteúdo.
    # É importante garantir que o cursor esteja no início se for BytesIO.
    if isinstance(image_data, io.BytesIO):
        image_data.seek(0) # Volta o cursor para o início do BytesIO
        bytes_to_hash = image_data.read()
    elif isinstance(image_data, bytes):
        bytes_to_hash = image_data
    else:
        raise TypeError("A entrada deve ser 'bytes' ou 'io.BytesIO'.")

    # Calcula o hash MD5
    md5_hash = hashlib.md5(bytes_to_hash)
    
    # Retorna o hash em formato hexadecimal
    return md5_hash.hexdigest()