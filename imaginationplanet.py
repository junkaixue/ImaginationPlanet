import argparse
import datetime

from common import print
from email_tools import send_email
from fight import Fight
from running import MainRun

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--run", default=False, help="Just regular run and visiting")
    parser.add_argument("-f", "--fight", default=False, help="Just fight")
    args = parser.parse_args()

    content = ""
    time = datetime.datetime.now()
    if args.run:
        run = MainRun()
        run.run()
        print("Complete single run for " + str(datetime.datetime.now() - time) + " seconds!")
        print("Total visits " + str(run.visits) + " times")
        content = "The run starts at: " + str(time) + "\n Takes " + str(
            datetime.datetime.now() - time) + " seconds!\nTotal " + str(run.visits) + " visits\n"
        content += "The fight has total " + str(run.f.total) + " fights\n"
    elif args.fight:
        fight = Fight()
        fight.fight()
        print("Complete single fight for " + str(datetime.datetime.now() - time) + " seconds!")
        print("Total fights " + str(fight.total) + " times")
        content = "The run starts at: " + str(time) + "\n Total " + str(fight.total) + " fights\n"
    send_email(content)
