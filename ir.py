#!/usr/bin/python

from support import debug
from graphviz import Digraph

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
        # label tot he beginning of the body of the function
        self.qual_list = []


class Symbol(object):
    def __init__(self, name, stype, value=None, level=None, temp=False):
        self.name = name  # string that identifies it
        self.stype = stype
        self.value = value  # if not None, it is a constant
        self.level = level
        self.temp = temp
        self.address = dict()
        #debug("Created : " + self.name + " Value : " + str(self.value))

    # the way in which we can implement the printing facilities

    def instr_dot_repr(self):
        return self.name


    def __repr__(self):
        return self.stype.name + ' ' + self.name + " " + (self.value if type(self.value) == str else '') + " " + \
               (("address : " + str(self.address)) if self.address else '')


class RegisterType(Type):
    created_register_list = []

    def __init__(self):
        self.name = 'register'

        # create base pointer register
        self.bp = Symbol(name="bp", stype=self, value=None)
        RegisterType.created_register_list.append(self.bp)

        # create stack pointer register
        self.sp = Symbol(name="sp", stype=self, value=None)
        RegisterType.created_register_list.append(self.sp)

        # create instruction pointer register
        self.ip = Symbol(name="ip", stype=self, value=None)
        RegisterType.created_register_list.append(self.ip)

        # create return address register
        self.ra = Symbol(name="ra", stype=self, value=None)
        RegisterType.created_register_list.append(self.ip)

        self.size = 0
        self.ids = 0

    def __call__(self, target=None):
        self.ids += 1
        register_name = "register" + str(self.ids)
        new_register = Symbol(name=register_name, stype=self, value=target)
        RegisterType.created_register_list.append(new_register)
        return new_register

    def get_bp_register(self):
        return Register(None, self.bp, None)

    def get_sp_register(self):
        return Register(None, self.sp, None)

    def get_ip_register(self):
        return Register(None, self.ip, None)

    def get_ra_register(self):
        return Register(None, self.ra, None)

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

function_labels = {}

# it is implemented as a list (it is its extension)
class LocalSymbolTable(list):

    def __init__(self, fsym, parent=None):
        super(LocalSymbolTable,self).__init__()
        # symbol of the funciton
        self.fsym = fsym
        self.parent = parent
        self.children = []

        self.temp_counter = 0

    # find an object by its name
    def find(self, name):
        print 'Looking up', name
        for s in self:
            if s.name == name:
                return s
        if self.parent == None:
            return None 
        
        symb = self.parent.find(name)

        if symb == None:
            print 'Looking up failed!'
        
        return symb

    def get_external_var(self):
        res = set()

        for sym in self:
            if isinstance(sym.stype, FunctionType):
                continue
            if sym.level != self.fsym:
                res.add(sym)

        return res


    def __repr__(self):
        res = 'LocalSymbolTable:\n'
        for s in self:
            res += repr(s) + '\n'
        return res

    def exclude(self, barred_types):
        return [symb for symb in self if symb.stype not in barred_types]

    def instr_dot_repr(self):
        res = "{" + self.fsym.name
        for s in self:
            res +=  '|{' + s.name + "|" + str(s.stype.name) + "}"
        return res + "}"

    def get_temp_variable(self):

        tempname = "temp_" + str(self.temp_counter) + "_" + self.fsym.name
        self.temp_counter += 1

        sym = Symbol(tempname, stype=standard_types["int"],level=self.fsym, temp=True)
        return Var(var=sym, symtab=self)

    def _get_function_uses(self, exclude=[]):

        uses = []

        for symb in self:
            if symb.level == self.fsym or \
                symb.level in exclude or \
                isinstance(symb.stype, FunctionType):
                continue

            uses.append(symb.level)
        return uses


