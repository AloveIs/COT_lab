from ir import *
from logger import logger





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
    def __init__(self, cfg):
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
