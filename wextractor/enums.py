from enum import Enum, IntFlag, auto


class TexFormat(Enum):
    RGBA8888 = 0
    DXT5 = 4
    DXT3 = 6
    DXT1 = 7
    RG88 = 8
    R8 = 9


class TexFlags(IntFlag):
    NONE = 0
    NoInterpolation = 1
    ClampUVs = 2
    IsGif = 4
    # Placeholders
    Unk3 = 8
    Unk4 = 16
    IsVideoTexture = 32
    Unk6 = 64
    Unk7 = 128


class FreeImageFormat(Enum):
    # Unknown format (returned value only never use it as input value)
    FIF_UNKNOWN = -1
    # Windows or OS/2 Bitmap File (*.BMP)
    FIF_BMP = 0
    # Windows Icon (*.ICO)
    FIF_ICO = 1
    # Independent JPEG Group (*.JPG *.JIF *.JPEG *.JPE)
    FIF_JPEG = 2
    # JPEG Network Graphics (*.JNG)
    FIF_JNG = 3
    # Commodore 64 Koala format (*.KOA)
    FIF_KOALA = 4
    # Amiga IFF (*.IFF *.LBM)
    FIF_LBM = 5
    # Amiga IFF (*.IFF *.LBM)
    FIF_IFF = 5
    # Multiple Network Graphics (*.MNG)
    FIF_MNG = 6
    # Portable Bitmap (ASCII) (*.PBM)
    FIF_PBM = 7
    # Portable Bitmap (BINARY) (*.PBM)
    FIF_PBMRAW = 8
    # Kodak PhotoCD (*.PCD)
    FIF_PCD = 9
    # Zsoft Paintbrush PCX bitmap format (*.PCX)
    FIF_PCX = 10
    # Portable Graymap (ASCII) (*.PGM)
    FIF_PGM = 11
    # Portable Graymap (BINARY) (*.PGM)
    FIF_PGMRAW = 12
    # Portable Network Graphics (*.PNG)
    FIF_PNG = 13
    # Portable Pixelmap (ASCII) (*.PPM)
    FIF_PPM = 14
    # Portable Pixelmap (BINARY) (*.PPM)
    FIF_PPMRAW = 15
    # Sun Rasterfile (*.RAS)
    FIF_RAS = 16
    # truevision Targa files (*.TGA *.TARGA)
    FIF_TARGA = 17
    # Tagged Image File Format (*.TIF *.TIFF)
    FIF_TIFF = 18
    # Wireless Bitmap (*.WBMP)
    FIF_WBMP = 19
    # Adobe Photoshop (*.PSD)
    FIF_PSD = 20
    # Dr. Halo (*.CUT)
    FIF_CUT = 21
    # X11 Bitmap Format (*.XBM)
    FIF_XBM = 22
    # X11 Pixmap Format (*.XPM)
    FIF_XPM = 23
    # DirectDraw Surface (*.DDS)
    FIF_DDS = 24
    # Graphics Interchange Format (*.GIF)
    FIF_GIF = 25
    # High Dynamic Range (*.HDR)
    FIF_HDR = 26
    # Raw Fax format CCITT G3 (*.G3)
    FIF_FAXG3 = 27
    # Silicon Graphics SGI image format (*.SGI)
    FIF_SGI = 28
    # OpenEXR format (*.EXR)
    FIF_EXR = 29
    # JPEG-2000 format (*.J2K *.J2C)
    FIF_J2K = 30
    # JPEG-2000 format (*.JP2)
    FIF_JP2 = 31
    # Portable FloatMap (*.PFM)
    FIF_PFM = 32
    # Macintosh PICT (*.PICT)
    FIF_PICT = 33
    # RAW camera image (*.*)
    FIF_RAW = 34


