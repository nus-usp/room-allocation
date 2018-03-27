import pandas as pd
from z3 import *
from time import time
from copy import copy
from tqdm import tqdm
from collections import defaultdict

def timeit(method):
    def timed(*args, **kw):
        ts = time()
        result = method(*args, **kw)
        te = time()
        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = (te - ts)
        else:
            print '%r \t\t %.4f s' %                   (method.__name__, (te - ts))
        return result
    return timed



# Define floors
floors = set(range(4, 22))
male_floors = set([8, 10, 16, 19])
female_floors = set([7, 14, 18, 20])
mixed_floors = floors.difference(male_floors).difference(female_floors)
rf_floors = set(range(5, 22, 4))
laundry_floors = set([9, 17])
freshmen_floors = set([6, 8, 11, 14, 16, 17, 20])
senior_floors = floors.difference(freshmen_floors)

# Define room positions
corridor_nonaircon_pos = set(map(str, range(101, 107) + range(115, 120)))
corridor_aircon_pos = set(map(str, range(109, 115)))
suite_room_letters = map(lambda x: chr(ord('A') + x), range(6))
suite_nonaircon_pos = set([str(suite_num) + letter for suite_num in [100, 107] for letter in suite_room_letters])
suite_aircon_pos = set([str(suite_num) + letter for suite_num in [108] for letter in suite_room_letters])
aircon_pos = corridor_aircon_pos.union(suite_aircon_pos)
nonaircon_pos = corridor_nonaircon_pos.union(suite_nonaircon_pos)
corridor_pos = corridor_nonaircon_pos.union(corridor_aircon_pos)
suite_room_pos = suite_nonaircon_pos.union(suite_aircon_pos)
absent_laundry_pos = set(map(str, range(103, 107)))
room_pos = corridor_pos.union(suite_room_pos)

# Rooms and floor query methods
def get_valid_floors(include_male_floors=True, include_female_floors=True, include_mixed_floors=True, include_freshman_floors=True, include_senior_floors=True):
    gender_floors = male_floors if include_male_floors else set()
    gender_floors = gender_floors.union(female_floors) if include_female_floors else gender_floors
    gender_floors = gender_floors.union(mixed_floors) if include_mixed_floors else gender_floors

    seniority_floors = freshmen_floors if include_freshman_floors else set()
    seniority_floors = seniority_floors.union(senior_floors) if include_senior_floors else seniority_floors

    return gender_floors.intersection(seniority_floors)


def get_valid_pos(floor_num, include_suites=True, include_corridors=True, include_aircon=True, include_non_aircon=True):
    positions = set()
    positions = positions.union(suite_room_pos) if include_suites else positions
    positions = positions.union(corridor_pos) if include_corridors else positions
    positions = positions.difference(aircon_pos) if not include_aircon else positions
    positions = positions.difference(nonaircon_pos) if not include_non_aircon else positions

    if floor_num not in floors:
        positions = positions.difference(room_pos)

    if floor_num in rf_floors:
        positions = positions.difference(suite_aircon_pos)

    if floor_num in laundry_floors:
        positions = positions.difference(absent_laundry_pos)

    return positions


# Returns a set of preferred floors for a person
def get_preferred_floors(is_male=True, is_freshmen=False, include_single_gen_floors=True, include_mixed_floors=True):
    include_male_floors = is_male and include_single_gen_floors
    include_female_floors = (not is_male) and include_single_gen_floors
    include_freshman_floors = is_freshmen
    include_senior_floors = not is_freshmen

    return get_valid_floors(include_male_floors, include_female_floors, include_mixed_floors, include_freshman_floors, include_senior_floors)


def get_all_rooms_on_floor(floor_num):
    rooms = []

    if floor_num not in floors:
        return rooms
    elif floor_num in laundry_floors:
        rooms.extend([str(floor_num) + '-' + pos for pos in room_pos.difference(absent_laundry_pos)])
    elif floor_num in rf_floors:
        rooms.extend([str(floor_num) + '-' + pos for pos in room_pos.difference(suite_aircon_pos)])
    else:
        rooms.extend([str(floor_num) + '-' + pos for pos in room_pos])
    return rooms


def get_all_rooms(floors_set=floors):
    rooms = []
    for floor_num in floors_set:
        rooms.extend(get_all_rooms_on_floor(floor_num))
    return rooms

suite_rooms = reduce(lambda x, y: x.union(y), [set(map(lambda x: "{}-{}".format(floor, x), get_valid_pos(floor, True, False, True, True))) for floor in floors])
mixed_floor_suite_rooms = reduce(lambda x, y: x.union(y), [set(map(lambda x: "{}-{}".format(floor, x), get_valid_pos(floor, True, False, True, True))) for floor in mixed_floors])

def get_suite_neighbours(room):
    if room not in mixed_floor_suite_rooms:
        return set()
    else:
        neighbors = []
        for alpha in set(['A', 'B', 'C', 'D', 'E', 'F']):
            if alpha == room[-1]:
                continue
            neighbors.append(room[:-1] + alpha)
        return set(neighbors)



