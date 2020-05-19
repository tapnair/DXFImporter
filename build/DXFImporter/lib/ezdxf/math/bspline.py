# Created: 2012.01.03
# Copyright (c) 2012-2018 Manfred Moitzi
# License: MIT License
"""
B-Splines
=========

https://www.cl.cam.ac.uk/teaching/2000/AGraphHCI/SMEG/node4.html

n + 1 ... number of control points P_1, P_2, ..., P_{n+1} or P_0, P_1, ..., P_n
k ... order of the B-spline, 2 <= k <= n + 1
degree ... k - 1

B-splines are a more general type of curve than Bezier curves. In a B-spline each control point is associated with a 
basis function.

(87) P(t) = sum {i=1}^{n+1} N_{i,k}(t) P_i, t_min <= t < t_max

There are n + 1 control points,  P_1, P_2, ..., P_{n+1}. The N_{i,k} basis functions are of order k(degree k-1). 
k must be at least 2 (linear), and can be no more than n+1 (the number of control points). The important point here is 
that the order of the curve (linear, quadratic, cubic,...) is therefore not dependent on the number of control points 
(which it is for Bezier curves, where k must always equal n+1).

Equation (87) defines a piecewise continuous function. A knot vector,  (t_1, t_2, ..., t_{k+(n+1)}), must be specified. 
This determines the values of t at which the pieces of curve join, like knots joining bits of string. It is necessary 
that:

(88)  t_i <= t_{i+1}, for all i

The N_{i,k} depend only on the value of k and the values in the knot vector. N is defined recursively as:

(89) N_{i,1}(t)	= 1 for t_i <= t < t_{i+1}; 0 otherwise
     N_{i,k}(t)	= (t-t_i) / ({t_{i+k-1} - t_i}) * N_{i,k-1}(t) + (t_{i+k}-t) / (t_{i+k} - t_{i+1}) * N_{i+1,k-1}(t)

This is essentially a modified version of the idea of taking linear interpolations of linear interpolations of linear 
interpolations ... n


The Knot Vector
---------------

The above explanation shows that the knot vector is very important. The knot vector can, by its definition, be any 
sequence of numbers provided that each one is greater than or equal to the preceding one. Some types of knot vector are 
more useful than others. Knot vectors are generally placed into one of three categories: uniform, open uniform, and 
non-uniform.

Uniform Knot Vector
~~~~~~~~~~~~~~~~~~~

These are knot vectors for which 

(90) t_{i+1} - t_i = constant, for all i

e.g. [1, 2, 3, 4, 5, 6, 7, 8], [0, .25, .5, .75, 1.]

Open Uniform Knot Vector
~~~~~~~~~~~~~~~~~~~~~~~~

These are uniform knot vectors which have k equal knot values at each end
 
(91) t_i = t_1,  i <= k
     t_{i+1} - t_i = constant, k <= i < n+2
     t_i = t_{k+(n+1)}, i >= n + 2

e.g. [0, 0, 0, 0, 1, 2, 3, 4, 4, 4, 4] for k=4, 
     [1, 1, 1, 2, 3, 4, 5, 6, 6, 6] for k=3
     [.1, .1, .1, .1, .1, .3, .5, .7, .7, .7, .7, .7] for k=5

Non-uniform Knot Vector
~~~~~~~~~~~~~~~~~~~~~~~

This is the general case, the only constraint being the standard  t_i <= t_{i+1}, for all i (Equations 88). 

e.g. [1, 3, 7, 22, 23, 23, 49, 50, 50]
     [1, 1, 1, 2, 2, 3, 4, 5, 6, 6, 6, 7, 7, 7]
     [.2, .7, .7, .7, 1.2, 1.2, 2.9, 3.6]

The shapes of the N_{i,k} basis functions are determined entirely by the relative spacing between the knots.
 
    scaling: t_i' = alpha * t_i, for all i
    translating t_i'= t_i + delta t, for all i
    
The knot vector has no effect on the shapes of the N_{i,k}.

The above gives a description of the various types of knot vector but it doesn't really give you any insight into how 
the knot vector determines the shape of the curve. The following subsections look at the different types of knot vector 
in more detail. However, the best way to get to feel for these is to derive and draw the basis functions yourself.

Uniform Knot Vector
~~~~~~~~~~~~~~~~~~~

For simplicity, let t_i = i (this is allowable given that the scaling or translating the knot vector has no effect on 
the shapes of the N_{i,k}). The knot vector thus becomes  [1,2,3, ... ,k+(n+1)] and equation (89) simplifies to:

(92) N_{i,1}(t)	= 1 for t_i <= t < t_{i+1}; 0 otherwise
     N_{i,k}(t)	= (t-i)(k-1) * N_{i,k-1}(t) + (i+k-t)/ (k-1) * N_{i+1,k-1}(t)

Things you can change about a uniform B-spline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With a uniform B-spline, you obviously cannot change the basis functions (they are fixed because all the knots are 
equi-spaced). However you can alter the shape of the curve by modifying a number of things:

Moving control points:

Moving the control points obviously changes the shape of the curve.

Multiple control points:

Sticking two adjacent control points on top of one another causes the curve to pass closer to that point. Stick enough 
adjacent control points on top of one another and you can make the curve pass through that point.

Order:

Increasing the order k increases the continuity of the curve at the knots, increases the smoothness of the curve, and 
tends to move the curve farther from its defining polygon.

Joining the ends:

You can join the ends of the curve to make a closed loop. Say you have M points,  P_1, ... P_M. You want a closed 
B-spline defined by these points. For a given order, k, you will need M+(k-1) control points (repeating the first k-1 
points):  P_1, ... P_M, P_1, ..., P_{k-1}. Your knot vector will thus have M+2k-1 uniformly spaced knots.

Open Uniform Knot Vector
~~~~~~~~~~~~~~~~~~~~~~~~

The previous section intimated that uniform B-splines can be used to describe closed curves: all you have to do is join 
the ends as described above. If you do not want a closed curve, and you use a uniform knot vector, you find that you 
need to specify control points at each end of the curve which the curve doesn't go near.

If you wish your B-spline to start and end at your first and last control points then you need an open uniform knot 
vector. The only difference between this and the uniform knot vector being that the open uniform version has k equal 
knots at each end.

An order k open uniform B-spline with n+1=k points is the Bezier curve of order k.

Non-uniform Knot Vector
~~~~~~~~~~~~~~~~~~~~~~~

Any B-spline whose knot vector is neither uniform nor open uniform is non-uniform. Non-uniform knot vectors allow any 
spacing of the knots, including multiple knots (adjacent knots with the same value). We need to know how this 
non-uniform spacing affects the basis functions in order to understand where non-uniform knot vectors could be useful. 

It transpires that there are only three cases of any interest: 

    1. multiple knots (adjacent knots equal)
    2. adjacent knots more closely spaced than the next knot in the vector
    3. adjacent knots less closely spaced than the next knot in the vector 
    
Obviously, case (3) is simply case (2) turned the other way round.

Multiple knots:

A multiple knot reduces the degree of continuity at that knot value. Across a normal knot the continuity is Ck-2. Each 
extra knot with the same value reduces continuity at that value by one. This is the only way to reduce the continuity of 
the curve at the knot values. If there are k-1 (or more) equal knots then you get a discontinuity in the curve.

Close knots:

As two knots' values get closer together, relative to the spacing of the other knots, the curve moves closer to the 
related control point.

Distant knots:

As two knots' values get further apart, relative to the spacing of the other knots, the curve moves further away from 
the related control point.

Use of Non-uniform Knot Vectors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Standard procedure is to use uniform or open uniform B-splines unless there is a very good reason not to do so. 
Moving two knots closer together tends to move the curve only slightly and so there is usually little point in doing it. 
This leads to the conclusion that the main use of non-uniform B-splines is to allow for multiple knots, which adjust the 
continuity of the curve at the knot values.

However, non-uniform B-splines are the general form of the B-spline because they incorporate open uniform and uniform 
B-splines as special cases. Thus we will talk about non-uniform B-splines when we mean the general case, incorporating 
both uniform and open uniform.

What can you do to control the shape of a B-spline?

    - Move the control points.
    - Add or remove control points.
    - Use multiple control points.
    - Change the order, k.
    - Change the type of knot vector.
    - Change the relative spacing of the knots.
    - Use multiple knot values in the knot vector.

What should the defaults be?

If there are no pressing reasons for doing otherwise, your B-spline should be defined as follows:

    - k=4 (cubic)
    - no multiple control points
    - uniform (for a closed curve) or open uniform (for an open curve) knot vector.


Rational B-splines
==================

https://www.cl.cam.ac.uk/teaching/2000/AGraphHCI/SMEG/node5.html:

Rational B-splines have all of the properties of non-rational B-splines plus the following two useful features:
They produce the correct results under projective transformations (while non-rational B-splines only produce the correct
results under affine transformations).

They can be used to represent lines, conics, non-rational B-splines; and, when generalised to patches, can represents
planes, quadrics, and tori.

The antonym of rational is non-rational. Non-rational B-splines are a special case of rational B-splines, just as
uniform B-splines are a special case of non-uniform B-splines. Thus, non-uniform rational B-splines encompass almost
every other possible 3D shape definition. Non-uniform rational B-spline is a bit of a mouthful and so it is generally
abbreviated to NURBS.

We have already learnt all about the the B-spline bit of NURBS and about the non-uniform bit. So now all we need to
know is the meaning of the rational bit and we will fully(?) understand NURBS.

Rational B-splines are defined simply by applying the B-spline equation (Equation 87) to homogeneous coordinates,
rather than normal 3D coordinates.

"""
from typing import List, Iterable, Sequence, TYPE_CHECKING, Dict, Tuple, Optional
from .vector import Vector, distance
from .matrix import Matrix
from math import pow, isclose
from ezdxf.lldxf.const import DXFValueError

