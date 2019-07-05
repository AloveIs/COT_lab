#!/bin/bash

python2 frontend.py test.pl0;
dot -Tpdf cfg.dot -o cfg.pdf;
dot -Tpdf call_graph.dot -o call_graph.pdf;