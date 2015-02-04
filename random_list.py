# -*- coding: utf-8 -*-

import random


class RandomList(list):
    
    def __init__(self, default=None):
        self.default = default
    
    def pop(self):
        if len(self):
            return super(RandomList, self).pop(random.randint(0, len(self)-1))
        
        return self.default
