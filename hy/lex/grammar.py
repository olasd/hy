#!/usr/bin/env python
#
# Copyright (c) 2013 Nicolas Dandrimont <nicolas.dandrimont@crans.org>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

from pkg_resources import resource_string

import parsley
from ometa.runtime import OMetaBase

from hy.models.expression import HyExpression
from hy.models.integer import HyInteger
from hy.models.symbol import HySymbol
from hy.models.string import HyString
from hy.models.dict import HyDict
from hy.models.list import HyList

from hy.errors import HyError


class LexException(parsley.ParseError, HyError):
    """
    Error during the Lexing of a Hython expression.
    """
    def __init__(self, input, position, message, trail=None):
        super(LexException, self).__init__(input, position, message, trail)

    @classmethod
    def from_parseerror(cls, pe):
        return cls(pe.input, pe.position, pe.message, pe.trail)


def emit_dict(contents):
    it = iter(contents)

    return HyDict(dict(zip(it, it)))


def emit_symbol(contents):
    table = {
        "true": "True",
        "false": "False",
        "null": "None",
    }

    obj = contents[0]

    try:
        return HyInteger(obj)
    except:
        pass

    if obj in table:
        return HySymbol(table[obj])

    if obj.startswith("*") and obj.endswith("*") and obj != "*":
        obj = obj[1:-1].upper()

    if "-" in obj and obj != "-":
        obj = obj.replace("-", "_")

    return HySymbol(obj)


class HyGrammarBase(OMetaBase):
    dispatch = {
        "dict": emit_dict,
        "identifier": emit_symbol,
        "list": HyList,
        "parens": HyExpression,
        "root": list,
        "string": lambda contents: HyString(*contents),
    }

    def __init__(self, *args, **kwargs):
        super(HyGrammarBase, self).__init__(*args, **kwargs)

        linecounts = []
        counter = 0
        for line in self.input.data.split('\n'):
            counter += len(line) + 1
            linecounts.append(counter)
        self.__linecounts = linecounts
        self.curpos = []

    @property
    def pos(self):
        return self.input.position

    def decode_pos(self, pos):
        prevcount = 0
        for lineNo, count in enumerate(self.__linecounts):
            if pos < count:
                break
            prevcount = count

        return (lineNo + 1, pos - prevcount + 1)

    @property
    def boundaries(self):
        end = self.pos - 1
        return self.decode_pos(self.curpos[-1]), self.decode_pos(end)

    def _apply(self, rule, ruleName, args):
        try:
            self.curpos.append(self.pos)
            ret = super(HyGrammarBase, self)._apply(rule, ruleName, args)
        finally:
            self.curpos.pop()
        return ret

    def emit(self, kind, *contents):
        if kind not in self.dispatch:
            raise LexException(self.input, self.input.position,
                               "Unimplemented atom type %s" % kind)

        fun = self.dispatch[kind]

        ret = fun(list(contents))
        try:
            bounds = self.boundaries
            ret.start_line, ret.start_column = bounds[0]
            ret.end_line, ret.end_column = bounds[1]
        except AttributeError:
            pass

        return ret

HyGrammar = parsley.makeGrammar(resource_string(__name__, "hy.parsley"), {},
                                extends=HyGrammarBase)