class SymbolTable():
    def __init__(self,ir):
        # root, the global symbols
        self.root = ir.local_symtab

        # list of all the symbol tables
        self.symtab_dict = dict()

        # create the symbol table tree
        self.__gather_symtab(ir)

        self.global_sym = self.root.fsym

    def get_function_uses(self):

        func_uses = dict()

        for func, symtab in self.symtab_dict.items():

            func_uses[func] = symtab._get_function_uses(exclude=self.global_sym)

        return func_uses




    def show_graphviz(self):
        G = Digraph("Symbol Table")

        for table in self.symtab_dict.values():
            G.node(str(id(table)), table.instr_dot_repr(), {"shape":"record"})
            for c in table.children:
                G.edge(str(id(table)), str(id(c)))

        G.render('symtab.gv', view=True)



    def __gather_symtab(self, ir):

        local_symtab = ir.local_symtab
        self.symtab_dict[local_symtab.fsym] = local_symtab
        for c in ir.defs.children:
            local_symtab.children.append(c.body.local_symtab)
            self.__gather_symtab(c.body)

    def get_symtab_dict(self):
        return self.symtab_dict


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

    def get_uses(self):
        return set()

    def get_defs(self):
        return set()

    def generate_code(self, fsym):
        return self.instr_dot_repr()

    def instr_dot_repr(self):
        res = str(self.__class__.__name__) + " "
        return res

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

    
    def constant_propagation(self):
        # indexes of children which are constant var
        if "children" not in dir(self):
            return
        indexs = []

        # find the constant among children
        for idx, c in enumerate(self.children):
            if isinstance(c, Var):
                if c.symbol.value is not None:
                    # it is a constant variable
                    indexs.append(idx)

        # substitute constat children
        for idx in indexs:
            c = self.children[idx]
            value = c.symbol.value
            self.children[idx] = Const(parent=self, value=value)#, symb=c.symbol)


    def _get_symbol_level(self):
        
        res = set()

        if 'children' not in dir(self):
            return res

        for c in self.children:
            # if is a symbol and not a function call and not a constant
            if isinstance(c, Symbol) and \
               not isinstance(c.stype, FunctionType) and\
               c.value is None :
                print("found " + c.name)
                res.add(c.level)
            elif isinstance(c, IRNode):
                res.update(c._get_symbol_level())
        return res


    def navigate_postvisit(self, action):
        # call action on the self node
        attrs = set(
            ['body', 'cond', 'value', 'thenpart', 'elsepart', 'symbol', 'call', 'step', 'expr', 'target', 'defs',
             'global_symtab', 'local_symtab']) & set(dir(self))
        if 'children' in dir(self) and len(self.children):
            # print 'navigating children of', type(self), id(self), len(self.children)
            for i in range(len(self.children)):
                try:
                    self.children[i].navigate_postvisit(action)
                except Exception:
                    pass
        for d in attrs:
            try:
                getattr(self, d).navigate_postvisit(action)
            except Exception:
                pass

        action(self)


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

    def to_three_addr_form(self):
        return self


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

    def instr_dot_repr(self):
        return str(self.value)


class Var(IRNode):
    def __init__(self, parent=None, var=None, symtab=None):
        self.parent = parent
        # Symbol object representing the variable
        self.symbol = var
        # name of the variable
        self.name = var
        self.symtab = symtab

        self.address = dict()

    def collect_uses(self):
        return [self.symbol]

    def instr_dot_repr(self):
        return self.symbol.instr_dot_repr()

    def _get_symbol_level(self):
        res = set()
        c = self.symbol
        if isinstance(c, Symbol) and \
           not isinstance(c.stype, FunctionType) and\
           c.value is None :
            print("found " + c.name)
            res.add(c.level)
        return res


# EXPRESSIONS
class Expr(IRNode):
    def __init__(self, parent=None, children=None, symtab=None, destination_register=None):
        super(Expr, self).__init__(parent, children, symtab)
        self.destination_register = destination_register

    def get_destination_register(self):
        if not self.destination_register:
            self.destination_register = Register(None, standard_types['register'](), self.symtab)
        return self.destination_register


    def get_uses(self):
        res = set()

        for c in self.children:
            if isinstance(c, Var):
                res.add(c.symbol)
        return res

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


    def instr_dot_repr(self):
        return self.children[0]

    def to_three_addr_form(self):
        pass


class BinExpr(Expr):
    # to lower this we have to translate it with
    # assembly code
    # var -> load statement LoadStatMIPS (symbol, sp/fp, dest -> [a register]) we have an infinite number
    # constant are ok

    # this will be turned into also a BinExpr
    # with:
    # - Operator
    # src1 , src2, destination

    # in order we have to replace the original statement
    # so we use a StatList with LoadStatMIPS and a BinStat with register this time

    def getOperands(self):
        return self.children[1:]


    def instr_dot_repr(self):
        operator =  " " + self.children[0] + " "
        op1 = self.children[1].instr_dot_repr()
        op2 = self.children[2].instr_dot_repr()
        return "( " + op1 + operator + op2 + " )"



    def lower(self):
        # debug("calling lower on " + str(self))
        # debug("expression ->" + str(self.children[1]) + str(self.children[2]))
        statement_list = []
        parameter1 = None
        parameter2 = None

        try:
            if isinstance(self.children[1], Var):
                parameter1 = Register(None, standard_types['register'](), self.symtab)
                statement_list.append(LoadStatMIPS(parameter1, None, symbol=self.children[1], symtab=self.symtab))
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
                statement_list.append(LoadStatMIPS(parameter2, None, self.children[2], self.symtab))
            elif isinstance(self.children[2], Const):
                parameter2 = self.children[2]
            elif isinstance(self.children[2], BinExpr):
                debug("now inspecting : " + str(type(self.children[2])))
                parameter2 = self.children[2].get_destination_register()
                self.children[2].lower()
                statement_list.append(self.children[2])
            else:
                pass
            lowered_expression = BinStat(self.children[0], parameter1, parameter2, self.get_destination_register(),
                                         symtab=self.symtab)
            statement_list.append(lowered_expression)
            # debug("starting replacing now " + str(self) + " with " + statement_list)
        except Exception as e:
            debug("raising an exception in lowering")
            print e
        return self.parent.replace(self, StatList(self.parent, statement_list, self.symtab))


    def to_three_addr_form(self):

        op = self.children[0]
        op1 = self.children[1]
        op2 = self.children[2]

        new_op1 = op1
        new_op2 = op2

        # ssa list of the instructions needed to perform the 
        # original expression

        res = []

        if not(isinstance(op1, Var) or isinstance(op1, Const)):
            new_op1 = self.symtab.get_temp_variable()

            previous_ssa_list1, new_exp1 = op1.to_three_addr_form()
            res.extend(previous_ssa_list1)
            res.append(AssignStat(target=new_op1.symbol, expr=new_exp1, symtab=self.symtab))


        if not(isinstance(op2, Var) or isinstance(op2, Const)):
            new_op2 = self.symtab.get_temp_variable()

            previous_ssa_list2, new_exp2 = op2.to_three_addr_form()
            res.append(AssignStat(target=new_op2.symbol, expr=new_exp2, symtab=self.symtab))

        newBinExpr = BinExpr(children=[op, new_op1, new_op2], symtab=self.symtab)

        return (res, newBinExpr)

