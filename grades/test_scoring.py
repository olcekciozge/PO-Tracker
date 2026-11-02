import unittest

from grades.scoring import lo_score, weighted_average


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

    def test_lo_score_with_all_grades(self):
        contributions = {"Midterm": 0.6, "Project": 0.4}
        grades = {"Midterm": 90, "Project": 80}
        self.assertAlmostEqual(lo_score(contributions, grades), 86.0)

    def test_lo_score_skips_missing_grade(self):
        contributions = {"Midterm": 0.6, "Project": 0.4}
        grades = {"Midterm": 90}
        self.assertAlmostEqual(lo_score(contributions, grades), 90.0)

    def test_lo_score_without_grades_returns_none(self):
        contributions = {"Midterm": 0.6, "Project": 0.4}
        self.assertIsNone(lo_score(contributions, {}))


if __name__ == "__main__":
    unittest.main()