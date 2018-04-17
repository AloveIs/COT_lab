#!/usr/bin/python

from support import debug

__doc__ = '''Intermediate Representation
Could be improved by relying less on class hierarchy and more on string tags and/or duck typing
Includes lowering and flattening functions'''

# SYMBOLS AND TYPES
basetypes = ['Int', 'Float', 'Label', 'Struct', 'Function']
qualifiers = ['unsigned']


class Type(object):
    def __init__(self, name, size, basetype, qualifiers=None):
        self.name = name
        self.size = size
        self.basetype = basetype
        self.qual_list = qualifiers


class ArrayType(Type):
    def __init__(self, name, size, basetype):
        self.name = name
        self.size = size
        self.basetype = basetype
        self.qual_list = []


class StructType(Type):
    def __init__(self, name, size, fields):
        self.name = name
        self.fields = fields
        self.size = self.getSize()
        self.basetype = 'Struct'
        self.qual_list = []

    def getSize(self):
        return sum([f.size for f in self.fields])


class LabelType(Type):
    def __init__(self):
        self.name = 'label'
        self.size = 0
        self.basetype = 'Label'
        self.qual_list = []
        self.ids = 0

    def __call__(self, target=None):
        self.ids += 1
        return Symbol(name='label' + `self.ids`, stype=self, value=target)


class FunctionType(Type):
    def __init__(self):
        self.name = 'function'
        self.size = 0
        self.basetype = 'Function'
        self.qual_list = []


class RegisterType(Type):
    created_register_list = []

    def __init__(self):
        self.name = 'register'
        self.size = 0
        self.ids = 0

    # TODO: remove target
    def __call__(self, target=None):
        self.ids += 1
        register_name = "register" + str(self.ids)
        new_register = Symbol(name=register_name, stype=self, value=target)
        RegisterType.created_register_list.append(new_register)
        return new_register

    def __repr__(self):
        return self.name + str(self.ids)


standard_types = {
    'int': Type('int', 32, 'Int'),
    'short': Type('short', 16, 'Int'),
    'char': Type('char', 8, 'Int'),
    'uchar': Type('uchar', 8, 'Int', ['unsigned']),
    'uint': Type('uint', 32, 'Int', ['unsigned']),
    'ushort': Type('ushort', 16, 'Int', ['unsigned']),
    'float': Type('float', 32, 'Float'),
    'label': LabelType(),
    'function': FunctionType(),
    'register': RegisterType()
}


class Symbol(object):
    def __init__(self, name, stype, value=None):
        self.name = name  # string that identifies it
        self.stype = stype
        self.value = value  # if not None, it is a constant

    # the way in which we can implement the printing facilities
    def __repr__(self):
        return self.stype.name + ' ' + self.name + (self.value if type(self.value) == str else '')


# it is implemented as a list (it is its extension)
class SymbolTable(list):
    # find an object by its name
    def find(self, name):
        print 'Looking up', name
        for s in self:
            if s.name == name:
                return s
        print 'Looking up failed!'
        return None

    def __repr__(self):
        res = 'SymbolTable:\n'
        for s in self:
            res += repr(s) + '\n'
        return res

    def exclude(self, barred_types):
        return [symb for symb in self if symb.stype not in barred_types]