class UnExpr(Expr):
    def getOperand(self):
        return self.children[1]


    def instr_dot_repr(self):
        operand = self.children[0]
        arg = self.children[1].instr_dot_repr() 
        return "(" + operand + " " + arg + ")"


    def to_three_addr_form(self):
        op = self.children[0]
        op1 = self.children[1]

        new_op1 = op1

        # ssa list of the instructions needed to perform the 
        # original expression

        res = []

        if not(isinstance(op1, Var) or isinstance(op1, Const)):
            new_op1 = self.symtab.get_temp_variable()

            previous_ssa_list1, new_exp1 = op1.to_three_addr_form()
            res.extend(previous_ssa_list1)
            res.append(AssignStat(target=new_op1.symbol, expr=new_exp1, symtab=self.symtab))

        newBinExpr = UnExpr(children=[op, new_op1], symtab=self.symtab)

        return (res, newBinExpr)



class CallExpr(Expr):
    def __init__(self, parent=None, function=None, parameters=None, symtab=None):
        self.parent = parent
        self.symbol = function
        self.symtab = symtab
        if parameters:
            self.children = parameters[:]
        else:
            self.children = []

    def instr_dot_repr(self):
        return "call " + self.symbol.instr_dot_repr()

    def to_three_addr_form(self):
        return self

    def generate_code(self, fsym):
       
        calling_fn = self.symtab.fsym

        called_fn = self.symbol

        called_fn_stack = called_fn.stack
        calling_fn_stack = calling_fn.stack

        res = "# preamble, save variables and push $ra, $fp, and the other's functions's $sp\n"



        res += """
# save $ra $fp  on stack
\taddi $sp, $sp, -8
\tsw   $fp, 8($sp)
\tsw   $ra, 4($sp)
# fill in function stack
"""



        for idx, sym in enumerate(called_fn_stack):
            if isinstance(sym.stype, FunctionType):
                if sym == calling_fn:
                    res += "\t" + "sw $fp, -" + str(idx*4) + "($sp)" + "\n"
                else:
                    idx_on_callee_stack = calling_fn_stack.index(sym)
                    res += "\t" + "lw $4, -" + str(idx_on_callee_stack*4) + "($fp)" + "\n"
                    res += "\t" + "sw $4, -" + str(idx*4) + "($sp)" + "\n"

        res += "\t" + "move $fp, $sp" + "\n"
        res += "\taddi $sp,$sp, -" + str(4*len(called_fn_stack)) + "\n"

        """
        \taddi $sp $sp -12
        \tsw   $ra  -4($fp)
        \tsw   $a0  -8($fp)
        \tsw   $s0 -12($fp)\n"""
        """ push
        sub $sp,$sp,4
        sw $t2,($sp)
        """

        """ pop
        lw $t2,($sp)
        addiu $sp,$sp,4
        """

        """
        #save $ra $s0, $a0 on stack
        addi $sp $sp -4
        sw   $fp 0($sp)
        move $fp $sp
        addi $sp $sp -12
        sw   $ra  -4($fp)
        sw   $a0  -8($fp)
        sw   $s0 -12($fp)

        ...

        #restore and shrink stack
        lw $s0 -12($fp)
        lw $ra  -4($fp)
        lw $fp   0($fp)
        addi $sp $sp 16

        jr $ra
        """
        
        res += "# call the function\n"
        res += "\tjal " + self.symbol.name + "_" + str(id(self.symbol))
        res += "# Restore environment\n"


        res += """
#restore and shrink stack
\tmove $sp, $fp
\tlw $ra, 4($sp)
\tlw $fp,  8($sp)
\taddi $sp, $sp, 8
\n"""

        return res

        
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

    def get_function_call_uses(self):
        return ([],[])

    def enclosing_function(self):
        p = self.parent
        while not isinstance(p, FunctionDef):
            p = p.parent
        return  p


