import io
from dataclasses import dataclass, field
from io import BytesIO
from typing import BinaryIO, List, Union

import lz4.block

import enums
import exceptions
import extensions
from DXT import decompressImage
from exceptions import InvalidTextureFormat
from extensions import is_valid_format, read_n_bytes


@dataclass
class Texture:
    Format: enums.TexFormat
    Flags: enums.TexFlags
    TextureWidth: int
    TextureHeight: int
    ImageWidth: int
    ImageHeight: int
    UnkInt0: int
    images_container: "TexImageContainer" = None
    frame_info_container: "TexFrameInfoContainer" = None
    _magic1: str = None
    _magic2: str = None

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
        return (self.Flags.value & flag.value) == flag.value


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
class TexImageContainer:
    Magic: str = None
    Images: List["TexImage"] = field(default_factory=list)
    ImageContainerVersion: enums.TexImageContainerVersion = None
    ImageFormat: enums.FreeImageFormat = enums.FreeImageFormat.FIF_UNKNOWN

    @property
    def firstImage(self) -> "TexImage":
        return self.Images[0]


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
        self.Magic = read_n_bytes(self._fd, "<8sx").decode()
        frameConut = read_n_bytes(self._fd)

        match self.Magic:
            case "TEXS0001":
                for i in range(frameConut):
                    data = read_n_bytes(self._fd, "<ifiiiiii")
                    self.Frames.append(TexFrameInfo(*data))
            case "TEXS0002":
                pass
            case "TEXS0003":
                self.GifWidth, self.GifHeight = read_n_bytes(self._fd, "<ii")
                for i in range(frameConut):
                    data = read_n_bytes(self._fd, "<ifffffff")
                    self.Frames.append(TexFrameInfo(*data))
            case _:
                raise exceptions.UnknownMagicError()

        if self.GifWidth == 0 or self.GifHeight == 0:
            self.GifWidth = int(self.Frames[0].Width)
            self.GifHeight = int(self.Frames[0].Height)


class TexReader:
    # equal to char[8], pad byte, char[8], pad byte and 7 int
    # in little-endian byte order
    HEADER_STRUCT = "<8sx8sxiiiiiii"

    def __init__(self, file: Union[str, bytes, BinaryIO, BytesIO]):
        if isinstance(file, str):
            self._fd: BinaryIO = open(file, "r+b")
        elif isinstance(file, bytes):
            self._fd: BytesIO = io.BytesIO(file)
        else:
            self._fd = file
        self._read_header()
        self.texture.images_container = self._read_image_container()
        if self.texture.is_gif:
            self.texture.frame_info_container = TexFrameInfoContainer(self._fd)
            self.texture.frame_info_container.read()

    def _read_header(self):
        data = read_n_bytes(self._fd, self.HEADER_STRUCT)
        self.texture = Texture(
            Format=enums.TexFormat(data[2]),
            Flags=enums.TexFlags(data[3]),
            TextureWidth=data[4],
            TextureHeight=data[5],
            ImageWidth=data[6],
            ImageHeight=data[7],
            UnkInt0=data[8],
        )
        self.texture.magic1 = data[0].decode()
        self.texture.magic2 = data[1].decode()
        if not is_valid_format(self.texture.Format):
            raise InvalidTextureFormat()

    def _read_image_container(self) -> TexImageContainer:
        container = TexImageContainer(
            Magic=read_n_bytes(self._fd, "<8sx").decode()
        )
        image_count = read_n_bytes(self._fd)

        match container.Magic:
            case "TEXB0001" | "TEXB0002":
                pass
            case "TEXB0003":
                try:
                    container.ImageFormat = enums.FreeImageFormat(
                        read_n_bytes(self._fd)
                    )
                except ValueError:
                    container.ImageFormat = enums.FreeImageFormat.FIF_UNKNOWN
            case _:
                raise exceptions.UnknownMagicError(container.Magic)

        container.ImageContainerVersion = enums.TexImageContainerVersion(
            int(container.Magic[4:])
        )

        if not is_valid_format(container.ImageFormat):
            raise InvalidTextureFormat()

        reader = TexImage(self._fd, container, self.texture.Format)
        reader.read()

        for i in range(image_count):
            container.Images.append(reader)

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

        match self.mipmap.Format:
            case enums.MipmapFormat.CompressedDXT5:
                self.mipmap.Bytes = decompressImage(
                    self.mipmap.Width, self.mipmap.Height,
                    self.mipmap.Bytes, enums.DXTFlags.DXT5
                )
                self.mipmap.Format = enums.MipmapFormat.RGBA8888
            case enums.MipmapFormat.CompressedDXT3:
                self.mipmap.Bytes = decompressImage(
                    self.mipmap.Width, self.mipmap.Height,
                    self.mipmap.Bytes, enums.DXTFlags.DXT3
                )
                self.mipmap.Format = enums.MipmapFormat.RGBA8888
            case enums.MipmapFormat.CompressedDXT1:
                self.mipmap.Bytes = decompressImage(
                    self.mipmap.Width, self.mipmap.Height,
                    self.mipmap.Bytes, enums.DXTFlags.DXT1
                )
                self.mipmap.Format = enums.MipmapFormat.RGBA8888

    def lz4decompress(self) -> bytes:
        decompressed = lz4.block.decompress(
            self.mipmap.Bytes, uncompressed_size=self.mipmap.DecompressedBytesCount
        )
        if len(decompressed) != self.mipmap.DecompressedBytesCount:
            raise exceptions.DecompressionError()
        return decompressed


@dataclass
class TexImage:
    _fd: Union[BinaryIO, BytesIO]
    _container: TexImageContainer
    _texFormat: enums.TexFormat
    # ReadMipmapBytes: bool = True  # variable not used
    DecompressMipmapBytes: bool = True
    Mipmaps: List[TexMipmap] = field(default_factory=list)

    @property
    def firstMipmap(self):
        return self.Mipmaps[0]

    def read(self):
        mipmapCount = read_n_bytes(self._fd)
        read_func = self.pickMipmapReader(self._container.ImageContainerVersion)
        mipmapFormat = extensions.getFormatForTex(
            self._container.ImageFormat, self._texFormat
        )
        for i in range(mipmapCount):
            mipmap = read_func(self._fd)
            mipmap.Format = mipmapFormat
            if self.DecompressMipmapBytes:  # redundant condition
                _decompressor = TexMipmapDecompressor(mipmap)
                _decompressor.decompressMipmap()
            self.Mipmaps.append(mipmap)

    @staticmethod
    def readMipmapV1(fd: Union[BinaryIO, BytesIO]):
        return TexMipmap(
            Width=read_n_bytes(fd),
            Height=read_n_bytes(fd),
            Bytes=TexImage.readBytes(fd),
            IsLZ4Compressed=False,
        )

    @staticmethod
    def readMipmapV2AndV3(fd: Union[BinaryIO, BytesIO]):
        return TexMipmap(
            Width=read_n_bytes(fd),
            Height=read_n_bytes(fd),
            IsLZ4Compressed=read_n_bytes(fd) == 1,
            DecompressedBytesCount=read_n_bytes(fd),
            Bytes=TexImage.readBytes(fd),
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
                return TexImage.readMipmapV1
            case (
                enums.TexImageContainerVersion.Version2
                | enums.TexImageContainerVersion.Version3
            ):
                return TexImage.readMipmapV2AndV3
            case _:
                raise exceptions.InvalidContainerVersion