# IRNODE
class IRNode(object):
    def __init__(self, parent=None, children=None, symtab=None):
        self.parent = parent
        if children:
            self.children = children
        else:
            self.children = []
        for c in self.children:
            if 'parent' in dir(c):
                c.parent = self

        self.symtab = symtab

    def __repr__(self):
        from string import split, join
        attrs = set(
            ['body', 'cond', 'value', 'thenpart', 'elsepart', 'symbol', 'call', 'step', 'expr', 'target', 'defs',
             'global_symtab', 'local_symtab']) & set(dir(self))

        res = repr(type(self)) + ' ' + str(id(self)) + ' {\n'
        try:
            label = self.getLabel()
            res = label.name + ': ' + res
        except Exception, e:
            pass
        if 'children' in dir(self) and len(self.children):
            res += '\tchildren:\n'
            for node in self.children:
                rep = repr(node)
                res += join(['\t' + s for s in rep.split('\n')], '\n') + '\n'
        for d in attrs:
            node = getattr(self, d)
            rep = repr(node)
            res += '\t' + d + ': ' + join(['\t' + s for s in rep.split('\n')], '\n') + '\n'
        res += '}'
        return res

    def navigate(self, action):
        # call action on the self node
        action(self)
        attrs = set(
            ['body', 'cond', 'value', 'thenpart', 'elsepart', 'symbol', 'call', 'step', 'expr', 'target', 'defs',
             'global_symtab', 'local_symtab']) & set(dir(self))
        if 'children' in dir(self) and len(self.children):
            # print 'navigating children of', type(self), id(self), len(self.children)
            for i in range(len(self.children)):
                try:
                    self.children[i].navigate(action)
                except Exception:
                    pass
        for d in attrs:
            try:
                getattr(self, d).navigate(action)
            except Exception:
                pass

    def replace(self, old, new):
        debug("#### replacing " + str(id(old)) + " with " + str(id(new)))
        if 'children' in dir(self) and len(self.children) and old in self.children:
            self.children[self.children.index(old)] = new
            return True
        attrs = set(
            ['body', 'cond', 'value', 'thenpart', 'elsepart', 'symbol', 'call', 'step', 'expr', 'target', 'defs',
             'global_symtab', 'local_symtab']) & set(dir(self))
        for d in attrs:
            try:
                if getattr(self, d) == old:
                    setattr(self, d, new)
                    return True
            except Exception:
                pass
        return False


class Register(IRNode):
    def __init__(self, parent=None, symbol=None, symtab=None):
        self.parent = parent
        self.symbol = symbol
        self.symtab = symtab

    def __repr__(self):
        res = repr(type(self)) + ' ' + str(id(self)) + ' {\n'
        res += '\t' + self.symbol.name + '\n'
        res += '}'
        return res


# CONST and VAR
class Const(IRNode):
    def __init__(self, parent=None, value=0, symb=None, symtab=None):
        self.parent = parent
        self.value = value
        self.symbol = symb
        self.symtab = symtab


class Var(IRNode):
    def __init__(self, parent=None, var=None, symtab=None):
        self.parent = parent
        self.symbol = var
        self.symtab = symtab

    def collect_uses(self):
        return [self.symbol]


# EXPRESSIONS
class Expr(IRNode):
    def __init__(self, parent=None, children=None, symtab=None, destination_register=None):
        super(Expr, self).__init__(parent, children, symtab)
        self.destination_register = destination_register

    def get_destination_register(self):
        if not self.destination_register:
            self.destination_register = Register(None, standard_types['register'](), self.symtab)
        return self.destination_register

    def getOperator(self):
        return self.children[0]

    def collect_uses(self):
        uses = []
        for c in self.children:
            try:
                uses += c.collect_uses()
            except AttributeError:
                pass
        return uses


