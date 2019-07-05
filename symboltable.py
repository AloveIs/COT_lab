from graphviz import Digraph
from texttable import Texttable


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

    # create a symbol table diagram
    G = Digraph("Symbol Tables")

    # print information about the first node
    print("Global")

    # print symbol table in terminal
    print_symtab(ir.local_symtab)
    #print_symbol_tables(ir)
    for c in ir.defs.children:
        print(c.get_name())
        _print_symbol_tables(c.body,G)
    def _print_symbol_tables(ir,G):
        print_symtab(ir.local_symtab)
        #print_symbol_tables(ir)
        for c in ir.defs.children:
            print(c.get_name())
            _print_symbol_tables(c.body)