%% FLOORS ==============================================

floor(X) :- member(X, [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]).

rf_floor(X) :- member(X, [5, 9, 13, 17, 21]).
laundry_floor(X) :- member(X, [9, 17]).

freshmen_floor(X) :- member(X, [6, 8, 11, 14, 16, 17, 20]).
senior_floor(X) :- floor(X), not(freshmen_floor(X)).

male_floor(X) :- member(X, [8, 10, 16, 19]).
female_floor(X) :- member(X, [7, 14, 18, 20]).
mixed_floor(X) :- floor(X), not(male_floor(X)), not(female_floor(X)).


%% ROOMS ==============================================

corridor_room(X) :- member(X, [1010, 1020, 1030, 1040, 1050, 1060, 1090, 1100, 1110, 1120, 1130, 1140, 1150, 1160, 1170, 1180, 1190, 1200]).

suite_room(X) :- member(X, [1001, 1002, 1003, 1004, 1005, 1006, 1071, 1072, 1073, 1074, 1075, 1076, 1081, 1082, 1083, 1084, 1085, 1086]).

aircon_room(X) :- member(X, [1081, 1082, 1083, 1084, 1085, 1086, 1090, 1100, 1110, 1120, 1130, 1140, 1150]).

room(X) :- corridor_room(X); suite_room(X).

non_aircon_room(X) :- room(X), not(aircon_room(X)).

unit([X, Y]) :- floor(X), room(Y).

unit_num([X, Y], U) :- floor(X), room(Y), U #= X * 10000 + Y.

all_distinct_units(Units) :-
	maplist(unit_num, Units, UnitNums),
	all_distinct(UnitNums).