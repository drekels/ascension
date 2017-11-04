from unittest2 import TestCase
from decimal import Decimal, getcontext
import math


from tools.util import (
    line_gt, line_gtoe, line_lt, line_ltoe, get_line_intersection,
    get_line_through_point, line_eq, get_distance_to_line_segment,
    get_distance_to_line,
)


class TestLine(TestCase):

    def setUp(self):
        getcontext().prec = 10


    def test_line_point_compare(self):
        tests = [
            ((0, 1, 3), 1, 3, 1),
            ((0, 1, 3), 5, -3, 0),
            ((0, 1, 3), 6, -4, -1),
            ((1, 1, 4), 0, -4, 0),
            ((1, 1, 4), -4, 0, 0),
            ((1, 1, 4), 1, 2, 1),
            ((1, 1, 4), -2, -1, 1),
            ((1, 1, 4), -2, -3, -1),
            ((1, 1, 4), -5, 0, -1),
        ]
        for line, x, y, expected in tests:
            if expected == 1:
                self.assertTrue(line_gt(line, x, y))
                self.assertTrue(line_gtoe(line, x, y))
                self.assertFalse(line_lt(line, x, y))
                self.assertFalse(line_ltoe(line, x, y))
            if expected == 0:
                self.assertFalse(line_gt(line, x, y))
                self.assertTrue(line_gtoe(line, x, y))
                self.assertFalse(line_lt(line, x, y))
                self.assertTrue(line_ltoe(line, x, y))
            if expected == -1:
                self.assertFalse(line_gt(line, x, y))
                self.assertFalse(line_gtoe(line, x, y))
                self.assertTrue(line_lt(line, x, y))
                self.assertTrue(line_ltoe(line, x, y))
        with self.assertRaises(ZeroDivisionError):
            line_gt((1, 0, 3), 1, 2)
        with self.assertRaises(ZeroDivisionError):
            line_gtoe((1, 0, 3), 1, 2)
        with self.assertRaises(ZeroDivisionError):
            line_lt((1, 0, 3), 1, 2)
        with self.assertRaises(ZeroDivisionError):
            line_ltoe((1, 0, 3), 1, 2)

    def test_line_intersection_simple(self):
        line1 = (Decimal(1), Decimal(1), Decimal(-3))
        line2 = (Decimal(2), Decimal(-3), Decimal(-6))
        x, y = get_line_intersection(line1, line2)
        self.assertAlmostEquals(x, 3)
        self.assertAlmostEquals(y, 0)

    def test_line_intersection_horz(self):
        line1 = (Decimal(0), Decimal(1), Decimal(-3))
        line2 = (Decimal(2), Decimal(-3), Decimal(-6))
        x, y = get_line_intersection(line1, line2)
        self.assertAlmostEquals(x, Decimal(15)/Decimal(2))
        self.assertAlmostEquals(y, 3)

        line1 = (Decimal(2), Decimal(-3), Decimal(-6))
        line2 = (Decimal(0), Decimal(1), Decimal(-3))
        x, y = get_line_intersection(line1, line2)
        self.assertAlmostEquals(x, Decimal(15)/Decimal(2))
        self.assertAlmostEquals(y, 3)

    def test_line_intersection_vert_1(self):
        line1 = (Decimal(1), Decimal(0), Decimal(-3))
        line2 = (Decimal(2), Decimal(-3), Decimal(-6))
        x, y = get_line_intersection(line1, line2)
        self.assertAlmostEquals(x, 3)
        self.assertAlmostEquals(y, 0)

        line1 = (Decimal(2), Decimal(-3), Decimal(-6))
        line2 = (Decimal(1), Decimal(0), Decimal(-3))
        x, y = get_line_intersection(line1, line2)
        self.assertAlmostEquals(x, 3)
        self.assertAlmostEquals(y, 0)

    def test_line_intersection_parallel(self):
        line1 = (Decimal(2), Decimal(-3), Decimal(-6))
        line2 = (Decimal(-4), Decimal(6), Decimal(13))
        with self.assertRaises(ZeroDivisionError) as ar:
            get_line_intersection(line1, line2)
        self.assertTrue("parallel" in str(ar.exception).lower())

        line1 = (Decimal(0), Decimal(-3), Decimal(-6))
        line2 = (Decimal(0), Decimal(6), Decimal(13))
        with self.assertRaises(ZeroDivisionError) as ar:
            get_line_intersection(line1, line2)
        self.assertTrue("parallel" in str(ar.exception).lower())

        line1 = (Decimal(2), Decimal(0), Decimal(-6))
        line2 = (Decimal(-4), Decimal(0), Decimal(13))
        with self.assertRaises(ZeroDivisionError) as ar:
            get_line_intersection(line1, line2)
        self.assertTrue("parallel" in str(ar.exception).lower())

    def test_get_line_through_point(self):
        args = 5, 6, 4, 0
        expected = 1, 0, -5
        value = get_line_through_point(*args)
        self.assertTrue(
            line_eq(expected, value),
            "Line {} does not equal expected {}".format(value, expected)
        )

        args = 5, 6, 2, 1
        expected = -2, 1, 4
        value = get_line_through_point(*args)
        self.assertTrue(
            line_eq(expected, value),
            "Line {} does not equal expected {}".format(value, expected)
        )

    def test_get_distance_to_line_segment_vertical_line(self):
        expected = 4
        actual = get_distance_to_line_segment(1, 2, -3, -2, -3, 4)
        self.assertEquals(expected, actual)

        expected = 4
        actual = get_distance_to_line_segment(1, 0, -3, -2, -3, 4)
        self.assertEquals(expected, actual)

        expected = 4
        actual = get_distance_to_line_segment(-7, 0, -3, -2, -3, 4)
        self.assertEquals(expected, actual)

        expected = 5
        actual = get_distance_to_line_segment(-6, -6, -3, -2, -3, 4)
        self.assertAlmostEquals(expected, actual)

    def test_get_distance_to_line_segment_horizontal_line(self):
        expected = 4
        actual = get_distance_to_line_segment(2, 1, -2, -3, 4, -3)
        self.assertEquals(expected, actual)

        expected = 4
        actual = get_distance_to_line_segment(0, 1, -2, -3, 4, -3)
        self.assertEquals(expected, actual)

        expected = 4
        actual = get_distance_to_line_segment(0, -7, -2, -3, 4, -3)
        self.assertEquals(expected, actual)

        expected = 5
        actual = get_distance_to_line_segment(-6, -6, -2, -3, 4, -3)
        self.assertAlmostEquals(expected, actual)

    def test_get_distance_to_line_segment(self):
        expected = Decimal(math.sqrt(2))
        actual = get_distance_to_line_segment(-1, 1, -2, -2, 4, 4)
        self.assertAlmostEquals(expected, actual)

    def test_get_distance_to_line(self):
        expected = Decimal(math.sqrt(2))
        actual = get_distance_to_line(-1, 1, (-1, 1, 0))
        self.assertAlmostEquals(expected, actual)




