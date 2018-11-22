from bitarray import bitarray

from .config import *
from .helper import *

from PIL import Image, ImageDraw


# Entry for Compression
def compress_to_bitarray(path_image, block_size=8):
    """
    Compress a grayscale image, return the result after transform but do not encode them

    The returned result has following structure:

    header: height, width, number of color channel
    body: compressed image

    :param path_image: path to the image
    :type path_image: str
    :param block_size: size of the DCT block, could be 8(8x8) or 16(16x16)
    :type block_size int
    :return: compressed image
    :rtype: bitarray
    """
    pix, im = load_image(path_image)

    result = bitarray()
    # encode height and width
    y, x = im.size
    result.extend(encode_image_shape((x, y)))

    # DC coefficient of the preceding block
    prev_dc = 0

    for block in split_image(pix, im, block_size):
        # For each block, do:
        # Level adjustment
        # DCT
        # Quantization
        # 2D -> 1D
        # encode DC and AC coefficients

        block -= LEVEL_ADJUSTMENT
        block = DCT(block)
        block = quantization(block)
        array = zigzag(block)

        # encode array[0] as diff
        diff = array[0] - prev_dc
        prev_dc = array[0]
        array[0] = diff

        # encode DC and AC
        encoded = encode_coefficient(array)

        # output result
        result.extend(encoded)

    # add end of image bits
    result.extend("00")

    return result


def decompress_bitarray(array):
    pos, (height, width) = decode_image_shape(array, 0)

    # L: black and white
    im = Image.new("L", (width, height))
    draw = ImageDraw.Draw(im)

    # find out number of blocks per row
    block_size = None
    num_block_y = None

    prev_dc = 0

    count = 0
    N = len(array)
    while N - pos >= 8:
        pos, coefficients = decode_coefficient(array, pos, prev_dc)

        # store previous DC coe
        prev_dc = coefficients[0]

        # reverse each steps during compression
        block = reverse_zigzag(coefficients)
        block = reverse_quantization(block)
        block = iDCT(block)
        block += LEVEL_ADJUSTMENT

        # clamp value between 0, 255
        block = np.clip(block, 0, 255)

        # we only know the size of block after decoded one block
        if block_size is None:
            block_size = block.shape[0]
            num_block_y = math.ceil(width / block_size)

        # draw this block into image
        block_x = count // num_block_y
        block_y = count % num_block_y
        fill_image(draw, block, (block_x, block_y), (height, width))

        # finally
        count += 1

    return im


def decompress_data_to_file(file_in, file_out):
    array = load_bitarray(file_in)
    im = decompress_bitarray(array)
    im.save(file_out, "bmp")
