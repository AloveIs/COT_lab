#!/usr/bin/python

__doc__ = '''Control Flow Graph implementation
Includes cfg construction and liveness analysis.'''

from support import get_node_list, get_symbol_tables
from ir import *
from graphviz import Digraph

class LivenessNode:

    def __init__(self,statement, BB):

        self.BB = BB
        self.children = []

        self.statement = statement

        self.defs = statement.get_defs()
        self.uses = statement.get_uses()
        self.visited = False

        self.live_in = set()
        self.live_out = set()


    def add_follower(self, node):
        self.children.append(node)

    def unvisit(self):
        self.visited = False

    def dot_format(self):
        return self.statement.instr_dot_repr()

    def __add_load(self, variables, end=False):

        if len(variables) == 0:
            return

        idx = self.BB.instrs.index(self.statement)

        stat = LoadStat(variables,symtab=self.statement.symtab)

        if end:
            self.BB.instrs.insert(idx + 1, stat)
        else:
            self.BB.instrs.insert(idx, stat)


    def __add_store(self, variables):

        if len(variables) == 0:
            return

        before = set()
        after = set()
        for var in variables:
            if var in self.defs:
                after.add(var)
            else:
                before.add(var)

        if len(before) > 0:
            idx = self.BB.instrs.index(self.statement)
            stat = StoreStat(before,symtab=self.statement.symtab)
            self.BB.instrs.insert(idx, stat)
        if len(after) > 0:
            idx = self.BB.instrs.index(self.statement)
            stat = StoreStat(after,symtab=self.statement.symtab)
            self.BB.instrs.insert(idx + 1, stat)


    def add_loads(self, root=False):
        if root:
            self.__add_load(self.live_in)

        for c in self.children:
            vars_to_load = set()
            # find newborn variables, not defined
            vars_to_load |= (c.live_in - self.live_in) - self.defs
            c.__add_load(vars_to_load)

        if isinstance(self.statement, CallStat) or isinstance(self.statement, CallExpr):
            vars_to_load = set() 
            vars_to_load |= self.live_in
            self.__add_load(vars_to_load, end=True)




    def add_stores(self):

        vars_to_store = set()

        for c in self.children:
            # find dead variables
            vars_to_store |= (self.live_in - c.live_in)
            if self.defs.issubset(c.live_in):
                continue
            else:
                vars_to_store |= self.defs


        if isinstance(self.statement, CallStat) or isinstance(self.statement, CallExpr):
            vars_to_store |= self.live_in

        if len(self.children) == 0:
            vars_to_store |= self.live_in | self.defs 


        self.__add_store(vars_to_store)


    def live_fixed_point(self):

        has_changed = False

        # live_out equations
        live_out = set()

        for c in self.children:
            live_out.update(c.live_in)


        has_changed |= (not live_out.issubset(self.live_out))

        self.live_out |= live_out


        # live_in equations
        live_in = self.uses | (self.live_out - self.defs)

        has_changed |= (not live_in.issubset(self.live_in))

        self.live_in |= live_in

        return has_changed


