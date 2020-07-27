import unittest

from tabpy.tabpy_tools.schema import generate_schema


class TestSchema(unittest.TestCase):
    def test_schema(self):
        schema = generate_schema(
            input={"x": ["happy", "sad", "neutral"]},
            input_description={"x": "text to analyze"},
            output=[0.98, -0.99, 0],
            output_description="scores for input texts",
        )
        expected = {
            "input": {
                "type": "object",
                "properties": {
                    "x": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "text to analyze",
                    }
                },
                "required": ["x"],
            },
            "sample": {"x": ["happy", "sad", "neutral"]},
            "output": {
                "type": "array",
                "items": {"type": "number"},
                "description": "scores for input texts",
            },
        }
        self.assertEqual(schema, expected)
