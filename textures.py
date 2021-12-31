import io
from dataclasses import dataclass, field
from io import BytesIO
from typing import BinaryIO, List, Union

from decompress import decompressMipmap
import enums
import exceptions
import extensions
from exceptions import InvalidTextureFormat
from extensions import is_valid_format, read_n_bytes


@dataclass
class TexMipmap:
    data: bytes = field(repr=False)
    width: int = None
    height: int = None
    decompressedBytesCount: int = None
    isLZ4Compressed: bool = None
    format: enums.MipmapFormat = None

    def getBytesStream(self) -> BytesIO:
        return io.BytesIO(self.data)


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


class Texture:
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
        self._read_image_container()

        self.frameInfoContainer = None
        if self.is_gif:
            self.frameInfoContainer = TexFrameInfoContainer(self._fd)
            self.frameInfoContainer.read()

    def _read_header(self):
        data = read_n_bytes(self._fd, self.HEADER_STRUCT)

        self._magic1 = data[0].decode()
        self._magic2 = data[1].decode()
        if self._magic1 != "TEXV0005" or self._magic2 != "TEXI0001":
            raise ValueError("Incorrect magic value")
        self.format = enums.TexFormat(data[2])
        self.flags = enums.TexFlags(data[3])
        self.textureWidth = data[4]
        self.textureHeight = data[5]
        self.imageWidth = data[6]
        self.imageHeight = data[7]
        self.unkInt0 = data[8]

        if not is_valid_format(self.format):
            raise InvalidTextureFormat()

    def _read_image_container(self):
        self.imagesContainer = TexImageContainer(
            Magic=read_n_bytes(self._fd, "<8sx").decode()
        )
        image_count = read_n_bytes(self._fd)

        match self.imagesContainer.Magic:
            case "TEXB0001" | "TEXB0002":
                pass
            case "TEXB0003":
                try:
                    self.imagesContainer.ImageFormat = enums.FreeImageFormat(
                        read_n_bytes(self._fd)
                    )
                except ValueError:
                    self.imagesContainer.ImageFormat = enums.FreeImageFormat.FIF_UNKNOWN
            case _:
                raise exceptions.UnknownMagicError(self.imagesContainer.Magic)

        self.imagesContainer.ImageContainerVersion = enums.TexImageContainerVersion(
            int(self.imagesContainer.Magic[4:])
        )

        if not is_valid_format(self.imagesContainer.ImageFormat):
            raise InvalidTextureFormat()

        reader = TexImage(self._fd, self.imagesContainer, self.format)
        reader.read()

        for i in range(image_count):
            self.imagesContainer.Images.append(reader)

    @property
    def is_gif(self) -> bool:
        return self.has_flag(enums.TexFlags.IsGif)

    def has_flag(self, flag: enums.TexFlags) -> bool:
        return (self.flags.value & flag.value) == flag.value


@dataclass
class TexImage:
    _fd: Union[BinaryIO, BytesIO]
    _container: TexImageContainer
    _texFormat: enums.TexFormat
    # readMipmapBytes: bool = True  # variable not used
    decompressMipmapBytes: bool = True
    mipmaps: List[TexMipmap] = field(default_factory=list)

    @property
    def firstMipmap(self):
        return self.mipmaps[0]

    def read(self):
        mipmapCount = read_n_bytes(self._fd)
        read_func = self.pickMipmapReader(self._container.ImageContainerVersion)
        mipmapFormat = extensions.getFormatForTex(
            self._container.ImageFormat, self._texFormat
        )
        for i in range(mipmapCount):
            mipmap = read_func(self._fd)
            mipmap.format = mipmapFormat
            if self.decompressMipmapBytes:  # redundant condition
                decompressMipmap(mipmap)
            self.mipmaps.append(mipmap)

    @staticmethod
    def readMipmapV1(fd: Union[BinaryIO, BytesIO]):
        return TexMipmap(
            width=read_n_bytes(fd),
            height=read_n_bytes(fd),
            data=TexImage.readBytes(fd),
            isLZ4Compressed=False,
        )

    @staticmethod
    def readMipmapV2AndV3(fd: Union[BinaryIO, BytesIO]):
        return TexMipmap(
            width=read_n_bytes(fd),
            height=read_n_bytes(fd),
            isLZ4Compressed=read_n_bytes(fd) == 1,
            decompressedBytesCount=read_n_bytes(fd),
            data=TexImage.readBytes(fd),
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
