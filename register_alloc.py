from graphviz import Graph
from random import randint


# $0            $zero       Hard-wired to 0
# $1            $at         Reserved for pseudo-instructions
######### TO USE FOR SYSCALLS
# $2 - $3       $v0, $v1    Return values from functions
# $4 - $7       $a0 - $a3   Arguments to functions - not preserved by subprograms

######### LOCAL VARIABLES TO USE
# $8 - $15      $t0 - $t7   Temporary data, not preserved by subprograms
# $16 - $23     $s0 - $s7   Saved registers, preserved by subprograms
# $24 - $25     $t8 - $t9   More temporary registers, not preserved by subprograms

# $26 - $27     $k0 - $k1   Reserved for kernel. Do not use.
# $28           $gp         Global Area Pointer (base of global data segment)
# $29           $sp         Stack Pointer
# $30           $fp         Frame Pointer
# $31           $ra         Return Address
# $f0 - $f3     -           Floating point return values
# $f4 - $f10    -           Temporary registers, not preserved by subprograms
# $f12 - $f14   -           First two arguments to subprograms, not preserved by subprograms
# $f16 - $f18   -           More temporary registers, not preserved by subprograms
# $f20 - $f31   -           Saved registers, preserved by subprograms




TEMP_REGISTERS = 18 # from $8 to $25


colors = {
    0 : "Peru",
    1 : "Aquamarine",
    2 : "Coral",
    3 : "Beige",
    4 : "Cadetblue",
    5 : "Darksalmon",
    6 : "DarkSeaGreen",
    7 : "DarkTurquoise",
    8 : "DeepPink",
    9 : "Gray",
    10 : "Gold",
    11 : "GreenYellow",
    12 : "Magenta",
    13 : "Pink",
    14 : "Salmon",
    15 : "RosyBrown",
    16 : "SpringGreen",
    17 : "SkyBlue"
}



class ColorNode:
    def __init__(self, symbol=None):

        self.symbol = symbol
        self.color = None

        self.co_live_with = set()

    def add_relations(self,co_livers):
        self.co_live_with |= co_livers

    def set_color(self, color):
        self.color = color
        self.symbol.address = color + 8
        print("For "  + self.symbol.name + " the register is " + str(self.symbol.address))



class ColorGraph:
    def __init__(self, fsym, live_graph):
        self.fsym = fsym
        self.live_graph = live_graph
        self.variables = set()

        for node in live_graph.node_list:
            self.variables |= node.uses
            self.variables |= node.defs
        # dictionary of the function nodes
        self.nodes =dict()

        self.__create_graph()
        self.color()


    def __create_graph(self):
        # create the nodes
        for var in self.variables:
            self.nodes[var] = ColorNode(var)

        # create connections
        for var in self.variables:
            for node in self.live_graph.node_list:
                if var in node.live_in:
                    self.nodes[var].add_relations(node.live_in - set([var]))

    def color(self):
        for node in self.nodes.values():
            taken_col = set()
            for neigh in node.co_live_with:
                if self.nodes[neigh].color is not None:
                    taken_col.add(self.nodes[neigh].color)

            for i in range(18):
                if i in taken_col:
                    continue
                else:
                    node.set_color(i)
                    break


    def graphviz(self):

        G = Graph("ColorGraph" + self.fsym.name + str(id(self.fsym)))

        visited = set()

        for k,v in self.nodes.items():
            if v.color is None:
                G.node(str(id(k)), k.name)
            else:
                G.node(str(id(k)), k.name, {"style":"filled","color": colors[v.color]})

            visited.add(k)

            for co_live in v.co_live_with:
                if co_live not in visited:
                    G.edge(str(id(k)),str(id(co_live)))

        G.view()


class RegisterAllocator:
    def __init__(self, liveness_graphs, cfg):
        self.live_graphs = liveness_graphs
        self.cfg = cfg
        self.cfgs = cfg.cfgs

        self.color_graphs = dict()

        self.__assign_registers()

    def __assign_registers(self):

        for fsym, live_graph in self.live_graphs.items():
            print("Assigning register to function: " + fsym.name)
            self.__assign_registers_function(fsym, live_graph, self.cfgs[fsym])

    def __assign_registers_function(self, fsym, live_graph, cfg):
        
        self.color_graphs[fsym] = ColorGraph(fsym, live_graph)
        self.color_graphs[fsym].graphviz()