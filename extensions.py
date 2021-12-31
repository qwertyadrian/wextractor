from io import BytesIO
from typing import Union, BinaryIO
import struct

from enums import FreeImageFormat, TexFormat, MipmapFormat


def isValidFormat(enum: Union[TexFormat, FreeImageFormat]):
    if isinstance(enum, FreeImageFormat):
        return -1 <= enum.value <= 34
    else:
        match enum:
            case (
                TexFormat.RGBA8888
                | TexFormat.DXT5
                | TexFormat.DXT3
                | TexFormat.DXT1
                | TexFormat.RG88
                | TexFormat.R8
            ):
                return True
            case _:
                return False


def readNBytes(fd: Union[BinaryIO, BytesIO], fmt: str = "<i"):
    size = struct.calcsize(fmt)
    data = struct.unpack(fmt, fd.read(size))
    if len(data) == 1:
        return data[0]
    else:
        return data


def getFormatForTex(imageFormat: FreeImageFormat, texFormat: TexFormat) -> MipmapFormat:
    if imageFormat != FreeImageFormat.FIF_UNKNOWN:
        return freeImageFormatToMipmapFormat(imageFormat)

    match texFormat:
        case TexFormat.RGBA8888:
            return MipmapFormat.RGBA8888
        case TexFormat.DXT5:
            return MipmapFormat.CompressedDXT5
        case TexFormat.DXT3:
            return MipmapFormat.CompressedDXT3
        case TexFormat.DXT1:
            return MipmapFormat.CompressedDXT1
        case TexFormat.R8:
            return MipmapFormat.R8
        case TexFormat.RG88:
            return MipmapFormat.RG88
        case _:
            raise Exception("Argument out of range")


def freeImageFormatToMipmapFormat(freeImageFormat) -> MipmapFormat:
    match freeImageFormat:
        case FreeImageFormat.FIF_UNKNOWN:
            raise Exception(f"Can't convert {freeImageFormat} to MipmapFormat")
        case FreeImageFormat.FIF_BMP:
            return MipmapFormat.ImageBMP

        case FreeImageFormat.FIF_ICO:
            return MipmapFormat.ImageICO

        case FreeImageFormat.FIF_JPEG:
            return MipmapFormat.ImageJPEG

        case FreeImageFormat.FIF_JNG:
            return MipmapFormat.ImageJNG

        case FreeImageFormat.FIF_KOALA:
            return MipmapFormat.ImageKOALA

        case FreeImageFormat.FIF_LBM:
            return MipmapFormat.ImageLBM

        case FreeImageFormat.FIF_MNG:
            return MipmapFormat.ImageMNG

        case FreeImageFormat.FIF_PBM:
            return MipmapFormat.ImagePBM

        case FreeImageFormat.FIF_PBMRAW:
            return MipmapFormat.ImagePBMRAW

        case FreeImageFormat.FIF_PCD:
            return MipmapFormat.ImagePCD

        case FreeImageFormat.FIF_PCX:
            return MipmapFormat.ImagePCX

        case FreeImageFormat.FIF_PGM:
            return MipmapFormat.ImagePGM

        case FreeImageFormat.FIF_PGMRAW:
            return MipmapFormat.ImagePGMRAW

        case FreeImageFormat.FIF_PNG:
            return MipmapFormat.ImagePNG

        case FreeImageFormat.FIF_PPM:
            return MipmapFormat.ImagePPM

        case FreeImageFormat.FIF_PPMRAW:
            return MipmapFormat.ImagePPMRAW

        case FreeImageFormat.FIF_RAS:
            return MipmapFormat.ImageRAS

        case FreeImageFormat.FIF_TARGA:
            return MipmapFormat.ImageTARGA

        case FreeImageFormat.FIF_TIFF:
            return MipmapFormat.ImageTIFF

        case FreeImageFormat.FIF_WBMP:
            return MipmapFormat.ImageWBMP

        case FreeImageFormat.FIF_PSD:
            return MipmapFormat.ImagePSD

        case FreeImageFormat.FIF_CUT:
            return MipmapFormat.ImageCUT

        case FreeImageFormat.FIF_XBM:
            return MipmapFormat.ImageXBM

        case FreeImageFormat.FIF_XPM:
            return MipmapFormat.ImageXPM

        case FreeImageFormat.FIF_DDS:
            return MipmapFormat.ImageDDS

        case FreeImageFormat.FIF_GIF:
            return MipmapFormat.ImageGIF

        case FreeImageFormat.FIF_HDR:
            return MipmapFormat.ImageHDR

        case FreeImageFormat.FIF_FAXG3:
            return MipmapFormat.ImageFAXG3

        case FreeImageFormat.FIF_SGI:
            return MipmapFormat.ImageSGI

        case FreeImageFormat.FIF_EXR:
            return MipmapFormat.ImageEXR

        case FreeImageFormat.FIF_J2K:
            return MipmapFormat.ImageJ2K

        case FreeImageFormat.FIF_JP2:
            return MipmapFormat.ImageJP2

        case FreeImageFormat.FIF_PFM:
            return MipmapFormat.ImagePFM

        case FreeImageFormat.FIF_PICT:
            return MipmapFormat.ImagePICT

        case FreeImageFormat.FIF_RAW:
            return MipmapFormat.ImageRAW

        case _:
            raise Exception("Argument out of range")


