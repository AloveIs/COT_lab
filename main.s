.text
.ent	main

 main:
	
# save $ra $fp  on stack
	addi $sp, $sp, -8
	sw   $fp, 8($sp)
	sw   $ra, 4($sp)
# fill in function stack
	move $fp, $sp
	addi $sp,$sp, -8
	j global_140578378816016
	# exiting the program
	li	$v0, 10
	syscall



#####################################
######    global
#####################################
global_140578378816016 : 
#************************************

global_140578378817488 :
# loading x
	lw $8, -0($fp)
# input x
	addi $v0 , $0 , 5
	syscall
	move $8, $v0
global_140578378887056 :
# temp_0_global := ( x leq 10 )
	
	ori $7, $0,10
	addi $4 $7, 1
	slt $8, $8, $4
# BNEQZ temp_0_global
	bnez $8, global_140578378937680
	j global_140578378936464
global_140578378936464 :
# print x
	ori $2, $0, 1
	or $4, $0, $8
	syscall
# print a newline
	addi $a0, $0, 0xA
	addi $v0, $0, 0xB
	syscall
global_140578378936848 :
# temp_1_global := ( x leq 25 )
	
	ori $7, $0,25
	addi $4 $7, 1
	slt $8, $8, $4
# storing x
	sw $8, -0($fp)
# BNEQZ temp_1_global
	bnez $8, global_140578378937296
	j global_140578378937104
global_140578378937104 :

	jr	$ra
global_140578378937296 :
# storing x
	sw $8, -0($fp)
# preamble, save variables and push $ra, $fp, and the other's functions's $sp

# save $ra $fp  on stack
	addi $sp, $sp, -8
	sw   $fp, 8($sp)
	sw   $ra, 4($sp)
# fill in function stack
	sw $fp, -0($sp)
	move $fp, $sp
	addi $sp,$sp, -12
# call the function
	jal square_140578378883344# Restore environment

#restore and shrink stack
	move $sp, $fp
	lw $ra, 4($sp)
	lw $fp,  8($sp)
	addi $sp, $sp, 8

# loading x
	lw $8, -0($fp)
global_140578378937424 :
# print x
	ori $2, $0, 1
	or $4, $0, $8
	syscall
# print a newline
	addi $a0, $0, 0xA
	addi $v0, $0, 0xB
	syscall
# x := ( x plus 1 )
	addi $8, $8, 1
	ori $7, $0,1
	
	j	global_140578378936848
global_140578378937680 :
# print x
	ori $2, $0, 1
	or $4, $0, $8
	syscall
# print a newline
	addi $a0, $0, 0xA
	addi $v0, $0, 0xB
	syscall
# x := ( x plus 1 )
	addi $8, $8, 1
	ori $7, $0,1
	
	j	global_140578378887056

#####################################
######    square
#####################################
square_140578378883344 : 
#************************************

square_140578378937936 :
# loading x
	lw $4, -0($fp)
	lw $8, -0($4)
# x := ( x times 2 )
	ori $4, $0, 2
	mul $8, $8, $4
	ori $7, $0,2
	
# storing x
	lw $4, -0($fp)
	sw $8, -0($4)
# print x
	ori $2, $0, 1
	or $4, $0, $8
	syscall
# print a newline
	addi $a0, $0, 0xA
	addi $v0, $0, 0xB
	syscall
	jr	$ra
