from .enums import DXTFlags
import numpy as np


def decompress_image(width: int, height: int, data: bytes, format_type: DXTFlags) -> bytes:
    """
    Decompress headerless DXT/S3TC compressed texture data

    :param width: Width of the texture
    :param height: Height of the texture
    :param data: Raw compressed bytes or bytearray
    :param format_type: DXT format type (DXT1, DXT3, DXT5)
    :return: Decompressed pixel data as bytes

    """
    # Calculate block size and bytes per block based on format
    if format_type == DXTFlags.DXT1:
        block_size = 8  # 8 bytes per 4x4 pixel block
        has_alpha = False
    elif format_type == DXTFlags.DXT3 or format_type == DXTFlags.DXT5:
        block_size = 16  # 16 bytes per 4x4 pixel block
        has_alpha = True
    else:
        raise ValueError(f"Unsupported format: {format_type}")

    # Calculate number of blocks and expected data size
    blocks_width = (width + 3) // 4  # Integer division, rounding up
    blocks_height = (height + 3) // 4
    expected_size = blocks_width * blocks_height * block_size

    if len(data) < expected_size:
        raise ValueError(f"Data size mismatch: expected at least {expected_size} bytes, got {len(data)}")

    # Prepare array for decompressed pixels
    channels = 4 if has_alpha else 3
    pixels = np.zeros((height, width, channels), dtype=np.uint8)

    # Process each 4x4 block
    block_idx = 0
    for by in range(blocks_height):
        for bx in range(blocks_width):
            offset = block_idx * block_size
            block_data = data[offset:offset + block_size]

            # Get the coordinates for this block
            x = bx * 4
            y = by * 4

            # Decompress this block and place in the pixel array
            match format_type:
                case DXTFlags.DXT1:
                    _decompress_dxt1_block(block_data, pixels, x, y, width, height)
                case DXTFlags.DXT3:
                    _decompress_dxt3_block(block_data, pixels, x, y, width, height)
                case DXTFlags.DXT5:
                    _decompress_dxt5_block(block_data, pixels, x, y, width, height)

            block_idx += 1

    if has_alpha:
        return pixels.tobytes()
    else:
        # If DXT1 with no alpha, convert to RGB
        return pixels[:, :, :3].tobytes()


def _decompress_dxt1_block(block_data, pixels, x, y, width, height):
    """
    Decompress a DXT1 block (8 bytes total)

    Format:
    - 2 bytes: color0 (RGB565)
    - 2 bytes: color1 (RGB565)
    - 4 bytes: color indices (2 bits per pixel)
    """
    # Extract the two color values (stored as RGB565)
    color0 = block_data[0] | (block_data[1] << 8)
    color1 = block_data[2] | (block_data[3] << 8)

    # Convert RGB565 to RGB888
    r0 = ((color0 >> 11) & 31) * 255 // 31
    g0 = ((color0 >> 5) & 63) * 255 // 63
    b0 = (color0 & 31) * 255 // 31

    r1 = ((color1 >> 11) & 31) * 255 // 31
    g1 = ((color1 >> 5) & 63) * 255 // 63
    b1 = (color1 & 31) * 255 // 31

    # Create the color palette based on the two colors
    palette = [
        (r0, g0, b0, 255),  # First color with alpha=255
        (r1, g1, b1, 255)  # Second color with alpha=255
    ]

    # If color0 > color1, we use linear interpolation for colors 2 and 3
    if color0 > color1:
        palette.append((
            (2 * r0 + r1) // 3,
            (2 * g0 + g1) // 3,
            (2 * b0 + b1) // 3,
            255
        ))
        palette.append((
            (r0 + 2 * r1) // 3,
            (g0 + 2 * g1) // 3,
            (b0 + 2 * b1) // 3,
            255
        ))
    else:
        # Otherwise color 2 is average, color 3 is transparent black
        palette.append((
            (r0 + r1) // 2,
            (g0 + g1) // 2,
            (b0 + b1) // 2,
            255
        ))
        palette.append((0, 0, 0, 0))  # Transparent

    # Extract color indices (4 bytes, 2 bits per pixel)
    indices = np.zeros(16, dtype=np.uint8)
    for i in range(4):
        byte = block_data[i + 4]
        for j in range(4):
            pixel_idx = i * 4 + j
            indices[pixel_idx] = (byte >> (j * 2)) & 0x3

    # Fill the pixels array
    for i in range(4):
        for j in range(4):
            if y + i < height and x + j < width:
                color_idx = indices[i * 4 + j]
                color = palette[color_idx]
                pixels[y + i, x + j, :3] = color[:3] # R, G, B
                if pixels.shape[2] > 3:  # If we have alpha
                    pixels[y + i, x + j, 3] = color[3]  # A


