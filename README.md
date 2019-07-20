## Introduction

This is a compiler for the PL\0  language.

### The EBNF grammar

```c
program = block "." .

block = [ "const" ident "=" number {"," ident "=" number}* ";"]
        [ "var" ident {"," ident} ";"]
        { "procedure" ident ";" block ";" }* statement .

statement = [ ident ":=" expression 
			| "call" ident
            | "?" ident | "!" expression
            | "begin" statement {";" statement }* "end"
            | "if" condition "then" statement ["else" statement]
            | "while" condition "do" statement ].

condition = "odd" expression |
            expression ("="|"#"|"<"|"<="|">"|">=") expression .

expression = [ "+"|"-"] term { ("+"|"-") term}*.

term = factor {("*"|"/") factor}*.

factor = ident | number | "(" expression ")".
```

## Tools

## Useful information





### Sites where to plot .dot file

- [webraphviz](http://www.webgraphviz.com/)
- [GraphvizOnline](https://dreampuf.github.io/GraphvizOnline/)


# Problems to fix

 - In the construction of the CFG if we have 2 omonymous functions one will overwrite the CFG of the other one (only the graph because of the name)
 - Test the for loop
 - Functions can call only other functions that have been previously defined 
 - call cannot be the first instruciton in a BB