class MipmapFormat(Enum):
    def is_image(self, mipmap_format):
        return mipmap_format.value >= self.ImageBMP.value

    def is_raw(self):
        return self.RGBA8888.value <= self.value <= self.RG88.value

    # Invalid format
    Invalid = 0
    # Raw pixels (4 bytes per pixel) (RGBA8888)
    RGBA8888 = 1
    # Raw pixels (1 byte per pixel) (R8)
    R8 = 2
    # Raw pixels (2 bytes per pixel) (RG88)
    RG88 = 3
    # Raw pixels compressed using DXT5 -> decompressing in RGBA8888
    CompressedDXT5 = auto()
    # Raw pixels compressed using DXT3 -> decompressing in RGBA8888
    CompressedDXT3 = auto()
    # Raw pixels compressed using DXT1 -> decompressing in RGBA8888
    CompressedDXT1 = auto()
    # MP4 Video
    VideoMP4 = auto()
    # Windows or OS/2 Bitmap File (*.BMP)
    # Keep '= 1000' because MipmapFormatExtensions.IsImage uses this to check if format is an image format
    ImageBMP = 1000
    # Windows Icon (*.ICO)
    ImageICO = auto()
    # Independent JPEG Group (*.JPG *.JIF *.JPEG *.JPE)
    ImageJPEG = auto()
    # JPEG Network Graphics (*.JNG)
    ImageJNG = auto()
    # Commodore 64 Koala format (*.KOA)
    ImageKOALA = auto()
    # Amiga IFF (*.IFF *.LBM)
    ImageLBM = auto()
    # Amiga IFF (*.IFF *.LBM)
    ImageIFF = auto()
    # Multiple Network Graphics (*.MNG)
    ImageMNG = auto()
    # Portable Bitmap (ASCII) (*.PBM)
    ImagePBM = auto()
    # Portable Bitmap (BINARY) (*.PBM)
    ImagePBMRAW = auto()
    # Kodak PhotoCD (*.PCD)
    ImagePCD = auto()
    # Zsoft Paintbrush PCX bitmap format (*.PCX)
    ImagePCX = auto()
    # Portable Graymap (ASCII) (*.PGM)
    ImagePGM = auto()
    # Portable Graymap (BINARY) (*.PGM)
    ImagePGMRAW = auto()
    # Portable Network Graphics (*.PNG)
    ImagePNG = auto()
    # Portable Pixelmap (ASCII) (*.PPM)
    ImagePPM = auto()
    # Portable Pixelmap (BINARY) (*.PPM)
    ImagePPMRAW = auto()
    # Sun Rasterfile (*.RAS)
    ImageRAS = auto()
    # truevision Targa files (*.TGA *.TARGA)
    ImageTARGA = auto()
    # Tagged Image File Format (*.TIF *.TIFF)
    ImageTIFF = auto()
    # Wireless Bitmap (*.WBMP)
    ImageWBMP = auto()
    # Adobe Photoshop (*.PSD)
    ImagePSD = auto()
    # Dr. Halo (*.CUT)
    ImageCUT = auto()
    # X11 Bitmap Format (*.XBM)
    ImageXBM = auto()
    # X11 Pixmap Format (*.XPM)
    ImageXPM = auto()
    # DirectDraw Surface (*.DDS)
    ImageDDS = auto()
    # Graphics Interchange Format (*.GIF)
    ImageGIF = auto()
    # High Dynamic Range (*.HDR)
    ImageHDR = auto()
    # Raw Fax format CCITT G3 (*.G3)
    ImageFAXG3 = auto()
    # Silicon Graphics SGI image format (*.SGI)
    ImageSGI = auto()
    # OpenEXR format (*.EXR)
    ImageEXR = auto()
    # JPEG-2000 format (*.J2K *.J2C)
    ImageJ2K = auto()
    # JPEG-2000 format (*.JP2)
    ImageJP2 = auto()
    # Portable FloatMap (*.PFM)
    ImagePFM = auto()
    # Macintosh PICT (*.PICT)
    ImagePICT = auto()
    # RAW camera image (*.*)
    ImageRAW = auto()


class TexImageContainerVersion(Enum):
    Version1 = 1
    Version2 = 2
    Version3 = 3


class DXTFlags(IntFlag):
    DXT1 = 1
    DXT3 = 1 << 1
    DXT5 = 1 << 2
