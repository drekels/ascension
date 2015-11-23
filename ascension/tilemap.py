from ascension.util import Singleton
from Queue import PriorityQueue
import math
from ascension.ascsprite import Sprite


class TileMap(object):
    __metaclass__ = Singleton
    unit_z = 0.5
    tile_z = 0


    def __init__(self):
        self.reset_tiles()

    def reset_tiles(self):
        self.tiles = {}
        self.count = 0

    def generate_square(self, width=10, height=10):
        min_x = -(width - 1) / 2
        max_x = (width + 1)/ 2
        min_y = -(height - 1) / 2
        max_y = (height + 1)/ 2
        for x in range(min_x, max_x):
            y_offset = -int(math.ceil(x / 2.0))
            for y in range(min_y + y_offset, max_y + y_offset):
                self.addtile(x, y, Tile())

    def addtile(self, x, y, tile):
        if x not in self.tiles:
            self.tiles[x] = {}
        elif y in self.tiles[x]:
            raise KeyError(
                "TileMap already contains a tile for point ({}, {})"
                .format(x, y)
            )
        self.tiles[x][y] = tile
        self.count += 1

    def gettile(self, x, y):
        return self.tiles[x][y]

    def hastile(self, x, y):
        return x in self.tiles and y in self.tiles[x]

    def get_tile_sprites(self):
        for column in self.tiles:
            for tile in column:
                yield tile.get_sprite()

    def add_tile_sprites(self, sprite_manager, anchor=(0, 0)):
        for x in self.tiles:
            for y in self.tiles[x]:
                self.add_tile_sprite(x, y, sprite_manager, anchor=anchor)

    def get_horz_point_width(self):
        return 16

    def get_vert_x_shift(self):
        return 15

    def add_tile_sprite(self, x, y, sprite_manager, anchor=(0, 0)):
        s = self.tiles[x][y].get_sprite()
        x_position = anchor[0] + x * (s.component_width - self.get_horz_point_width())
        y_position = anchor[1] + y * s.component_height + x * self.get_vert_x_shift()
        s.x, s.y = x_position, y_position
        sprite_manager.add_sprite(s)


class Tile(object):

    def __init__(self):
        self.sprite = None

    def get_sprite(self):
        if not self.sprite:
            self.make_sprite()
        return self.sprite

    def make_sprite(self):
        self.sprite = Sprite(component_name="terrain.grassland")


class SimpleHexMoveRules(object):

    def __init__(self):
        self.adjacent_diffs = [
            (1, -1), (-1, 0), (0, -1), (0, 1), (1, 0), (-1, 1)
        ]

    def getadjacent(self, x, y):
        return [(x + i, y + j) for i, j in self.adjacent_diffs]

    def isadjacent(self, from_x, from_y, to_x, to_y):
        return (to_x - from_x, to_y - from_y) in self.adjacent_diffs

    def getcost(self, from_x, from_y, to_x, to_y):
        if self.isadjacent(from_x, from_y, to_x, to_y):
            return 1
        else:
            return None

    def get_distance(self, from_x, from_y, to_x, to_y):
        x_change = to_x - from_x
        y_change = to_y - from_y
        return max([abs(x_change), abs(y_change), abs(x_change - y_change)])


class DijkstraBase(object):

    def __init__(self, move_rules, origin_x, origin_y):
        self.move_rules = move_rules
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.visible_queue = PriorityQueue()
        self.visible_queue.put((0, (origin_x, origin_y)))
        self.costs = {(origin_x, origin_y): 0}
        self.visited = {}

    def run(self):
        while not self.is_done():
            _, (next_x, next_y) = self.visible_queue.get()
            if (next_x, next_y) not in self.visited:
                self.visit_tile(next_x, next_y)

    def visit_tile(self, x, y):
        base_cost = self.costs[(x, y)]
        for a_x, a_y in self.move_rules.getadjacent(x, y):
            cost = base_cost + self.move_rules.getcost(x, y, a_x, a_y)
            if (a_x, a_y) not in self.costs or self.costs[a_x, a_y] > cost:
                self.costs[(a_x, a_y)] = cost
                priority = self.get_visit_priority(cost, a_x, a_y)
                self.visible_queue.put((priority, (a_x, a_y)))
        self.visited[(x, y)] = base_cost

    def get_visit_priority(self, cost, x, y):
        return cost

    def is_done(self):
        raise NotImplementedError()


class AStar(DijkstraBase):

    def __init__(self, move_rules, origin_x, origin_y, target_x, target_y):
        super(AStar, self).__init__(move_rules, origin_x, origin_y)
        self.target_x = target_x
        self.target_y = target_y

    def get_visit_priority(self, cost, x, y):
        return self.move_rules.get_distance(x, y, self.target_x, self.target_y) + cost

    def is_done(self):
        return (self.target_x, self.target_y) in self.visited or not self.visible_queue.qsize()

    def get_cost(self):
        return self.visited[(self.target_x, self.target_y)]
