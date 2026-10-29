"""Master E2E Test Suite Runner for Apriori Web Application.

Assembles and executes all test suites across:
- Tier 1: Feature Coverage (Data Schema, Product Coverage, HTTP Routes, Admin Portal, Navbar)
- Tier 2: Boundary & Corner Cases (Empty Cart, Invalid SKUs, Edge Sliders, Rule Integrity, Boundary Lift)
- Tier 3: Cross-Feature Interactions (Pairwise Combinations)
- Tier 4: Real-World Workload Scenarios (Shopping Basket Journey, Admin Data Science Journey)

Usage:
    python3 tests/e2e/suite.py
    python3 -m unittest discover -s tests/e2e
"""
from __future__ import annotations

import os
import sys
import unittest

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.e2e.test_tier1_features import (
    TestTier1Feature1DataSchema,
    TestTier1Feature2ProductCoverage,
    TestTier1Feature3HTTPRoutes,
    TestTier1Feature4AdminPortal,
    TestTier1Feature5GlobalNavbar,
)
from tests.e2e.test_tier2_boundaries import (
    TestTier2EmptyCartAndStepper,
    TestTier2InvalidSKUs,
    TestTier2EdgeThresholds,
    TestTier2RuleIntegrity,
    TestTier2BoundaryLift,
)
from tests.e2e.test_tier3_interactions import (
    TestTier3CrossFeatureInteractions,
)
from tests.e2e.test_tier4_scenarios import (
    TestTier4ShoppingWorkflow,
    TestTier4AdminWorkflow,
)


def load_e2e_suite() -> unittest.TestSuite:
    """Load all E2E test cases into a structured TestSuite."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Tier 1: Feature Coverage
    suite.addTests(loader.loadTestsFromTestCase(TestTier1Feature1DataSchema))
    suite.addTests(loader.loadTestsFromTestCase(TestTier1Feature2ProductCoverage))
    suite.addTests(loader.loadTestsFromTestCase(TestTier1Feature3HTTPRoutes))
    suite.addTests(loader.loadTestsFromTestCase(TestTier1Feature4AdminPortal))
    suite.addTests(loader.loadTestsFromTestCase(TestTier1Feature5GlobalNavbar))

    # Tier 2: Boundary & Corner Cases
    suite.addTests(loader.loadTestsFromTestCase(TestTier2EmptyCartAndStepper))
    suite.addTests(loader.loadTestsFromTestCase(TestTier2InvalidSKUs))
    suite.addTests(loader.loadTestsFromTestCase(TestTier2EdgeThresholds))
    suite.addTests(loader.loadTestsFromTestCase(TestTier2RuleIntegrity))
    suite.addTests(loader.loadTestsFromTestCase(TestTier2BoundaryLift))

    # Tier 3: Cross-Feature Interactions
    suite.addTests(loader.loadTestsFromTestCase(TestTier3CrossFeatureInteractions))

    # Tier 4: Real-World Scenarios
    suite.addTests(loader.loadTestsFromTestCase(TestTier4ShoppingWorkflow))
    suite.addTests(loader.loadTestsFromTestCase(TestTier4AdminWorkflow))

    return suite


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    suite = load_e2e_suite()
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
