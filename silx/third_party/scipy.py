# coding: utf-8
# /*##########################################################################
#
# Copyright (c) 2017-2018 European Synchrotron Radiation Facility
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
# ###########################################################################*/
"""Wrapper module for scipy features used in silx.

Uses a local copy of `scipy.spatial.Delaunay` and
`scipy.interpolate.LinearNDInterpolator` if available,
else it loads it from `scipy`.

It should be used like that:

.. code-block::

    from silx.third_party.scipy import Delaunay, LinearNDInterpolator

"""

from __future__ import absolute_import

__authors__ = ["T. Vincent"]
__license__ = "MIT"
__date__ = "07/11/2017"

try:
    # try to import silx local copy of LinearNDInterpolator
    from ._local.scipy import LinearNDInterpolator  # noqa
except ImportError:
    # else import it from the python path
    from scipy.interpolate import LinearNDInterpolator  # noqa

try:
    # try to import silx local copy of Delaunay
    from ._local.scipy import Delaunay  # noqa
except ImportError:
    # else import it from the python path
    from scipy.spatial import Delaunay  # noqa

__all__ = ['Delaunay', 'LinearNDInterpolator']