class CallStat(Stat):
    '''Procedure call (non returning)'''

    def __init__(self, parent=None, call_expr=None, symtab=None):
        self.parent = parent
        self.call = call_expr
        self.call.parent = self
        self.symtab = symtab

    def get_function_call_uses(self):
        return ([self.call.symbol.name] , [])

    def collect_uses(self):
        return self.call.collect_uses() + self.symtab.exclude([standard_types['function'], standard_types['label']])

    def lower_calls(self):
        instruction_list = []

        # store $bp, ($sp)
        # destinazione valore
        inst = StoreStatMIPS(None, standard_types['register'].get_sp_register(), self.symtab,
                         standard_types['register'].get_bp_register())
        instruction_list.append(inst)
        # $bp = $sp
        inst = BinStat("plus", Const(), standard_types['register'].get_sp_register(),
                       standard_types['register'].get_bp_register(), self.symtab)
        instruction_list.append(inst)
        # $sp = $sp - 8
        inst = BinStat("minus", standard_types['register'].get_sp_register(), Const(value=8),
                       standard_types['register'].get_sp_register(), self.symtab)
        instruction_list.append(inst)
        # store $ra, 4($sp)   -- saving the return address
        inst = StoreStatMIPS(None, standard_types['register'].get_sp_register(), self.symtab,
                         value=standard_types['register'].get_ra_register(), offset=4)
        instruction_list.append(inst)
        # jump function
        inst = BranchStat(parent=None, cond=None, target=function_labels[self.call.symbol.name], symtab=self.symtab)
        instruction_list.append(inst)
        # $sp = $bp             -- restore stack pointer
        inst = BinStat("plus", Const(), standard_types['register'].get_bp_register(),
                       standard_types['register'].get_sp_register(), self.symtab)
        instruction_list.append(inst)
        # load $bp, ($sp)      -- restore the base pointer
        inst = LoadStatMIPS(standard_types['register'].get_bp_register(), None,
                        standard_types['register'].get_sp_register(), self.symtab)
        instruction_list.append(inst)
        # load $ra, -4($sp)      -- restore the base pointer
        inst = LoadStatMIPS(standard_types['register'].get_ra_register(), None,
                        standard_types['register'].get_sp_register(), self.symtab, -4)
        instruction_list.append(inst)
        # ...

        lowered = StatList(self.parent, instruction_list, self.symtab)
        self.parent.replace(self, lowered)

    def generate_code(self, fsym):
        return self.call.instr_dot_repr()

    def instr_dot_repr(self):
        return self.call.instr_dot_repr()
    
    def to_three_addr_form(self):
        return self


