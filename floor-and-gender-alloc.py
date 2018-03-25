
# coding: utf-8

# In[1]:


import pandas as pd
from z3 import *
from time import time
from copy import copy

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



# In[2]:


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


    # Only one set of valid floors for one person
    def valid_floors(self):
        include_single_gen_floors = self.pref_floor_gender == "Single Gender Floor" or self.pref_floor_gender == "No Preference"
        include_mixed_floors = self.pref_floor_gender == "Mixed Gender Floor" or self.pref_floor_gender == "No Preference"
        return get_preferred_floors(self.is_male, not self.is_senior, include_single_gen_floors, include_mixed_floors)




# In[3]:


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


# In[4]:


def view_times(times):
    if len(times) < 1:
        return
    last_t = times[0][1]
    new_times = []
    for t in times:
        new_times.append([t[0], t[1] - last_t])
        last_t = t[1]

    return pd.DataFrame(new_times)


# In[5]:


def solve(nrows=None):
    times = []
    times.append(["start time", time()])

    input_data_frame = pd.read_csv('data/usprc.csv', nrows=nrows, dtype=object).fillna('').values

    times.append(["read file", time()])
    print times[-1][0], times[-1][1] - times[-2][1]

    constraints = []
    standard_implications = []
    room_type_preferences = []
    floor_type_preferences = []
    opt = Optimize()

    # Populate people
    all_people = []
    for row in input_data_frame:
        person = Person(*row[:8])
        all_people.append(person)

    times.append(["make person objects", time()])
    print times[-1][0], times[-1][1] - times[-2][1]

    # Populate rooms into a hashmap Eg. {'16-118': Room-Object}
    all_rooms = dict(map(Room.make_label_room_tuple, get_all_rooms()))

    # Valid people for each room
    valid_people_for_rooms = {}
    for label, room in all_rooms.items():
        valid_people_for_rooms[label] = set()

    times.append(["make room objects", time()])
    print times[-1][0], times[-1][1] - times[-2][1]


    # Populate all room possible assignments
    assignments = {}
    for person in all_people:
        assignments[person] = {}

        for label, room in all_rooms.items():
            possibility = Bool("{} gets {}".format(person.entry_id, room))

            # Add possibility to possible assignments
            assignments[person][room] = possibility

    times.append(["make all possible person-room pair", time()])
    print times[-1][0], times[-1][1] - times[-2][1]

    # One person can only get one room
    for person in all_people:
        constraints.append(Or(assignments[person].values()))


    # Add hard constraints for floor preference
    for person in all_people:
        possible_assignments = []
        for room in person.valid_rooms(0):

            # Construct Boolean
            possible_assignments.append(Bool("{} gets {}".format(person.entry_id, room)))

            # Populate valid_people_for_rooms
            valid_people_for_rooms[room].add(person)

        floor_type_preferences.append(Or(possible_assignments))

    times.append(["list floor type preferences constraints", time()])
    print times[-1][0], times[-1][1] - times[-2][1]

    # Add soft constraints for first preference
    for person in all_people:
        possible_assignments = []
        for room in person.valid_rooms(1):

            # Construct Boolean
            possible_assignments.append(Bool("{} gets {}".format(person.entry_id, room)))

            # Populate valid_people_for_rooms
            valid_people_for_rooms[room].add(person)

        room_type_preferences.append(Or(possible_assignments))

    times.append(["list room type preferences constraints", time()])
    print times[-1][0], times[-1][1] - times[-2][1]


    # One room can only be assigned to one person from the contenders for that room
    for person in all_people:
        for label, room in all_rooms.items():
            for other_person in valid_people_for_rooms[room.label]:
                if other_person == person:
                    continue

                implication = Implies(assignments[person][room], Not(assignments[other_person][room]))
                constraints.append(implication)

    times.append(["list standard constraints", time()])
    print times[-1][0], times[-1][1] - times[-2][1]


    # Solve
    for constraint in constraints:
        opt.add(constraint)

    for implication in standard_implications:
        opt.add(implication)

    for preference in floor_type_preferences:
        opt.add(preference)

    for preference in room_type_preferences:
        opt.add_soft(preference)

    times.append(["add all constraints", time()])
    print times[-1][0], times[-1][1] - times[-2][1]

    opt.check()
    model = opt.model()

    times.append(["find solution", time()])
    print times[-1][0], times[-1][1] - times[-2][1]

    all_symbols = [assignments[person][room] for person in all_people for room in all_rooms.values()]
    return filter(lambda x: is_true(model.eval(x)), all_symbols)


# In[ ]:


solve(100)


# In[19]:


# floors = set(range(4, 22))
# male_floors = set([8, 10, 16, 19])
# female_floors = set([7, 14, 18, 20])
# mixed_floors = floors.difference(male_floors).difference(female_floors)
# rf_floors = set(range(5, 22, 4))
# laundry_floors = set([9, 17])
# freshmen_floors = set([6, 8, 11, 14, 16, 17, 20])
# senior_floors = floors.difference(freshmen_floors)

pd.read_csv('data/usprc.csv', nrows=10, dtype=object).fillna('')

