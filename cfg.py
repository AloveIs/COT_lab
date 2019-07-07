#!/usr/bin/python

__doc__ = '''Control Flow Graph implementation
Includes cfg construction and liveness analysis.'''

from support import get_node_list, get_symbol_tables
from ir import *
from graphviz import Digraph


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
                    # then do not create one only for the 
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
        self.__build_CFG("global", root)


    def __build_CFG(self, fname, block):
        self.__build_CFG_function(fname, block)

        # look for other functions to inspect
        for c in block.defs.children:
            self.__build_CFG(c.symbol.name, c.body)


    def __build_CFG_function(self, fname, block):
        
        # build the CFG of a function in the program
        print(">>>>> CFG of " + fname)
        self.cfgs[fname] = BasicBlock(block)
        self.BB_list[fname]


    def graphviz(self):

        for fname, cfg in self.cfgs.iteritems():
            G = Digraph(fname + "CFG")

            G.node(str(id(fname)), fname, {"shape":"house","style":"filled","color":"orange"})
            G.node(str(0),"End "  + fname, {"shape":"house","style":"filled","color":"red"})
            G.edge(str(id(fname)), str(id(cfg)))

            cfg._graphviz_unvisit()
            cfg.graphviz(G)
            G.view()

    def SSA(self):

        for fname, cfg in self.cfgs.iteritems():
            print("SSA in " + fname)
            cfg.to_SSA()