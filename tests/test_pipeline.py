import unittest

from backend.pipeline import _extract_tasks


class TaskExtractionTests(unittest.TestCase):
    def test_russian_assignment_with_name_and_deadline(self):
        rows = _extract_tasks([{"start": 4.2, "text": "Айжан, подготовь отчёт до пятницы.", "speaker": "Говорящий 2"}])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["responsible"], "Айжан")
        self.assertEqual(rows[0]["deadline"], "пятницы")
        self.assertEqual(rows[0]["speaker"], "Говорящий 2")
        self.assertIn("подготовь", rows[0]["task"].lower())

    def test_kazakh_assignment_is_detected(self):
        rows = _extract_tasks([{"start": 0, "text": "Ұсынысты дайындаңыз ертеңге дейін.", "speaker": "Говорящий 1"}])
        self.assertEqual(len(rows), 1)

    def test_non_assignment_is_ignored(self):
        rows = _extract_tasks([{"start": 0, "text": "Обсудили итоги прошлой встречи.", "speaker": "Говорящий 1"}])
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