if TYPE_CHECKING:
    from ezdxf.eztypes import Vertex


def open_uniform_knot_vector(n: int, order: int) -> List[float]:
    """
    Returns an open uniform knot vector for a B-spline of `order` and `n` control points.

    `order` = degree + 1

    Args:
        n: count of control points
        order: spline order

    """
    nplusc = n + order
    nplus2 = n + 2
    knots = [0.]
    for i in range(2, nplusc + 1):
        if (i > order) and (i < nplus2):
            knots.append(knots[-1] + 1.)
        else:
            knots.append(knots[-1])
    return knots


def is_uniform_knots(knots: Sequence[float], places: int = 4) -> bool:
    deltas = set(round(k2 - k1, ndigits=places) for k1, k2 in zip(knots, knots[1:]))
    return len(deltas) == 1


def uniform_knot_vector(n: int, order: int) -> List[float]:
    """
    Returns an uniform knot vector for a B-spline of `order` and `n` control points.

    `order` = degree + 1

    Args:
        n: count of control points
        order: spline order

    """
    return [float(knot_value) for knot_value in range(0, n + order)]


def required_knot_values(count: int, order: int) -> int:
    """
    Returns the count of required knot values for a B-spline of `order` and `count` control points.

    degree =  degree of B-spline, in math papers often called: `p`

    Args:
        count: count of control points, in math papers often called:  `n` + 1
        order: order of B-Spline, in math papers often called:  `k`

    Relationships:

    - `k` (order) = `p` (degree) + 1
    - 2 ≤ `k` (order) ≤ `n` + 1 (count)

    """
    k = order
    n = count - 1
    p = k - 1
    if not (2 <= k <= (n + 1)):
        raise DXFValueError('Invalid count/order combination')
    # n + p + 2 = count + order
    return n + p + 2


