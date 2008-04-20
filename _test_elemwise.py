
import time
import unittest

from gof import Result, Op, Env, modes
import gof

from scalar import *

import tensor
from elemwise import *


def inputs():
    x = modes.build(Tensor('float64', (0, 0), name = 'x'))
    y = modes.build(Tensor('float64', (1, 0), name = 'y'))
    z = modes.build(Tensor('float64', (0, 0), name = 'z'))
    return x, y, z

def env(inputs, outputs, validate = True, features = []):
    return Env(inputs, outputs, features = features, consistency_check = validate)


class _test_DimShuffle(unittest.TestCase):

    def with_linker(self, linker):
        for xsh, shuffle, zsh in [((2, 3), (1, 'x', 0), (3, 1, 2)),
                                  ((1, 2, 3), (1, 2), (2, 3)),
                                  ((1, 2, 1, 3), (1, 3), (2, 3)),
                                  ((2, 3, 4), (2, 1, 0), (4, 3, 2)),
                                  ((2, 3, 4), ('x', 2, 1, 0, 'x'), (1, 4, 3, 2, 1)),
                                  ((1, 4, 3, 2, 1), (3, 2, 1), (2, 3, 4)),
                                  ((1, 1, 4), (1, 2), (1, 4))]:
            x = modes.build(Tensor('float64', [1 * (entry == 1) for entry in xsh], name = 'x'))
            e = DimShuffle(x, shuffle).out
#             print shuffle, e.owner.grad(e.owner.inputs, e.owner.outputs).owner.new_order
            f = linker(env([x], [e])).make_function(inplace=False)
            assert f(numpy.ones(xsh)).shape == zsh

    def test_perform(self):
        self.with_linker(gof.PerformLinker)


class _test_Broadcast(unittest.TestCase):

    def with_linker(self, linker):
        for xsh, ysh in [((3, 5), (3, 5)),
                         ((3, 5), (1, 5)),
                         ((3, 5), (3, 1)),
                         ((1, 5), (5, 1)),
                         ((1, 1), (1, 1)),
                         ((2, 3, 4, 5), (2, 3, 4, 5)),
                         ((2, 3, 4, 5), (1, 3, 1, 5)),
                         ((2, 3, 4, 5), (1, 1, 1, 1)),
                         ((), ())]:
            x = modes.build(Tensor('float64', [1 * (entry == 1) for entry in xsh], name = 'x'))
            y = modes.build(Tensor('float64', [1 * (entry == 1) for entry in ysh], name = 'y'))
            e = Broadcast(Add, (x, y)).out
            f = linker(env([x, y], [e])).make_function(inplace = False)
#             xv = numpy.array(range(numpy.product(xsh)))
#             xv = xv.reshape(xsh)
#             yv = numpy.array(range(numpy.product(ysh)))
#             yv = yv.reshape(ysh)
            xv = numpy.asarray(numpy.random.rand(*xsh))
            yv = numpy.asarray(numpy.random.rand(*ysh))
            zv = xv + yv

#             print "AAAAAAAAAAAAAAAAAA"
#             print f(xv, yv)
#             print zv
#             print "BBBBBBBBBBBBBBBBBB"
            self.failUnless((f(xv, yv) == zv).all())

    def with_linker_inplace(self, linker):
        for xsh, ysh in [((5, 5), (5, 5)),
                         ((5, 5), (1, 5)),
                         ((5, 5), (5, 1)),
                         ((1, 1), (1, 1)),
                         ((2, 3, 4, 5), (2, 3, 4, 5)),
                         ((2, 3, 4, 5), (1, 3, 1, 5)),
                         ((2, 3, 4, 5), (1, 1, 1, 1)),
                         ((), ())]:
            x = modes.build(Tensor('float64', [1 * (entry == 1) for entry in xsh], name = 'x'))
            y = modes.build(Tensor('float64', [1 * (entry == 1) for entry in ysh], name = 'y'))
            e = Broadcast(Add, (x, y), {0:0}).out
            f = linker(env([x, y], [e])).make_function(inplace = False)
            xv = numpy.asarray(numpy.random.rand(*xsh))
            yv = numpy.asarray(numpy.random.rand(*ysh))
            zv = xv + yv

            f(xv, yv)

            self.failUnless((xv == zv).all())

    def test_perform(self):
        self.with_linker(gof.PerformLinker)

    def test_c(self):
        self.with_linker(gof.CLinker)

    def test_perform_inplace(self):
        self.with_linker_inplace(gof.PerformLinker)

    def test_c_inplace(self):
        self.with_linker_inplace(gof.CLinker)

    def test_fill(self):
        x = modes.build(Tensor('float64', [0, 0], name = 'x'))
        y = modes.build(Tensor('float64', [1, 1], name = 'y'))
        e = Broadcast(Second, (x, y), {0:0}).out
        f = gof.CLinker(env([x, y], [e])).make_function(inplace = False)
        xv = numpy.ones((5, 5))
        yv = numpy.random.rand(1, 1)
        f(xv, yv)
        assert (xv == yv).all()

    def test_weird_strides(self):
        x = modes.build(Tensor('float64', [0, 0, 0, 0, 0], name = 'x'))
        y = modes.build(Tensor('float64', [0, 0, 0, 0, 0], name = 'y'))
        e = Broadcast(Add, (x, y)).out
        f = gof.CLinker(env([x, y], [e])).make_function(inplace = False)
        xv = numpy.random.rand(2, 2, 2, 2, 2)
        yv = numpy.random.rand(2, 2, 2, 2, 2).transpose(4, 0, 3, 1, 2)
        zv = xv + yv
        assert (f(xv, yv) == zv).all()

    def test_same_inputs(self):
        x = modes.build(Tensor('float64', [0, 0], name = 'x'))
        e = Broadcast(Add, (x, x)).out
        f = gof.CLinker(env([x], [e])).make_function(inplace = False)
        xv = numpy.random.rand(2, 2)
        zv = xv + xv
        assert (f(xv) == zv).all()


