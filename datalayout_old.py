from texttable import Texttable

from ir import *
from logger import logger

GLOBAL_VARIABLE_BASE_ADDR = 0x10000000

call_graph = None


class CallNode:
    def __init__(self, symbol=None, parent=None):
        self.backward = []
        self.forward = []
        self.function = symbol
        self.parent = parent
        self.used = set()

    def add_child(self, node):
        self.forward.append(node)
        node.parent = self

    def get_dotty_format(self):
        rep = str(id(self)) + ' [label="' + self.function + str(list(self.used)) + '"];\n'

        for n in self.forward:
            rep = rep + str(id(self)) + " -> " + str(id(n)) + ";\n"
        return rep


class CallGraph:
    def __init__(self):
        self.root = CallNode("global")
        self.current_node = self.root
        self.function_dependencies = dict()
        self.node_list = [self.root]
        self.function_dependencies["global"] = ([], [])

    def fixed_point(self):

        changed = True
        while changed:
            changed = False
            for n in self.node_list:
                for next_n in n.forward:
                    print str(n.used) + "\t",
                    print str(next_n.used) + "\t removing : " + n.function,
                    updated = n.used.union(next_n.used)
                    if n.function in updated:
                        for x in n.used.union(next_n.used):
                            if x == n.function or x == "global":
                                updated.remove(x)
                    print str(updated) + "\t"
                    if len(n.used) != len(updated):
                        n.used = updated
                        changed = True

    def create(self, ast):
        self.get_dependencies(ast.defs)
        self.print_definition_tree()
        self.build_graph()
        self.fixed_point()
        self.print_graph()

    def print_definition_tree(self, level=0):
        print("\t" * level + self.current_node.function)
        for c in self.current_node.forward:
            self.current_node = c
            self.print_definition_tree(level + 1)
            self.current_node = c.parent

    def print_graph(self):
        graph_str = "Digraph G {\n"

        for n in self.node_list:
            graph_str = graph_str + n.get_dotty_format()

        graph_str = graph_str + "}\n"

        file = open("call_graph.dot", "w")
        file.write(graph_str)
        file.close()

    def get_node(self, name):
        for n in self.node_list:
            if n.function == name:
                return n
        return None

    def build_graph(self):
        for n in self.node_list:
            to_add = []

            for dep in self.function_dependencies[n.function][0]:
                to_add.append(self.get_node(dep))
            n.forward = n.forward + to_add
            n.used = set(self.function_dependencies[n.function][1])

    def get_dependencies(self, definition_list):
        for c in definition_list.children:
            node = CallNode(c.get_name())
            self.node_list.append(node)
            self.current_node.add_child(node)
            self.current_node = node

            self.function_dependencies[c.get_name()] = c.get_used_frame()
            self.get_dependencies(c.body.defs)

            self.current_node = self.current_node.parent

    def get_bp_to_stack(self, function_name):
        for n in self.node_list:
            if n.function == function_name:
                return n.used


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


def global_variables_layout(symtab):
    offset = 0

    for symbol in symtab:
        if symbol.stype.size != 0:
            debug("stype " + str(symbol.stype))
            symbol.address = GLOBAL_VARIABLE_BASE_ADDR + offset
            assert symbol.stype.size % 8 == 0
            offset += (symbol.stype.size / 8)


def function_data_layout(function_def):
    global call_graph

    debug("#### > function : " + function_def.symbol.name)
    local_symtab = function_def.body.local_symtab

    # -- return address
    # -- base pointer
    offset = -0x00000008

    for used_function in call_graph.get_bp_to_stack(function_def.symbol.name):
        symbol = Symbol("bp_" + used_function, standard_types['int'], level=function_def.symbol.name)
        local_symtab.append(symbol)
        symbol.address = offset
        offset -= (symbol.stype.size / 8)

    for symbol in local_symtab:
        if symbol.stype.size != 0:
            debug("stype " + str(symbol.stype))
            symbol.address = offset
            assert symbol.stype.size % 8 == 0
            offset -= (symbol.stype.size / 8)

    print(function_def.body.body.collect_uses())
    print_symtab(function_def.body.global_symtab)
    print_symtab(function_def.body.local_symtab)
    debug("####### <")

    for d in function_def.body.defs.children:
        if isinstance(d, FunctionDef):
            function_data_layout(d)


@logger
def data_layout(program):
    global call_graph
    call_graph = CallGraph()

    call_graph.create(program)

    print(call_graph.function_dependencies)

    debug("#### begin data layout")
    global_variables_symtab = program.local_symtab
    debug("#### > data layout - global variables")
    print_symtab(global_variables_symtab)
    global_variables_layout(global_variables_symtab)
    debug("#### < data layout - end global variables")
    print_symtab(global_variables_symtab)

    definition_list = program.defs
    for function_def in definition_list.children:
        function_data_layout(function_def)