def uniform_t_vector(fit_points: Sequence) -> Iterable[float]:
    n = float(len(fit_points) - 1)
    for t in range(len(fit_points)):
        yield float(t) / n


def distance_t_vector(fit_points: Iterable['Vertex']):
    return centripetal_t_vector(fit_points, power=1)


def centripetal_t_vector(fit_points: Iterable['Vertex'], power: float = .5) -> Iterable[float]:
    distances = [pow(distance(p1, p2), power) for p1, p2 in zip(fit_points, fit_points[1:])]
    total_length = sum(distances)
    s = 0.
    yield s
    for d in distances:
        s += d
        yield s / total_length


def bspline_basis(u: float, index: int, degree: int, knots: Sequence[float]) -> float:
    """
    B-spline basis function.

    Simple recursive implementation for testing and comparison.

    Args:
        u: curve parameter in range [0 .. max(knots)]
        index: index of control point
        degree: degree of B-spline
        knots: knots vector

    Returns:
        float: basis value N_i,p(u)

    """
    cache = {}  # type: Dict[Tuple[int, int], float]
    u = float(u)

    def N(i: int, p: int) -> float:
        try:
            return cache[(i, p)]
        except KeyError:
            if p == 0:
                retval = 1 if knots[i] <= u < knots[i + 1] else 0.
            else:
                dominator = (knots[i + p] - knots[i])
                f1 = (u - knots[i]) / dominator * N(i, p - 1) if dominator else 0.

                dominator = (knots[i + p + 1] - knots[i + 1])
                f2 = (knots[i + p + 1] - u) / dominator * N(i + 1, p - 1) if dominator else 0.

                retval = f1 + f2
            cache[(i, p)] = retval
            return retval

    return N(int(index), int(degree))


