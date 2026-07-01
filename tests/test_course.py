import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mentor_that_knows.course import build_course
from mentor_that_knows.orchestrator import run_scripted


class CourseTests(unittest.TestCase):
    def test_course_has_ten_lessons(self):
        course = build_course(seed=7)
        self.assertEqual(len(course), 10)
        self.assertEqual(course[0].number, 1)
        self.assertEqual(course[-1].number, 10)

    def test_scripted_run_catches_planned_bluffs(self):
        result = run_scripted(seed=7)
        self.assertEqual(len(result.lessons), 10)
        self.assertEqual(sum(lesson.caught_bluff for lesson in result.lessons), 2)
        self.assertTrue(all(lesson.passed for lesson in result.lessons))

    def test_submission_contains_required_sections(self):
        result = run_scripted(seed=7)
        text = "\n".join(turn.text for turn in result.turns)
        self.assertIn("ADVANCE: NO", text)
        self.assertIn("ADVANCE: YES", text)


if __name__ == "__main__":
    unittest.main()

