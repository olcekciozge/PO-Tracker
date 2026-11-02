import unittest

from grades.scoring import weighted_average

class WeightedAverageTests(unittest.TestCase):
    def test_elif_example(self):
        lo1 = weighted_average([(0.6, 90), (0.4, 80)])
        lo2 = weighted_average([(0.4, 90), (1.0, 80)])
        po1 = weighted_average([(2, lo1), (1, lo2)])
        po2 = weighted_average([(1, lo2)])

        self.assertAlmostEqual(lo1, 86.0, places=1)
        self.assertAlmostEqual(lo2, 82.9, places=1)
        self.assertAlmostEqual(po1, 85.0, places=1)
        self.assertAlmostEqual(po2, 82.9, places=1)

    def test_no_data_returns_none(self):
        self.assertIsNone(weighted_average([]))


if __name__ == "__main__":
    unittest.main()