def bspline_basis_vector(u: float, count: int, degree: int, knots: Sequence[float]) -> List[float]:
    """
    Create basis vector at parameter u.

    Used with the bspline_basis() for testing and comparison.

    Args:
        u: curve parameter in range [0 .. max(knots)]
        count: control point count (n + 1)
        degree: degree of B-spline (order = degree + 1)
        knots: knot vector

    Returns:
        List[float]: basis vector, len(basis) == count

    """
    assert len(knots) == (count + degree + 1)
    basis = [bspline_basis(u, index, degree, knots) for index in range(count)]  # type: List[float]
    if isclose(u, knots[-1]):  # pick up last point ??? why is this necessary ???
        basis[-1] = 1.
    return basis


def bspline_vertex(u: float, degree: int, control_points: Sequence['Vertex'], knots: Sequence[float]) -> Vector:
    """
    Calculate B-spline vertex at parameter u.

    Used with the bspline_basis_vector() for testing and comparison.

    Args:
        u:  curve parameter in range [0 .. max(knots)]
        degree: degree of B-spline (order = degree + 1)
        control_points: control points as list of (x, y[,z]) tuples
        knots: knot vector as list of floats, len(knots) == (count + order)

    """
    basis_vector = bspline_basis_vector(u, count=len(control_points), degree=degree, knots=knots)

    vertex = Vector()
    for basis, point in zip(basis_vector, control_points):
        vertex += Vector(point) * basis
    return vertex


def bspline_control_frame(fit_points: Iterable['Vertex'], degree: int = 3, method: str = 'distance', power: float = .5):
    """
    Generates the control points for the `B-spline`_ control frame by `Curve Global Interpolation`_.
    Given are the fit points and the degree of the B-spline. The function provides 3 methods for generating the
    parameter vector t:

    =================== ============================================================
    Method              Description
    =================== ============================================================
    ``'uniform'``       creates a uniform t vector, from ``0`` to ``1`` evenly spaced; see `uniform`_ method
    ``'distance'``      creates a t vector with values proportional to the fit point distances, see `chord length`_ method
    ``'centripetal'``   creates a t vector with values proportional to the fit point distances ^ ``power``; see `centripetal`_ method
    =================== ============================================================

    Args:
        fit_points: fit points of B-spline, as list of :class:`Vector` compatible objects
        degree: degree of B-spline
        method: calculation method for parameter vector t
        power: power for centripetal method

    Returns:
        :class:`BSpline`

    """

    def create_t_vector():
        if method == 'uniform':
            return uniform_t_vector(fit_points)  # equally spaced 0 .. 1
        elif method == 'distance':
            return distance_t_vector(fit_points)
        elif method == 'centripetal':
            return centripetal_t_vector(fit_points, power=power)
        else:
            raise DXFValueError('Unknown method: {}'.format(method))

    fit_points = Vector.list(fit_points)
    count = len(fit_points)
    order = degree + 1
    if order > count:
        raise DXFValueError('Need more fit points for degree {}'.format(degree))

    t_vector = list(create_t_vector())
    knots = list(control_frame_knots(count - 1, degree, t_vector))
    control_points = global_curve_interpolation(fit_points, degree, t_vector, knots)
    bspline = BSpline(control_points, order=order, knots=knots)
    bspline.t_array = t_vector
    return bspline


