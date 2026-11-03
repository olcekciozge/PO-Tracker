import unittest

from grades.scoring import lo_score, po_score, weighted_average


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

    def test_po_score_elif_example(self):
        lo_links = {"LO1": 2, "LO2": 1}
        lo_scores = {"LO1": 86.0, "LO2": 82.9}
        self.assertAlmostEqual(po_score(lo_links, lo_scores), 85.0, places=1)

    def test_po_score_combines_courses(self):
        lo_links = {"CSE 311 LO1": 5, "CSE 321 LO1": 1}
        lo_scores = {"CSE 311 LO1": 90, "CSE 321 LO1": 60}
        self.assertAlmostEqual(po_score(lo_links, lo_scores), 85.0)

    def test_po_score_skips_lo_without_score(self):
        lo_links = {"LO1": 2, "LO2": 1}
        lo_scores = {"LO1": 86.0, "LO2": None}
        self.assertAlmostEqual(po_score(lo_links, lo_scores), 86.0)

    def test_po_score_counts_zero_as_a_real_score(self):
        lo_links = {"LO1": 1, "LO2": 1}
        lo_scores = {"LO1": 80, "LO2": 0}
        self.assertAlmostEqual(po_score(lo_links, lo_scores), 40.0)


if __name__ == "__main__":
    unittest.main()