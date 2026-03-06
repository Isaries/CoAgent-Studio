"""Courses have been replaced by Spaces — these legacy tests are skipped."""

import pytest

pytestmark = pytest.mark.skip(reason="Courses endpoint replaced by Spaces")