def bspline_control_frame_approx(fit_points: Iterable['Vertex'], count: int, degree: int = 3, method: str = 'distance',
                                 power: float = .5):
    """
    Approximate `B-spline`_ by a reduced count of control points, given are the fit points and the degree of
    the B-spline.

    Args:
        fit_points: all fit points of B-spline as :class:`Vector` compatible objects
        count: count of designated control points
        degree: degree of B-spline
        method: calculation method for parameter vector t, see :func:`bspline_control_frame`
        power: power for centripetal method

    Returns:
        :class:`BSpline`

    """

    def create_t_vector():
        if method == 'uniform':
            return uniform_t_vector(fit_points)  # equally spaced 0 .. 1
        elif method == 'distance':
            return distance_t_vector(fit_points)
        elif method == 'centripetal':
            return centripetal_t_vector(fit_points, power=power)
        else:
            raise DXFValueError('Unknown method: {}'.format(method))

    fit_points = list(fit_points)
    order = degree + 1
    if order > count:
        raise DXFValueError('More control points for degree {} required.'.format(degree))

    t_vector = list(create_t_vector())
    knots = list(control_frame_knots(len(fit_points) - 1, degree, t_vector))
    control_points = global_curve_approximation(fit_points, count, degree, t_vector, knots)
    bspline = BSpline(control_points, order=order)
    return bspline


def control_frame_knots(n: int, p: int, t_vector: Iterable[float]) -> Iterable[float]:
    """
    Generates a 'clamped' knot vector for control frame creation. All knot values in the range [0 .. 1].

    Args:
        n: count fit points - 1
        p: degree of spline
        t_vector: parameter vector, length(t_vector) == n+1

    Returns:
        Iterable[float]: n+p+2 knot values

    """
    order = int(p + 1)
    if order > (n + 1):
        raise DXFValueError('Invalid n/p combination')

    t_vector = [float(t) for t in t_vector]
    for _ in range(order):  # clamped spline has 'order' leading 0s
        yield t_vector[0]
    for j in range(1, n - p + 1):
        yield sum(t_vector[j: j + p]) / p
    for _ in range(order):  # clamped spline has 'order' appended 1s
        yield t_vector[-1]


def global_curve_interpolation(fit_points: Sequence['Vertex'],
                               degree: int,
                               t_vector: Iterable[float],
                               knots: Iterable[float]) -> List[Vector]:
    """ Algorithm: http://pages.mtu.edu/~shene/COURSES/cs3621/NOTES/INT-APP/CURVE-INT-global.html """
    def create_matrix_N():
        spline = Basis(knots=knots, order=degree + 1, count=len(fit_points))
        return Matrix([spline.basis(t) for t in t_vector])

    matrix_N = create_matrix_N()
    control_points = matrix_N.gauss_matrix(fit_points)
    return Vector.list(control_points.rows())


def global_curve_approximation(fit_points: Iterable['Vertex'],
                               count: int,
                               degree: int,
                               t_vector: Iterable[float],
                               knots: Iterable[float]) -> List[Vector]:
    """
    Approximate `B-spline`_ by a reduced count of control points, given are the fit points and the degree of the B-spline.

    Args:
        fit_points: all B-spline fit points as :class:`Vector` compatible objects
        count: count of designated control points
        degree: degree of B-spline
        t_vector: parameter vector
        knots: knot vector

    Returns:
        List[Vector]: control points

    """
    # source: http://pages.mtu.edu/~shene/COURSES/cs3621/NOTES/INT-APP/CURVE-APP-global.html
    fit_points = Vector.list(fit_points)  # data points D
    n = len(fit_points) - 1
    h = count - 1
    d0 = fit_points[0]
    dn = fit_points[n]
    spline = Basis(knots, order=degree + 1, count=len(fit_points))
    # matrix_N[0] == row 0
    matrix_N = [spline.basis(t) for t in t_vector]  # 0 .. n

    def Q(k):
        ntk = matrix_N[k]
        return fit_points[k] - d0 * ntk[0] - dn * ntk[h]

    # matrix_Q[0] == row 1
    matrix_Q = [sum(Q(k) * matrix_N[k][i] for k in range(1, n)) for i in range(1, h)]
    matrix_N = Matrix([row[1:h] for row in matrix_N[1:-1]])
    matrix_M = matrix_N.transpose() * matrix_N
    P = matrix_M.gauss_matrix(matrix_Q)
    control_points = [d0]
    control_points.extend(Vector.generate(P.rows()))
    control_points.append(dn)
    return control_points


