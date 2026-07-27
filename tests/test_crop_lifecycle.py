import unittest

from app.digital_twin.crop_catalog import get_crop_catalog


class CropLifecycleConfigTests(unittest.TestCase):
    def test_all_supported_crops_have_lifecycle_data(self):
        expected_crops = {
            "rice",
            "maize",
            "cotton",
            "jute",
            "sugarcane",
            "turmeric",
            "banana",
            "mango",
            "orange",
            "apple",
            "grapes",
            "pomegranate",
            "coconut",
            "coffee",
            "papaya",
            "watermelon",
            "muskmelon",
            "chickpea",
            "kidneybeans",
            "blackgram",
            "mungbean",
            "mothbeans",
            "pigeonpeas",
        }

        for crop in expected_crops:
            cfg = get_crop_catalog(crop)
            self.assertGreater(cfg["duration_days"], 0)
            self.assertTrue(cfg["growth_stages"])
            self.assertEqual(cfg["growth_stages"][0][1], 0)
            self.assertGreaterEqual(cfg["growth_stages"][-1][2], cfg["duration_days"])


if __name__ == "__main__":
    unittest.main()
