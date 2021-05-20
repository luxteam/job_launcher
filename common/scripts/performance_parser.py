import argparse
import json
import os
from statistics import mean
from dateutil.parser import parse


def extract_datetime(line):
    return parse(line.split('-')[0])


def closest_line_num_by_datetime(datetime, lines):
    

    left = 0
    right = len(lines) - 1
    best_ind = left

    while left <= right:
        mid = left + (right - left) // 2
        if extract_datetime(lines[mid]) < datetime:
            left = mid + 1
        elif extract_datetime(lines[mid]) > datetime:
            right = mid - 1
        else:
            best_ind = mid
            break

        if abs(extract_datetime(lines[mid]) - datetime) <= abs(extract_datetime(lines[best_ind]) - datetime):
            best_ind = mid
    
    
    return best_ind


def main(args):
    with open(args.i, 'r') as f:
        lines = f.readlines()
        start = closest_line_num_by_datetime(args.periods[0], lines)
        end = closest_line_num_by_datetime(args.periods[1], lines)
    
    lines_range = lines[start:end+1]
    values = list(map(lambda x: float(x.split('-')[1].strip().split(' ')[0]), lines_range))

    res = {
        'mean': mean(values),
        'max': max(values),
        'min': min(values)
    }
    
    if not os.path.exists(os.path.dirname(args.o)):
        os.makedirs(os.path.dirname(args.o))

    with open(args.o, 'w') as f:
        f.write(json.dumps(res))


if __name__ == '__main__':

    def parsed_datetime(str):
        return parse(str)

    parser = argparse.ArgumentParser()
    parser.add_argument('periods', type=parsed_datetime, nargs=2)
    parser.add_argument('-i', type=str, required=True)
    parser.add_argument('-o', type=str, required=True)

    args = parser.parse_args()
    main(args)