class Basis:
    def __init__(self, knots: Iterable[float], order: int, count: int, weights: Sequence[float] = None):
        self.knots = list(knots)  # type: List[float]
        self.order = order  # type: int
        self.count = count  # type: int
        self.weights = weights  # type: Optional[Sequence[float]]

    @property
    def max_t(self) -> float:
        return self.knots[-1]

    @property
    def nplusc(self) -> int:
        return self.count + self.order

    def create_nbasis(self, t: float) -> List[float]:
        """
        Calculate the first order basis functions N[i][1]

        Returns: list of basis values

        """
        return [1. if k1 <= t < k2 else 0. for k1, k2 in zip(self.knots, self.knots[1:])]

    def basis(self, t: float) -> List[float]:
        knots = self.knots
        nbasis = self.create_nbasis(t)
        # calculate the higher order basis functions
        for k in range(2, self.order + 1):
            for i in range(self.nplusc - k):
                d = ((t - knots[i]) * nbasis[i]) / (knots[i + k - 1] - knots[i]) if nbasis[i] != 0. else 0.
                e = ((knots[i + k] - t) * nbasis[i + 1]) / (knots[i + k] - knots[i + 1]) if nbasis[i + 1] != 0. else 0.
                nbasis[i] = d + e
        if isclose(t, self.max_t):  # pick up last point
            nbasis[self.count - 1] = 1.
        if self.weights is None:
            return nbasis[:self.count]
        else:
            return self.weighting(nbasis[:self.count])

    def weighting(self, nbasis: Iterable[float]) -> List[float]:
        products = [nb * w for nb, w in zip(nbasis, self.weights)]
        s = sum(products)
        return [0.0] * self.count if s == 0.0 else [p / s for p in products]


class DBasis(Basis):
    def basis(self, t: float) -> Tuple[List[float], List[float], List[float]]:
        knots = self.knots
        nbasis = self.create_nbasis2(t)
        d1nbasis = [0.] * self.nplusc
        d2nbasis = d1nbasis[:]

        for k in range(2, self.order + 1):
            for i in range(self.nplusc - k):
                # calculate basis functions
                b1 = ((t - knots[i]) * nbasis[i]) / (knots[i + k - 1] - knots[i]) if nbasis[i] != 0. else 0.
                b2 = ((knots[i + k] - t) * nbasis[i + 1]) / (knots[i + k] - knots[i + 1]) if nbasis[i + 1] != 0. else 0.

                # calculate first derivative
                f1 = nbasis[i] / (knots[i + k - 1] - knots[i]) if nbasis[i] != 0. else 0.
                f2 = -nbasis[i + 1] / (knots[i + k] - knots[i + 1]) if nbasis[i + 1] != 0. else 0.
                f3 = ((t - knots[i]) * d1nbasis[i]) / (knots[i + k - 1] - knots[i]) if d1nbasis[i] != 0. else 0.
                f4 = ((knots[i + k] - t) * d1nbasis[i + 1]) / (knots[i + k] - knots[i + 1]) if d1nbasis[
                                                                                                   i + 1] != 0. else 0.

                # calculate second derivative
                s1 = (2 * d1nbasis[i]) / (knots[i + k - 1] - knots[i]) if d1nbasis[i] != 0. else 0.
                s2 = (-2 * d1nbasis[i + 1]) / (knots[i + k] - knots[i + 1]) if d1nbasis[i + 1] != 0. else 0.
                s3 = ((t - knots[i]) * d2nbasis[i]) / (knots[i + k - 1] - knots[i]) if d2nbasis[i] != 0. else 0.
                s4 = ((knots[i + k] - t) * d2nbasis[i + 1]) / (knots[i + k] - knots[i + 1]) if d2nbasis[
                                                                                                   i + 1] != 0. else 0.

                nbasis[i] = b1 + b2
                d1nbasis[i] = f1 + f2 + f3 + f4
                d2nbasis[i] = s1 + s2 + s3 + s4

        count = self.count
        if self.weights is None:
            return nbasis[:count], d1nbasis[:count], d2nbasis[:count]
        else:
            self.weighting(nbasis[:count]), self.weighting(d1nbasis[:count]), self.weighting(d2nbasis[:count])

    def create_nbasis2(self, t: float) -> List[float]:
        nbasis = self.create_nbasis(t)
        if isclose(t, self.max_t):
            nbasis[self.count - 1] = 1.
        return nbasis


