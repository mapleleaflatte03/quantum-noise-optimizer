MAIN = main
LATEX = pdflatex
BIBTEX = bibtex

.PHONY: pdf clean arxiv

pdf: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex refs.bib sections/*.tex
	$(LATEX) $(MAIN)
	$(BIBTEX) $(MAIN)
	$(LATEX) $(MAIN)
	$(LATEX) $(MAIN)

clean:
	rm -f *.aux *.bbl *.blg *.log *.out *.toc *.fls *.fdb_latexmk *.synctex.gz *.nav *.snm *.vrb

arxiv: clean pdf
	tar -czf arxiv_submission.tar.gz $(MAIN).tex $(MAIN).bbl sections/ refs.bib Makefile
