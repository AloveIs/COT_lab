#!/usr/bin/python

__doc__ = '''Control Flow Graph implementation
Includes cfg construction and liveness analysis.'''

from support import get_node_list, get_symbol_tables
from ir import *
from graphviz import Digraph

class LivenessNode:

    def __init__(self,statement):

        self.children = []

        self.statement = statement

        self.defs = statement.get_uses()
        self.uses = statement.get_defs()
        self.visted = False

    def add_follower(self, node):
        self.children.append(node)

    def unvisit(self):
        self.visited = False

    def dot_format(self):
        return self.statement.instr_dot_repr()

class LivenessGraph:

    def __init__(self,root_BB):

        self.node_list = []

        # create the graph
        self.create(root_BB)


    def create(self, BB):

        BB.visted = True

        root = LivenessNode(BB.instrs[0])
        self.node_list.append(root)
        current_node = root
        prev = None
        for i in range(1, len(BB.instrs)):
            prev = current_node
            current_node = LivenessNode(BB.instrs[i])
            self.node_list.append(current_node)
            prev.add_follower(current_node)

        # the last one must be added to the begining of the other BB
        for child in BB.children.values():
            if child is None:
                continue
            current_node.add_follower(self._create_recursion(child))

        self.root = root


    def _create_recursion(self, BB):

        if BB.visited:
            return self.find_node(BB.instrs[0])
        else:
            # mark the BB as visted
            BB.visited = True

        root = LivenessNode(BB.instrs[0])
        self.node_list.append(root)
        current_node = root
        prev = None
        for i in range(1, len(BB.instrs)):
            prev = current_node
            current_node = LivenessNode(BB.instrs[i])
            self.node_list.append(current_node)
            prev.add_follower(current_node)

        # the last one must be added to the begining of the other BB


        for key, child in BB.children.items():
            print("\tkey :" + str(key))
            if child is None:
                continue
            current_node.add_follower(self._create_recursion(child))

        return root

    def find_node(self, instr):
        for node in self.node_list:
            if node.statement == instr:
                return node
        return None


    def _unvisit(self):
        for node in self.node_list:
            node.unvisit()

    def graphviz(self):

        G = Digraph(str(id(self)))

        for node in self.node_list:
            G.node(str(id(node)), node.dot_format(), {"shape":"record"}) 

            for c in node.children:
                label = "{ }"
                G.edge(str(id(node)), str(id(c)), label=label)

        G.view()


class BasicBlock(object):
    def __init__(self, block, parents=None, next=None):
        '''Structure:
		Zero, one (next) or two (next, target_bb) successors
		Keeps information on labels
		'''
        self.children = dict()
        self.visited = False
        #if next is not None:
        self.children["next"] = next

        if parents is None:
            self.parents = []
        else:
            self.parents = list([parents])

        # list of instructions in the BB
        self.instrs = []
        self.__expand_block(block)


    def get_all_blocks(self):
        """Get the list of all the BB reachable from the node"""
        if self.visited is True:
            return []

        res = [self]
        self.visited = True

        for c in self.children.values():
            if c is None:
                continue
            res.extend(c.get_all_blocks())
        return res

    def _get_function_calls(self):

        res = set()

        for inst in self.instrs:
            if isinstance(inst, CallStat):
                # get the symbol of the function called
                res.add(inst.call.symbol)
            if isinstance(inst, CallExpr):
                # get the symbol of the function called
                res.add(inst.symbol)
        return res

    def _get_used_vars(self):
        res = set()

        # if there are no instructions
        if len(self.instrs) == 0:
            return self.children.values()[0]._get_used_vars()

        symtab = self.instrs[0].local_symtab

        res.update(symtab.get_external_var())
        return res

    def _get_function_dependency(self):
        dep = set()

        for inst in self.instrs:
            dep.update(inst._get_symbol_level())

        # remove this function and global
        return dep


    def add_parent(self, parent):
        self.parents.append(parent)


    def _graphviz_unvisit(self):
        self.visited = False
        
        for c in self.children.values():
            if c is not None and c.visited:
                c._graphviz_unvisit()

    def to_SSA(self):
        # new instructions in the list
        new_instr_list = []

        for inst in self.instrs:
            # new form of the instruction
            new_instr = inst.to_SSA()

            # if it is a list or a single element
            if isinstance(new_instr, list):
                new_instr_list.extend(new_instr)
            else:
                new_instr_list.append(new_instr)

        self.instrs = new_instr_list


    def __expand_block(self, instr_list):

        # if block is of class Block
        if isinstance(instr_list, Block):
            statlist = instr_list.body.children
        # if block is a StatList
        elif isinstance(instr_list, StatList):
            statlist = instr_list.children
        elif isinstance(instr_list, list):
            statlist = instr_list
        else:
            # if it is just one node try to put it in a list
            if isinstance(instr_list, Expr):
                statlist = [instr_list]
            else:
                print(">>>>>>>>>> Unexpected instr_list | Type : " + str(type(instr_list)))
                statlist = []

        # Now statlist is a list of instructions

        for index, inst in enumerate(statlist):
            if isinstance(inst, IfStat):
                self.instrs.append(inst.cond)
                
                # the remaining instructions
                bb = BasicBlock(statlist[index + 1:], parents = None, next=self.children["next"])
                
                self.children["then"] = BasicBlock(inst.thenpart, self, bb)
                self.children["else"] = BasicBlock(inst.elsepart, self, bb)
                bb.add_parent(self.children["then"])
                bb.add_parent(self.children["else"])

                # remove the "next" entry
                self.children["next"] = None
                #self.children["then"].children["next"] = bb
                #self.children["else"].children["next"] = bb
                break
            elif isinstance(inst, WhileStat):

                # the while condition
                cond =  BasicBlock(inst.cond,  parents=self)
                
                # the remaining instructions
                rest = BasicBlock(statlist[index + 1:], parents=cond, next=self.children["next"])
                
                self.children["next"] = cond

                # the body
                
                body = BasicBlock(inst.body, cond, next=cond)

                cond.children["true"] = body

                cond.children["false"] = rest
                break
            elif isinstance(inst, CallStat):
                rest = BasicBlock(statlist[index + 1:], parents=None ,next=self.children["next"])
                if len(self.instrs) == 0:
                    # if no other instructions in the BB
                    # then do not create another BB 
                    self.instrs.append(inst.call)
                    self.children["next"] = rest
                    rest.add_parent(self)
                else:
                    # otherwise create a new one
                    call =  BasicBlock(inst.call,  parents=self, next=self.children["next"])
                    self.children["next"] = call
                    call.children["next"] = rest
                    rest.add_parent(call)
                break
            elif isinstance(inst, ForStat):
                pass
            else:
                self.instrs.append(inst)

    def graphviz(self, G):
        
        has_successor = False

        if self.visited is True:
            return

        G.node(str(id(self)), self.__instr_dot_format(), {"shape":"record"}) 
        self.visited = True

        for label, node in self.children.iteritems():
            if node is None:
                continue
            node.graphviz(G)
            G.edge(str(id(self)), str(id(node)), label=label)
            has_successor = True
        # if no successor go to end
        if not has_successor:
            # add the END node
            G.edge(str(id(self)), str(0))



    def __instr_dot_format(self):
        res = "{"
        for inst in self.instrs:
            res += inst.instr_dot_repr() + "|"

        res = res[:-1] + "}"
        return res