class Person:
    def __init__(self, entry_id, gender, person_type, room_pref1, room_pref2, room_pref3, preference_comment, pref_floor_gender):
        self.entry_id = entry_id
        self.gender = gender
        self.is_male = self.gender == "Male"
        self.person_type = person_type
        self.is_senior = person_type == "USP Senior UG"
        self.room_pref1 = RoomType.make_room_type(room_pref1)
        self.room_pref2 = RoomType.make_room_type(room_pref2)
        self.room_pref3 = RoomType.make_room_type(room_pref3)
        self.preferences = [self.room_pref1, self.room_pref2, self.room_pref3]
        self.preference_comment = preference_comment
        self.pref_floor_gender = pref_floor_gender

    def valid_rooms(self, preference_rank):

        # Basic list: Takes into account only floor gender and seriority floor preference
        if preference_rank == 0:
            return get_all_rooms(self.valid_floors())
        else:
            return self.preferences[preference_rank - 1].valid_rooms(self.valid_floors())

    def all_valid_rooms(self):
        valid_room_sets = [set(self.valid_rooms(x)) for x in range(4)]
        return reduce(lambda x, y: x.union(y), valid_room_sets)


    # Only one set of valid floors for one person
    def valid_floors(self):
        include_single_gen_floors = self.pref_floor_gender == "Single Gender Floor" or self.pref_floor_gender == "No Preference"
        include_mixed_floors = self.pref_floor_gender == "Mixed Gender Floor" or self.pref_floor_gender == "No Preference"
        return get_preferred_floors(self.is_male, not self.is_senior, include_single_gen_floors, include_mixed_floors)


class Room:
    def __init__(self, level, position):
        self.level = level
        self.position = position
        self.label = str(self)
        self.room_type = RoomType(self.is_suite(), self.is_aircon())

    def __init__(self, room_string):
        self.level = room_string.split('-')[0]
        self.position = room_string.split('-')[1]
        self.label = str(self)
        self.room_type = RoomType(self.is_suite(), self.is_aircon())

    @staticmethod
    def make_label_room_tuple(description):
        room = Room(description)
        return (str(room), room)

    def __str__(self):
        return str(self.level) + '-' + str(self.position)

    def is_aircon(self):
        return self.position in aircon_pos

    def is_suite(self):
        return self.position in suite_room_pos

    def get_type(self):
        return self.room_type.get_attributes()

    def get_inverse_type(self):
        return self.room_type.get_inverse_attributes()


class RoomType:
    def __init__(self, is_suite, is_aircon):
        self.is_suite = is_suite
        self.is_aircon = is_aircon

    # Initialises from description Eg. USP, Single (6 bdrm Apt, Non Air-Con)
    @staticmethod
    def make_room_type(description):
        is_suite = '6 bdrm Apt' in description
        is_aircon = 'Non Air-Con' not in description
        return RoomType(is_suite, is_aircon)

    def valid_rooms(self, valid_floors=floors):
        valid_rooms = set()
        for floor in valid_floors:
            for pos in get_valid_pos(floor, self.is_suite, not self.is_suite, self.is_aircon, not self.is_aircon):
                valid_rooms.add(str(floor) + '-' + str(pos))

        return valid_rooms

    def __str__(self):
        return 'Suite: {}, Aircon: {} '.format(self.is_suite, self.is_aircon)

    def __hash__(self):
        return hash(frozenset(self.__dict__.iteritems()))

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.is_suite == other.is_suite and self.is_aircon == other.is_aircon



def view_times(times):
    if len(times) < 1:
        return
    last_t = times[0][1]
    new_times = []
    for t in times:
        new_times.append([t[0], t[1] - last_t])
        last_t = t[1]

    return pd.DataFrame(new_times)


@timeit
def get_solver_package(nrows=None):
    input_data_frame = pd.read_csv('data/usprc.csv', nrows=nrows, dtype=object).fillna('')

    @timeit
    def get_all_people():
           # Populate people
        all_people = []
        male_people = []
        female_people = []

        for row in input_data_frame.values:
            person = Person(*row[:8])
            all_people.append(person)

            if person.is_male:
                male_people.append(person)
            else:
                female_people.append(person)

        return all_people, male_people, female_people

    @timeit
    def get_all_rooms(all_people):
        # Populate rooms into a hashmap Eg. {'16-118': Room-Object}
        all_rooms = reduce(lambda x, y: x.union(y), map(lambda x: x.all_valid_rooms(), all_people))