class DBasisU(DBasis):
    def create_nbasis2(self, t: float) -> List[float]:
        nbasis = self.create_nbasis(t)
        if isclose(t, self.knots[self.count]):
            nbasis[self.count - 1] = 1.
            nbasis[self.count] = 0.
        return nbasis


class BSpline:
    """
    Calculate the points of a `B-spline`_ curve, using an uniform open `knot`_ vector ("clamped").

    Accepts 2D points as definition points, but output is always 3D (z-axis = ``0``).

    Args:
        control_points: iterable of control points as :class:`Vector` compatible objects
        order: spline order
        knots: iterable of knot values
        weights: iterable of weight values

    """

    def __init__(self, control_points: Iterable['Vertex'],
                 order: int = 4,
                 knots: Iterable[float] = None,
                 weights: Iterable[float] = None):
        self.control_points = Vector.list(control_points)
        self.order = order
        if order > self.count:
            raise DXFValueError('Invalid need more control points for order {}'.format(order))

        if knots is None:
            knots = open_uniform_knot_vector(self.count, self.order)
        else:
            knots = list(knots)
            if len(knots) != self.nplusc:
                raise ValueError("{} knot values required, got {}.".format(self.nplusc, len(knots)))

        self.basis = Basis(knots, self.order, self.count, weights=weights)

    @property
    def nplusc(self) -> int:
        return self.count + self.order

    @property
    def count(self) -> int:
        """ Count of control points, (n + 1 in math definition). """
        return len(self.control_points)

    @property
    def max_t(self) -> float:
        """ Biggest `knot`_ value. """
        return self.basis.max_t

    @property
    def degree(self) -> int:
        """ Degree (p) of B-spline = order - 1 """
        return self.order - 1

    def knot_values(self) -> List[float]:
        """ Returns a list of `knot`_ values as floats, the knot vector always has order+count values
        (n + p + 2 in math definition).
        """
        return self.basis.knots

    def basis_values(self, t: float) -> List[float]:
        """ Returns the `basis`_ vector for position t. """
        return self.basis.basis(t)

    def step_size(self, segments: int) -> float:
        return self.max_t / float(segments)

    def approximate(self, segments: int = 20) -> Iterable[Vector]:
        """ Approximates the whole B-spline from 0 to max_t, by line segments as a list of vertices, vertices count =
        segments + 1.
        """
        step = self.step_size(segments)
        for point_index in range(segments + 1):
            yield self.point(point_index * step)

    def point(self, t: float) -> Vector:
        """
        Get point at SplineCurve(t) as tuple (x, y, z).

        Args:
            t: parameter in range [0, max_t]

        Returns: Vector(x, y, z)

        """
        if isclose(t, self.max_t):
            t = self.max_t

        p = Vector()
        for control_point, basis in zip(self.control_points, self.basis_values(t)):
            p += control_point * basis
        return p

    def insert_knot(self, t: float) -> None:
        """
        Insert additional knot, without altering the curve shape.

        Args:
            t: position of new knot 0 < t < max_t

        """
        if self.basis.weights is not None:
            raise DXFValueError('Rational splines not supported.')

        knots = self.basis.knots
        cpoints = self.control_points
        p = self.degree

        def find_knot_index() -> int:
            for knot_index in range(1, len(knots)):
                if knots[knot_index - 1] <= t < knots[knot_index]:
                    return knot_index - 1

        def new_point(index: int) -> Vector:
            a = (t - knots[index]) / (knots[index + p] - knots[index])
            return cpoints[index - 1] * (1 - a) + cpoints[index] * a

        if t <= 0. or t >= self.max_t:
            raise DXFValueError('Invalid position t')

        k = find_knot_index()
        if k < p:
            raise DXFValueError('Invalid position t')

        cpoints[k - p + 1:k] = [new_point(i) for i in range(k - p + 1, k + 1)]
        knots.insert(k + 1, t)  # knot[k] <= t < knot[k+1]
        self.basis.count = len(cpoints)