class NopStat(IRNode):
    def __init(self):
        self.name = None

    def generate_code(self, fsym):
        return "\n"

    def get_uses(self):
        return set()

    def get_defs(self):
        return set()

    def get_function_call_uses(self):
        return ([],[])

    def instr_dot_repr(self):
        return "NOP"
    
    def to_three_addr_form(self):
        return self


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
        self.local_symtab = symtab
        self.symtab = self.local_symtab

    def get_uses(self):
        return self.expr.get_uses()
    def get_defs(self):
        return set([self.symbol])

    def instr_dot_repr(self):
        return self.expr.instr_dot_repr()

    def collect_uses(self):
        try:
            return self.expr.collect_uses()
        except AttributeError:
            return []

    def generate_code(self, fsym):
        instr = "# " + self.instr_dot_repr() + "\n\t"

        expr = self.expr
        if isinstance(self.expr, Const):
            instr += "ori $" + str(self.symbol.address[fsym]) + ", $0, " + str(self.expr.value)
        if isinstance(self.expr, UnExpr):

            op = self.expr.children[0]
            var = self.expr.children[1]
            instr += "\t" + "\n"

            if isinstance(var, Var):
                if op == "minus":
                    instr += "sub $" + str(self.symbol.address[fsym]) +", $0, $" + str(var.symbol.address[fsym])
                elif op == "plus":
                    instr += "add $" + str(self.symbol.address[fsym]) +", $0, $" + str(var.symbol.address[fsym])
                elif op == "oddsym":
                    instr += "and $" + str(self.symbol.address[fsym]) +", $"+ str(var.symbol.address[fsym]) + ", 1"
            elif isinstance(var, Const):
                if op == "minus":
                    instr += "ori $4, $0, " + str(var.value) 
                    instr += "\n\t"
                    instr += "sub $" + str(self.symbol.address[fsym]) +", $0, $4"
                elif op == "plus":
                    instr += "ori $4, $0, " + str(var.value) 
                    instr += "\n\t"
                    instr += "add $" + str(self.symbol.address[fsym]) +", $0, $4"
                elif op == "oddsym":
                    instr += "ori $4, $0, " + str(var.value)
                    instr += "\n\t" 
                    instr += "and $4, $" + str(var.symbol.address[fsym]) + ", 1"

        if isinstance(self.expr, BinExpr):
            # both variables
            if isinstance(expr.children[1], Var) and \
                isinstance(expr.children[2], Var):
                if expr.children[0] == 'times':
                    instr += "mul $" + str(self.symbol.address[fsym]) +", $" +str(expr.children[1].symbol.address[fsym]) +", $" +str(expr.children[2].symbol.address[fsym]) 
                if expr.children[0] == 'slash':
                    instr += "div $" + str(self.symbol.address[fsym]) +", $" +str(expr.children[1].symbol.address[fsym]) +", $" +str(expr.children[2].symbol.address[fsym])
                if expr.children[0] == 'plus':
                    instr += "add $" + str(self.symbol.address[fsym]) +", $" +str(expr.children[1].symbol.address[fsym]) +", $" +str(expr.children[2].symbol.address[fsym])
                if expr.children[0] == 'minus':
                    instr += "sub $" + str(self.symbol.address[fsym]) +", $" +str(expr.children[1].symbol.address[fsym]) +", $" +str(expr.children[2].symbol.address[fsym]) 
                if expr.children[0] == 'eql':
                    instr += "sub $4 " +", $" +str(expr.children[1].symbol.address[fsym]) +", $" +str(expr.children[2].symbol.address[fsym])
                    instr += "\n\t"
                    instr += "slti $5, $4, 1"
                    instr += "\n\t"
                    instr += "addi $6, $0, -1"
                    instr += "\n\t"
                    instr += "slt $4, $6, $4"
                    instr += "\n\t"
                    instr += "and $" + str(self.symbol.address[fsym])  + ", $4, $5"
                if expr.children[0] == 'neq':
                    instr += "sub $4 " +", $" +str(expr.children[1].symbol.address[fsym]) +", $" +str(expr.children[2].symbol.address[fsym])
                    instr += "\n\t"
                    instr += "slti $5, $4, 0"
                    instr += "\n\t"
                    instr += "slt $4, $0, $4"
                    instr += "\n\t"
                    instr += "or $" + str(self.symbol.address[fsym])  + ", $4, $5"
                if expr.children[0] == 'lss':
                    instr += "slt $" + str(self.symbol.address[fsym]) +", $" +str(expr.children[1].symbol.address[fsym]) +", $" +str(expr.children[2].symbol.address[fsym])
                if expr.children[0] == 'leq':
                    instr += "addi " + "$4" +" $" +str(expr.children[2].symbol.address[fsym]) + ", 1"
                    instr += "\n\t"
                    instr += "slt $" + str(self.symbol.address[fsym]) +", $" +str(expr.children[1].symbol.address[fsym]) +", $4"
                if expr.children[0] == 'gtr':
                    instr += "slt $" + str(self.symbol.address[fsym]) +", $" +str(expr.children[2].symbol.address[fsym]) +", $" +str(expr.children[1].symbol.address[fsym]) 
                if expr.children[0] == 'geq':
                    instr += "addi " + "$4" +", $" +str(expr.children[1].symbol.address[fsym]) + ", 1"
                    instr += "\n\t"
                    instr += "slt $" + str(self.symbol.address[fsym]) +", $" +str(expr.children[2].symbol.address[fsym]) +", $4"
                    
            # one immediate
            elif not(isinstance(expr.children[1], Const) and \
                isinstance(expr.children[2], Const)):
                immediate = expr.children[1] if isinstance(expr.children[1], Const) else expr.children[2]
                reg = expr.children[2] if isinstance(expr.children[1], Const) else expr.children[1]

                if expr.children[0] == 'times':
                    instr += "ori $4, $0, " + str(immediate.value) 
                    instr += "\n\t"
                    instr += "mul $" + str(self.symbol.address[fsym]) +", $" + str(reg.symbol.address[fsym]) + ", $4"
                if expr.children[0] == 'slash':
                    instr += "ori $4, $0, " + str(immediate.value) 
                    instr += "\n\t"
                    if immediate == expr.children[1]:
                        instr += "div $" + str(self.symbol.address[fsym]) +", $4, $" + str(expr.children[2].symbol.address[fsym])
                    else:
                        instr += "div $" + str(self.symbol.address[fsym])  + ", $" + str(expr.children[2].symbol.address[fsym]) +", $4"
                if expr.children[0] == 'plus':
                    instr += "addi $" + str(self.symbol.address[fsym]) +", $" + str(reg.symbol.address[fsym]) + ", " + str(immediate.value)
                if expr.children[0] == 'minus':
                    instr += "ori $4, $0," + str(immediate.value) 
                    instr += "\n\t"
                    if immediate == expr.children[1]:
                        instr += "sub $" + str(self.symbol.address[fsym]) +", $4, $" + str(expr.children[2].symbol.address[fsym])
                    else:
                        instr += "sub $" + str(self.symbol.address[fsym])  + ", $" + str(expr.children[1].symbol.address[fsym]) +", $4"

                if immediate == expr.children[1]:
                    instr += "\n\tori $7, $0," + str(immediate.value)
                    instr += "\n\t"   
                    if expr.children[0] == 'eql':
                        instr += "sub $4 " + ", $7" +", $" +str(expr.children[2].symbol.address[fsym])
                        instr += "\n\t"
                        instr += "slti $5, $4, 1"
                        instr += "\n\t"
                        instr += "subi $6, $0, 1"
                        instr += "\n\t"
                        instr += "slt $4, $6, $4"
                        instr += "\n\t"
                        instr += "and $" + str(self.symbol.address[fsym])  + ", $4, $5"
                    if expr.children[0] == 'neq':
                        instr += "sub $4 " +", " + "$7" +", $" +str(expr.children[2].symbol.address[fsym])
                        instr += "\n\t"
                        instr += "slti $5, $4, 0"
                        instr += "\n\t"
                        instr += "slt $4, $0, $4"
                        instr += "\n\t"
                        instr += "or $" + str(self.symbol.address[fsym])  + ", $4, $5"
                    if expr.children[0] == 'lss':
                        instr += "slt $" + str(self.symbol.address[fsym]) +", " + "$7" +", $" +str(expr.children[2].symbol.address[fsym])
                    if expr.children[0] == 'leq':
                        instr += "addi " + "$4" +" $" +str(expr.children[2].symbol.address[fsym]) + ", 1"
                        instr += "\n\t"
                        instr += "slt $" + str(self.symbol.address[fsym]) +", " + "$7" +", $4"
                    if expr.children[0] == 'gtr':
                        instr += "slt $" + str(self.symbol.address[fsym]) +", $" +str(expr.children[2].symbol.address[fsym]) +", " + "$7" 
                    if expr.children[0] == 'geq':
                        instr += "addi " + "$4" +", " + "$7" + ", 1"
                        instr += "\n\t"
                        instr += "slt $" + str(self.symbol.address[fsym]) +", $" +str(expr.children[2].symbol.address[fsym]) +", $4"
                else:
                    instr += "\n\tori $7, $0," + str(immediate.value) 
                    instr += "\n\t"
                    if expr.children[0] == 'eql':
                        instr += "sub $4 " +", $" +str(expr.children[1].symbol.address[fsym]) +", " +"$7"
                        instr += "\n\t"
                        instr += "slti $5, $4, 1"
                        instr += "\n\t"
                        instr += "addi $6, $0, -1"
                        instr += "\n\t"
                        instr += "slti $4, $6, $4"
                        instr += "\n\t"
                        instr += "and $" + str(self.symbol.address[fsym])  + ", $4, $5"
                    if expr.children[0] == 'neq':
                        instr += "sub $4 " +", $" +str(expr.children[1].symbol.address[fsym]) +", " +"$7"
                        instr += "\n\t"
                        instr += "slti $5, $4, 0"
                        instr += "\n\t"
                        instr += "slt $4, $0, $4"
                        instr += "\n\t"
                        instr += "or $" + str(self.symbol.address[fsym])  + ", $4, $5"
                    if expr.children[0] == 'lss':
                        instr += "slt $" + str(self.symbol.address[fsym]) +", $" +str(expr.children[1].symbol.address[fsym]) +", " +"$7"
                    if expr.children[0] == 'leq':
                        instr += "addi " + "$4" +" " +"$7" + ", 1"
                        instr += "\n\t"
                        print("############ " + self.symbol.name  + str(self.symbol.address[fsym]))
                        instr += "slt $" + str(self.symbol.address[fsym]) +", $" +str(expr.children[1].symbol.address[fsym]) +", $4"
                    if expr.children[0] == 'gtr':
                        instr += "slt $" + str(self.symbol.address[fsym]) +", " +"$7" +", $" +str(expr.children[1].symbol.address[fsym]) 
                    if expr.children[0] == 'geq':
                        instr += "addi " + "$4" +", $" +str(expr.children[1].symbol.address[fsym]) + ", 1"
                        instr += "\n\t"
                        instr += "slt $" + str(self.symbol.address[fsym]) +", " +"$7" +", $4"
            else:
                instr +="< Errore - no operation defined"
        return instr + "\n"




    def _get_symbol_level(self):
        res = set()

        for c in [self.symbol, self.expr]:
            # if is a symbol and not a function call and not a constant
            if isinstance(c, Symbol) and \
               not isinstance(c.stype, FunctionType) and\
               c.value is None :
                print("found " + c.name)
                res.add(c.level)
            elif isinstance(c, IRNode):
                res.update(c._get_symbol_level())
        return res



    def lower(self):
        if isinstance(self.expr, Expr):
            register = self.expr.get_destination_register()
            self.expr.lower()
            store = StoreStatMIPS(self.parent, self.symbol, self.symtab, register)
            res = StatList(self.parent, [self.expr, store], self.symtab)
            return self.parent.replace(self, res)
        elif isinstance(self.expr, Const):
            store = StoreStatMIPS(self.parent, self.symbol, self.symtab, self.expr)
            return self.parent.replace(self, store)
        elif isinstance(self.expr, Var):
            load = LoadStatMIPS(None, None, self.expr.symbol, self.symtab)
            store = StoreStatMIPS(self.parent, self.symbol, self.symtab, load.get_dest_register())
            res = StatList(self.parent, [load, store], self.symtab)
            return self.parent.replace(self, res)

    def instr_dot_repr(self):
        return self.symbol.instr_dot_repr() + " := " + self.expr.instr_dot_repr()

    def to_three_addr_form(self):

        if isinstance(self.expr, Var) or isinstance(self.expr, Const):
            return AssignStat(target=self.symbol, expr=self.expr, symtab=self.local_symtab)

        SSA_list, expr_ssa = self.expr.to_three_addr_form()

        SSA_list.append(AssignStat(target=self.symbol, expr=expr_ssa, symtab=self.local_symtab))

        return SSA_list