class LivenessGraph:

    def __init__(self,root_BB, fsym):

        self.fsym = fsym

        self.node_list = []

        # create the graph
        self.create(root_BB)

        self.__liveness_fixed_point()

        self.__add_loads()
        self.__add_stores()



    def __add_loads(self):
        for idx, node in enumerate(self.node_list):
            
            if idx == 0:
                # has no predecessors
                node.add_loads(root=True)

            node.add_loads()
    def __add_stores(self):
        for node in self.node_list:
            node.add_stores()


    def create(self, BB):

        BB.visited = True

        root = LivenessNode(BB.instrs[0], BB)
        self.node_list.append(root)
        current_node = root
        prev = None
        for i in range(1, len(BB.instrs)):
            prev = current_node
            current_node = LivenessNode(BB.instrs[i], BB)
            self.node_list.append(current_node)
            prev.add_follower(current_node)

        # the last one must be added to the begining of the other BB
        for child in BB.children.values():
            if child is None:
                continue
            current_node.add_follower(self._create_recursion(child))

        self.root = root


    def __liveness_fixed_point(self):
        changed = True

        while changed:
            
            changed = False

            for node in self.node_list:
                changed |= node.live_fixed_point()

        print("Finished liveness")

    def _create_recursion(self, BB):

        if BB.visited:
            return self.find_node(BB.instrs[0])
        else:
            # mark the BB as visited
            BB.visited = True

        root = LivenessNode(BB.instrs[0], BB)
        self.node_list.append(root)
        current_node = root
        prev = None
        for i in range(1, len(BB.instrs)):
            prev = current_node
            current_node = LivenessNode(BB.instrs[i], BB)
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

        G.node(str(id(self.fsym)), self.fsym.name, {"shape":"house","style":"filled","color":"orange"})
        G.node(str(0),"End "  + self.fsym.name, {"shape":"house","style":"filled","color":"red"})
        G.edge(str(id(self.fsym)), str(id(self.node_list[0])))


        for node in self.node_list:
            G.node(str(id(node)), node.dot_format(), {"shape":"record"}) 

            if len(node.children) == 0:
                G.edge(str(id(node)), str(0))

            for c in node.children:
                label = "{"
                for sym in c.live_in:
                    label += sym.name + ","

                if len(label) > 1:
                    label = label[:-1] + "}"
                else:
                    label ="{ }"
                G.edge(str(id(node)), str(id(c)), label=label)

        G.view()