class CFG(list):
    '''Control Flow Graph representation'''

    def __init__(self, root):
        # root of the CFG graph
        self.cfgs = dict()

        # dictionary of list of 
        # all the BB in the CFG
        self.BB_list = dict()

        # build CFG recursively
        self.__build_CFG(root.local_symtab.fsym, root)

        # which other functions a function calls
        self.function_calls = dict()

        # Which functions' $sp each function
        # must save 
        self.function_dependency = dict()

        # Which variables from other
        # functions each function uses
        self.used_var = dict()

    def __build_CFG(self, fsym, block):
        self.__build_CFG_function(fsym, block)

        # look for other functions to inspect
        for c in block.defs.children:
            self.__build_CFG(c.symbol, c.body)


    def __build_CFG_function(self, fsym, block):
        
        # build the CFG of a function in the program
        print(">>>>> CFG of " + fsym.name)
        self.cfgs[fsym] = BasicBlock(block)
        self.BB_list[fsym] = self.cfgs[fsym].get_all_blocks()
        self.cfgs[fsym]._graphviz_unvisit()
        print(len(self.BB_list[fsym]))



    def get_function_calls(self):

        # rename it for more readable code
        fun_calls = self.function_calls

        for fsym in self.cfgs.keys():
            fun_calls[fsym] = set()

            for BB in self.BB_list[fsym]:
                fun_calls[fsym].update(BB._get_function_calls())

        for f, v in fun_calls.items():
            print(f.name  + "calls ")
            for j in v:
                print("\t" + j.name)


        return fun_calls

    def graphviz(self):

        for fsym, cfg in self.cfgs.iteritems():
            G = Digraph(fsym.name + "CFG" + str(id(fsym)))

            G.node(str(id(fsym)), fsym.name, {"shape":"house","style":"filled","color":"orange"})
            G.node(str(0),"End "  + fsym.name, {"shape":"house","style":"filled","color":"red"})
            G.edge(str(id(fsym)), str(id(cfg)))

            cfg._graphviz_unvisit()
            cfg.graphviz(G)
            G.view()

    def SSA(self):
        """ Put the CFG int SSA form """
        for fsym, cfg in self.cfgs.iteritems():
            print("SSA in " + fsym.name)
            cfg.to_SSA()
 

    def get_function_dependency(self):
        """ Obtain whose base pointer I need to keep track of """
        fun_dep = self.function_dependency
        used_var = self.used_var

        for fsym in self.cfgs.keys():
            fun_dep[fsym] = set()
            used_var[fsym] = set()
            for BB in self.BB_list[fsym]:
                fun_dep[fsym].update(BB._get_function_dependency())
            
            fun_dep[fsym].discard(fsym)
            
            used_var[fsym].update(self.BB_list[fsym][0]._get_used_vars())


        for f, v in fun_dep.items():
            print(f.name  + " uses ")
            for j in v:
                print("\t" + str(j))

        return fun_dep

    def liveness_graphs(self, show=False):

        self.liveness_graphs = dict()

        for fsym in self.cfgs.keys():
            print(">>> Computing liveness grpah of " + fsym.name) 
            self.cfgs[fsym]._graphviz_unvisit()
            self.liveness_graphs[fsym] = LivenessGraph(self.cfgs[fsym])


        if show:
            for fsym in self.cfgs.keys(): 
                self.liveness_graphs[fsym].graphviz()
            