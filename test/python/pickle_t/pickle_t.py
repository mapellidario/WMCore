# -*- coding: utf-8 -*-

"""
Check how pickle behaves across WMCore's py2 and py3 environment. 

See #9128, #10609 and #10619 for more information

Some general information about pickle protocols (in 2021-06):

- py2 supports protocols 0,1,2
- py3 supports protocols 0,1,2,3,4,5
- py3 dumps with py2-supported protocols are a bit different from their py2 
  equivalents

Guide:

- if you change some data, update the json file by calling 
  `self.genericDumpStability(<data updated>, <key>, update=True)` in testDump

References

- https://docs.python.org/2.7/library/pickle.html#module-pickle
- https://docs.python.org/3.8/library/pickle.html#module-pickle
- https://portingguide.readthedocs.io/en/latest/classes.html
- https://github.com/PythonCharmers/python-future/blob/master/src/future/types/newobject.py

"""

# the following line is not needed here, but we use it a lot in WMCore.
# adding this import from python-future does not change the result of the tests
#from builtins import object

import unittest

try:
    import cPickle as pickle
except:
    import pickle
import json
import os
import base64

from Utils.PythonVersion import PY2, PY3


class MyClassA():
    mystr = "This is a native str"
    myunicode = u"This is a unicode string - ₩ℳ℃◎ґ℮"
    mybytes = "This is a bytes string - ₩ℳ℃◎ґ℮".encode("utf8") if PY3 else "This is a bytes string - ₩ℳ℃◎ґ℮"
    myint = 1234867767
    myfloat = 3.14159
    mylist = [1, 2.5, "hello", u"world", b"\xe2\x82\xa9" ]


class MyClassB():
    def __init__(self):
        self.mystr = "This is a native str"
        self.myunicode = u"This is a unicode string - ₩ℳ℃◎ґ℮"
        self.mybytes = "This is a bytes string - ₩ℳ℃◎ґ℮".encode("utf8") if PY3 else "This is a bytes string - ₩ℳ℃◎ґ℮"
        self.myint = 1234867767
        self.myfloat = 3.14159
        self.mylist = [1, 2.5, "hello", u"world", b"\xe2\x82\xa9" ]


class MyClassC(object):
    def __init__(self):
        self.mystr = "This is a native str"
        self.myunicode = u"This is a unicode string - ₩ℳ℃◎ґ℮"
        self.mybytes = "This is a bytes string - ₩ℳ℃◎ґ℮".encode("utf8") if PY3 else "This is a bytes string - ₩ℳ℃◎ґ℮"
        self.myint = 1234867767
        self.myfloat = 3.14159
        self.mylist = [1, 2.5, "hello", u"world", b"\xe2\x82\xa9" ]


MYDICT = {
    "mynone": None, "mytrue": True, "myfalse": False,
    "myint": 1234867767, "myfloat": 3.14159, "mycomplex": 1+2j,
    "mystr": "This is a native str",
    "myunicode": u"This is a unicode string - ₩ℳ℃◎ґ℮",
    "mybytes": "This is a bytes string - ₩ℳ℃◎ґ℮".encode("utf8") if PY3 else "This is a bytes string - ₩ℳ℃◎ґ℮",
    "mytuple": (1, 2.5, "hello", u"world", b"\xe2\x82\xa9"),
    "mylist": [1, 2.5, "hello", u"world", b"\xe2\x82\xa9" ],
    # "myset": set([1, 2.5, "hello", u"world", b"\xe2\x82\xa9" ])
}

MYSET = set([1, 2.5, "hello", u"world", b"\xe2\x82\xa9" ])