class BranchStat(Stat):
    def __init__(self, cond_var, on_true=None, on_false=None, symtab=None, parent=None):
        self.parent = parent
        self.cond_var = cond_var
        self.symtab = symtab

        self.on_true = on_true
        self.on_false = on_false

    def get_uses(self):
        return set([self.cond_var])

    def set_on_true(self, BB):
        self.on_true = BB


    def set_on_false(self, BB):
        self.on_false = BB

    def generate_code(self, fsym):
        res = "# " + self.instr_dot_repr() + "\n"

        res += "\tbnez $" + str(self.cond_var.address[fsym]) + ", " + self.on_true.lbl_begin + "\n"
        res += "\tj " + self.on_false.lbl_begin + "\n"

        return res

    def instr_dot_repr(self):
        return "BNEQZ "  + self.cond_var.instr_dot_repr()



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


class StoreStatMIPS(Stat):
    def __init__(self, parent=None, symbol=None, symtab=None, value=None, offset=0):
        self.parent = parent
        self.store_symbol = symbol
        # offset from the register specified in value
        self.offset = offset
        # the symbol is the address where to store the value
        self.symbol = symbol
        self.symtab = symtab
        # the value contains the register or the value to be stored in memory
        self.store_value = value
        if not (isinstance(value, Register) or isinstance(value, Const)):
            raise Exception("Argument of store must be a register or a constant")

        if isinstance(self.store_symbol, Register) or isinstance(self.store_symbol, Const):
            self.children = [self.store_symbol, self.store_value]
        else:
            self.children = [Var(self, self.store_symbol, self.symtab), self.store_value]
        self.store_symbol.parent = self
        self.store_value.parent = self

    def collect_uses(self):
        return [self.store_symbol]


    def get_function_call_uses(self):
        sym = self.symtab.find(self.store_symbol.name)
        if sym.level != self.enclosing_function().get_name():
            return [], [sym.level]
        else :
            return [], []


