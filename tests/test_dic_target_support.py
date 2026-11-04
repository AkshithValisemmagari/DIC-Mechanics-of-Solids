"""Regression tests for mask-aware integer initialization in both DIC paths."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from scipy.ndimage import binary_erosion

from dic import integer_match, run_dic
from dic_support import supported_subset_centres
from image_preprocessing import prepare_images
from stereo_dic import ImageMatcher


class TargetSupportTests(unittest.TestCase):
    def setUp(self):
        self.size = 9
        self.radius = 20
        self.centre = np.array([27, 27])
        self.bad = np.array([12, 27])
        self.good = np.array([42, 27])
        rng = np.random.default_rng(142)
        self.reference = rng.uniform(.2, .8, (96, 96))
        self.target = rng.uniform(.2, .8, (96, 96))
        template = self.reference[23:32, 23:32]
        for centre, noise in [(self.bad, 0), (self.good, .002)]:
            x, y = centre
            self.target[y-4:y+5, x-4:x+5] = template + rng.normal(0, noise, template.shape)
        self.mask = np.ones(self.reference.shape, bool)

    def target_mask(self, boundary):
        mask = self.mask.copy()
        if boundary == 'hole':
            yy, xx = np.indices(mask.shape)
            mask[(xx-self.bad[0])**2 + (yy-self.bad[1])**2 <= 4] = False
        else:
            mask[:, :20] = False
        return mask

    def flat(self, mask, **kwargs):
        return run_dic(self.reference, self.target, self.mask, mask,
                       subset_size=self.size, step=100, search_radius=self.radius, **kwargs)

    def stereo(self, mask):
        return (ImageMatcher(self.reference, self.mask, self.size),
                ImageMatcher(self.target, mask, self.size))

    def test_support_map_matches_exhaustive_windows_after_each_filter(self):
        rng = np.random.default_rng(91)
        image = rng.uniform(.2, .8, (39, 45))
        yy, xx = np.indices(image.shape)
        mask = (xx-21)**2 + (yy-19)**2 > 16
        for option in [0, .5, .7, 1, 'wiener']:
            with self.subTest(filter=option):
                _, masks, _ = prepare_images({'a': image}, {'a': mask}, option)
                processed = binary_erosion(masks['a'], iterations=3)
                actual = supported_subset_centres(processed, self.size)
                expected = np.zeros_like(processed)
                for y in range(6, image.shape[0]-6):
                    for x in range(6, image.shape[1]-6):
                        expected[y, x] = processed[y-4:y+5, x-4:x+5].all()
                np.testing.assert_array_equal(actual, expected)
        self.assertFalse(supported_subset_centres(np.ones((5, 7), bool), 9).any())

    def test_integer_search_excludes_invalid_peak_and_handles_no_support(self):
        template = self.reference[23:32, 23:32]
        search = self.target[3:52, 3:52]
        raw = integer_match(template, search)
        self.assertEqual(raw[:2], (20, 5))  # exact but unsupported copy
        centres = supported_subset_centres(binary_erosion(self.target_mask('hole'), iterations=3), 9)
        supported = centres[7:48, 7:48]
        selected = integer_match(template, search, supported)
        self.assertEqual(selected[:2], (20, 35))
        self.assertIsNone(integer_match(template, search, np.zeros_like(supported)))
        self.assertEqual(integer_match(template, search, np.ones_like(supported)), raw)

    def test_flat_and_stereo_choose_supported_alternative(self):
        for boundary in ['hole', 'edge']:
            with self.subTest(boundary=boundary):
                mask = self.target_mask(boundary)
                result = self.flat(mask)
                self.assertEqual(result.shape, (1, 11))
                self.assertEqual(result[0, -1], 0)
                np.testing.assert_allclose(result[0, 2:4], [15, 0], atol=.05)
                source, target = self.stereo(mask)
                for epipolar in [False, True]:
                    match, reason = source.match(target, self.centre, self.radius, epipolar=epipolar)
                    self.assertIsNone(reason)
                    np.testing.assert_allclose(match['point'], self.good, atol=.05)

    def test_no_supported_target_rejects_before_refinement(self):
        empty = np.zeros_like(self.mask)
        with patch('dic.least_squares', side_effect=AssertionError('Refinement must not run')):
            result = self.flat(empty)
        self.assertEqual(result[0, -1], 5)
        self.assertEqual(result[0, 9], 0)
        self.assertTrue(np.isnan(result[0, 2:9]).all())
        source, target = self.stereo(empty)
        with patch('stereo_dic.least_squares', side_effect=AssertionError('Refinement must not run')):
            for epipolar in [False, True]:
                match, reason = source.match(target, self.centre, self.radius, epipolar=epipolar)
                self.assertIsNone(match)
                self.assertEqual(reason, 'target_support')

    def test_interior_seeds_remain_identical(self):
        with patch('dic.integer_match', wraps=integer_match) as matcher:
            flat = self.flat(self.mask)
        template, search, support = matcher.call_args.args
        self.assertTrue(support.all())
        self.assertEqual(integer_match(template, search, support), integer_match(template, search))
        # Without invalid support, both paths still select the exact first copy.
        np.testing.assert_allclose(flat[0, 2:4], [-15, 0], atol=1e-7)
        self.assertEqual(flat[0, -1], 0)
        source, target = self.stereo(self.mask)
        match, reason = source.match(target, self.centre, self.radius)
        self.assertIsNone(reason)
        np.testing.assert_allclose(match['point'], self.bad, atol=1e-7)

    def test_final_support_checks_still_reject_refinement_into_hole(self):
        mask = self.target_mask('hole')
        # Force a nominally converged fit from the valid seed onto the invalid
        # copy. The real final geometric support checks must still reject it.
        fit = SimpleNamespace(x=np.array([-15., 0, 0, 0, 0, 0]),
                              fun=np.zeros(self.size**2), success=True)
        with patch('dic.least_squares', return_value=fit):
            result = self.flat(mask)
        self.assertEqual(result[0, -1], 5)
        self.assertEqual(result[0, 9], 0)
        source, target = self.stereo(mask)
        with patch('stereo_dic.least_squares', return_value=fit):
            match, reason = source.match(target, self.centre, self.radius)
        self.assertIsNone(match)
        self.assertEqual(reason, 'target_support')


if __name__ == '__main__':
    unittest.main()
