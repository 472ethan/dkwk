# -*- coding: utf-8 -*-

import unittest
import dkwk

class TestVersion(unittest.TestCase):
    def test_load(self):
        self.assertIsNot(dkwk.__version__, None)
