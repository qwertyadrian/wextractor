import lz4.block

from .DXT import decompressImage
from .enums import DXTFlags, MipmapFormat
from .exceptions import DecompressionError


def lz4decompress(data: bytes, decompressedBytesCount: int):
    decompressed = lz4.block.decompress(data, uncompressed_size=decompressedBytesCount)
    if len(decompressed) != decompressedBytesCount:
        raise DecompressionError()
    return decompressed


def decompressMipmap(mipmap):
    if mipmap.isLZ4Compressed:
        mipmap.data = lz4decompress(mipmap.data, mipmap.decompressedBytesCount)
        mipmap.isLZ4Compressed = False

    if mipmap.format.isImage(mipmap.format):
        return mipmap

    match mipmap.format:
        case MipmapFormat.CompressedDXT5:
            mipmap.data = decompressImage(
                mipmap.width, mipmap.height, mipmap.data, DXTFlags.DXT5
            )
            mipmap.format = MipmapFormat.RGBA8888
        case MipmapFormat.CompressedDXT3:
            mipmap.data = decompressImage(
                mipmap.width, mipmap.height, mipmap.data, DXTFlags.DXT3
            )
            mipmap.format = MipmapFormat.RGBA8888
        case MipmapFormat.CompressedDXT1:
            mipmap.data = decompressImage(
                mipmap.width, mipmap.height, mipmap.data, DXTFlags.DXT1
            )
            mipmap.format = MipmapFormat.RGBA8888
