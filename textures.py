import io
import struct
from dataclasses import dataclass, field
from io import BytesIO
from typing import BinaryIO, Union, List

import lz4.block
from DXTDecompress import DXTBuffer

import enums
import exceptions
import extensions
from exceptions import InvalidTextureFormat
from extensions import is_valid_format, read_n_bytes


@dataclass
class TexHeader:
    Format: enums.TexFormat
    Flags: enums.TexFlags
    TextureWidth: int
    TextureHeight: int
    ImageWidth: int
    ImageHeight: int
    UnkInt0: int


@dataclass
class TexMipmap:
    Bytes: bytes = field(repr=False)
    Width: int = None
    Height: int = None
    DecompressedBytesCount: int = None
    IsLZ4Compressed: bool = None
    Format: enums.MipmapFormat = None

    def getBytesStream(self) -> BytesIO:
        return io.BytesIO(self.Bytes)


@dataclass
class TexImage:
    Mipmaps: List[TexMipmap] = field(default_factory=list)

    def FirstMipmap(self):
        return self.Mipmaps[0]


@dataclass
class TexImageContainer:
    Magic: str = None
    Images: List[TexImage] = field(default_factory=list)
    ImageContainerVersion: enums.TexImageContainerVersion = None
    ImageFormat: enums.FreeImageFormat = enums.FreeImageFormat.FIF_UNKNOWN


@dataclass
class TexFrameInfo:
    ImageId: int
    FrameTime: float
    X: float
    Y: float
    Width: float
    WidthY: float
    HeightX: float
    Height: float


@dataclass
class TexFrameInfoContainer:
    _fd: Union[BinaryIO, BytesIO]
    Magic: str = None
    Frames: List[TexFrameInfo] = field(default_factory=list)
    GifWidth: int = 0
    GifHeight: int = 0

    def read(self):
        self.Magic = self._fd.read(8).decode()
        self._fd.read(1)
        frameConut = read_n_bytes(self._fd)

        match self.Magic:
            case "TEXS0001":
                for i in range(frameConut):
                    self.Frames.append(
                        TexFrameInfo(
                            ImageId=read_n_bytes(self._fd),
                            FrameTime=struct.unpack("<i", self._fd.read(4))[0],
                            X=read_n_bytes(self._fd),
                            Y=read_n_bytes(self._fd),
                            Width=read_n_bytes(self._fd),
                            WidthY=read_n_bytes(self._fd),
                            HeightX=read_n_bytes(self._fd),
                            Height=read_n_bytes(self._fd),
                        )
                    )
            case "TEXS0002": pass
            case "TEXS0003":
                self.GifWidth = read_n_bytes(self._fd)
                self.GifHeight = read_n_bytes(self._fd)
                for i in range(frameConut):
                    self.Frames.append(
                        TexFrameInfo(
                            ImageId=read_n_bytes(self._fd),
                            FrameTime=struct.unpack("<i", self._fd.read(4))[0],
                            X=struct.unpack("<i", self._fd.read(4))[0],
                            Y=struct.unpack("<i", self._fd.read(4))[0],
                            Width=struct.unpack("<i", self._fd.read(4))[0],
                            WidthY=struct.unpack("<i", self._fd.read(4))[0],
                            HeightX=struct.unpack("<i", self._fd.read(4))[0],
                            Height=struct.unpack("<i", self._fd.read(4))[0],
                        )
                    )
            case _:
                raise exceptions.UnknownMagicError()

        if self.GifWidth == 0 or self.GifHeight == 0:
            self.GifWidth = int(self.Frames[0].Width)
            self.GifHeight = int(self.Frames[0].Height)



@dataclass
class Texture:
    _magic1: str = None
    _magic2: str = None
    header: TexHeader = None
    images_container: TexImageContainer = None
    frame_info_container: TexFrameInfoContainer = None
    first_image: TexImage = None

    @property
    def is_gif(self) -> bool:
        return self.has_flag(enums.TexFlags.IsGif)

    @property
    def magic1(self):
        return self._magic1

    @magic1.setter
    def magic1(self, value):
        if value != "TEXV0005":
            raise ValueError("Incorrect magic1")
        self._magic1 = value

    @property
    def magic2(self):
        return self._magic2

    @magic2.setter
    def magic2(self, value):
        if value != "TEXI0001":
            raise ValueError("Incorrect magic2")
        self._magic2 = value

    def has_flag(self, flag: enums.TexFlags) -> bool:
        if not self.header:
            return False
        return (self.header.Flags.value & flag.value) == flag.value


