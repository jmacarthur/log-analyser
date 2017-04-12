tall: test

android-log-example: | android-log-example.bz2
	bunzip2 -k android-log-example.bz2

test: analyser.py android-log-example
	python analyser.py android-log-example
