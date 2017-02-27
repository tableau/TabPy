import unittest
import sys

from tabpy_client.rest import RESTObject, RESTProperty, enum

class TestRESTObject(unittest.TestCase):

    def test_new_class(self):

        class FooObject(RESTObject):
            f = RESTProperty(float)
            i = RESTProperty(int)
            s = RESTProperty(str)
            e = RESTProperty(enum("a", "b"))

        f = FooObject(f="6.0", i="3", s="hello!")
        self.assertEqual(f.f, 6.0)
        self.assertEqual(f.i, 3)
        self.assertEqual(f.s, "hello!")

        with self.assertRaises(AttributeError):
            f.e

        self.assertEqual(f['f'], 6.0)
        self.assertEqual(f['i'], 3)
        self.assertEqual(f['s'], "hello!")

        with self.assertRaises(KeyError):
            f['e']
        with self.assertRaises(KeyError):
            f['cat']
        with self.assertRaises(KeyError):
            f['cat']=5

        self.assertEqual(len(f), 3)
        self.assertEqual(set(f), set(['f', 'i', 's']))
        self.assertEqual(set(f.keys()), set(['f', 'i', 's']))
        self.assertEqual(set(f.values()), set([6.0, 3, "hello!"]))
        self.assertEqual(set(f.items()), set([('f',6.0),('i',3), ('s',"hello!")]))

        f.e = "a"
        self.assertEqual(f.e, "a")
        self.assertEqual(f['e'], "a")
        f['e']='b'
        self.assertEqual(f.e, "b")

        with self.assertRaises(ValueError):
            f.e = 'fubar'

        f.f = sys.float_info.max
        self.assertEquals(f.f,sys.float_info.max)
        f.f = float("inf")
        self.assertEquals(f.f, float("inf"))
        f.f = None
        self.assertEquals(f.f, None)

        class BarObject(FooObject):
            x = RESTProperty(str)

        f = BarObject(f="6.0", i="3", s="hello!", x="5")
        self.assertEqual(f.f, 6.0)
        self.assertEqual(f.i, 3)
        self.assertEqual(f.s, "hello!")
        self.assertEqual(f.x, "5")

