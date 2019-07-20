#!/usr/bin/python

from ir import *
from logger import logger
import sys
from lexer import symbols as lex_symbols
from lexer import lexer, __test_program
from sys import argv
from call_graph import CallGraph



from support import *
from datalayout import data_layout
from cfg import *

# this implement the recursive descent parser for PL/0
__doc__ = '''PL/0 recursive descent parser adapted from Wikipedia'''

symbols = lex_symbols.keys()  # [ 'ident', 'number', 'lparen', 'rparen', 'times', 'slash', 'plus', 'minus', 'eql',
# 'neq', 'lss', 'leq', 'gtr', 'geq', 'callsym', 'beginsym', 'semicolon', 'endsym', 'ifsym', 'whilesym', 'becomes',
# 'thensym', 'dosym', 'constsym', 'comma', 'varsym', 'procsym', 'period', 'oddsym' ]

sym = None
value = None
new_sym = None
new_value = None




class FunctionStack(list):
    def __init__(self):
        self.level = 0
        self.global_sym = Symbol("global", standard_types['function'], level=None)
        self.global_sym.level = self.global_sym

    def peek(self):
        if self.level == 0:
            return self.global_sym
        return self[self.level - 1]

    def pop(self):
        r = super(FunctionStack, self).pop(self.level - 1)
        debug("exiting " + r.name + " , level is " + str(self.level))
        self.level -= 1
        return r

    def push(self, o):
        self.append(o)
        self.level += 1
        debug("entering " + o.name + " , now level is " + str(self.level))


function_stack = FunctionStack()


# this method updates the global variables
def getsym():
    """Update sym"""
    global new_sym
    global new_value
    global sym
    global value
    try:
        sym = new_sym
        value = new_value
        new_sym, new_value = the_lexer.next()
    except StopIteration:  # this in case I don't have anymore tokens
        return 2  # 2 to signal the end of the program
    print 'getsym:', new_sym, new_value
    return 1


def error(msg):
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    print FAIL, msg, new_sym, new_value, ENDC


# if the next symbol is the one we are looking for then we consume it
# and return ut
def accept(s):
    print 'accepting', s, '==', new_sym
    return getsym() if new_sym == s else 0


# if we find the symbol we are expectiong we return 1 otherwhise 0
def expect(s):
    print 'expecting', s
    if accept(s):
        return 1
    error("expect: unexpected symbol")
    return 0


###################################
# Grammar Rules
#
# for each rule  aseries of conditional
# is put for each symbol to accept.


# the symbol table is used also for some semantic checks
@logger
def factor(symtab):
    # we return small parts of the AST, in this case Variables nodes
    # and also constants
    if accept('ident'):
        return Var(var=symtab.find(value), symtab=symtab)
    if accept('number'):
        return Const(value=value, symtab=symtab)
    elif accept('lparen'):
        expr = expression(symtab)
        expect('rparen')
        return expr
    else:
        error("factor: syntax error")
        getsym()


@logger
def term(symtab):
    op = None
    expr = factor(symtab)
    while new_sym in ['times', 'slash', 'mod']:
        getsym()
        op = sym
        # build and unbalanced tree ( we are keeping the order of the operations)
        expr2 = factor(symtab)
        expr = BinExpr(children=[op, expr, expr2], symtab=symtab)
    return expr


@logger
def expression(symtab):
    op = None

    # takes in account for the first unary operator
    if new_sym in ['plus', 'minus']:
        getsym()
        op = sym
    expr = term(symtab)

    # FIXED_ERROR: i changed 'initial_op' to just 'op' into the constructor of UnExp
    if op:
        expr = UnExpr(children=[op, expr], symtab=symtab)
    while new_sym in ['plus', 'minus']:
        getsym()
        op = sym
        expr2 = term(symtab)
        expr = BinExpr(children=[op, expr, expr2], symtab=symtab)
    return expr


@logger
def condition(symtab):
    if accept('oddsym'):
        return UnExpr(children=['odd', expression(symtab)], symtab=symtab)
    else:
        expr = expression(symtab)
        if new_sym in ['eql', 'neq', 'lss', 'leq', 'gtr', 'geq']:
            getsym()
            print 'condition operator', sym, new_sym
            op = sym
            expr2 = expression(symtab)
            return BinExpr(children=[op, expr, expr2], symtab=symtab)
        else:
            error("condition: invalid operator")
            getsym()


