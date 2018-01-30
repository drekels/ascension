import random
from decimal import Decimal


def smoothstep(a0, a1, w):
    value = w**3 * (w * (w*6 - 15) + 10)
    return a0 + value *(a1 - a0)


def get_dot_product(v1, v2):
    return sum([a*b for (a, b) in zip(v1, v2)])


def normalize(vector):
    length = sum([x**2 for x in vector])**Decimal('0.5')
    return [x / length for x in vector]


def get_random_vector(num_dimensions):
    """ Based on http://mathworld.wolfram.com/HyperspherePointPicking.html """
    xn = []
    for _ in range(num_dimensions):
        xn.append(Decimal(random.random())*2 - 1)
    scalar = 1 / (sum([xi**2 for xi in xn])**Decimal('0.5'))
    return normalize([Decimal(xi * scalar) for xi in xn])


def get_coor_set(dimensions):
    if not dimensions:
        yield []
    else:
        dimensions = list(dimensions)
        dimension = dimensions.pop()
        coor_starts = list(get_coor_set(dimensions))
        for i in range(dimension):
            for coor_start in coor_starts:
                coor = list(coor_start)
                coor.append(i)
                yield coor


def get_bitlist(number, min_digits=0):
    bitlist = []
    while number:
        bitlist.append(number % 2)
        number = number >> 1
    while len(bitlist) < min_digits:
        bitlist.append(0)
    bitlist.reverse()
    return bitlist



class TileablePerlinGenerator(object):
    seed = False
    dimensions = [1, 2, 3]

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.generate_vectors()

    def generate_vectors(self):
        if self.seed:
            random.seed(self.seed)
        self.vectors = {}
        for coor in get_coor_set(self.dimensions):
            self.vectors[tuple(coor)] = get_random_vector(len(self.dimensions))

    def get_value(self, *position):
        normalized = [p * d for (p, d) in zip(position, self.dimensions)]
        anchor_coor = [int(n) % d for (n, d) in zip(normalized, self.dimensions)]
        dot_products = []
        for i in range(2**len(self.dimensions)):
            bitlist = get_bitlist(i, min_digits=len(self.dimensions))
            overflow_coor = [(a + b) for (a, b) in zip(anchor_coor, bitlist)]
            coor = [c % d for (c, d) in zip(overflow_coor, self.dimensions)]
            diff = [n - c for (n, c) in zip(normalized, overflow_coor)]
            vector = self.vectors[tuple(coor)]
            dot_product = get_dot_product(diff, vector)
            dot_products.append(dot_product)

        for i in range(len(self.dimensions)):
            dim_position = normalized[-(i+1)] % 1
            interpolated = []
            for i in range(len(dot_products) / 2):
                left = dot_products[i*2]
                right = dot_products[i*2 + 1]
                interpolated.append(smoothstep(left, right, dim_position))
            dot_products = interpolated

        value = dot_products[0]
        return value
