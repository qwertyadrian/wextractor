"""
S3TC DXT1/DXT5 Texture Decompression

Inspired by Benjamin Dobell

Original C++ code https://github.com/Benjamin-Dobell/s3tc-dxt-decompression
"""

import struct

def unpack(_bytes):
	STRUCT_SIGNS = {
	1 : 'B',
	2 : 'H',
	4 : 'I',
	8 : 'Q'
	}
	return struct.unpack('<' + STRUCT_SIGNS[len(_bytes)], _bytes)[0]

# This function converts RGB565 format to raw pixels
def unpackRGB(packed):
	R = (packed >> 11) & 0x1F
	G = (packed >> 5) & 0x3F
	B = (packed) & 0x1F

	R = (R << 3) | (R >> 2)
	G = (G << 2) | (G >> 4)
	B = (B << 3) | (B >> 2)

	return (R, G, B, 255)

class DXTBuffer:
	def __init__(self, width, height):
		self.width = width
		self.height = height

		self.block_countx = self.width // 4
		self.block_county = self.height// 4

		self.decompressed_buffer = ["X"] * ((width * height) * 2) # Dont ask me why
		print(f"Log: New DXTBuffer instance created {width}x{height}")


	def DXT5Decompress(self, file):
		print("Log: DTX5 Decompressing..")

		# Loop through each block and decompress it
		for row in range(self.block_county):
			for col in range(self.block_countx):

				# Get the alpha values
				a0 = unpack(file.read(1))
				a1 = unpack(file.read(1))
				atable = file.read(6)

				acode0 = atable[2] | (atable[3] << 8) | (atable[4] << 16) | (atable[5] << 24)
				acode1 = atable[0] | (atable[1] << 8)

				# Color 1 color 2, color look up table
				c0 = unpack(file.read(2))
				c1 = unpack(file.read(2))
				ctable = unpack(file.read(4))

				# The 4x4 Lookup table loop
				for j in range(4):
					for i in range(4):
						alpha = self.getAlpha(j, i, a0, a1, atable, acode0, acode1)
						self.getColors(row * 4, col * 4, i, j, ctable, unpackRGB(c0) ,unpackRGB(c1), alpha) # Set the color for the current pixel


		print("Log: DXT Buffer decompressed and returned successfully.")
		return b''.join([_ for _ in self.decompressed_buffer if _ != 'X'])


	def DXT1Decompress(self, file):
		print(f"Log: DTX1 Decompressing..")
		# Loop through each block and decompress it
		for row in range(self.block_county):
			for col in range(self.block_countx):

				# Color 1 color 2, color look up table
				c0 = unpack(file.read(2))
				c1 = unpack(file.read(2))
				ctable = unpack(file.read(4))

				# The 4x4 Lookup table loop
				for j in range(4):
					for i in range(4):
						self.getColors(row * 4, col * 4, i, j, ctable, unpackRGB(c0) ,unpackRGB(c1), 255) # Set the color for the current pixel

		print("Log: DXT Buffer decompressed and returned successfully.")
		return b''.join([_ for _ in self.decompressed_buffer if _ != 'X'])

	def getColors(self, x, y, i, j, ctable, c0, c1, alpha):
		code = (ctable >> ( 2 * (4 * i + j))) & 0x03 # Get the color of the current pixel
		pixel_color = None

		r0 = c0[0]
		g0 = c0[1]
		b0 = c0[2]

		r1 = c1[0]
		g1 = c1[1]
		b1 = c1[2]

		# Main two colors
		if code == 0:
			pixel_color = (r0, g0, b0, alpha)
		if code == 1:
			pixel_color = (r1, g1, b1, alpha)

		# Use the lookup table to determine the other two colors
		if c0 > c1:
			if code == 2:
				pixel_color = ((2*r0+r1)//3, (2*g0+g1)//3, (2*b0+b1)//3, alpha)
			if code == 3:
				pixel_color = ((r0+2*r1)//3, (g0+2*g1)//3, (b0+2*b1)//3, alpha)
		else:
			if code == 2:
				pixel_color = ((r0+r1)//2, (g0+g1)//2, (b0+b1)//2, alpha)
			if code == 3:
				pixel_color = (0, 0, 0, alpha)

		# While not surpassing the image dimensions, assign pixels the colors
		if (x + i) < self.width:
			self.decompressed_buffer[(y + j) * self.width + (x + i)] = struct.pack('<B', pixel_color[0]) + \
				struct.pack('<B', pixel_color[1]) + struct.pack('<B', pixel_color[2]) + struct.pack('<B', pixel_color[3])

	def getAlpha(self, i, j, a0, a1, atable, acode0, acode1):

		# Using the same method as the colors calculate the alpha values

		alpha = 255
		alpha_index = 3 * (4 * j+i)
		alpha_code = None

		if alpha_index <= 12:
			alpha_code = (acode1 >> alpha_index) & 0x07
		elif alpha_index == 15:
			alpha_code = (acode1 >> 15) | ((acode0 << 1) & 0x06)
		else:
			alpha_code = (acode0 >> (alpha_index - 16)) & 0x07

		if alpha_code == 0:
			alpha = a0
		elif alpha_code == 1:
			alpha = a1
		else:
			if a0 > a1:
				alpha = ((8-alpha_code) * a0 + (alpha_code-1) * a1) // 7
			else:
				if alpha_code == 6:
					alpha = 0
				elif alpha_code == 7:
					alpha = 255
				elif alpha_code == 5:
					alpha = (1 * a0 + 4 * a1) // 5
				elif alpha_code == 4:
					alpha = (2 * a0 + 3 * a1) // 5
				elif alpha_code == 3:
					alpha = (3 * a0 + 2 * a1) // 5
				elif alpha_code == 2:
					alpha = (4 * a0 + 1 * a1) // 5
				else:
					alpha = 0 # For safety
		return alpha