def _decompress_dxt3_block(block_data, pixels, x, y, width, height):
    """
    Decompress a DXT3 block (16 bytes total)

    Format:
    - 8 bytes: alpha values (4 bits per pixel)
    - 8 bytes: color data (same as DXT1)
    """
    # Extract explicit alpha values (8 bytes, 4 bits per pixel)
    alphas = np.zeros(16, dtype=np.uint8)
    for i in range(8):
        byte = block_data[i]
        alphas[i * 2] = (byte & 0xF) * 17  # Scale 0-15 to 0-255
        alphas[i * 2 + 1] = (byte >> 4) * 17

    # Handle color data (same as DXT1 but always use 4-color mode)
    color_data = block_data[8:16]

    # Extract the two color values (stored as RGB565)
    color0 = color_data[0] | (color_data[1] << 8)
    color1 = color_data[2] | (color_data[3] << 8)

    # Convert RGB565 to RGB888
    r0 = ((color0 >> 11) & 31) * 255 // 31
    g0 = ((color0 >> 5) & 63) * 255 // 63
    b0 = (color0 & 31) * 255 // 31

    r1 = ((color1 >> 11) & 31) * 255 // 31
    g1 = ((color1 >> 5) & 63) * 255 // 63
    b1 = (color1 & 31) * 255 // 31

    # Create the color palette - DXT3 always uses 4 colors
    palette = [
        (r0, g0, b0),
        (r1, g1, b1),
        ((2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3),
        ((r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3)
    ]

    # Extract color indices
    indices = np.zeros(16, dtype=np.uint8)
    for i in range(4):
        byte = color_data[i + 4]
        for j in range(4):
            pixel_idx = i * 4 + j
            indices[pixel_idx] = (byte >> (j * 2)) & 0x3

    # Fill the pixels array
    for i in range(4):
        for j in range(4):
            if y + i < height and x + j < width:
                color_idx = indices[i * 4 + j]
                color = palette[color_idx]
                alpha = alphas[i * 4 + j]

                pixels[y + i, x + j, :3] = color # R, G, B
                pixels[y + i, x + j, 3] = alpha  # A


def _decompress_dxt5_block(block_data, pixels, x, y, width, height):
    """
    Decompress a DXT5 block (16 bytes total)

    Format:
    - 1 byte: alpha0
    - 1 byte: alpha1
    - 6 bytes: alpha indices (3 bits per pixel)
    - 8 bytes: color data (same as DXT1)
    """
    # Extract alpha endpoints
    alpha0, alpha1 = block_data[0], block_data[1]

    # Create alpha palette
    alpha_palette = [alpha0, alpha1]
    if alpha0 > alpha1:
        # 8-value alpha
        for i in range(6):
            alpha_palette.append(((6 - i) * alpha0 + (i + 1) * alpha1) // 7)
    else:
        # 6-value alpha + transparent + opaque
        for i in range(4):
            alpha_palette.append(((4 - i) * alpha0 + (i + 1) * alpha1) // 5)
        alpha_palette.append(0)  # Fully transparent
        alpha_palette.append(255)  # Fully opaque

    # Extract alpha indices (6 bytes for 16 pixels, 3 bits per pixel)
    alpha_indices = np.zeros(16, dtype=np.uint8)

    # This is complex - we have 3 bits per pixel across 6 bytes
    bits = 0
    current_byte = 0
    for i in range(16):
        # We need 3 bits for each index
        if bits < 3:
            # Need to load more data
            current_byte |= block_data[2 + (i * 3) // 8] << bits
            bits += 8

        # Extract 3 bits
        alpha_indices[i] = current_byte & 0x7
        current_byte >>= 3
        bits -= 3

    # Handle color data (same as DXT1)
    color_data = block_data[8:16]

    # Extract the two color values (stored as RGB565)
    color0 = color_data[0] | (color_data[1] << 8)
    color1 = color_data[2] | (color_data[3] << 8)

    # Convert RGB565 to RGB888
    r0 = ((color0 >> 11) & 31) * 255 // 31
    g0 = ((color0 >> 5) & 63) * 255 // 63
    b0 = (color0 & 31) * 255 // 31

    r1 = ((color1 >> 11) & 31) * 255 // 31
    g1 = ((color1 >> 5) & 63) * 255 // 63
    b1 = (color1 & 31) * 255 // 31

    # Create the color palette - for DXT5 we always use 4 colors
    palette = [
        (r0, g0, b0),
        (r1, g1, b1),
        ((2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3),
        ((r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3)
    ]

    # Extract color indices
    indices = np.zeros(16, dtype=np.uint8)
    for i in range(4):
        byte = color_data[i + 4]
        for j in range(4):
            pixel_idx = i * 4 + j
            indices[pixel_idx] = (byte >> (j * 2)) & 0x3

    # Fill the pixels array
    for i in range(4):
        for j in range(4):
            if y + i < height and x + j < width:
                color_idx = indices[i * 4 + j]
                alpha_idx = alpha_indices[i * 4 + j]

                color = palette[color_idx]
                alpha = alpha_palette[alpha_idx]

                pixels[y + i, x + j, :3] = color # R, G, B
                pixels[y + i, x + j, 3] = alpha  # A