class TestPickle(unittest.TestCase):
    def setUp(self):
        """
        Load the pickle dumps references from a json file.

        Notice that pickle dumps should be of type bytes, but bytes are not
        json serializable, since json only supports unicode strings.
        We have to use base64 to encode the pickle dumps byte data into unicode 
        ascii strings.
        """
        with open(os.path.join(os.path.dirname(__file__), "pickle_data.json")) as f_:
            self.PICKLE_DATA = json.load(f_)

        for k,v in self.PICKLE_DATA.items():
            for proto, pickledata in v.items():
                self.PICKLE_DATA[k][proto] = base64.b64decode(pickledata)


    def writePickleData(self):
        """
        Write the pickle data to the disk, without changing `self.PICKLE_DATA`,
        so that it can later be used by other tests.
        """
        pickle_data = {}
        for k,v in self.PICKLE_DATA.items():
            pickle_data[k] = {}
            for proto, bytesdata in v.items():
                pickle_data[k][proto] = base64.b64encode(bytesdata).decode("ascii")

        with open(os.path.join(os.path.dirname(__file__),"pickle_data.json"), "w") as f_:
            json.dump(pickle_data, f_)

    def testDefaultProtocol(self):
        """
        __testDefault__

        Check self.PICKLE_DATA to make sure that 
        - python2 default protocol is 0
        - python3 default protocol is 4
        """
        self.assertEqual(self.PICKLE_DATA["mydict"]["py2-default"], self.PICKLE_DATA["mydict"]["py2-proto0"])
        self.assertEqual(self.PICKLE_DATA["mydict"]["py3-default"], self.PICKLE_DATA["mydict"]["py3-proto4"])

        self.assertEqual(self.PICKLE_DATA["MyClassA"]["py2-default"], self.PICKLE_DATA["MyClassA"]["py2-proto0"])
        self.assertEqual(self.PICKLE_DATA["MyClassA"]["py3-default"], self.PICKLE_DATA["MyClassA"]["py3-proto4"])

        self.assertEqual(self.PICKLE_DATA["MyClassB"]["py2-default"], self.PICKLE_DATA["MyClassB"]["py2-proto0"])
        self.assertEqual(self.PICKLE_DATA["MyClassB"]["py3-default"], self.PICKLE_DATA["MyClassB"]["py3-proto4"])


    def genericDumpStability(self, target, reference, debug=False, update=False):
        """
        __testDumpStability__

        This test has multiple purposes

        1. Test that dumping the same object multiple times in the same Python 
           process always results in the same bytes sequence
        2. Test that the dump of an object is the same as the data loaded from disk,
           i.e. that the dump is consistent across Python processes. 
           This is true for every type, apart from sets and objects containing sets.
        """
        maxproto = 6 if PY3 else 3
        N = 100

        if debug:
            print("def", self.PICKLE_DATA[reference][("py3" if PY3 else "py2") + "-default"])
            print("def", pickle.dumps(target))
            print()
            for i in range(maxproto):
                print(i, self.PICKLE_DATA[reference][("py3" if PY3 else "py2") + "-proto" + str(i)])
                print(i, pickle.dumps(target, protocol=i))
                print()

        dumps = set()
        for _ in range(N):
            dumps.add(pickle.dumps(target))
        self.assertEqual(1, len(dumps))
        if update and len(dumps) == 1:
            self.PICKLE_DATA[reference][("py3" if PY3 else "py2") + "-default"] = pickle.dumps(target)

        for i in range(maxproto):
            dumps = set()
            for _ in range(N):
                dumps.add(pickle.dumps(target, protocol=i))
            self.assertEqual(1, len(dumps))
            if update and len(dumps) == 1:
                self.PICKLE_DATA[reference][("py3" if PY3 else "py2") + "-proto" + str(i)] = pickle.dumps(target, protocol=i)

        if update:
            self.writePickleData()


    def genericTestDump(self, target, reference):
        """
        Template for checking the pickle dump, in both py2 and py3
        """
        if PY2:
            self.assertEqual(pickle.dumps(target),             reference["py2-default"])
            self.assertEqual(pickle.dumps(target, protocol=0), reference["py2-proto0"])
            self.assertEqual(pickle.dumps(target, protocol=1), reference["py2-proto1"])
            self.assertEqual(pickle.dumps(target, protocol=2), reference["py2-proto2"])
        if PY3:
            self.assertEqual(pickle.dumps(target),             reference["py3-default"])
            self.assertEqual(pickle.dumps(target, protocol=0), reference["py3-proto0"])
            self.assertEqual(pickle.dumps(target, protocol=1), reference["py3-proto1"])
            self.assertEqual(pickle.dumps(target, protocol=2), reference["py3-proto2"])
            self.assertEqual(pickle.dumps(target, protocol=3), reference["py3-proto3"])
            self.assertEqual(pickle.dumps(target, protocol=4), reference["py3-proto4"])
            self.assertEqual(pickle.dumps(target, protocol=5), reference["py3-proto5"])

    def testDump(self):
        """
        __testDump__

        Tests the dump of all the considered types

        ACHTUNG!
        - in py3, the pickle dump bytes sequence of a set is not consistent 
          across Python procesess
        - in py2, the pickle dump bytes sequence of a dict containing a tuple 
          may not be not consistent across Python procesess
        """
        self.genericDumpStability(MYDICT, "mydict", debug=True)
        self.genericTestDump(MYDICT, self.PICKLE_DATA["mydict"])

        self.genericDumpStability(MYSET, "myset", update=True)
        self.genericTestDump(MYSET, self.PICKLE_DATA["myset"])

        myobj = MyClassA()
        self.genericDumpStability(myobj, "MyClassA")
        self.genericTestDump(myobj, self.PICKLE_DATA["MyClassA"])

        myobj = MyClassB()
        self.genericDumpStability(myobj, "MyClassB")
        self.genericTestDump(myobj, self.PICKLE_DATA["MyClassB"])

        myobj = MyClassC()
        self.genericDumpStability(myobj, "MyClassC")
        self.genericTestDump(myobj, self.PICKLE_DATA["MyClassC"])

    def assertRegularDict(self, target, reference):
        """
        Template for checking the data in an unpickled dictionary.

        When this is not used, it means that the uinpickled dictionary requires
        some manipilation to be made identical to the reference dictionary
        """
        self.assertEqual(target["mynone"],    reference["mynone"])
        self.assertEqual(target["mytrue"],    reference["mytrue"])
        self.assertEqual(target["myfalse"],   reference["myfalse"])
        self.assertEqual(target["myint"],     reference["myint"])
        self.assertEqual(target["myfloat"],   reference["myfloat"])
        self.assertEqual(target["mycomplex"], reference["mycomplex"])
        self.assertEqual(target["mystr"],     reference["mystr"])
        self.assertEqual(target["myunicode"], reference["myunicode"])
        self.assertEqual(target["mybytes"],   reference["mybytes"])
        self.assertEqual(target["mylist"],    reference["mylist"])
        self.assertEqual(target["mytuple"],   reference["mytuple"])
        # self.assertEqual(target["myset"],     reference["myset"])


    def assertRegularObj(self, target, reference):
        """
        Template for checking the data in and unpickled class instance
        """
        self.assertEqual(target.myint,     reference.myint)
        self.assertEqual(target.mystr,     reference.mystr)
        self.assertEqual(target.myunicode, reference.myunicode)
        self.assertEqual(target.mybytes,   reference.mybytes)
        self.assertEqual(target.mylist,    reference.mylist)

    def testLoadDict(self):
        """
        __testLoadDict__

        Test the unpickling of a dictionary, containing both basic types and 
        collections.

        ACHTUNG! 
        - unpickling in py3 a string that has been pickled in py2 is not trivial
        """
        for proto in ["py2-proto0", "py2-proto1", "py2-proto2"]:
            if PY2:
                mydict = pickle.loads(self.PICKLE_DATA["mydict"][proto])
                self.assertRegularDict(mydict, MYDICT)
            if PY3:
                mydict = pickle.loads(self.PICKLE_DATA["mydict"][proto], encoding="utf8")
                self.assertEqual(mydict["myint"],     MYDICT["myint"])
                self.assertEqual(mydict["mystr"],     MYDICT["mystr"])
                self.assertEqual(mydict["myunicode"], MYDICT["myunicode"])
                self.assertEqual(mydict["mybytes"],   MYDICT["mybytes"].decode("utf8"))
                self.assertEqual(mydict["mylist"],    [1, 2.5, "hello", u"world", b"\xe2\x82\xa9".decode("utf8") ])

                mydict = pickle.loads(self.PICKLE_DATA["mydict"][proto], encoding="bytes")
                self.assertEqual(mydict[b"myint"],     MYDICT["myint"])
                self.assertEqual(mydict[b"mystr"],     b"This is a native str")
                self.assertEqual(mydict[b"myunicode"], MYDICT["myunicode"])
                self.assertEqual(mydict[b"mybytes"],   MYDICT["mybytes"])
                self.assertEqual(mydict[b"mylist"],    [1, 2.5, b"hello", u"world", b"\xe2\x82\xa9"])

                # The following lines breaks in py3 with every protocol 
                # because pickle.load() by default uses `encoding="ascii"`, 
                # but the strings contains utf8 codepoints -> UnicodeDecodeError
                #if PY3: mydict = pickle.loads(self.PICKLE_DATA["mydict"][proto])

        for proto in ["py3-proto0", "py3-proto1", "py3-proto2"]:
            if PY2:
                mydict = pickle.loads(self.PICKLE_DATA["mydict"][proto])
                self.assertRegularDict(mydict, MYDICT)
            if PY3:
                mydict = pickle.loads(self.PICKLE_DATA["mydict"][proto])
                self.assertRegularDict(mydict, MYDICT)
                mydict = pickle.loads(self.PICKLE_DATA["mydict"][proto], encoding="utf8")
                self.assertRegularDict(mydict, MYDICT)
                mydict = pickle.loads(self.PICKLE_DATA["mydict"][proto], encoding="bytes")
                self.assertRegularDict(mydict, MYDICT)

        for proto in ["py3-proto3", "py3-proto4", "py3-proto5"]:
            if PY3:
                mydict = pickle.loads(self.PICKLE_DATA["mydict"][proto])
                self.assertRegularDict(mydict, MYDICT)
                mydict = pickle.loads(self.PICKLE_DATA["mydict"][proto], encoding="utf8")
                self.assertRegularDict(mydict, MYDICT)
                mydict = pickle.loads(self.PICKLE_DATA["mydict"][proto], encoding="bytes")
                self.assertRegularDict(mydict, MYDICT)


    def testLoadObjA(self):
        """
        __testLoadObjA__

        Test the unpickling of an instance of a class with only static attributes, 
        containing both basic types and collections.

        ACHTUNG! 
        - py2 does not pickle the attributes, there is no need to encode/decode strings
        - since MyClassA does not subclass `object` from future's `builtins`, 
          unpickling in py2 the class instance pickles in py3 fails.
        """
        myobj_reference = MyClassA()

        for proto in ["py2-proto0", "py2-proto1", "py2-proto2"]:
            myobj = pickle.loads(self.PICKLE_DATA["MyClassA"][proto])
            self.assertRegularObj(myobj, myobj_reference)

        for proto in ["py3-proto0", "py3-proto1", "py3-proto2"]:
            if PY2:
                # The following line fails with different errors based on the protocol.
                # in proto0 and proto1:
                # > lib/python2.7/copy_reg.py", line 48, in _reconstructor
                # >    obj = object.__new__(cls)
                # > TypeError: object.__new__(X): X is not a type object (classobj)
                # while in proto2:
                # > UnpicklingError: NEWOBJ class argument isn't a type object
                #myobj = pickle.loads(self.PICKLE_DATA["MyClassA"][proto])
                pass
            if PY3: 
                myobj = pickle.loads(self.PICKLE_DATA["MyClassA"][proto])
                self.assertRegularObj(myobj, myobj_reference)
                myobj = pickle.loads(self.PICKLE_DATA["MyClassA"][proto], encoding="utf8")
                self.assertRegularObj(myobj, myobj_reference)
                myobj = pickle.loads(self.PICKLE_DATA["MyClassA"][proto], encoding="bytes")
                self.assertRegularObj(myobj, myobj_reference)

        for proto in ["py3-proto3", "py3-proto4", "py3-proto5"]:
            if PY3: 
                myobj = pickle.loads(self.PICKLE_DATA["MyClassA"][proto])
                self.assertRegularObj(myobj, myobj_reference)
                myobj = pickle.loads(self.PICKLE_DATA["MyClassA"][proto], encoding="utf8")
                self.assertRegularObj(myobj, myobj_reference)
                myobj = pickle.loads(self.PICKLE_DATA["MyClassA"][proto], encoding="bytes")
                self.assertRegularObj(myobj, myobj_reference)


    def testLoadObjB(self):
        """
        __testLoadObjB__

        Test the unpickling of an instance of a class with attributes defined at
        instantiation time, containing both basic types and collections.

        ACHTUNG! 
        - py2 pickles the attributes defiend in __init__(), so in py3 we need
          to decode strings. Moreover, if no encoding is specified 
          (with encoding=bytes), then the object attributes are of type bytes,
          so they can not be retrived with `myobj.attribute` nor 
          `getattr(myobj, b"attribute")`.
        - since MyClassB does not subclass `object` from future's `builtins`, 
          unpickling in py2 the class instance pickles in py3 fails.
        """
        myobj_reference = MyClassB()

        for proto in ["py2-proto0", "py2-proto1", "py2-proto2"]:
            if PY2:
                myobj = pickle.loads(self.PICKLE_DATA["MyClassB"][proto])
                self.assertRegularObj(myobj, myobj_reference)

            if PY3:
                myobj = pickle.loads(self.PICKLE_DATA["MyClassB"][proto], encoding="utf8")
                self.assertEqual(myobj.myint,     myobj_reference.myint)
                self.assertEqual(myobj.mystr,     myobj_reference.mystr)
                self.assertEqual(myobj.myunicode, myobj_reference.myunicode)
                self.assertEqual(myobj.mybytes,   myobj_reference.mybytes.decode("utf8"))
                self.assertEqual(myobj.mylist,    [1, 2.5, "hello", u"world", b"\xe2\x82\xa9".decode("utf8") ])

                myobj = pickle.loads(self.PICKLE_DATA["MyClassB"][proto], encoding="bytes")
                self.assertEqual(myobj.__dict__[b"myint"],     MYDICT["myint"])
                self.assertEqual(myobj.__dict__[b"mystr"],     b"This is a native str")
                self.assertEqual(myobj.__dict__[b"myunicode"], MYDICT["myunicode"])
                self.assertEqual(myobj.__dict__[b"mybytes"],   MYDICT["mybytes"])
                self.assertEqual(myobj.__dict__[b"mylist"],    [1, 2.5, b"hello", u"world", b"\xe2\x82\xa9"])
                # The following line fails with
                # > TypeError: getattr(): attribute name must be string
                #self.assertEqual(getattr(myobj,b"myint"), myobj_reference.myint)

        for proto in ["py3-proto0", "py3-proto1", "py3-proto2"]:
            if PY2:
                # The following line fails with different errors based on the protocol.
                # in proto0 and proto1:
                # > lib/python2.7/copy_reg.py", line 48, in _reconstructor
                # >    obj = object.__new__(cls)
                # > TypeError: object.__new__(X): X is not a type object (classobj)
                # while in proto2:
                # > UnpicklingError: NEWOBJ class argument isn't a type object
                # myobj = pickle.loads(self.PICKLE_DATA["MyClassA"][proto])
                pass
            if PY3:
                myobj = pickle.loads(self.PICKLE_DATA["MyClassB"][proto])
                self.assertRegularObj(myobj, myobj_reference)
                myobj = pickle.loads(self.PICKLE_DATA["MyClassB"][proto], encoding="utf8")
                self.assertRegularObj(myobj, myobj_reference)
                myobj = pickle.loads(self.PICKLE_DATA["MyClassB"][proto], encoding="bytes")
                self.assertRegularObj(myobj, myobj_reference)

        for proto in ["py3-proto3", "py3-proto4", "py3-proto5"]:
            if PY3: 
                myobj = pickle.loads(self.PICKLE_DATA["MyClassB"][proto])
                self.assertRegularObj(myobj, myobj_reference)
                myobj = pickle.loads(self.PICKLE_DATA["MyClassB"][proto], encoding="utf8")
                self.assertRegularObj(myobj, myobj_reference)
                myobj = pickle.loads(self.PICKLE_DATA["MyClassB"][proto], encoding="bytes")
                self.assertRegularObj(myobj, myobj_reference)


    def testLoadObjC(self):
        """
        __testLoadObjC__

        Test the unpickling of an instance of a class that subclasses 
        `object` from future's `builtins` with attributes defined at instantiation
        time, containing both basic types and collections.

        ACHTUNG! 
        - py2 pickles the attributes defiend in __init__(), so in py3 we need
          to decode strings. Moreover, if no encoding is specified 
          (with encoding=bytes), then the object attributes are of type bytes,
          so they can not be retrived with `myobj.attribute` nor 
          `getattr(myobj, b"attribute")`.
        - since MyClassC subclasses `object` from future's `builtins`, 
          unpickling in py2 the class instance pickles in py3 succeeds.
        """
        myobj_reference = MyClassC()

        for proto in ["py2-proto0", "py2-proto1", "py2-proto2"]:
            if PY2:
                myobj = pickle.loads(self.PICKLE_DATA["MyClassC"][proto])
                self.assertRegularObj(myobj, myobj_reference)

            if PY3:
                myobj = pickle.loads(self.PICKLE_DATA["MyClassC"][proto], encoding="utf8")
                self.assertEqual(myobj.myint,     myobj_reference.myint)
                self.assertEqual(myobj.mystr,     myobj_reference.mystr)
                self.assertEqual(myobj.myunicode, myobj_reference.myunicode)
                self.assertEqual(myobj.mybytes,   myobj_reference.mybytes.decode("utf8"))
                self.assertEqual(myobj.mylist,    [1, 2.5, "hello", u"world", b"\xe2\x82\xa9".decode("utf8") ])

                myobj = pickle.loads(self.PICKLE_DATA["MyClassC"][proto], encoding="bytes")
                self.assertEqual(myobj.__dict__[b"myint"],     MYDICT["myint"])
                self.assertEqual(myobj.__dict__[b"mystr"],     b"This is a native str")
                self.assertEqual(myobj.__dict__[b"myunicode"], MYDICT["myunicode"])
                self.assertEqual(myobj.__dict__[b"mybytes"],   MYDICT["mybytes"])
                self.assertEqual(myobj.__dict__[b"mylist"],    [1, 2.5, b"hello", u"world", b"\xe2\x82\xa9"])
                # The following line fails with
                # > TypeError: getattr(): attribute name must be string
                # self.assertEqual(getattr(myobj,b"myint"), myobj_reference.myint)

        for proto in ["py3-proto0", "py3-proto1", "py3-proto2"]:
            if PY2:
                myobj = pickle.loads(self.PICKLE_DATA["MyClassC"][proto])
                self.assertRegularObj(myobj, myobj_reference)
            if PY3:
                myobj = pickle.loads(self.PICKLE_DATA["MyClassC"][proto])
                self.assertRegularObj(myobj, myobj_reference)
                myobj = pickle.loads(self.PICKLE_DATA["MyClassC"][proto], encoding="utf8")
                self.assertRegularObj(myobj, myobj_reference)
                myobj = pickle.loads(self.PICKLE_DATA["MyClassC"][proto], encoding="bytes")
                self.assertRegularObj(myobj, myobj_reference)

        for proto in ["py3-proto3", "py3-proto4", "py3-proto5"]:
            if PY3: 
                myobj = pickle.loads(self.PICKLE_DATA["MyClassC"][proto])
                self.assertRegularObj(myobj, myobj_reference)
                myobj = pickle.loads(self.PICKLE_DATA["MyClassC"][proto], encoding="utf8")
                self.assertRegularObj(myobj, myobj_reference)
                myobj = pickle.loads(self.PICKLE_DATA["MyClassC"][proto], encoding="bytes")
                self.assertRegularObj(myobj, myobj_reference)
