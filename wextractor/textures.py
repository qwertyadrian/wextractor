from dataclasses import dataclass, field
from io import BytesIO
from math import atan2, copysign, degrees, pi
from pathlib import Path
from typing import BinaryIO, List, Union, Callable

from PIL import Image as Img
from PIL import UnidentifiedImageError
from PIL.Image import Image

from . import enums
from .decompress import decompress_mipmap
from .exceptions import InvalidContainerVersion, InvalidTextureFormat, UnknownMagicError
from .extensions import get_format_for_tex, is_valid_format, read_n_bytes


@dataclass
class TexMipmap:
    data: bytes = field(repr=False)
    width: int
    height: int
    is_lz4_compressed: bool = False
    decompressed_bytes_count: int = 0
    format: enums.MipmapFormat = enums.MipmapFormat.Invalid

    def get_bytes_stream(self) -> BytesIO:
        return BytesIO(self.data)


@dataclass
class TexImageContainer:
    magic: str
    images: List["TexImage"] = field(default_factory=list)
    version: enums.TexImageContainerVersion = None
    format: enums.FreeImageFormat = enums.FreeImageFormat.FIF_UNKNOWN

    @property
    def first_image(self) -> "TexImage":
        return self.images[0]


@dataclass
class TexFrameInfo:
    image_id: int
    frame_time: float
    x: float
    y: float
    width: float
    width_y: float
    height_x: float
    height: float


@dataclass
class TexFrameInfoContainer:
    _fd: Union[BinaryIO, BytesIO]
    magic: str = ""
    frames: List[TexFrameInfo] = field(default_factory=list)
    gif_width: int = 0
    gif_height: int = 0

    def read(self):
        self.magic = read_n_bytes(self._fd, "<8sx").decode()
        frames_count = read_n_bytes(self._fd)

        match self.magic:
            case "TEXS0001":
                for i in range(frames_count):
                    data = read_n_bytes(self._fd, "<if6i")
                    self.frames.append(TexFrameInfo(*data))
            case "TEXS0002":
                for i in range(frames_count):
                    data = read_n_bytes(self._fd, "<i7f")
                    self.frames.append(TexFrameInfo(*data))
            case "TEXS0003":
                self.gif_width, self.gif_height = read_n_bytes(self._fd, "<2i")
                for i in range(frames_count):
                    data = read_n_bytes(self._fd, "<i7f")
                    self.frames.append(TexFrameInfo(*data))
            case _:
                raise UnknownMagicError(self.magic)

        if self.gif_width == 0 or self.gif_height == 0:
            self.gif_width = int(self.first_frame.width)
            self.gif_height = int(self.first_frame.height)

    @property
    def first_frame(self) -> TexFrameInfo:
        return self.frames[0]


