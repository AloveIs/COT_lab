#!/usr/bin/python

from graphviz import Digraph
from texttable import Texttable

__doc__ = '''Support functions for visiting the AST
These functions expose high level interfaces (passes) for actions that can be applied to multiple IR nodes.'''


def get_node_list(root):
    '''Get a list of all nodes in the AST'''

    def register_nodes(l):
        def r(node):
            if node not in l:
                l.append(node)

        return r

    node_list = []
    root.navigate(register_nodes(node_list))
    return node_list




def rowify(symbol):
    if symbol.address:
        addr = str(hex(symbol.address)) + ("" if symbol.level == "global" else "($fp)")
        return [symbol.name, symbol.stype, symbol.level, addr]
    return [symbol.name, symbol.stype, symbol.level, symbol.address]


def print_symtab(symtab):
    table = Texttable()
    table.add_row(['Symbol', 'Type', 'Level', 'Address'])

    for sym in symtab:
        table.add_row(rowify(sym))
    print table.draw()



def print_symbol_tables(ir):

    # recursive part of it to handle the root node
    def _print_symbol_tables(ir,G):
        print_symtab(ir.local_symtab)
        #print_symbol_tables(ir)
        for c in ir.defs.children:
            print(c.get_name())
            _print_symbol_tables(c.body)


    # create a symbol table diagram
    G = Digraph("Symbol Tables")

    # print information about the first node
    print("Global")
    label = "GLOBAL:\n"

    for s in ir.local_symtab:
        label = label + (s.name + "\n")

    G.node("Global", label,  {"shape":"box"})


    # print symbol table in terminal
    print_symtab(ir.local_symtab)
    #print_symbol_tables(ir)
    for c in ir.defs.children:
        print(c.get_name())
        _print_symbol_tables(c.body,G)

    print(G)
    G.render('testsymtab.gv', view=True)  # doctest: +SKIP


def get_symbol_tables(root):
    '''Get a list of all symtabs in the AST'''

    def register_nodes(l):
        def r(node):
            try:
                if node.symtab not in l: l.append(node.symtab)
            except Exception:
                pass
            try:
                if node.lc_sym not in l: l.append(node.symtab)
            except Exception:
                pass

        return r

    node_list = []
    root.navigate(register_nodes(node_list))
    return node_list


def constant_propagation(node):
    try:
        node.constant_propagation()
    except Exception, e:
        print 'Cannot Perform Constat Prop', type(node), e
        pass  # lowering not yet implemented for this class


def resolve_bin_expr(node):
    from ir import Const
    
    value = 0

    op1 = node.children[1]
    op2 = node.children[2]



    if node.children[0] == 'times':
        value = int(int(op1.value) * int(op2.value))
    if node.children[0] == 'slash':
        value = int(int(op1.value) / int(op2.value))
    if node.children[0] == 'plus':
        value = int(int(op1.value) + int(op2.value))
    if node.children[0] == 'minus':
        value = int(int(op1.value) - int(op2.value))
    if node.children[0] == 'eql':
        value = int(int(op1.value) == int(op2.value))
    if node.children[0] == 'neq':
        value = int(int(op1.value) != int(op2.value))
    if node.children[0] == 'lss':
        value = int(int(op1.value) < int(op2.value))
    if node.children[0] == 'leq':
        value = int(int(op1.value) <= int(op2.value))
    if node.children[0] == 'gtr':
        value = int(int(op1.value) > int(op2.value))
    if node.children[0] == 'geq':
        value = int(int(op1.value) >= int(op2.value))

    return Const(value=value, parent=node.parent)

def resolve_un_expr(node):
    from ir import Const
        
    value = 0

    op1 = node.children[1]

    if node.children[0] == 'plus':
        value = int(op1.value)
    if node.children[0] == 'minus':
        value = - int(op1.value)
    if node.children[0] == 'oddsym':
        value = int((int(op1.value) % 2) == 1)

    return Const(value=value, parent=node.parent)




