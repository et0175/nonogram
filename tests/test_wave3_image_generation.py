"""Wave 3 tests: Image-based batch generation.

CARD-505 deleted the 22 tests this file used to declare whose body was only
a docstring and ``pass``: they asserted nothing, so a green run of them was a
coverage claim with no evidence behind it.
"""

import pytest


class TestImageSelection:
    """Tests for image selection and upload (CARD-004p)."""

    @pytest.mark.integration
    def test_image_selection_page_loads(self, client):
        """Test that image selection page renders."""
        response = client.get("/batch/select-images")
        assert response.status_code == 200
        # TODO: assert "select images" in response.data.decode()