class BinStat(Stat):
    def __init__(self, operation, operand_1, operand_2, destination, parent=None, symtab=None):
        self.children = [operation, operand_1, operand_2, destination]
        self.parent = parent
        self.symtab = symtab

    def get_dest_register(self):
        return self.children[3]

    def collect_uses(self):
        return []


class StoreStat(Stat):
    def __init__(self, variables, parent=None, symtab=None):
        
        if variables is None:
            self.to_load = set()
        else:
            self.to_load = variables

        self.parent = parent
        self.symtab = symtab
        self.fsym = symtab.fsym

    def add_var_to_store(self, var):
        self.to_load.update(var)

    def instr_dot_repr(self):

        res = ""

        for sym in self.to_load:
            res += sym.instr_dot_repr() + ", "

        return  "Store [" + res[:-2] + "]"


    def generate_code(self, fsym):

        code = ""

        for sym in self.to_load:

            if sym.temp:
                continue

            if sym.level == self.fsym:
                # find the index on the stack

                code += "# storing " + sym.name + "\n"

                idx = self.fsym.stack.index(sym)

                code +="\tsw $" + str(sym.address[fsym]) + ", -" + str(idx*4) + "($fp)\n"

            else:
                # find the index on the stack of the parent function
                code += "# storing " + sym.name + "\n"

                fn_idx = self.fsym.stack.index(sym.level)
                code +="\tlw $4, -" + str(fn_idx*4) + "($fp)\n"
                idx = sym.level.stack.index(sym)
                code +="\tsw $" + str(sym.address[fsym]) + ", -" + str(idx*4) + "($4)\n"

        return code