def constant_folding(node):
    from ir import BinExpr, UnExpr, Const
    try:
        if isinstance(node, BinExpr):
            if isinstance(node.children[1], Const) and \
                isinstance(node.children[2], Const):
                node.parent.replace(node, resolve_bin_expr(node))
        if isinstance(node, UnExpr):
            if isinstance(node.children[1], Const):
                node.parent.replace(node, resolve_un_expr(node))
    except Exception, e:
        print 'Cannot Perform Constat Folding', type(node), e
        pass  # lowering not yet implemented for this class





def lowering(node):
    '''Lowering action for a node
	(all high level nodes can be lowered to lower-level representation'''
    try:
        check = node.lower()
        print 'Lowering', type(node), id(node)
        if not check:
            print 'Failed!'
    except Exception, e:
        print 'Cannot lower', type(node), e
        pass  # lowering not yet implemented for this class


def flattening(node):
    '''Flattening action for a node 
	(only StatList nodes are actually flattened)'''
    try:
        check = node.flatten()
        print 'Flattening', type(node), id(node)
        if not check:
            print 'Failed!'
    except Exception, e:
        # print type(node), e
        pass  # this type of node cannot be flattened


def dotty_wrapper(fout):
    '''Main function for graphviz dot output generation'''

    def dotty_function(irnode, G):
        from string import split, join
        from ir import Stat, Symbol
        attrs = set(['body', 'cond', 'thenpart', 'elsepart', 'call', 'step', 'expr', 'target', 'defs']) & set(
            dir(irnode))
        # the name as the ID of the object
        res = str(id(irnode)) + ' ['
        label = ""
        if isinstance(irnode, Stat) or isinstance(irnode, Symbol):
            res += 'shape=box,'
        res += 'label="' + str(irnode.__class__.__name__) + ' ' + str(id(irnode))
        label += str(irnode.__class__.__name__) + ' ' # + str(id(irnode))
        try:
            res += ': ' + str(irnode.value)
            label += str(irnode.value)
        except Exception:
            pass
        try:
            res += ': ' + irnode.name
            label += irnode.name
        except Exception:
            pass
        try:
            res += ': ' + getattr(irnode, 'symbol').name
            label += getattr(irnode, 'symbol').name
        except Exception:
            pass


        G.node(str(id(irnode)), label)

        res += '" ];\n'

        if 'children' in dir(irnode) and len(irnode.children):
            for node in irnode.children:
                G.edge(str(id(irnode)),str(id(node)))
                res += str(id(irnode)) + ' -> ' + str(id(node)) + ' [pos=' + `irnode.children.index(node)` + '];\n'
                if type(node) == str:
                    G.node(str(id(node)), node)
                    res += str(id(node)) + ' [label=' + node + '];\n'
        for d in attrs:
            node = getattr(irnode, d)
            if d == 'target':
                from ir import Register
                if isinstance(node, Register):
                    res += str(id(irnode)) + ' -> ' + str(id(node)) + ' [label=' + "jump to register_ra" + '];\n'
                else:
                    res += str(id(irnode)) + ' -> ' + str(id(node.value)) + ' [label=' + node.name + '];\n'
            else:
                G.edge(str(id(irnode)),str(id(node)))
                res += str(id(irnode)) + ' -> ' + str(id(node)) + ';\n'
        fout.write(res)
 
        return res

    return dotty_function


def print_dotty(root, filename):
    '''Print a graphviz dot representation to file'''
    G = Digraph("IR representation")

    fout = open(filename, "w")
    fout.write("digraph G {\n")
    node_list = get_node_list(root)
    dotty = dotty_wrapper(fout)
    
    for n in node_list: dotty(n, G)
    fout.write("}\n")

    G.render('ir.gv', view=True)



__DEBUG = True


def debug(string):
    if __DEBUG:
        print '\033[46m' + string + '\033[0m'  # '\033[33m' +
    else:
        pass
