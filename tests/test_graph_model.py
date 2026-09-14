import unittest

from graph_model import GraphModel


class GraphModelTests(unittest.TestCase):
    def test_round_trip_serialization(self):
        model = GraphModel()
        model.add_node(1, (0.1, 0.2))
        model.add_node(2, (0.3, 0.4))
        model.add_edge(1, 2, peso=5)

        data = model.to_dict()

        loaded = GraphModel()
        loaded.load_from_dict(data)

        self.assertEqual(sorted(loaded.graph.nodes()), [1, 2])
        self.assertEqual(sorted(loaded.graph.edges(data=True))[0][2]["weight"], 5)
        self.assertEqual(loaded.pos[1], (0.1, 0.2))
        self.assertEqual(loaded.pos[2], (0.3, 0.4))

    def test_add_edge_requires_existing_nodes(self):
        model = GraphModel()

        with self.assertRaises(ValueError):
            model.add_edge(1, 2, peso=3)

    def test_set_node_position_updates_position(self):
        model = GraphModel()
        model.add_node(1, (0.1, 0.1))

        model.set_node_position(1, (0.5, 0.6))

        self.assertEqual(model.pos[1], (0.5, 0.6))

    def test_update_edge_weight_updates_existing_edge(self):
        model = GraphModel()
        model.add_node(1)
        model.add_node(2)
        model.add_edge(1, 2, peso=3)

        model.update_edge_weight(1, 2, 9)

        self.assertEqual(model.graph[1][2]["weight"], 9)
        self.assertEqual(model.edge_weights[(1, 2)], 9)


if __name__ == "__main__":
    unittest.main()