class _test_CAReduce(unittest.TestCase):

    def with_linker(self, linker):
        for xsh, tosum in [((5, 6), (0, 1)),
                           ((5, 6), (0, )),
                           ((5, 6), (1, )),
                           ((5, 6), ()),
                           ((2, 3, 4, 5), (0, 1, 3)),
                           ((), ())]:
            x = modes.build(Tensor('float64', [1 * (entry == 1) for entry in xsh], name = 'x'))
            e = CAReduce(Add, [x], axis = tosum).out
            f = linker(env([x], [e])).make_function(inplace = False)
            xv = numpy.asarray(numpy.random.rand(*xsh))
            zv = xv
            for axis in reversed(sorted(tosum)):
                zv = numpy.add.reduce(zv, axis)
#             print "AAAAAAAAAAAAAAAAAA"
#             print xsh, tosum
#             print f(xv)
#             print zv
#             print f(xv) - zv
#             print "BBBBBBBBBBBBBBBBBB"
            self.failUnless((numpy.abs(f(xv) - zv) < 1e-10).all())

    def test_perform(self):
        self.with_linker(gof.PerformLinker)

    def test_c(self):
        self.with_linker(gof.CLinker)
        

if __name__ == '__main__':
    unittest.main()
    
# #     x = modes.build(Tensor('int32', [0, 0], name = 'x'))
# #     y = modes.build(Tensor('int32', [0, 0], name = 'y'))
#     from scalar import Scalar, composite
#     x = modes.build(Tensor('float64', [0, 0], name = 'x'))
#     y = modes.build(Tensor('float64', [0, 0], name = 'y'))
#     xs, ys = Scalar('float64'), Scalar('float64')
#     e = Broadcast(composite([xs, ys], [(xs * ys) + (xs / ys) * 7.0]), (x, y)).out
#     f = gof.CLinker(env([x, y], [e])).make_function(inplace = False)
#     size = 2000
#     xv = numpy.random.rand(size, size)
#     yv = numpy.random.rand(size, size)
#     zv = numpy.random.rand(size, size)
# #     xv = numpy.random.randint(1, 5, (1000, 1000))
# #     yv = numpy.random.randint(1, 5, (1000, 1000))

# #     t0 = time.time()
# #     for i in xrange(100):
# #         xv / yv
# #     print time.time() - t0

# #     t0 = time.time()
# #     for i in xrange(10):
# #         f(xv, yv)
# #     print time.time() - t0

# #     t0 = time.time()
# #     for i in xrange(10):
# #         (xv * yv) + (xv / yv) * 7.0
# #     print time.time() - t0

#     from scipy import weave
#     import numpy
#     t0 = time.time()
#     for i in xrange(10):
#         weave.blitz("zv = dot(xv, yv)", locals())
#     print time.time() - t0

    # speed ratios:
    # add : 1
    # mul : 1
    # div : 2
    # pow : 20



#     def test_straightforward(self):
#         x, y, z = inputs()
#         e0 = CAReduce(Add, [x]).out
# #        print e0.owner
#         f = gof.PerformLinker(env([x], [e0])).make_function(inplace=True)
#         assert f(numpy.ones((2, 2))) == 4.0
##########

##########
#     def test_straightforward(self):
#         x, y, z = inputs()
#         e0 = Broadcast(Add, (x, y)).out
#         f = gof.PerformLinker(env([x, y], [e0])).make_function(inplace=True)
#         assert (f(numpy.ones((2, 2)), numpy.ones((1, 2))) == numpy.ones((2, 2))*2).all()
# #         for result in e0.owner.grad(e0.owner.inputs, (z, )):
# #             print env([x, y, z], [result])

#     def test_c(self):
#         x = modes.build(Tensor('float64', (0, 0), name = 'x'))
#         y = modes.build(Tensor('float64', (0, 1), name = 'y'))
#         z = modes.build(Tensor('float64', (0, 0), name = 'z'))
# #        x = modes.build(Tensor('float64', (), name = 'x'))
# #        y = modes.build(Tensor('float64', (), name = 'y'))
# #        x, y, z = inputs()
#         e0 = Broadcast(Add, (x, y)).out
#         f = gof.CLinker(env([x, y], [e0])).make_function(inplace=True)
#         print f(numpy.ones((4, 4), order = 'f'), numpy.array([[1], [2], [3], [4]]))
# #        print f(numpy.ones(()), numpy.ones(()))
#         assert (f(numpy.ones((2, 2)), numpy.ones((2, 1))) == numpy.ones((2, 2))*2).all()

