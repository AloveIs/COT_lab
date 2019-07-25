
all: slides.pdf

slides.pdf : presentation.md
	pandoc presentation.md -t beamer --slide-level 2  -o slides.pdf
		