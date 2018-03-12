?- use_module(library(clpfd)).
:- consult(util).
:- consult(room).

%% ALLOCATION =========================================

gender_ok([Person, [Floor, _]]) :-
	gender(Person, male), male_floor(Floor);
	gender(Person, female), female_floor(Floor).

seniority_ok([Person, [Floor, _]]) :-
	senior(Person), senior_floor(Floor).

room_pref_ok(_).

alloc(X) :-
	gender_ok(X),
	seniority_ok(X),
	room_pref_ok(X).

match_all(Persons, Units) :-
	unzip(Persons, Units, Allocs),
	maplist(alloc, Allocs),
	all_distinct_units(Units).

%% ====================================================

person(X) :- table(X, _, _, _).
gender(X, Y) :- table(X, Y, _, _).
senior(X) :- table(X, _, senior, _).

solve :-
	csv_read_file('simple.csv', Rows, [functor(table), arity(4)]),
	maplist(assert, Rows),
	findall(X, person(X), Persons),
	match_all(Persons, Units),
	unzip(Rows, Units, RowUnits),
	findall(row(A, B, C, D, X, Y), member([table(A, B, C, D), [X, Y]], RowUnits), Output),
	csv_write_file('output.csv', Output).


