#!/usr/bin/python

# documentation of the file
__doc__='''Simple lexer for PL/0 using generators'''

# PL/0 is a very simple procedural language
# it has some pascal-like feature


# Tokens can have multiple definitions if needed
symbols =  {
	'lparen' : ['('],
	'rparen' : [')'],
	'times'  : ['*'],
	'slash'  : ['/'],
	'plus'   : ['+'],
	'minus'  : ['-'],
	'eql'    : ['='],
	'neq'    : ['!='],
	'lss'    : ['<'],
	'leq'    : ['<='],
	'gtr'    : ['>'],
	'geq'    : ['>='],
	'mod'	 : ['%'],
	'callsym': ['call'],
	'beginsym'  : ['begin', '{'],
	'semicolon' : [';'],
	'endsym'    : ['end', '}'],
	'ifsym'     : ['if'],
	'elsesym'	: ['else'],
	'whilesym'  : ['while'],
	'becomes'   : [':='],
	'thensym'   : ['then'],
	'dosym'     : ['do'],
	'constsym'  : ['const'],
	'comma'     : [','],
	'varsym'    : ['var'],
	'procsym'   : ['procedure'],
	'period'    : ['.'],
	'oddsym'    : ['odd'],
	'print'		: ['!', 'print'],
	'input'		: ['?', 'input'],
}

def token(word):
	'''Return corresponding token for a given word'''
	for s in symbols : 
		if word in symbols[s] :
			return s
	try : # If a terminal is not one of the standard tokens but can be converted to float, then it is a number,
		# otherwise, an identifier
		float(word)
		# we are not going to care about the value
		return 'number'
	except ValueError, e :
		return 'ident'

def lexer(text):
	"""Generator implementation of a lexer"""

	# Generator: it keeps a state between different invocations
	#   		it recieves the whole program and splits it
	import re
	from string import split, strip, lower, join
	t = re.split('(\W+)', text)  # Split at non alphanumeric sequences
	text = join(t ,' ')  # Join alphanumeric and non-alphanumeric, with spaces
	words = [strip(w) for w in split(lower(text))]  # Split tokens (make it lowercase)
	for word in words:
		yield token(word), word    # we return the token and the value/word


# Test support
__test_program = '''
	VAR x, squ;
	
	PROCEDURE square;
	VAR gian, maria;
	BEGIN
	   x :=  35
	END;
	BEGIN
	   	? x ;	  
	   	squ := 2* 3 + 5  - (12 / 6) ; 	
	   	WHILE x <= 25 DO
	   	BEGIN
	   	call square;
		! x ;
	   	x := x + 1
	   	END
	END.
	'''
__test_program1 = '''
	CONST ciao = 2 , miao = 3 ;
	VAR x, squ;
	
	PROCEDURE square;
	VAR gian, maria, carlo ;
		PROCEDURE marco;
		VAR luca, abc, ab, bc;
		BEGIN
		   abc := ab * bc * gian
		END;
	BEGIN
	   squ := x * x
	END;

	PROCEDURE cube;
	VAR dani;
	PROCEDURE marco;
		VAR luca, abc, ab, bc;
		BEGIN
		   abc := ab * bc * x
		END;
	BEGIN
	   CALL marco;
	   dani := 2 * 3;
	   dani := 2
	END;
	
	BEGIN
	   x := 1;
	   WHILE x <= 10 DO
	   BEGIN
		  CALL square;
		  CALL cube ;
		  x := x + 1 ;
		  IF x < 2 THEN
			  BEGIN
				  ! x
		      END
		  ELSE
			  BEGIN
				  ! squ
		      END;
		  !squ
	   	END;
	   ! x
	END.
	'''

if __name__ == '__main__' :
	for t,w in lexer(__test_program):
		print t, w
