import argparse
from running import MainRun
from fight import Fight
import datetime
from common import print

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--run", default=False, help="Just regular run and visiting")
    parser.add_argument("-f", "--fight", default=False, help="Just fight")
    args = parser.parse_args()

    time = datetime.datetime.now()
    if args.run:
        run = MainRun()
        run.run()
        print("Complete single run for " + str(datetime.datetime.now() - time) + " seconds!")
        print("Total visits " + str(run.visits) + " times")
    elif args.fight:
        fight = Fight()
        fight.fight()
        print("Complete single fight for " + str(datetime.datetime.now() - time) + " seconds!")
        print("Total fights " + str(fight.total) + " times")

