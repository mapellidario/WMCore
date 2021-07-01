from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
import urllib.request

import unittest

import os
from functools import reduce
from hashlib import md5

from WMCore.WMSpec.Steps.Executors.DQMUpload import DQMUpload

class StepPatch():
    def __init__(self, upload=None):
        self.upload = upload

class UploadPatch():
    def __init__(self):
        self.proxy = False

class DQMUpload_t(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testA_Upload(self):
        filename = "/tmp/dqm.root"
        urllib.request.urlretrieve(
            "http://amaltaro.web.cern.ch/amaltaro/forAlan/DQM_V0001_R000000001__RelValH125GGgluonfusion_13__CMSSW_8_1_0-RecoFullPU_2017PU_TaskChain_PUMCRecyc_HG1705_Validation_TEST_Alan_v67-v11__DQMIO.root", 
            filename)

        dqm = DQMUpload()
        upload_patch = UploadPatch()
        step_patch = StepPatch(upload_patch)
        dqm.step = step_patch

        args = {}
        # Preparing a checksum
        blockSize = 0x10000
        def upd(m, data):
            m.update(data)
            return m
        with open(filename, 'rb') as fd:
            contents = iter(lambda: fd.read(blockSize), '')
            m = reduce(upd, contents, md5())
        args['checksum'] = 'md5:%s' % m.hexdigest()
        # args['checksum'] = 'md5:%s' % md5.new(filename).read()).hexdigest()
        args['size'] = os.path.getsize(filename)
        dqm.upload(
            "https://cmsweb-testbed.cern.ch/dqm/dev/", 
            args,
            filename)

        raise Exception

if __name__ == '__main__':
    unittest.main()