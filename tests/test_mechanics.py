"""Independent physical checks for the first milestone."""

import unittest
import numpy as np
from mechanics import solve_axial_bar


class AxialBarTests(unittest.TestCase):
    def test_known_example(self):
        r = solve_axial_bar(1.0, 0.001, 200e9, 1000.0)
        self.assertEqual(r.displacement_m[0], 0.0)
        self.assertAlmostEqual(r.displacement_m[-1], 5e-6, places=14)
        np.testing.assert_allclose(r.stress_pa, 1e6)
        np.testing.assert_allclose(r.strain, 5e-6)

    def test_equilibrium_and_kinematics(self):
        r = solve_axial_bar(0.8, 2e-4, 70e9, 500.0, 51)
        np.testing.assert_allclose(r.stress_pa * 2e-4, 500.0)
        np.testing.assert_allclose(np.gradient(r.displacement_m, r.x_m), r.strain)

    def test_zero_and_compression(self):
        r = solve_axial_bar(1, 0.001, 200e9, 0)
        np.testing.assert_array_equal(r.displacement_m, 0)
        r = solve_axial_bar(1, 0.001, 200e9, -1000)
        self.assertAlmostEqual(r.displacement_m[-1], -5e-6, places=14)

    def test_invalid_inputs(self):
        for key, value in [("length_m", 0), ("area_m2", -1),
                           ("youngs_modulus_pa", float("nan")),
                           ("force_n", float("inf")), ("n_points", 1),
                           ("n_points", 2.5), ("n_points", True)]:
            parameters = dict(length_m=1, area_m2=0.001, youngs_modulus_pa=200e9,
                              force_n=1000, n_points=201)
            parameters[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                solve_axial_bar(**parameters)


if __name__ == "__main__":
    unittest.main()
