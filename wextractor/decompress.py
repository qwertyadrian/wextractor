import lz4.block

from .DXT import decompress_image
from .enums import DXTFlags, MipmapFormat
from .exceptions import DecompressionError


def lz4decompress(data: bytes, decompressed_bytes_count: int):
    decompressed = lz4.block.decompress(data, uncompressed_size=decompressed_bytes_count)
    if len(decompressed) != decompressed_bytes_count:
        raise DecompressionError()
    return decompressed


def decompress_mipmap(mipmap):
    if mipmap.is_lz4_compressed:
        mipmap.data = lz4decompress(mipmap.data, mipmap.decompressed_bytes_count)
        mipmap.is_lz4_compressed = False

    if mipmap.format.is_image(mipmap.format):
        return mipmap

    match mipmap.format:
        case MipmapFormat.CompressedDXT5:
            mipmap.data = decompress_image(
                mipmap.width, mipmap.height, mipmap.data, DXTFlags.DXT5
            )
            mipmap.format = MipmapFormat.RGBA8888
        case MipmapFormat.CompressedDXT3:
            mipmap.data = decompress_image(
                mipmap.width, mipmap.height, mipmap.data, DXTFlags.DXT3
            )
            mipmap.format = MipmapFormat.RGBA8888
        case MipmapFormat.CompressedDXT1:
            mipmap.data = decompress_image(
                mipmap.width, mipmap.height, mipmap.data, DXTFlags.DXT1
            )
            mipmap.format = MipmapFormat.RGBA8888
