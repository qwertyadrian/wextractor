"""
S3TC DXT1/DXT3/DXT5 Texture Decompression

Original C# code:
https://github.com/notscuffed/repkg/blob/master/RePKG.Application/Texture/Helpers/DXT.cs
"""
from enums import DXTFlags


def unpack565(block: bytes, blockIndex: int, packedOffset: int, colour: bytearray, colourOffset: int):
    # Build packed value
    value = block[blockIndex + packedOffset] | (block[blockIndex + 1 + packedOffset] << 8)

    # get components in the stored range
    red = (value >> 11) & 0x1F
    green = (value >> 5) & 0x3F
    blue = (value & 0x1F)

    # Scale up to 8 Bit
    colour[0 + colourOffset] = (red << 3) | (red >> 2)
    colour[1 + colourOffset] = (green << 2) | (green >> 4)
    colour[2 + colourOffset] = (blue << 3) | (blue >> 2)
    colour[3 + colourOffset] = 255

    return value


def decompressColor(rgba: bytearray, block: bytes, blockIndex: int, isDxt1: bool):
    # Unpack Endpoints
    codes = bytearray(16)
    a = unpack565(block, blockIndex, 0, codes, 0)
    b = unpack565(block, blockIndex, 2, codes, 4)

    # generate Midpoints
    for i in range(3):
        c = codes[i]
        d = codes[4 + i]

        if isDxt1 and a <= b:
            codes[8 + i] = (c + d) // 2
            codes[12 + i] = 0
        else:
            codes[8 + i] = (2 * c + d) // 3
            codes[12 + i] = (c + 2 * d) // 3

        # Fill in alpha for intermediate values
        codes[8 + 3] = 255
        codes[12 + 3] = 0 if (isDxt1 and a <= b) else 255

        # unpack the indices
        indices = bytearray(16)
        for i in range(3):
            packed = block[blockIndex + 4 + i]
            indices[0 + i * 4] = packed & 0x3
            indices[1 + i * 4] = (packed >> 2) & 0x3
            indices[2 + i * 4] = (packed >> 4) & 0x3
            indices[3 + i * 4] = (packed >> 6) & 0x3

        # store out the colours
        for i in range(16):
            offset = 4 * indices[i]
            rgba[4 * i + 0] = codes[offset + 0]
            rgba[4 * i + 1] = codes[offset + 1]
            rgba[4 * i + 2] = codes[offset + 2]
            rgba[4 * i + 3] = codes[offset + 3]


def decompressAlphaDxt3(rgba: bytearray, block: bytes, blockIndex: int):
    # Unpack the alpha values pairwise
    for i in range(8):
        # Quantise down to 4 bits
        quant = block[blockIndex + i]

        lo = quant & 0x0F
        hi = quant & 0xF0

        # Convert back up to bytes
        rgba[8 * i + 3] = lo | (lo << 4)
        rgba[8 * i + 7] = hi | (hi >> 4)


def decompressAlphaDxt5(rgba: bytearray, block: bytes, blockIndex: int):
    # Get the two alpha values
    alpha0 = block[blockIndex + 0]
    alpha1 = block[blockIndex + 1]

    # compare the values to build the codebook
    codes = bytearray(8)
    codes[0] = alpha0
    codes[1] = alpha1
    if alpha0 <= alpha1:
        # Use 5-Alpha Codebook
        for i in range(5):
            codes[1 + i] = ((5 - i) * alpha0 + i * alpha1) // 5
            codes[6] = 0
            codes[7] = 255
    else:
        # Use 7-Alpha Codebook
        for i in range(5):
            codes[i + 1] = ((7 - i) * alpha0 + i * alpha1) // 7

    # decode indices
    indices = bytearray(16)
    blockSrc_pos = 2
    indices_pos = 0
    for i in range(2):
        # grab 3 bytes
        value = 0
        for j in range(3):
            byte = block[blockIndex + blockSrc_pos]
            blockSrc_pos += 1
            value |= byte << 8 * j

        # unpack 8 3-bit values from it
        for j in range(8):
            index = (value >> 3 * j) & 0x07
            indices[indices_pos] = index
            indices_pos += 1

    # write out the indexed codebook values
    for i in range(16):
        rgba[4 * i + 3] = codes[indices[i]]


def decompress(rgba: bytearray, block: bytes, blockIndex: int, flags: DXTFlags):
    # get the block locations
    colorBlockIndex = blockIndex

    if (flags & (DXTFlags.DXT3 | DXTFlags.DXT5)) != 0:
        colorBlockIndex += 8

    # decompress color
    decompressColor(rgba, block, colorBlockIndex, (flags & DXTFlags.DXT1) != 0)

    # decompress alpha separately if necessary
    if (flags & DXTFlags.DXT3) != 0:
        decompressAlphaDxt3(rgba, block, blockIndex)
    elif (flags & DXTFlags.DXT5) != 0:
        decompressAlphaDxt5(rgba, block, blockIndex)
    

def decompressImage(width: int, height: int, data: bytes, flags: DXTFlags):
    rgba = bytearray(width * height * 4)

    # initialise the block input
    sourceBlock_pos: int = 0
    bytesPerBlock: int = 8 if (flags & DXTFlags.DXT1) != 0 else 16
    targetRGBA = bytearray(4 * 16)

    # loop over blocks
    for y in range(0, height, 4):
        for x in range(0, width, 4):
            # decompress the block
            targetRGBA_pos = 0
            if len(data) == sourceBlock_pos:
                continue

            decompress(targetRGBA, data, sourceBlock_pos, flags)

            # Write the decompressed pixels to the correct image locations
            for py in range(4):
                for px in range(4):
                    sx = x + px
                    sy = y + py
                    if sx < width and sy < height:
                        targetPixel = 4 * (width * sy + sx)
                        rgba[targetPixel + 0] = targetRGBA[targetRGBA_pos + 0]
                        rgba[targetPixel + 1] = targetRGBA[targetRGBA_pos + 1]
                        rgba[targetPixel + 2] = targetRGBA[targetRGBA_pos + 2]
                        rgba[targetPixel + 3] = targetRGBA[targetRGBA_pos + 3]
                        targetRGBA_pos += 4
                    else:
                        # Ignore that pixel
                        targetRGBA_pos += 4

            sourceBlock_pos += bytesPerBlock
            
    return rgba

