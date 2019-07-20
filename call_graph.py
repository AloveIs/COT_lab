from ir import *
from graphviz import Digraph

class CallNode:
    def __init__(self, symbol=None, uses=None, calls=None, graph=None):

        self.symbol = symbol
        self.graph = graph

        # calling relationship
        if calls is None:
        	self.calls = set()
        else:
        	self.calls = calls

        # uses of other functions
        if uses is None:
        	self.uses = set()
        else:
        	self.uses = uses

    def __get_node(self, symbol):
    	return self.graph.nodes[symbol]

    def fixed_point_iteration(self):

    	called_uses = set()

    	for called in self.calls:
    		called_uses.update(self.__get_node(called).uses)

    	# find missing elements

    	to_update = called_uses.difference(self.uses)

    	if len(to_update) == 0:
    		return False
    	else:
    		self.uses.update(to_update)
    		return True


    def remove_refexivity(self):
    	if self.symbol in self.uses:
    		self.uses.remove(self.symbol)


class CallGraph:
    def __init__(self, cfg, symtab, show_before=True):
        self.symtab = symtab
        self.cfg = cfg

        self.function_calls = cfg.get_function_calls()
        self.function_uses = cfg.get_function_dependency()


        # dictionary of the function nodes
        self.nodes =dict()

        self.__create_graph()

        if show_before:
        	self.graphviz("before_closure")
        self.__fixed_point()



    def __create_graph(self):
		for function in self.symtab.get_symtab_dict().keys():
			self.nodes[function] = CallNode(function, calls=self.function_calls[function], uses=self.function_uses[function], graph=self) 

    def graphviz(self, name="callgraph"):
    	G = Digraph(name)

    	# add nodes
    	for function, node in self.nodes.items():
    		G.node(str(id(function)), function.name + "[" + function.level.name + "]")
    		
    		# add call relationship
    		for called in node.calls:
    			G.edge(str(id(function)),str(id(called)) ,"call", {"color":"forestgreen", "fontcolor":"forestgreen"})

    		# add use relationship
    		for used in node.uses:
    			G.edge(str(id(function)),str(id(used)) ,"uses", {"color":"chocolate", "fontcolor":"chocolate"})

    	G.view()

    def __remove_refexivity(self):

    	for node in self.nodes.values():
    		node.remove_refexivity()

    def __fixed_point(self):

    	is_updated = True

    	while is_updated:

    		is_updated = False

    		for function, node in self.nodes.items():
    			is_updated = is_updated or (node.fixed_point_iteration())

        self.__remove_refexivity()

    	print("Finished fixed point")
# 