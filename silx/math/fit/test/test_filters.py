# coding: utf-8
# /*##########################################################################
# Copyright (C) 2016 European Synchrotron Radiation Facility
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# ############################################################################*/
import numpy
import unittest
from silx.math.fit import filters
from silx.math.fit import functions

# TODO:
#     - snip1d
#     - snip2d

#     - snip3d
#     - strip

class Test_smooth(unittest.TestCase):
    """
    Unit tests of smoothing functions.

    Test that the difference between a synthetic curve with 5% added random
    noise and the result of smoothing that signal is less than 5%. We compare
    the sum of all samples in each curve.
    """
    def setUp(self):
        x = numpy.arange(5000)
        # (height1, center1, fwhm1, beamfwhm...)
        slit_params = (50, 500, 200, 100,
                        50, 600, 80, 30,
                        20, 2000, 150, 150,
                        50, 2250, 110, 100,
                        40, 3000, 50, 10,
                        23, 4980, 250, 20)

        self.y1 = functions.sum_slit(x, *slit_params)
        # 5% noise
        noise1 = 2 * numpy.random.random(5000) - 1
        noise1 *= 0.05
        self.y1 *= (1 + noise1)


        # (height1, center1, fwhm1...)
        step_params = (50, 500, 200,
                       50, 600, 80,
                       20, 2000, 150,
                       50, 2250, 110,
                       40, 3000, 50,
                       23, 4980, 250,)

        self.y2 = functions.sum_upstep(x, *step_params)
        # 5% noise
        noise2 = 2 * numpy.random.random(5000) - 1
        noise2 *= 0.05
        self.y2 *= (1 + noise2)

        self.y3 = functions.sum_downstep(x, *step_params)
        # 5% noise
        noise3 = 2 * numpy.random.random(5000) - 1
        noise3 *= 0.05
        self.y3 *= (1 + noise3)

    def tearDown(self):
        pass

    def testSavitskyGolay(self):
        npts = 25
        for y in [self.y1, self.y2, self.y3]:
            smoothed_y = filters.savitsky_golay(y, npoints=npts)

            # we added +-5% of random noise. The difference must be much lower
            # than 5%.
            diff = abs(sum(smoothed_y) - sum(y)) / sum(y)
            self.assertLess(diff, 0.05,
                            "Difference between data with 5%% noise and " +
                            "smoothed data is > 5%% (%f %%)" % (diff * 100))
            # Try various smoothing levels
            npts += 25

test_cases = (Test_smooth,)

def suite():
    loader = unittest.defaultTestLoader
    test_suite = unittest.TestSuite()
    for test_class in test_cases:
        tests = loader.loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    return test_suite

if __name__ == '__main__':
    unittest.main(defaultTest="suite")
