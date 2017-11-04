from unittest2 import TestCase
from ascension.tilemap import SimpleHexMoveRules, AStar


class TestSimpleHexMoveRules(TestCase):

    def setUp(self):
        self.adjacent_to_neg_one_neg_one = [(0, -2), (-2, -1), (-1, -2), (-1, 0), (0, -1), (-2, 0)]
        self.move_rules = SimpleHexMoveRules()

    def test_getadjacent(self):
        self.assertEquals(self.adjacent_to_neg_one_neg_one, self.move_rules.getadjacent(-1, -1))

    def test_isadjacent(self):
        for x, y in self.adjacent_to_neg_one_neg_one:
            self.assertTrue(self.move_rules.isadjacent(-1, -1, x, y))
        self.assertFalse(self.move_rules.isadjacent(-1, -1, -1, -1))
        self.assertFalse(self.move_rules.isadjacent(-1, -1, -3, -1))
        self.assertTrue(self.move_rules.isadjacent(-1, -1, -2, 0))

    def test_getcost(self):
        for x, y in self.adjacent_to_neg_one_neg_one:
            self.assertEqual(1, self.move_rules.getcost(-1, -1, x, y))
        self.assertIsNone(None, self.move_rules.getcost(-1, -1, -1, -1))
        self.assertIsNone(None, self.move_rules.getcost(-1, -1, 1, 2))

    def test_get_distance(self):
        for x, y in self.adjacent_to_neg_one_neg_one:
            distance = self.move_rules.get_distance(-1, -1, x, y)
            self.assertEqual(
                1, distance,
                "distance from (-1, -1) to ({}, {}) is {}, not 1".format(x, y, distance)
            )
        self.assertEqual(4, self.move_rules.get_distance(-1, -1, 1, 1))
        self.assertEqual(4, self.move_rules.get_distance(-1, -1, -3, -3))
        self.assertEqual(2, self.move_rules.get_distance(-1, -1, -3, -1))
        self.assertEqual(2, self.move_rules.get_distance(-1, -1, -3, 0))
        self.assertEqual(2, self.move_rules.get_distance(-1, -1, -3, 1))


class TestAStar(TestCase):

    def setUp(self):
        self.move_rules = SimpleHexMoveRules()

    def test_stay_still(self):
        astar = AStar(self.move_rules, origin_x=1, origin_y=1, target_x=1, target_y=1)
        astar.run()
        self.assertTrue((1, 1) in astar.visited)
        self.assertEqual(0, astar.visited[(1, 1)])

    def test_couple_steps(self):
        astar = AStar(self.move_rules, origin_x=1, origin_y=1, target_x=3, target_y=4)
        astar.run()
        self.assertTrue((1, 1) in astar.visited)
        self.assertTrue((3, 4) in astar.visited)
        self.assertEqual(5, astar.visited[(3, 4)])