class Texture:
    # equal to char[8], pad byte, char[8], pad byte and 7 int
    # in little-endian byte order
    HEADER_STRUCT = "<8sx8sx7i"

    def __init__(self, file: Union[str, bytes, BinaryIO, BytesIO]):
        if isinstance(file, str):
            self._fd: BinaryIO = open(file, "r+b")
        elif isinstance(file, bytes):
            self._fd: BytesIO = BytesIO(file)
        else:
            self._fd = file
        self._read_header()
        self._read_image_container()

        if self.is_gif:
            self.frame_info_container = TexFrameInfoContainer(self._fd)
            self.frame_info_container.read()

    def _read_header(self):
        data = read_n_bytes(self._fd, self.HEADER_STRUCT)

        self._magic1 = data[0].decode()
        self._magic2 = data[1].decode()
        if self._magic1 != "TEXV0005" or self._magic2 != "TEXI0001":
            raise UnknownMagicError("Incorrect magic value")
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
        self.images_container = TexImageContainer(
            magic=read_n_bytes(self._fd, "<8sx").decode()
        )
        image_count = read_n_bytes(self._fd)

        match self.images_container.magic:
            case "TEXB0001" | "TEXB0002":
                pass
            case "TEXB0003":
                try:
                    self.images_container.format = enums.FreeImageFormat(
                        read_n_bytes(self._fd)
                    )
                except ValueError:
                    self.images_container.format = enums.FreeImageFormat.FIF_UNKNOWN
            case _:
                raise UnknownMagicError(self.images_container.magic)

        self.images_container.version = enums.TexImageContainerVersion(
            int(self.images_container.magic[4:])
        )

        if not is_valid_format(self.images_container.format):
            raise InvalidTextureFormat()

        for i in range(image_count):
            reader = TexImage(self._fd, self.images_container, self.format)
            reader.read()
            self.images_container.images.append(reader)

    def save(self, path: Union[Path, str] = ""):
        path = Path(path)

        if self.is_gif:
            frames: list[Image] = list()
            for frame in self.frame_info_container.frames:
                width = frame.width if frame.width != 0 else frame.height_x
                height = frame.height if frame.height != 0 else frame.width_y
                x = min(frame.x, frame.x + width)
                y = min(frame.y, frame.y + height)

                rotation_angle = -(
                    degrees(atan2(copysign(1, height), copysign(1, width)) - pi / 4)
                )

                image = self._create_image(
                    self.images_container.first_image.first_mipmap
                )

                frames.insert(
                    frame.image_id,
                    image.crop(
                        (int(x), int(y), int(abs(width) + x), int(abs(height) + y))
                    ).rotate(rotation_angle),
                )
            # ignoring last black frame
            frames[0].save(
                path,
                save_all=True,
                append_images=frames[1:-1],
                duration=self.frame_info_container.first_frame.frame_time,
                loop=0,
            )
            return

        if self.images_container.format == enums.FreeImageFormat.FIF_UNKNOWN:
            if (
                self.images_container.first_image.first_mipmap.format
                == enums.MipmapFormat.RGBA8888
            ):
                self._create_image(self.images_container.first_image.first_mipmap).crop(
                    (0, 0, self.imageWidth, self.imageHeight)
                ).save(path)
            elif self.images_container.first_image.first_mipmap.format in (
                enums.MipmapFormat.R8,
                enums.MipmapFormat.RG88,
            ):
                self._create_image(
                    self.images_container.first_image.first_mipmap, "L"
                ).crop((0, 0, self.imageWidth, self.imageHeight)).save(path)
            else:
                raise InvalidTextureFormat("Unable to save compressed data")
        else:
            Img.open(
                self.images_container.first_image.first_mipmap.get_bytes_stream()
            ).save(path)

    @staticmethod
    def _create_image(mipmap: TexMipmap, mode: str = "RGBA") -> Image:
        try:
            return Img.open(BytesIO(mipmap.data))
        except UnidentifiedImageError:
            return Img.frombuffer(
                mode, (mipmap.width, mipmap.height), mipmap.data, "raw", mode, 0, 1
            )

    @property
    def is_gif(self) -> bool:
        return self.has_flag(enums.TexFlags.IsGif)

    @property
    def is_video_texture(self) -> bool:
        return self.has_flag(enums.TexFlags.IsVideoTexture)

    def has_flag(self, flag: enums.TexFlags) -> bool:
        return (self.flags & flag) == flag


@dataclass
class TexImage:
    _fd: Union[BinaryIO, BytesIO]
    _container: TexImageContainer
    _tex_format: enums.TexFormat
    # readMipmapBytes: bool = True  # variable not used
    decompress_mipmap_bytes: bool = True
    mipmaps: List[TexMipmap] = field(default_factory=list)

    @property
    def first_mipmap(self):
        return self.mipmaps[0]

    def read(self):
        mipmap_count = read_n_bytes(self._fd)
        read_func = self.pick_mipmap_reader(self._container.version)
        mipmap_format = get_format_for_tex(self._container.format, self._tex_format)
        for i in range(mipmap_count):
            mipmap = read_func(self._fd)
            mipmap.format = mipmap_format
            if self.decompress_mipmap_bytes:  # redundant condition
                decompress_mipmap(mipmap)
            self.mipmaps.append(mipmap)

    @staticmethod
    def read_mipmap_v1(fd: Union[BinaryIO, BytesIO]):
        return TexMipmap(
            width=read_n_bytes(fd),
            height=read_n_bytes(fd),
            data=TexImage.read_bytes(fd),
            is_lz4_compressed=False,
        )

    @staticmethod
    def read_mipmap_v2_and_v3(fd: Union[BinaryIO, BytesIO]):
        return TexMipmap(
            width=read_n_bytes(fd),
            height=read_n_bytes(fd),
            is_lz4_compressed=read_n_bytes(fd) == 1,
            decompressed_bytes_count=read_n_bytes(fd),
            data=TexImage.read_bytes(fd),
        )

    @staticmethod
    def read_bytes(fd: Union[BinaryIO, BytesIO]):
        byte_count = read_n_bytes(fd)
        bytes_read = fd.read(byte_count)
        if len(bytes_read) != byte_count:
            raise ValueError("Failed to read bytes from stream while reading mipmap")
        return bytes_read

    @staticmethod
    def pick_mipmap_reader(version: enums.TexImageContainerVersion) -> Callable:
        match version:
            case enums.TexImageContainerVersion.Version1:
                return TexImage.read_mipmap_v1
            case (
                enums.TexImageContainerVersion.Version2
                | enums.TexImageContainerVersion.Version3
            ):
                return TexImage.read_mipmap_v2_and_v3
            case _:
                raise InvalidContainerVersion()
