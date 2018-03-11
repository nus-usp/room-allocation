?- use_module(library(clpfd)).
:- consult(util).
:- consult(room).

%% ALLOCATION =========================================

alloc([Person, [Floor, _]]) :-
	gender(Person, male), male_floor(Floor);
	gender(Person, female), female_floor(Floor).

match_all(Persons, Units) :-
	unzip(Persons, Units, Allocs),
	maplist(alloc, Allocs),
	all_distinct_units(Units).

%% ====================================================

person(X) :- table(X, _).
gender(X, Y) :- table(X, Y).

solve :-
	csv_read_file('simple.csv', Rows, [functor(table), arity(2)]),
	maplist(assert, Rows),
	findall(X, person(X), Persons),
	match_all(Persons, Units),
	unzip(Rows, Units, RowUnits),
	findall(row(X, Y, F, P), member([table(X, Y), [F, P]], RowUnits), Output),
	csv_write_file('output.csv', Output).


