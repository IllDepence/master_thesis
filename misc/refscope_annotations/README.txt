This directory contains data corresponding to following publication:

Amjad Abu-Jbara and Dragomir Radev. 2012. Reference Scope Identification in Citing Sentences. The North American Chapter of the Association of Computational Linguistics (NAACL 2012)

There is only one file called refscope.ann.txt. For each sentence in this file, the citation anchors have been replaced by placeholder tokens to make syntactic parsing easier. Here is the list of tokens and what they mean:

REF: A reference anchor, e.g. Widdow 2013.
TREF: Reference anchor for the target paper for which the reference scope has been annotated.
GREF: A group of reference anchors, e.g. (Widdow 2013; Mark et al. 2010).
GTREF: A group of reference anchors which also contains the anchor for the target reference for which the reference scope has been annotated.

A citing sentence can have either one TREF or one GTREF and can have any number of REF and GREF tokens. 

The reference scope for the target reference is enclosed in HTML style <scope> tags. 

For any questions, please contact:

Amjad Abu Jbara (amjad13@gmail.com)
Rahul Jha (rahulkumar.jha@gmail.com)
Dragomir Radev (radev@umich.edu)



