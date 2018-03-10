?- use_module(library(clpfd)).
:- consult(util).
:- consult(room).

%% PEOPLE ==============================================

%% person(X) :- member(X, [varun, suyash, yunjie, imran, tham]).

male(varun).
male(suyash).
male(imran).
male(tham).

female(yunjie).
female(joey).
female(roslinda).
female(salina).

%% ALLOCATION =========================================

alloc([Person, [Floor, _]]) :-
	male(Person), male_floor(Floor);
	female(Person), female_floor(Floor).

match_all(Persons, Units) :-
	unzip(Persons, Units, Allocs),
	maplist(alloc, Allocs),
	all_distinct_units(Units).

%% ====================================================

%% ?- match_all([varun, yunjie, imran, salina], Y).