class LoadStat(Stat):
    def __init__(self, variables, parent=None, symtab=None):
        
        if variables is None:
            self.to_load = set()
        else:
            self.to_load = variables

        self.parent = parent
        self.symtab = symtab
        self.fsym = symtab.fsym

    def add_var_to_load(self, var):
        self.to_load.update(var)

    def generate_code(self, fsym):

        code = ""

        for sym in self.to_load:

            if sym.temp:
                continue

            if sym.level == self.fsym:
                # find the index on the stack

                code += "# loading " + sym.name + "\n"

                idx = self.fsym.stack.index(sym)

                code +="\tlw $" + str(sym.address[fsym]) + ", -" + str(idx*4) + "($fp)\n"

            else:
                # find the index on the stack of the parent function
                code += "# loading " + sym.name + "\n"

                fn_idx = self.fsym.stack.index(sym.level)
                code +="\tlw $4, -" + str(fn_idx*4) + "($fp)\n"
                idx = sym.level.stack.index(sym)
                code +="\tlw $" + str(sym.address[fsym]) + ", -" + str(idx*4) + "($4)\n"

        return code

    def instr_dot_repr(self):

        res = ""

        for sym in self.to_load:
            res += sym.instr_dot_repr() + ", "

        return  "Load [" + res[:-2] + "]"




class LoadStatMIPS(Stat):
    def __init__(self, register=None, parent=None, symbol=None, symtab=None, offset=0):
        self.offset = offset
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

    def get_function_call_uses(self):
        sym = self.symtab.find(self.symbol.symbol)
        if sym and  sym.level != self.enclosing_function().get_name():
            return [], [sym.level]
        else :
            return [], []


class StatList(Stat):
    def __init__(self, parent=None, children=None, symtab=None):
        self.parent = parent
        if children:
            self.children = children[:]
            for c in self.children:
                c.parent = self
        else:
            self.children = []
        self.symtab = symtab

    def get_function_call_uses(self):
        call_uses = ([],[])

        for c in self.children:
            call_uses = (call_uses[0] + c.get_function_call_uses()[0] ,
                         call_uses[1] + c.get_function_call_uses()[1])

        return call_uses

    def append(self, elem):
        elem.parent = self
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

    def get_function_call_uses(self):
        return self.body.get_function_call_uses()

class PrintStat(Stat):
    def __init__(self, parent=None, symbol=None, symtab=None):
        self.parent = parent
        self.symbol = symbol
        self.symtab = symtab

    def get_uses(self):
        return set([self.symbol])

    def collect_uses(self):
        return [self.symbol]

    def generate_code(self, fsym):
        res = "# " + self.instr_dot_repr() + "\n"

        res += "\tori $2, $0, 1\n"
        res += "\tor $4, $0, $" + str(self.symbol.address[fsym]) +  "\n"

        res += "\tsyscall\n"
        # print a newline

        res += "# print a newline\n"
        res += "\taddi $a0, $0, 0xA\n" 
        res += "\taddi $v0, $0, 0xB\n" 
        res += "\tsyscall\n"

        return res

    def get_function_call_uses(self):
        sym = self.symtab.find(self.symbol.name)
        if sym.level != self.enclosing_function().get_name():
            return [], [sym.level]
        else :
            return [], []

    def instr_dot_repr(self):
        return "print " + self.symbol.instr_dot_repr() 

class InputStat(Stat):
    def __init__(self, parent=None, symbol=None, symtab=None):
        self.parent = parent
        self.symbol = symbol
        self.symtab = symtab
        self.local_symtab = self.symtab

    def collect_defs(self):
        return [self.symbol]

    def get_function_call_uses(self):
        sym = self.symtab.find(self.symbol.name)
        if sym.level != self.enclosing_function().get_name():
            return [], [sym.level]
        else :
            return [], []



    def instr_dot_repr(self):
        return "input " + self.symbol.instr_dot_repr() 


    def generate_code(self, fsym):
        res = "# " + self.instr_dot_repr() + "\n"

        res += "\taddi $v0 , $0 , 5\n"
        res += "\tsyscall\n"
        res += "\tmove $" + str(self.symbol.address[fsym]) +  ", $v0\n"

        return res
  

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
        self.function_label = standard_types['label']()
        # add the pair name/label to the function_labels dictionary
        function_labels[self.symbol.name] = self.function_label
        self.body.parent = self

    def get_name(self):
        return self.symbol.name

    def get_used_frame(self):
        return self.body.body.get_function_call_uses()

    def get_base_label(self):
        """ returns the Symbol object containing
            the label used to jump to the function code """
        return self.function_label

    def getGlobalSymbols(self):
        return self.body.global_symtab.exclude([standard_types['function'], standard_types['label']])

    def lower(self):
        statement_list = self.body.body

        empty = EmptyStat()
        empty.setLabel(self.function_label)

        br = BranchStat(None, None, standard_types['register'].get_ra_register(), self.getGlobalSymbols())
        # add branch to return address
        statement_list.append(br)
        statement_list.children.insert(0, empty)


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
