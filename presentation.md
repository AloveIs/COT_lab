---
title: COT Lab Presentation
author: Pietro Alovisi (pietro.alovisi@mail.polimi.it)
date: 26-07-2019
theme: Madrid
colortheme: dolphin
fontfamily: noto-sans
header-includes:
- \usepackage{cmbright}
fontsize: 10pt
---


[//]: # (% ---
% titlepage-note: Lab presentation.
% institute: Polimi
% fontsize: 17pt
% ...)

# Content of the Lab

## Content: Objective

The objective is to build a fully functioning compilation pipeline.


![Goal pipeline of the project.](images/pipeline.pdf)

## Content: Results

 - Functioning pipeline
 - Correct input programs are limited by bugs
 - Limitations also due to register allocation

# Design Decision

## Design Decisions

 - More focused on visualization than performance
 - MIPS oriented
 - More oriented to 3 address operation IR
 - Function-wise analaysis
 - No SSA

# Limitations

## Limitations

The limiting factor of this comiler are:

 - No spilling
 - The backend is not too modular
 - No major optimization techniques performed

# Steps

## Compiler Pipeline

The steps that the compiler performs are:

 - Syntax analysis
 - Constant propagation
 - CFG
 - IR into 3-address-form
 - Call Graph
 - Liveness
 - Register Allocation
 - Code Generation

## Constant Propagation and Folding


Perform constant folding and propagation on the IR Tree.


## CFG


## Call Graph


## Liveness Analysis


## Liveness: Load and Stores


## 3-Address-Form

```FORTRAN
PROCEDURE marco;
		VAR abc, ab, bc;
		BEGIN
		   abc := ab * bc * x
		END;
```

## 3-Address-Form

![Before.](images/before3way.pdf)

## 3-Address-Form

![After.](images/after3way.pdf)


## Data Layout

![](images/stack.pdf)


## Register Allocation


MIPS registers:

```python
# $8 - $15      $t0 - $t7   Temporary data, 
# $16 - $23     $s0 - $s7   Saved registers,
# $24 - $25     $t8 - $t9   More temporary registers

# $26 - $27     $k0 - $k1   Reserved for kernel.
# $28           $gp         Global Area Pointer 
# $29           $sp         Stack Pointer
# $30           $fp         Frame Pointer
# $31           $ra         Return Address
# $f0 - $f3     -           Floating point return values
# $f4 - $f10    -           Temporary registers
# $f12 - $f14   -           First two arguments
# $f16 - $f18   -           More temporary registers
# $f20 - $f31   -           Saved registers
```

## Register Allocation

The registers from \$8 to \$25 are assignable to variables.

A simple algorithm is used without implementig spilling:

```python
for v in variables:
	for r in registers:
		if not v.interfere(r):
			v.assign(r)
			break
```




## Code Generation

Code generation starts from the CFG.

Each instruction mapped into one or more MIPS instructions.

One labels for each BB.

No optimization on the final assembly code.

## Code Generation


```MIPS
#####################################
######    marco
#####################################
marco_139736320808784 : 
#************************************

marco_139736320881104 :
# temp_0_marco := ( ab times bc )
	mul $8, $8, $10
# abc := ( temp_0_marco times x )
	mul $8, $8, $9
	jr	$ra
```

## Code Generation: Function calls

Callee saves the \$ra, \$fp and pushed the \$fp of the others functions. Also reserves space for local variables.

![](images/callstack.pdf)


# Take Home Concepts

## Take Home Concepts

I understood why compilers are:
 
 - Big 
 - Complex
 - a challenge for software enginnering



# End

