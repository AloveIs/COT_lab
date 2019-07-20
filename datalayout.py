from texttable import Texttable


def data_layout(symtab, call_graph):

	datalayout = dict()

	# do layout function-wise
	for function, f_symtab in symtab.symtab_dict.items():
		datalayout_f(function, f_symtab, call_graph)


def rowify(sym, idx):
	return [sym.name, str(sym.stype), str(hex(idx*4))]



def print_data_layout(stack):

    table = Texttable()
    table.add_row(['Symbol', 'Type', 'Offset'])

    for idx, sym in enumerate(stack):
        table.add_row(rowify(sym, idx))
    print table.draw()




def datalayout_f(function, f_symtab, call_graph):

	# first put the others function's stacks pointer
	used_functions = call_graph.function_uses[function]

	stack = []

	for uses in used_functions:
		stack.append(uses)

	# then reserve space for local variables
	
	for sym in f_symtab:
		if sym.level == function and \
			sym.value is None and \
			not sym.temp:
			stack.append(sym)

	# print the result 
	print("> Stack of " + function.name)
	print_data_layout(stack)