@logger
def statement(symtab):
    if accept('ident'):
        target = symtab.find(value)
        if target is None:
            debug("################### is None " + value)
        expect('becomes')  # ':='
        expr = expression(symtab)

        return AssignStat(target=target, expr=expr, symtab=symtab)
    elif accept('callsym'):
        expect('ident')
        # procedures works on global variables, there are no parameters or
        # return values.
        return CallStat(call_expr=CallExpr(function=symtab.find(value), symtab=symtab), symtab=symtab)
    elif accept('beginsym'):
        statement_list = StatList(symtab=symtab)
        statement_list.append(statement(symtab))
        while accept('semicolon'):
            statement_list.append(statement(symtab))
        expect('endsym')
        statement_list.print_content()
        return statement_list
    elif accept('ifsym'):
        debug("got if")
        cond = condition(symtab)
        expect('thensym')
        then = statement(symtab)
        debug("got then")
        if accept('elsesym'):
            debug("there is the else")
            else_statements = statement(symtab)
            return IfStat(cond=cond, thenpart=then, symtab=symtab, elsepart=else_statements)
        debug("returning if stat if")
        return IfStat(cond=cond, thenpart=then, symtab=symtab)
    elif accept('whilesym'):
        cond = condition(symtab)
        expect('dosym')
        body = statement(symtab)
        return WhileStat(cond=cond, body=body, symtab=symtab)
    elif accept('print'):
        expect('ident')
        # it represent a special node that will
        # be mapped to a system function call
        return PrintStat(symbol=symtab.find(value), symtab=symtab)
    elif accept('input'):
        expect('ident')
        return InputStat(symbol=symtab.find(value), symtab=symtab)


@logger
def block(symtab):
    local_vars = LocalSymbolTable(function_stack.peek(), parent=symtab)
    defs = DefinitionList()
    if accept('constsym'):
        expect('ident')
        name = value
        expect('eql')
        expect('number')
        # FIXED_ERROR : the constructor had the last parameter outside
        local_vars.append(Symbol(name, standard_types['int'], value=value, level=function_stack.peek()))
        while accept('comma'):
            expect('ident')
            name = value
            expect('eql')
            expect('number')
            local_vars.append(Symbol(name, standard_types['int'], value=value, level=function_stack.peek()))
        expect('semicolon')
    if accept('varsym'):
        expect('ident')
        local_vars.append(Symbol(value, standard_types['int'], level=function_stack.peek()))
        while accept('comma'):
            expect('ident')
            local_vars.append(Symbol(value, standard_types['int'], level=function_stack.peek()))
        expect('semicolon')
    while accept('procsym'):
        expect('ident')
        fname = value
        fsym = Symbol(fname, standard_types['function'], level=function_stack.peek())
        function_stack.push(fsym)
        expect('semicolon')
        # call block
        fbody = block(local_vars) # symtab[:] + 
        function_stack.pop()
        local_vars.append(fsym)
        expect('semicolon')
        defs.append(FunctionDef(symbol=local_vars.find(fname), body=fbody))
    # this statement represents the main
    stat = statement(local_vars) # symtab[:] + 
    return Block(gl_sym=symtab, lc_sym=local_vars, defs=defs, body=stat)


@logger
def program():
    '''Axiom'''
    getsym()
    the_program = block(None)
    expect('period')
    return the_program


if __name__ == '__main__':

    # read from files passed as arguments

    the_lexer = None
    try:
        if len(argv) == 1:
            the_lexer = lexer(__test_program)
        else:
            from string import join

            with open(argv[-1], "r") as fin:
                text = join(fin.readlines())
            the_lexer = lexer(text)
    except Exception:
        # use the sample program in the lexer module
        the_lexer = lexer(__test_program)



    # Build the syntactic tree/IR tree
    res = program()

    res.navigate(constant_propagation)

    #debug("printing the result")
    #print '\n', res, '\n'
    print_dotty(res, "log.dot")


    #print_symbol_tables(res)
    
    # the whole symbol table
    # as a tree structure
    symtab = SymbolTable(res)
    symtab.show_graphviz()


    # build the CFG from the IR
    cfg = CFG(res)
    
    # show the CFG for each
    # function
    cfg.graphviz()


    # put the CFG into SSA form
    cfg.SSA()

    # show the CFG in SSA for each
    # function
    cfg.graphviz()

    call_graph = CallGraph(cfg, symtab)

    call_graph.graphviz()
    
    debug("#######################################")
    debug("############ DATA LAYOUT ##############")
    debug("#######################################")

    data_layout(symtab, call_graph)


    cfg.liveness_graphs(show=True)

    sys.exit(0)
    debug("printing the result - navigation")
    res.navigate(print_stat_list)

    debug("getting the list of nodes")

    node_list = get_node_list(res)

    debug("printing the list of nodes")
    for n in node_list:
        print type(n), id(n), '->', type(n.parent), id(n.parent)
    print '\nTotal nodes in IR:', len(node_list), '\n'

    debug("#### > starting to lowering")
    res.navigate(lowering)
    debug("#### < end of lowering")



    


    data_layout(res)

    raw_input("press the enter key to continue...")
    debug(str(res.global_symtab))
    debug(str(res.local_symtab))
    raw_input("press the enter key to continue...")

    raw_input("press the enter key to continue...")

    node_list = get_node_list(res)
    print '\n', res, '\n'
    for n in node_list:
        print type(n), id(n)
        try:
            n.flatten()
        except Exception as e:
            print e
    res.navigate(flattening)

    print '\n', res, '\n'

    print_dotty(res, "log.dot")
    raw_input("Ended log, now CFG")


    cfg.liveness()
    cfg.print_liveness()
    cfg.print_cfg_to_dot("cfg.dot")

    print "end of CFG"
