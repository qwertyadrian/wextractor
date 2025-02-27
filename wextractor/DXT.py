"""
S3TC DXT1/DXT3/DXT5 Texture Decompression

Original C# code:
https://github.com/notscuffed/repkg/blob/master/RePKG.Application/Texture/Helpers/DXT.cs
"""
from .enums import DXTFlags


def unpack565(
    block: bytes,
    block_index: int,
    packed_offset: int,
    colour: bytearray,
    colour_offset: int,
):
    # Build packed value
    value = block[block_index + packed_offset] | (
            block[block_index + 1 + packed_offset] << 8
    )

    # get components in the stored range
    red = (value >> 11) & 0x1F
    green = (value >> 5) & 0x3F
    blue = value & 0x1F

    # Scale up to 8 Bit
    colour[0 + colour_offset] = (red << 3) | (red >> 2)
    colour[1 + colour_offset] = (green << 2) | (green >> 4)
    colour[2 + colour_offset] = (blue << 3) | (blue >> 2)
    colour[3 + colour_offset] = 255

    return value


def decompress_color(rgba: bytearray, block: bytes, block_index: int, is_dxt1: bool):
    # Unpack Endpoints
    codes = bytearray(16)
    a = unpack565(block, block_index, 0, codes, 0)
    b = unpack565(block, block_index, 2, codes, 4)

    # generate Midpoints
    for i in range(3):
        c = codes[i]
        d = codes[4 + i]

        if is_dxt1 and a <= b:
            codes[8 + i] = (c + d) // 2
            codes[12 + i] = 0
        else:
            codes[8 + i] = (2 * c + d) // 3
            codes[12 + i] = (c + 2 * d) // 3

        # Fill in alpha for intermediate values
        codes[8 + 3] = 255
        codes[12 + 3] = 0 if (is_dxt1 and a <= b) else 255

        # unpack the indices
        indices = bytearray(16)
        for i in range(3):
            packed = block[block_index + 4 + i]
            indices[0 + i * 4] = packed & 0x3
            indices[1 + i * 4] = (packed >> 2) & 0x3
            indices[2 + i * 4] = (packed >> 4) & 0x3
            indices[3 + i * 4] = (packed >> 6) & 0x3

        # store out the colours
        for i in range(16):
            offset = 4 * indices[i]
            rgba[4 * i:4 * i + 4] = codes[offset:offset + 4]


def decompress_alpha_dxt3(rgba: bytearray, block: bytes, block_index: int):
    # Unpack the alpha values pairwise
    for i in range(8):
        # Quantise down to 4 bits
        quant = block[block_index + i]

        lo = quant & 0x0F
        hi = quant & 0xF0

        # Convert back up to bytes
        rgba[8 * i + 3] = lo | (lo << 4)
        rgba[8 * i + 7] = hi | (hi >> 4)


def decompress_alpha_dxt5(rgba: bytearray, block: bytes, block_index: int):
    # Get the two alpha values
    alpha0 = block[block_index + 0]
    alpha1 = block[block_index + 1]

    # compare the values to build the codebook
    codes = bytearray(8)
    codes[0] = alpha0
    codes[1] = alpha1
    if alpha0 <= alpha1:
        # Use 5-Alpha Codebook
        for i in range(1, 5):
            codes[1 + i] = ((5 - i) * alpha0 + i * alpha1) // 5
            codes[6] = 0
            codes[7] = 255
    else:
        # Use 7-Alpha Codebook
        for i in range(1, 7):
            codes[i + 1] = ((7 - i) * alpha0 + i * alpha1) // 7

    # decode indices
    indices = bytearray(16)
    block_src_pos = 2
    indices_pos = 0
    for i in range(2):
        # grab 3 bytes
        value = 0
        for j in range(3):
            value |= block[block_index + block_src_pos] << (8 * j)
            block_src_pos += 1

        # unpack 8 3-bit values from it
        for j in range(8):
            index = (value >> 3 * j) & 0x07
            indices[indices_pos] = index
            indices_pos += 1

    # write out the indexed codebook values
    for i in range(16):
        rgba[4 * i + 3] = codes[indices[i]]


def decompress(rgba: bytearray, block: bytes, block_index: int, flags: DXTFlags):
    # get the block locations
    color_block_index = block_index

    if flags & (DXTFlags.DXT3 | DXTFlags.DXT5):
        color_block_index += 8

    # decompress color
    decompress_color(rgba, block, color_block_index, (flags & DXTFlags.DXT1) != 0)

    # decompress alpha separately if necessary
    if flags & DXTFlags.DXT3:
        decompress_alpha_dxt3(rgba, block, block_index)
    elif flags & DXTFlags.DXT5:
        decompress_alpha_dxt5(rgba, block, block_index)


def decompress_image(width: int, height: int, data: bytes, flags: DXTFlags) -> bytearray:
    rgba = bytearray(width * height * 4)

    # initialise the block input
    source_block_pos: int = 0
    bytes_per_block: int = 8 if flags & DXTFlags.DXT1 else 16
    target_rgba = bytearray(4 * 16)

    # loop over blocks
    for y in range(0, height, 4):
        for x in range(0, width, 4):
            # decompress the block
            target_rgba_pos = 0
            if len(data) == source_block_pos:
                continue

            decompress(target_rgba, data, source_block_pos, flags)

            # Write the decompressed pixels to the correct image locations
            for py in range(4):
                for px in range(4):
                    sx = x + px
                    sy = y + py
                    if sx < width and sy < height:
                        target_pixel = 4 * (width * sy + sx)
                        rgba[target_pixel:target_pixel + 4] = target_rgba[target_rgba_pos:target_rgba_pos + 4]
                        target_rgba_pos += 4
                    else:
                        # Ignore that pixel
                        target_rgba_pos += 4

            source_block_pos += bytes_per_block

    return rgba