def getFileExtension(imageFormat: MipmapFormat) -> str:
    match imageFormat:
        case MipmapFormat.ImageBMP:
            return "bmp"
        case MipmapFormat.ImageICO:
            return "ico"
        case MipmapFormat.ImageJPEG:
            return "jpg"
        case MipmapFormat.ImageJNG:
            return "jng"
        case MipmapFormat.ImageKOALA:
            return "koa"
        case MipmapFormat.ImageLBM:
            return "lbm"
        case MipmapFormat.ImageIFF:
            return "iff"
        case MipmapFormat.ImageMNG:
            return "mng"
        case MipmapFormat.ImagePBM | MipmapFormat.ImagePBMRAW:
            return "pbm"
        case MipmapFormat.ImagePCD:
            return "pcd"
        case MipmapFormat.ImagePCX:
            return "pcx"
        case MipmapFormat.ImagePGM | MipmapFormat.ImagePGMRAW:
            return "pgm"
        case MipmapFormat.ImagePNG:
            return "png"
        case MipmapFormat.ImagePPM | MipmapFormat.ImagePPMRAW:
            return "ppm"
        case MipmapFormat.ImageRAS:
            return "ras"
        case MipmapFormat.ImageTARGA:
            return "tga"
        case MipmapFormat.ImageTIFF:
            return "tif"
        case MipmapFormat.ImageWBMP:
            return "wbmp"
        case MipmapFormat.ImagePSD:
            return "psd"
        case MipmapFormat.ImageCUT:
            return "cut"
        case MipmapFormat.ImageXBM:
            return "xbm"
        case MipmapFormat.ImageXPM:
            return "xpm"
        case MipmapFormat.ImageDDS:
            return "dds"
        case MipmapFormat.ImageGIF:
            return "gif"
        case MipmapFormat.ImageHDR:
            return "hdr"
        case MipmapFormat.ImageFAXG3:
            return "g3"
        case MipmapFormat.ImageSGI:
            return "sgi"
        case MipmapFormat.ImageEXR:
            return "exr"
        case MipmapFormat.ImageJ2K:
            return "j2k"
        case MipmapFormat.ImageJP2:
            return "jp2"
        case MipmapFormat.ImagePFM:
            return "pfm"
        case MipmapFormat.ImagePICT:
            return "pict"
        case MipmapFormat.ImageRAW:
            return "raw"
        case _:
            return "png"