#         all_rooms = dict(map(Room.make_label_room_tuple, all_room_labels))
        return all_rooms

    @timeit
    def get_assignments(all_people, all_rooms):
        # Populate all room possible assignments
        assignments = {}
        for person in all_people:
            assignments[person] = {}

            for room in all_rooms:
                possibility = Bool("{} gets {}".format(person.entry_id, room))

                # Add possibility to possible assignments
                assignments[person][room] = possibility

        return assignments

    @timeit
    def get_valid_people_for_rooms(all_people, all_rooms):
        # Valid people for each room
        valid_people_for_rooms = {}
        for room in all_rooms:
            valid_people_for_rooms[room] = set()

        for person in all_people:
            possible_assignments = []
            for room in person.all_valid_rooms():

                # Populate valid_people_for_rooms
                valid_people_for_rooms[room].add(person)

        return valid_people_for_rooms

    @timeit
    def get_room_constraints(all_people, all_rooms, assignments, valid_people_for_rooms):
        room_constraints = []
        # One room can only be assigned to one person from the contenders for that room
        for person in tqdm(all_people):
            for room in all_rooms:
                for other_person in valid_people_for_rooms[room]:
                    if other_person == person:
                        continue

                    implication = Implies(assignments[person][room], Not(assignments[other_person][room]))
                    room_constraints.append(implication)

        return room_constraints

    @timeit
    def get_single_gender_suite_constraints(male_people, female_people):
        constraints = []
        for room in tqdm(mixed_floor_suite_rooms):
            for male in male_people:
                for female in female_people:
                    for suite_room in get_suite_neighbours(room):
                        constraints.append(Implies(Bool('{} gets {}'.format(male.entry_id, room)), Not(Bool('{} gets {}'.format(female.entry_id, suite_room)))))

        return And(constraints)

    @timeit
    def get_solver(room_constraints, suite_constraints):
        s = Solver()
        s.add(room_constraints)
        s.add(suite_constraints)
        return s

    all_people, male_people, female_people = get_all_people()
    all_rooms = get_all_rooms(all_people)
    assignments = get_assignments(all_people, all_rooms)
    valid_people_for_rooms = get_valid_people_for_rooms(all_people, all_rooms)
    room_constraints = get_room_constraints(all_people, all_rooms, assignments, valid_people_for_rooms)
    suite_constraints = get_single_gender_suite_constraints(male_people, female_people)
    s = get_solver(room_constraints, suite_constraints)
    all_symbols = [assignments[person][room] for person in all_people for room in person.all_valid_rooms()]

    return s, all_symbols, all_people

# Functions for solve()

def get_poss_assignments(person, pref_type=0):
    possible_assignments = []
    for room in person.valid_rooms(pref_type):
        possible_assignments.append(Bool("{} gets {}".format(person.entry_id, room)))

    return possible_assignments

def get_suite_list(rooms):
    rooms_to_split = sorted(list(filter(lambda x: x in suite_rooms, rooms)))
    split_rooms_list = []
    for room_idx in range(0, len(rooms_to_split), 6):
        rooms = rooms_to_split[room_idx : room_idx + 6]
        split_rooms_list.append(rooms)

    return split_rooms_list

def get_floor_list(rooms_to_split):
    split_rooms_dict = defaultdict(list)
    for room in rooms_to_split:
        floor, pos = room.split('-')
        split_rooms_dict[floor].append(room)

    return split_rooms_dict.values()

@timeit
def get_pref_comments(all_people):
    pref_comments = dict()
    for person in all_people:
        pref = person.preference_comment
        if pref == '':
            continue
        if pref not in pref_comments:
            pref_comments[pref] = []

        pref_comments[pref].append(person)

    return pref_comments



def get_rooms_list_constraint(group_mates, rooms_list):
    '''
    Takes in a list of list of rooms (either a suite or a floor usually) and assets that all group mates belong to the same room list
    '''
    rooms_list_constraints = []
    for rooms in rooms_list:
        rooms_constraints = []
        for person in group_mates:
            rooms_constraints.append(Or([Bool('{} gets {}'.format(person.entry_id, room)) for room in rooms]))

        rooms_list_constraints.append(And(rooms_constraints))
    return Or(rooms_list_constraints)

@timeit
def solve():
    pref_comments = get_pref_comments(all_people)
    people_left = set(all_people)
    preferences_checked = set()
    order_to_fill = [1, 2, 3, 0]
    for order in order_to_fill:
        for person in all_people:
            print('Handling person: {} and perference: {}'.format(person, order))
            if person not in people_left:
                continue

            pref = person.preference_comment
            if pref in pref_comments and pref not in preferences_checked and len(pref_comments[pref]) <= 6:
                preferences_checked.add(pref)
                group_mates = pref_comments[pref]

                if len(set(map(lambda x: x.room_pref1, group_mates))) == 1:
                    s.push()
                    # if the preference is a suite: same suite
                    if person.room_pref1.is_suite:
                        suite_list = get_suite_list(person.valid_rooms(1))
                        s.add(get_rooms_list_constraint(group_mates, suite_list))

                    # if the preference is not a suite: same floor
                    else:
                        floor_list = get_floor_list(person.valid_rooms(1))
                        s.add(get_rooms_list_constraint(group_mates, floor_list))

                    if s.check() == sat:
                        for person in group_mates:
                            people_left.remove(person)

                        continue
                    else:
                        s.pop()

            s.push()
            s.add(Or(get_poss_assignments(person, order)))
            if s.check() == sat:
                people_left.remove(person)
            else:
                s.pop()

    print "no of people unassigned: {}".format(len(people_left))



s, all_symbols, all_people = get_solver_package()

s.push()
solve()
model = s.model()
print filter(lambda x: is_true(model.eval(x)), all_symbols)
s.pop()