class BasicBlock(object):
    def __init__(self, block,fsym, parents=None, next=None):
        '''Structure:
		Zero, one (next) or two (next, target_bb) successors
		Keeps information on labels
		'''
        self.fsym = fsym
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

        self.lbl_begin = self.fsym.name + "_" + str(id(self))
        self.lbl_end = self.fsym.name + "_" + str(id(self)) + "_end"


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

    def to_three_addr_form(self):
        # new instructions in the list
        new_instr_list = []

        for inst in self.instrs:
            # new form of the instruction
            new_instr = inst.to_three_addr_form()

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

                symtab = inst.symtab
                new_temp = symtab.get_temp_variable()

                cond_eval = AssignStat(target=new_temp.symbol, expr=inst.cond, symtab=symtab)
                branch = BranchStat(new_temp.symbol, symtab=symtab) 
                self.instrs.append(cond_eval)
                self.instrs.append(branch)

                # the remaining instructions
                if len(statlist[index + 1:]) == 0:
                    bb = BasicBlock([NopStat()],self.fsym, parents=None, next=self.children["next"])
                else:
                    bb = BasicBlock(statlist[index + 1:],self.fsym, parents = None, next=self.children["next"])

                #bb = BasicBlock(statlist[index + 1:],self.fsym, parents = None, next=self.children["next"])
                
                self.children["then"] = BasicBlock(inst.thenpart,self.fsym, parents=self, next=bb)
                branch.set_on_true(self.children["then"])
                self.children["else"] = BasicBlock(inst.elsepart,self.fsym, parents=self, next=bb)
                branch.set_on_false(self.children["else"])
                bb.add_parent(self.children["then"])
                bb.add_parent(self.children["else"])

                # remove the "next" entry
                self.children["next"] = None
                #self.children["then"].children["next"] = bb
                #self.children["else"].children["next"] = bb
                break
            elif isinstance(inst, WhileStat):

                # the while condition
                symtab = inst.symtab
                new_temp = symtab.get_temp_variable()

                cond_eval = AssignStat(target=new_temp.symbol, expr=inst.cond, symtab=symtab)
                branch = BranchStat(new_temp.symbol, symtab=symtab) 


                cond =  BasicBlock([cond_eval, branch],self.fsym,  parents=self)
                
                # the remaining instructions
                if len(statlist[index + 1:]) == 0:
                    rest = BasicBlock([NopStat()],self.fsym, parents=cond, next=self.children["next"])
                else:
                    rest = BasicBlock(statlist[index + 1:],self.fsym, parents=cond, next=self.children["next"])
                
                self.children["next"] = cond

                # the body
                
                body = BasicBlock(inst.body,self.fsym, parents=cond, next=cond)

                cond.children["true"] = body
                branch.set_on_true(cond.children["true"])

                cond.children["false"] = rest
                branch.set_on_false(cond.children["false"])
                break
            elif isinstance(inst, CallStat):
                rest = BasicBlock(statlist[index + 1:],self.fsym, parents=None ,next=self.children["next"])
                if len(self.instrs) == 0:
                    # if no other instructions in the BB
                    # then do not create another BB 
                    self.instrs.append(inst.call)
                    self.children["next"] = rest
                    rest.add_parent(self)
                else:
                    # otherwise create a new one
                    call =  BasicBlock(inst.call,self.fsym,  parents=self, next=self.children["next"])
                    self.children["next"] = call
                    call.children["next"] = rest
                    rest.add_parent(call)
                break
            elif isinstance(inst, ForStat):
                pass
            else:
                self.instrs.append(inst)

        # if the BB is empty
        if len(self.instrs) == 0:
            self.instrs.append(NopStat)


    def generate_code(self, fsym):
        self.visited = True

        bb_code = ""

        bb_code += self.lbl_begin +  " :\n"


        for inst in self.instrs:
            bb_code += inst.generate_code(fsym)

        if len(self.children.keys()) >= 1:
            for child in self.children.values():
                if child is not None:
                    if child.visited:
                        bb_code += "\t" + "j\t" + self.children.values()[0].lbl_begin + "\n" 
                    else:
                        bb_code += child.generate_code(fsym)
        
        if len(self.children.keys()) == 1 and self.children.values()[0] is None: 
            # add return
            bb_code += "\tjr\t$ra\n"

        if len(self.children.keys()) == 0:
            # add return
            bb_code += "\tjr\t$ra\n"

        return bb_code


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

        self.entry_function = root.local_symtab.fsym
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
        self.cfgs[fsym] = BasicBlock(block, fsym)
        self.BB_list[fsym] = self.cfgs[fsym].get_all_blocks()
        self.cfgs[fsym]._graphviz_unvisit()



    def get_function_calls(self):

        # rename it for more readable code
        fun_calls = self.function_calls

        for fsym in self.cfgs.keys():
            fun_calls[fsym] = set()

            for BB in self.BB_list[fsym]:
                fun_calls[fsym].update(BB._get_function_calls())

        for f, v in self.function_calls.items():
            print(f.name  + " calls ")
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

    def three_addr_form(self):
        """ Put the CFG int three_addr_form form """
        for fsym, cfg in self.cfgs.iteritems():
            print("three_addr_form in " + fsym.name)
            cfg.to_three_addr_form()
 

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
            print(">>> Computing liveness graph of " + fsym.name) 
            self.cfgs[fsym]._graphviz_unvisit()
            self.liveness_graphs[fsym] = LivenessGraph(self.cfgs[fsym], fsym)


        if show:
            for fsym in self.cfgs.keys(): 
                self.liveness_graphs[fsym].graphviz()
        
        return self.liveness_graphs

    def code_generation(self, filename):

        file = open(filename,"w")

        called_fn = self.entry_function

        prelude =".text\n.ent\tmain\n\n main:\n\t" # ori $sp, $0, 0xfffc # Init stack\n\t j\t" \
        
        prelude += """
# save $ra $fp  on stack
\taddi $sp, $sp, -8
\tsw   $fp, 8($sp)
\tsw   $ra, 4($sp)
# fill in function stack
"""

        prelude += "\t" + "move $fp, $sp" + "\n"
        prelude += "\taddi $sp,$sp, -" + str(4*len(called_fn.stack)) + "\n"

        prelude += "\tj " + self.entry_function.name + "_" + str(id(self.entry_function)) \
                        + "\n\t# exiting the program\n\tli\t$v0, 10\n\tsyscall\n\n\n"


        body = ""

        for fsym in self.cfgs.keys():
            self.cfgs[fsym]._graphviz_unvisit()
            print(">>> Generatin code of " + fsym.name)

            # add the label for the function
            body += "\n#####################################\n######    " + fsym.name + \
                "\n#####################################\n" + fsym.name + "_" + str(id(fsym))  + " : \n" \
                    + "#************************************\n\n"

            body += self.cfgs[fsym].generate_code(fsym)
            # create code from cfg



        file.write(prelude + body)
        file.close()