class BSplineU(BSpline):
    """
    Subclass of :class:`BSpline`

    Calculate the points of a `B-spline`_ curve, uniform (periodic) `knot`_ vector (`open curve`_).

    """

    def __init__(self, control_points: Iterable['Vertex'], order: int = 4, weights: Iterable[float] = None):
        control_points = list(control_points)
        knots = uniform_knot_vector(len(control_points), order)
        super().__init__(control_points, order=order, knots=knots, weights=weights)

    def step_size(self, segments: int) -> float:
        return float(self.count - self.order + 1) / segments

    def approximate(self, segments=20) -> Iterable[Vector]:
        step = self.step_size(segments)
        base = float(self.order - 1)
        for point_index in range(segments + 1):
            yield self.point(base + point_index * step)

    def t_array(self) -> List[float]:
        raise NotImplemented


class BSplineClosed(BSplineU):
    """
    Subclass of :class:`BSpline`

    Calculate the points of a closed uniform `B-spline`_ curve (`closed curve`_).

    """

    def __init__(self, control_points: Iterable['Vertex'], order: int = 4, weights: Iterable[float] = None):
        # control points wrap around
        points = list(control_points)
        points.extend(points[:order - 1])
        if weights is not None:
            weights = list(weights)
            weights.extend(weights[:order - 1])
        super().__init__(points, order=order, weights=weights)


class DerivativePoint:  # Mixin
    def point(self, t: float) -> Tuple[Vector, Vector, Vector]:
        """
        Get point, 1st and 2nd derivative at B-spline(t) as tuple (p, d1, d3),
        where p, d1 and d2 are :class:`Vector` objects.

        Args:
            t: parameter in range [0, max_t]

        """
        if isclose(self.max_t, t):
            t = self.max_t

        nbasis, d1nbasis, d2nbasis = self.basis_values(t)
        point = Vector()
        d1 = Vector()
        d2 = Vector()
        for i, control_point in enumerate(self.control_points):
            point += control_point * nbasis[i]
            d1 += control_point * d1nbasis[i]
            d2 += control_point * d2nbasis[i]
        return point, d1, d2


class DBSpline(DerivativePoint, BSpline):
    """
    Subclass of :class:`BSpline`

    Calculate points and derivative of a `B-spline`_ curve, using an uniform open `knot`_ vector (`clamped curve`_).

    """

    def __init__(self, control_points: Iterable['Vertex'],
                 order: int = 4,
                 knots: Iterable[float] = None,
                 weights: Iterable[float] = None):
        super().__init__(control_points, order=order, knots=knots, weights=weights)
        self.basis = DBasis(self.knot_values(), self.order, self.count)


class DBSplineU(DerivativePoint, BSplineU):
    """
    Subclass of :class:`DBSpline`

    Calculate points and derivative of a `B-spline`_ curve, uniform (periodic) `knot`_ vector (`open curve`_).

    """

    def __init__(self, control_points: Iterable['Vertex'], order: int = 4, weights: Iterable[float] = None):
        super().__init__(control_points, order=order, weights=weights)
        self.basis = DBasisU(self.knot_values(), self.order, self.count)


class DBSplineClosed(DerivativePoint, BSplineClosed):
    """
    Subclass of :class:`DBSpline`

    Calculate the points and derivative of a closed uniform `B-spline`_ curve (`closed curve`_).

    UNTESTED!
    """

    def __init__(self, control_points: Iterable['Vertex'], order: int = 4, weights: Iterable[float] = None):
        super().__init__(control_points, order=order, weights=weights)
        self.basis = DBasisU(self.knot_values(), self.order, self.count)
