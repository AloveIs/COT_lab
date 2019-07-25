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
	j global_139976577755344
	# exiting the program
	li	$v0, 10
	syscall



#####################################
######    square
#####################################
square_139976577757072 : 
#************************************

square_139976577893008 :
# x := 35
	ori $8, $0, 35
# storing x
	lw $4, -0($fp)
	sw $8, -0($4)
	jr	$ra

#####################################
######    global
#####################################
global_139976577755344 : 
#************************************

global_139976577756816 :
# loading x
	lw $8, -0($fp)
# input x
	addi $v0 , $0 , 5
	syscall
	move $8, $v0
# squ := 9
	ori $8, $0, 9
# storing squ
	sw $8, -4($fp)
global_139976577842896 :
# temp_0_global := ( x leq 25 )
	
	ori $7, $0,25
	addi $4 $7, 1
	slt $9, $8, $4
# storing x
	sw $8, -0($fp)
# BNEQZ temp_0_global
	bnez $9, global_139976577892560
	j global_139976577843152
global_139976577843152 :

	jr	$ra
global_139976577892560 :
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
	jal square_139976577757072# Restore environment

#restore and shrink stack
	move $sp, $fp
	lw $ra, 4($sp)
	lw $fp,  8($sp)
	addi $sp, $sp, 8

# loading x
	lw $8, -0($fp)
global_139976577892688 :
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
	
	j	global_139976577842896