class BinExpr(Expr):
    # to lower this we have to translate it with
    # assembly code
    # var -> load statement LoadStat (symbol, sp/fp, dest -> [a register]) we have an infinite number
    # constant are ok

    # this will be turned into also a BinExpr
    # with:
    # - Operator
    # src1 , src2, destination

    # in order we have to replace the original statement
    # so we use a StatList with LoadStat and a BinStat with register this time

    def getOperands(self):
        return self.children[1:]

    def lower(self):
        # debug("calling lower on " + str(self))
        # debug("expression ->" + str(self.children[1]) + str(self.children[2]))
        statement_list = []
        parameter1 = None
        parameter2 = None

        try:
            if isinstance(self.children[1], Var):
                parameter1 = Register(None, standard_types['register'](), self.symtab)
                statement_list.append(LoadStat(parameter1, None, symbol=self.children[1], symtab=self.symtab))
            elif isinstance(self.children[1], Const):
                parameter1 = self.children[1]
            elif isinstance(self.children[1], BinExpr):
                debug("now inspecting : " + str(type(self.children[1])))
                parameter1 = self.children[1].get_destination_register()
                self.children[1].lower()
                statement_list.append(self.children[1])
            else:
                debug("Unrecognized token in the expression")
            if isinstance(self.children[2], Var):
                parameter2 = Register(None, standard_types['register'](), self.symtab)
                statement_list.append(LoadStat(parameter2, None, self.children[2], self.symtab))
            elif isinstance(self.children[2], Const):
                parameter2 = self.children[2]
            elif isinstance(self.children[2], BinExpr):
                debug("now inspecting : " + str(type(self.children[2])))
                parameter2 = self.children[2].get_destination_register()
                self.children[2].lower()
                statement_list.append(self.children[2])
            else:
                pass
            lowered_expression = BinStat(self.children[0], parameter1, parameter2, self.get_destination_register(), self.symtab)
            statement_list.append(lowered_expression)
            # debug("starting replacing now " + str(self) + " with " + statement_list)
        except Exception as e:
            debug("raising an exception in lowering")
            print e
        return self.parent.replace(self, StatList(self.parent, statement_list, self.symtab))


class UnExpr(Expr):
    def getOperand(self):
        return self.children[1]


class CallExpr(Expr):
    def __init__(self, parent=None, function=None, parameters=None, symtab=None):
        self.parent = parent
        self.symbol = function
        if parameters:
            self.children = parameters[:]
        else:
            self.children = []


# STATEMENTS
class Stat(IRNode):
    def setLabel(self, label):
        self.label = label
        label.value = self  # set target

    def getLabel(self):
        return self.label

    def getFunction(self):
        if not self.parent:
            return 'global'
        elif type(self.parent) == FunctionDef:
            return self.parent
        else:
            return self.parent.getFunction()


class CallStat(Stat):
    '''Procedure call (non returning)'''

    def __init__(self, parent=None, call_expr=None, symtab=None):
        self.parent = parent
        self.call = call_expr
        self.call.parent = self
        self.symtab = symtab

    def collect_uses(self):
        return self.call.collect_uses() + self.symtab.exclude([standard_types['function'], standard_types['label']])


class IfStat(Stat):
    def __init__(self, parent=None, cond=None, thenpart=None, elsepart=None, symtab=None):
        self.parent = parent
        self.cond = cond
        self.thenpart = thenpart
        self.elsepart = elsepart
        self.cond.parent = self
        self.thenpart.parent = self
        if self.elsepart:
            self.elsepart.parent = self
        self.symtab = symtab

    def lower(self):
        exit_label = standard_types['label']()
        exit_stat = EmptyStat(self.parent, symtab=self.symtab)
        exit_stat.setLabel(exit_label)
        if self.elsepart:
            then_label = standard_types['label']()
            # else_label = standard_types['label']()
            # FIXME: there is some confusion to the adresses and branching order
            self.thenpart.setLabel(then_label)
            branch_to_then = BranchStat(None, self.cond, then_label, self.symtab)
            try:
                branch_to_exit = BranchStat(None, None, exit_label, self.symtab)
            except Exception as e:
                print e
            # the statement list has the following elements:
            # - branch_to_then
            # - else_part
            # - branch_to_exit
            # - then_part
            # - exit_stat
            stat_list = StatList(self.parent, [branch_to_then, self.elsepart, branch_to_exit, self.thenpart, exit_stat],
                                 self.symtab)
            return self.parent.replace(self, stat_list)
        else:
            branch_to_exit = BranchStat(None, UnExpr(None, ['not', self.cond]), exit_label, self.symtab)
            # the statement list has the following elements:
            # - then_part
            # - exit_stat
            stat_list = StatList(self.parent, [branch_to_exit, self.thenpart, exit_stat], self.symtab)
            return self.parent.replace(self, stat_list)

    def collect_uses(self):
        # FIXME: missing collect_uses for the algorithm for the CFG
        debug("calling collect_uses on the if_stmt node, this should not happen")
        return self.thenpart.collect_uses() + self.elsepart.collect_uses()


