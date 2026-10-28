import unittest
from pathlib import Path
from unittest.mock import patch

import tools


class SearchQualityTests(unittest.TestCase):
    def test_plain_iphone_search_excludes_applecare_bundles(self):
        model = tools._iphone_model_key("iphone 16")
        self.assertTrue(tools._matches_requested_iphone("iPhone 16 128 GB Black", "iphone 16", model))
        self.assertFalse(tools._matches_requested_iphone("iPhone 16 128 GB TealWith Apple Care", "iphone 16", model))
        self.assertTrue(tools._matches_requested_iphone("iPhone 16 128 GB Teal with Apple Care", "iphone 16 with AppleCare", model))

    def test_provider_html_entities_are_decoded_as_plain_text(self):
        self.assertEqual(tools._clean_product_title("Compare&#x20;prices"), "Compare prices")

    def test_ambiguous_calendar_delivery_label_is_suppressed(self):
        self.assertEqual(tools._usable_delivery_estimate("Thu, 5 Nov"), "")
        self.assertEqual(tools._usable_delivery_estimate("Tomorrow"), "Tomorrow")
        self.assertEqual(tools._usable_delivery_estimate("2-3 days"), "2-3 days")

    def test_home_page_uses_structured_category_controls(self):
        template = (Path(__file__).parents[1] / "templates" / "index.html").read_text(encoding="utf-8")
        self.assertIn("What are you shopping for?", template)
        self.assertEqual(template.count('class="category"'), 6)
        self.assertNotIn(">hat are you shopping for?", template)

    @patch("tools._coordinates_for_location", return_value=(25.6, 85.1))
    @patch("tools.requests.get")
    def test_live_offer_normalization_filters_bundles_and_date_only_sla(self, mock_get, _coordinates):
        class Response:
            def raise_for_status(self):
                pass

            def json(self):
                return {"data": {"results": {"Amazon": [
                    {"name": "iPhone 16 128 GB Black", "offer_price": "76999", "url": "https://amazon.in/dp/black", "platform": {"name": "Amazon", "sla": "Thu, 5 Nov"}},
                    {"name": "iPhone 16 128 GB TealWith Apple Care", "offer_price": "85494", "url": "https://amazon.in/dp/teal"},
                ], "Flipkart": []}}}

        mock_get.return_value = Response()
        with patch.object(tools, "QUICKCOMMERCE_API_KEY", "test-key"):
            results = tools.fetch_market_data("iphone 16", location="Patna")

        self.assertEqual(len(results["shopping"]), 1)
        self.assertEqual(results["shopping"][0]["title"], "iPhone 16 128 GB Black")
        self.assertNotIn("delivery", results["shopping"][0])


if __name__ == "__main__":
    unittest.main()
