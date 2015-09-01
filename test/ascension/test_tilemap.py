from unittest2 import TestCase
from ascension.tilemap import SimpleHexMoveRules, AStar, TileMap, Tile


class TestTileMap(TestCase):

    def setUp(self):
        TileMap.reset()
        self.move_rules = SimpleHexMoveRules()

    def test_empty_square(self):
        TileMap.generate_square(0, 0)
        self.assertEqual(0, TileMap.count)
        TileMap.generate_square(0, 2)
        self.assertEqual(0, TileMap.count)
        TileMap.generate_square(1, 0)
        self.assertEqual(0, TileMap.count)


    def test_single_square(self):
        TileMap.generate_square(1, 1)
        print TileMap.tiles
        self.assertEqual(1, TileMap.count)
        self.assertTrue(TileMap.hastile(0, 0))
        self.assertTrue(isinstance(TileMap.gettile(0, 0), Tile))
        for x, y in self.move_rules.getadjacent(0, 0):
            self.assertFalse(TileMap.hastile(x, y))


class TestSimpleHexMoveRules(TestCase):

    def setUp(self):
        self.adjacent_to_neg_one_neg_one = [(-2, -2), (-2, -1), (-1, -2), (-1, 0), (0, -1), (0, 0)]
        self.move_rules = SimpleHexMoveRules()

    def test_getadjacent(self):
        self.assertEquals(self.adjacent_to_neg_one_neg_one, self.move_rules.getadjacent(-1, -1))

    def test_isadjacent(self):
        for x, y in self.adjacent_to_neg_one_neg_one:
            self.assertTrue(self.move_rules.isadjacent(-1, -1, x, y))
        self.assertFalse(self.move_rules.isadjacent(-1, -1, -1, -1))
        self.assertFalse(self.move_rules.isadjacent(-1, -1, -3, -1))
        self.assertFalse(self.move_rules.isadjacent(-1, -1, -2, 0))

    def test_getcost(self):
        for x, y in self.adjacent_to_neg_one_neg_one:
            self.assertEqual(1, self.move_rules.getcost(-1, -1, x, y))
        self.assertIsNone(None, self.move_rules.getcost(-1, -1, -1, -1))
        self.assertIsNone(None, self.move_rules.getcost(-1, -1, 1, 2))

    def test_get_distance(self):
        for x, y in self.adjacent_to_neg_one_neg_one:
            self.assertEqual(1, self.move_rules.get_distance(-1, -1, x, y))
        self.assertEqual(2, self.move_rules.get_distance(-1, -1, 1, 1))
        self.assertEqual(2, self.move_rules.get_distance(-1, -1, -3, -3))
        self.assertEqual(2, self.move_rules.get_distance(-1, -1, -3, -1))


class TestAStar(TestCase):

    def setUp(self):
        self.move_rules = SimpleHexMoveRules()

    def test_stay_still(self):
        astar = AStar(self.move_rules, 1, 1, 1, 1)
        astar.run()
        self.assertTrue((1, 1) in astar.visited)
        self.assertEqual(0, astar.visited[(1, 1)])

    def test_couple_steps(self):
        astar = AStar(self.move_rules, 1, 1, 3, 4)
        astar.run()
        self.assertTrue((1, 1) in astar.visited)
        self.assertEqual(3, astar.visited[(3, 4)])