class WhileStat(Stat):
    def __init__(self, parent=None, cond=None, body=None, symtab=None):
        self.parent = parent
        self.cond = cond
        self.body = body
        self.cond.parent = self
        self.body.parent = self
        self.symtab = symtab

    def lower(self):
        # move from high level construct to a lower level one
        # entry : ! cond
        # branch out
        # loop : body
        # branch entry
        # exit : empty statement

        entry_label = standard_types['label']()
        exit_label = standard_types['label']()
        exit_stat = EmptyStat(self.parent, symtab=self.symtab)
        exit_stat.setLabel(exit_label)
        branch = BranchStat(None, self.cond, exit_label, self.symtab)
        branch.setLabel(entry_label)
        loop = BranchStat(None, Const(None, 1), entry_label, self.symtab)
        stat_list = StatList(self.parent, [branch, self.body, loop, exit_stat], self.symtab)
        return self.parent.replace(self, stat_list)


class ForStat(Stat):
    def __init__(self, parent=None, init=None, cond=None, step=None, body=None, symtab=None):
        self.parent = parent
        self.init = init
        self.cond = cond
        self.step = step
        self.body = body
        self.cond.parent = self
        self.body.parent = self
        self.target.parent = self
        self.step.parent = self
        self.symtab = symtab


class AssignStat(Stat):
    def __init__(self, parent=None, target=None, expr=None, symtab=None):
        self.parent = parent
        self.symbol = target
        self.expr = expr
        self.expr.parent = self
        self.symtab = symtab

    def collect_uses(self):
        try:
            return self.expr.collect_uses()
        except AttributeError:
            return []

    def lower(self):
        if isinstance(self.expr, Expr):
            register = self.expr.get_destination_register()
            self.expr.lower()
            store = StoreStat(self.parent, self.symbol, self.symtab, register)
            res = StatList(self.parent, [self.expr, store], self.symtab)
            return self.parent.replace(self, res)
        elif isinstance(self.expr, Const):
            store = StoreStat(self.parent, self.symbol, self.symtab, self.expr)
            return self.parent.replace(self, store)
        elif isinstance(self.expr, Var):
            load = LoadStat(None, None, self.expr.symbol, self.symtab)
            store = StoreStat(self.parent, self.symbol, self.symtab, load.get_dest_register())
            res = StatList(self.parent,[load, store], self.symtab)
            return self.parent.replace(self, res)


class BranchStat(Stat):
    def __init__(self, parent=None, cond=None, target=None, symtab=None):
        self.parent = parent
        self.cond = cond  # cond == None -> True
        self.target = target
        if cond:
            self.cond.parent = self
        self.target.parent = self
        self.symtab = symtab

    def collect_uses(self):
        try:
            return self.cond.collect_uses()
        except AttributeError:
            return []

    def is_unconditional(self):
        try:
            check = self.cond.value
            return True
        except AttributeError:
            return False


class EmptyStat(Stat):
    pass

    def collect_uses(self):
        return []


class StoreStat(Stat):
    def __init__(self, parent=None, symbol=None, symtab=None, value=None):
        self.parent = parent
        self.store_symbol = symbol
        self.symtab = symtab
        # the value contains the register or the value to be stored in memory
        self.store_value = value
        if not (isinstance(value, Register) or isinstance(value, Const)):
            raise Exception("Argument of store must be a register or a constant")

        self.children = [Var(self,self.store_symbol, self.symtab), self.store_value]
        self.store_symbol.parent = self
        self.store_value.parent = self

    def collect_uses(self):
        return [self.store_symbol]


