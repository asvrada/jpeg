import numpy as np
from PIL import Image
import math
from bitarray import bitarray
from .huffman import huffman_encode_to_bitarray, huffman_decode
from .constants import JPEG_QUANTIZATION_TABLE_8


def zigzag(matrix):
    """
    Flattern 2D matrix to 1D array, in a zigzag manner (odds)

    :return numpy array of int
    :rtype np.ndarray
    """
    r, c = 0, 0
    x, y = matrix.shape

    ret = np.zeros((x * y,), dtype=int)

    for i in range(x * y):
        ret[i] = matrix[r][c]

        if (r + c) % 2 == 0:
            if c == y - 1:
                r += 1
            elif r == 0:
                c += 1
            else:
                r -= 1
                c += 1
        else:
            if r == x - 1:
                c += 1
            elif c == 0:
                r += 1
            else:
                r += 1
                c -= 1

    return ret


def reverse_zigzag(array):
    # todo
    pass


def convert_amp_to_bitarray(num):
    """
    Convert the amplitude into bitarray using 1's complement

    :param num: the number
    :type num: int
    :return: The 1's complement representation of the given number
    :rtype: bitarray
    """
    sign = True if num < 0 else False

    b_arr = bitarray("{:b}".format(abs(num)))

    # if negative, use complement
    if sign:
        one = len(b_arr) * bitarray('1')
        b_arr ^= one

    return b_arr


def encode_coefficient(array, prev_dc):
    """
    Encdoe DC and AC coefficient

    Encode into list of tuple (run, size, amplitude), while the first element is going to be (size, amplitude) since it's DC coe

    :param array: array of int
    :type array: np.ndarray
    :param prev_dc: DC coe of previous block
    :type prev_dc: int
    :return: encoded DC and AC coefficient
    :rtype: bitarray
    """

    def convert_ac_to_bitarray(runlength, element):
        """
        Encode AC coe
        tuple: ((runlength, size), amplitude)
                where runlength is constrained to 4 bits, and size is huffman coded, amplitude is one's complement representation
            runlength: number of zero coe preceding this element
            size: number of bits requred to represent amplitude

        Special code:
            eob: (0, 0)
            zrl: (15, 0)

        :param runlength: time the element repeated
        :type runlength: int
        :param element: the AC amplitude
        :type element: int
        :return: encoded AC eoe
        :rtype: bitarray
        """
        # If there are more than 15 preceding zeros
        if runlength > max_runlength:
            return zrl + convert_ac_to_bitarray(runlength - max_runlength, element)

        b_runlength = bitarray("{:04b}".format(runlength))
        b_ac = convert_amp_to_bitarray(element)
        b_size = huffman_encode_to_bitarray(len(b_ac))

        return b_runlength + b_size + b_ac

    if len(array) not in [8 * 8, 16 * 16]:
        raise "Length of array to encode is not valid: got {}".format(len(array))

    # special code for encoding AC coe
    eob = bitarray("000000")
    zrl = bitarray("111100")
    max_runlength = 15

    result = bitarray()

    # First
    # encode DC first
    diff = array[0] - prev_dc

    # use one's complement representation
    b_diff = convert_amp_to_bitarray(diff)
    b_size = huffman_encode_to_bitarray(len(b_diff))

    # store results
    result.extend(b_size)
    result.extend(b_diff)

    # Second
    # encode AC
    count = 0
    for ac in array[1:]:
        # zero, increment count
        if ac == 0:
            count += 1
            continue

        # not zero, encode prev
        result.extend(convert_ac_to_bitarray(count, ac))
        # reset count
        count = 0

    # add end of block
    result.extend(eob)

    return result


def decode_coefficient(bit_array, prev_dc):
    """
    todo
    """
    # build a tree to decode huffman code

    pass


def get_dct_matrix(N):
    D = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            if i == 0:
                tmp = math.sqrt(1 / N)
            else:
                tmp = math.sqrt(2 / N)

            D[i][j] = tmp * math.cos(math.pi * (2 * j + 1) * i / (2 * N))

    return D


def DCT(block):
    """
    DCT on a copy of block
    """
    D = get_dct_matrix(block.shape[0])

    # D * A * D'
    return np.matmul(np.matmul(D, block), D.transpose())


def iDCT(block):
    """
    Inverse DCT
    """
    D = get_dct_matrix(block.shape[0])

    # D' * A * D
    return np.matmul(np.matmul(D.transpose(), block), D)


def quantization(block):
    """
    Quantize on a copy of block
    """
    if block.shape[0] == 8:
        return np.round(block / JPEG_QUANTIZATION_TABLE_8)

    table_16 = np.zeros((16, 16))
    for i in range(8):
        for j in range(8):
            table_16[2 * i][2 * j] = JPEG_QUANTIZATION_TABLE_8[i][j]
            table_16[2 * i + 1][2 * j] = JPEG_QUANTIZATION_TABLE_8[i][j]
            table_16[2 * i][2 * j + 1] = JPEG_QUANTIZATION_TABLE_8[i][j]
            table_16[2 * i + 1][2 * j + 1] = JPEG_QUANTIZATION_TABLE_8[i][j]

    return np.round(block / table_16)


def reverse_quantization(block):
    """
    Reverse quantize on a copy of block
    """
    if block.shape[0] == 8:
        return np.round(block * JPEG_QUANTIZATION_TABLE_8)

    table_16 = np.zeros((16, 16))
    for i in range(8):
        for j in range(8):
            table_16[2 * i][2 * j] = JPEG_QUANTIZATION_TABLE_8[i][j]
            table_16[2 * i + 1][2 * j] = JPEG_QUANTIZATION_TABLE_8[i][j]
            table_16[2 * i][2 * j + 1] = JPEG_QUANTIZATION_TABLE_8[i][j]
            table_16[2 * i + 1][2 * j + 1] = JPEG_QUANTIZATION_TABLE_8[i][j]

    return np.round(block * table_16)


def load_image(path_image):
    im = Image.open(path_image)
    pix = im.load()
    return pix, im


def split_image(pix, im, block_size=8):
    """
    todo: 长宽顺序反了
    A generator that split a image into blocks and return one block at a time
    :param pix: the pix object
    :param im: the im object
    :param block_size: the size of block, could be 8 or 16
    :type block_size: int
    :return: one block of a image
    :rtype: numpy.darray
    """
    height, width = im.size

    num_block_x = math.ceil(height / block_size)
    num_block_y = math.ceil(width / block_size)

    for x in range(num_block_x):
        for y in range(num_block_y):
            block = np.zeros((block_size, block_size))

            # construct block
            for i in range(block_size):
                for j in range(block_size):
                    # the index of pixel for the image
                    img_i, img_j = i + block_size * x, j + block_size * y

                    # skip out of bound
                    if img_i >= height or img_j >= width:
                        continue

                    # assign color
                    block[i][j] = pix[img_i, img_j]

            # yield one block
            yield block
