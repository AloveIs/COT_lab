#!/usr/bin/python

from ir import *
from logger import logger

from lexer import symbols as lex_symbols

# this implement the recursive descent parser for PL/0
__doc__ = '''PL/0 recursive descent parser adapted from Wikipedia'''

symbols = lex_symbols.keys()  # [ 'ident', 'number', 'lparen', 'rparen', 'times', 'slash', 'plus', 'minus', 'eql',
# 'neq', 'lss', 'leq', 'gtr', 'geq', 'callsym', 'beginsym', 'semicolon', 'endsym', 'ifsym', 'whilesym', 'becomes',
# 'thensym', 'dosym', 'constsym', 'comma', 'varsym', 'procsym', 'period', 'oddsym' ]

sym = None
value = None
new_sym = None
new_value = None


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
    if accept(s): return 1
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
    if accept('ident'): return Var(var=symtab.find(value), symtab=symtab)
    if accept('number'):
        return Const(value=value, symtab=symtab)
    elif accept('lparen'):
        expr = expression()
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

    # FIXME: i changed 'initial_op' to just 'op' into the constructor of UnExp
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
        expr = expression(symtab);
        if new_sym in ['eql', 'neq', 'lss', 'leq', 'gtr', 'geq']:
            getsym()
            print 'condition operator', sym, new_sym
            op = sym
            expr2 = expression(symtab)
            return BinExpr(children=[op, expr, expr2], symtab=symtab)
        else:
            error("condition: invalid operator")
            getsym();


@logger
def statement(symtab):
    if accept('ident'):
        target = symtab.find(value)
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
        expect('endsym');
        statement_list.print_content()
        return statement_list
    elif accept('ifsym'):
        cond = condition(symtab)
        expect('thensym')
        then = statement(symtab)
        if accept('elsesym'):
            else_statements = statement(symtab)
            return IfStat(cond=cond, thenpart=then, symtab=symtab, elsepart=else_statements)
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
    local_vars = SymbolTable()
    defs = DefinitionList()
    if accept('constsym'):
        expect('ident')
        name = value
        expect('eql')
        expect('number')
        # FIXME : the constructor had the last parmeter outside
        local_vars.append(Symbol(name, standard_types['int'], value= value))
        while accept('comma'):
            expect('ident')
            name = value
            expect('eql')
            expect('number')
            local_vars.append(Symbol(name, standard_types['int'], value= value))
        expect('semicolon');
    if accept('varsym'):
        expect('ident')
        local_vars.append(Symbol(value, standard_types['int']))
        while accept('comma'):
            expect('ident')
            local_vars.append(Symbol(value, standard_types['int']))
        expect('semicolon');
    while accept('procsym'):
        expect('ident')
        fname = value
        expect('semicolon');
        local_vars.append(Symbol(fname, standard_types['function']))
        fbody = block(local_vars)
        expect('semicolon')
        defs.append(FunctionDef(symbol=local_vars.find(fname), body=fbody))
    stat = statement(SymbolTable(symtab[:] + local_vars))
    return Block(gl_sym=symtab, lc_sym=local_vars, defs=defs, body=stat)


@logger
def program():
    '''Axiom'''
    global_symtab = SymbolTable()
    getsym()
    the_program = block(global_symtab)
    expect('period')
    return the_program


if __name__ == '__main__':
    from lexer import lexer, __test_program
    from sys import argv

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

    res = program()
    print '\n', res, '\n'
    res.navigate(print_stat_list)
    from support import *

    node_list = get_node_list(res)
    for n in node_list:
        print type(n), id(n), '->', type(n.parent), id(n.parent)
    print '\nTotal nodes in IR:', len(node_list), '\n'

    res.navigate(lowering)

    node_list = get_node_list(res)
    print '\n', res, '\n'
    for n in node_list:
        print type(n), id(n)
        try:
            n.flatten()
        except Exception:
            pass
    # res.navigate(flattening)
    print '\n', res, '\n'

    print_dotty(res, "log.dot")

    from cfg import *

    cfg = CFG(res)
    cfg.liveness()
    cfg.print_liveness()
    cfg.print_cfg_to_dot("cfg.dot")
