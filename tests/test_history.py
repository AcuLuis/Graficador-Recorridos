import unittest

from core.history import History


class HistoryTests(unittest.TestCase):
    def test_undo_y_redo(self):
        history = History()
        history.push({"v": 1})

        self.assertEqual(history.undo({"v": 2}), {"v": 1})
        self.assertTrue(history.can_redo)
        self.assertEqual(history.redo({"v": 1}), {"v": 2})
        self.assertFalse(history.can_redo)

    def test_push_descarta_rehacer(self):
        history = History()
        history.push({"v": 1})
        history.undo({"v": 2})

        history.push({"v": 1})

        self.assertFalse(history.can_redo)

    def test_sin_historial_devuelve_none(self):
        history = History()

        self.assertIsNone(history.undo({"v": 1}))
        self.assertIsNone(history.redo({"v": 1}))

    def test_respeta_limite(self):
        history = History(limit=2)
        for value in range(5):
            history.push({"v": value})

        self.assertEqual(history.undo({}), {"v": 4})
        self.assertEqual(history.undo({}), {"v": 3})
        self.assertIsNone(history.undo({}))


if __name__ == "__main__":
    unittest.main()