class TexReader:
    def __init__(self, file: Union[str, bytes, BinaryIO, BytesIO]):
        if isinstance(file, str):
            self._fd: BinaryIO = open(file, "r+b")
        elif isinstance(file, bytes):
            self._fd: BytesIO = io.BytesIO(file)
        else:
            self._fd = file
        self.texture = Texture()
        self._read_magic()
        self.texture.header = self._read_header()
        self.texture.images_container = self._read_image_container()
        if self.texture.is_gif:
            self.texture.frame_info_container = TexFrameInfoContainer(self._fd)
            self.texture.frame_info_container.read()


    def _read_magic(self):
        self.texture.magic1 = self._fd.read(8).decode()
        self._fd.read(1)
        self.texture.magic2 = self._fd.read(8).decode()
        self._fd.read(1)

    def _read_header(self) -> TexHeader:
        header = TexHeader(
            Format=enums.TexFormat(read_n_bytes(self._fd)),
            Flags=enums.TexFlags(read_n_bytes(self._fd)),
            TextureWidth=read_n_bytes(self._fd),
            TextureHeight=read_n_bytes(self._fd),
            ImageWidth=read_n_bytes(self._fd),
            ImageHeight=read_n_bytes(self._fd),
            UnkInt0=read_n_bytes(self._fd),
        )
        if not is_valid_format(header.Format):
            raise InvalidTextureFormat()
        return header

    def _read_image_container(self) -> TexImageContainer:
        container = TexImageContainer(Magic=self._fd.read(8).decode())
        self._fd.read(1)
        image_count = read_n_bytes(self._fd)

        match container.Magic:
            case "TEXB0001" | "TEXB0002":
                pass
            case "TEXB0003":
                container.ImageFormat = enums.FreeImageFormat(read_n_bytes(self._fd))
            case _:
                raise exceptions.UnknownMagicError(container.Magic)

        container.ImageContainerVersion = enums.TexImageContainerVersion(
            int(container.Magic[4:])
        )

        if not is_valid_format(container.ImageFormat):
            raise InvalidTextureFormat()

        reader = TexImageReader(self._fd, container, self.texture.header.Format)

        for i in range(image_count):
            container.Images.append(reader.read())

        return container


class TexMipmapDecompressor:
    def __init__(self, mipmap: TexMipmap):
        self.mipmap = mipmap

    def decompressMipmap(self):
        if self.mipmap.IsLZ4Compressed:
            self.mipmap.Bytes = self.lz4decompress()
            self.mipmap.IsLZ4Compressed = False

        if self.mipmap.Format.isImage(self.mipmap.Format):
            return

        _buffer = DXTBuffer(self.mipmap.Width, self.mipmap.Height)
        match self.mipmap.Format:
            case enums.MipmapFormat.CompressedDXT5 | enums.MipmapFormat.CompressedDXT3:
                self.mipmap.Bytes = _buffer.DXT5Decompress(
                    io.BytesIO(self.mipmap.Bytes)
                )
                self.mipmap.Format = enums.MipmapFormat.RGBA8888
            case enums.MipmapFormat.CompressedDXT1:
                self.mipmap.Bytes = _buffer.DXT1Decompress(
                    io.BytesIO(self.mipmap.Bytes)
                )
                self.mipmap.Format = enums.MipmapFormat.RGBA8888

    def lz4decompress(self) -> bytes:
        decompressed = lz4.block.decompress(
            self.mipmap.Bytes,
            uncompressed_size=self.mipmap.DecompressedBytesCount
        )
        if len(decompressed) != self.mipmap.DecompressedBytesCount:
            raise exceptions.DecompressionError()
        return decompressed


class TexImageReader:
    def __init__(
        self,
        fd: Union[BinaryIO, BytesIO],
        container: TexImageContainer,
        texFormat: enums.TexFormat,
    ):
        self._texMipmapDecompressor = None
        self.ReadMipmapBytes = True
        self.DecompressMipmapBytes = True
        self._fd = fd
        self._container = container
        self._texFormat = texFormat

    def read(self):
        mipmapCount = read_n_bytes(self._fd)
        read_func = self.pickMipmapReader(self._container.ImageContainerVersion)
        mipmapFormat = extensions.getFormatForTex(
            self._container.ImageFormat, self._texFormat
        )
        image = TexImage()
        for i in range(mipmapCount):
            mipmap = read_func(self._fd)
            mipmap.Format = mipmapFormat
            if self.DecompressMipmapBytes:
                _decompressor = TexMipmapDecompressor(mipmap)
                _decompressor.decompressMipmap()
            image.Mipmaps.append(mipmap)

        return image

    @staticmethod
    def readMipmapV1(fd: Union[BinaryIO, BytesIO]):
        return TexMipmap(
            Width=read_n_bytes(fd),
            Height=read_n_bytes(fd),
            Bytes=TexImageReader.readBytes(fd),
            IsLZ4Compressed=False,
        )

    @staticmethod
    def readMipmapV2AndV3(fd: Union[BinaryIO, BytesIO]):
        return TexMipmap(
            Width=read_n_bytes(fd),
            Height=read_n_bytes(fd),
            IsLZ4Compressed=read_n_bytes(fd) == 1,
            DecompressedBytesCount=read_n_bytes(fd),
            Bytes=TexImageReader.readBytes(fd),
        )

    @staticmethod
    def readBytes(fd: Union[BinaryIO, BytesIO]):
        byteCount = read_n_bytes(fd)
        bytesRead = fd.read(byteCount)
        if len(bytesRead) != byteCount:
            raise ValueError("Failed to read bytes from stream while reading mipmap")
        return bytesRead

    @staticmethod
    def pickMipmapReader(version: enums.TexImageContainerVersion) -> callable:
        match version:
            case enums.TexImageContainerVersion.Version1:
                return TexImageReader.readMipmapV1
            case (
                enums.TexImageContainerVersion.Version2
                | enums.TexImageContainerVersion.Version3
            ):
                return TexImageReader.readMipmapV2AndV3
            case _:
                raise exceptions.InvalidContainerVersion