class BinStat(Stat):
    def __init__(self, operation, operand_1, operand_2, destination, parent=None, symtab=None):
        self.children = [operation, operand_1, operand_2, destination]
        self.parent = parent
        self.symtab = symtab

    def get_dest_register(self):
        return self.children[3]


class LoadStat(Stat):
    def __init__(self, register=None, parent=None, symbol=None, symtab=None):
        self.parent = parent
        self.symbol = symbol
        self.symtab = symtab
        # self.load_register = load_register

        if register:
            self.children = [self.symbol, register]
        else:
            register = Register(None, standard_types['register'](), self.symtab)
            self.children = [self.symbol, register]

    def get_dest_register(self):
        return self.children[1]

    def collect_uses(self):
        return [self.symbol]


class StatList(Stat):
    def __init__(self, parent=None, children=None, symtab=None):
        print 'StatList : new', id(self)
        self.parent = parent
        if children:
            self.children = children[:]
            for c in self.children:
                c.parent = self
        else:
            self.children = []
        self.symtab = symtab

    def append(self, elem):
        elem.parent = self
        print 'StatList: appending', id(elem), 'of type', type(elem), 'to', id(self)
        self.children.append(elem)

    def collect_uses(self):
        result = []
        # sum([c.collect_uses() for c in self.children])
        for c in self.children:
            result += c.collect_uses()
        return result

    def print_content(self):
        print 'StatList', id(self), ': [',
        for n in self.children:
            print id(n),
        print ']'

    def flatten(self):
        '''Remove nested StatLists'''
        if type(self.parent) == StatList:
            print 'Flattening', id(self), 'into', id(self.parent)
            for c in self.children:
                c.parent = self.parent
            try:
                label = self.getLabel()
                self.children[0].setLabel(label)
            except Exception:
                pass
            i = self.parent.children.index(self)
            self.parent.children = self.parent.children[:i] + self.children + self.parent.children[i + 1:]
            return True
        else:
            print 'Not flattening', id(self), 'into', id(self.parent), 'of type', type(self.parent)
            return False

    def lower(self):
        for i in range(len(self.children)):
            if 'lower' in dir(self.children):
                self.children[i].lower()


class Block(Stat):
    def __init__(self, parent=None, gl_sym=None, lc_sym=None, defs=None, body=None):
        self.parent = parent
        self.global_symtab = gl_sym
        self.local_symtab = lc_sym
        self.body = body
        self.defs = defs
        self.body.parent = self
        self.defs.parent = self


class PrintStat(Stat):
    def __init__(self, parent=None, symbol=None, symtab=None):
        self.parent = parent
        self.symbol = symbol
        self.symtab = symtab

    def collect_uses(self):
        return [self.symbol]


class InputStat(Stat):
    def __init__(self, parent=None, symbol=None, symtab=None):
        self.parent = parent
        self.symbol = symbol
        self.symtab = symtab

    def collect_uses(self):
        return [self.symbol]


# DEFINITIONS
class Definition(IRNode):
    def __init__(self, parent=None, symbol=None):
        self.parent = parent
        self.symbol = symbol


class FunctionDef(Definition):
    def __init__(self, parent=None, symbol=None, body=None):
        self.parent = parent
        self.symbol = symbol
        self.body = body
        self.body.parent = self

    def getGlobalSymbols(self):
        return self.body.global_symtab.exclude([standard_types['function'], standard_types['label']])


class DefinitionList(IRNode):
    def __init__(self, parent=None, children=None):
        self.parent = parent
        if children:
            self.children = children
        else:
            self.children = []

    def append(self, elem):
        elem.parent = self
        self.children.append(elem)


def print_stat_list(node):
    """Navigation action: print"""
    print type(node), id(node)
    if type(node) == StatList:
        print 'StatList', id(node), ': [',
        for n in node.children:
            print id(n),
        print ']'


if __name__ == '__main__':
    a = standard_types['register']()
    b = standard_types['register']()
    print a
    print b
