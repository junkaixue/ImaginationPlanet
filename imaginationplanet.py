import argparse
import datetime

from common import print
from email_tools import send_email
from fight import Fight
from running import MainRun
from red_pack import RedPack


def combo(skipcat):
    r = MainRun(skipcat)
    f = Fight()
    while True:
        r.light_run()
        f.fight()
        irp = RedPack(1)
        irp.get_red_pack()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--run", action='store_true', help="Just regular run and visiting")
    parser.add_argument("-l", "--lightrun", action='store_true', help="Light weight regular run and visiting")
    parser.add_argument("-f", "--fight", action='store_true', help="Just fight")
    parser.add_argument("-sc", "--skipcat", action='store_true', help="Skip cat grab")
    parser.add_argument("-c", "--combo", action='store_true', help="Comb of running + fighting + wait for red pack for 2 hours")
    
    args = parser.parse_args()

    content = ""
    time = datetime.datetime.now()
    if args.run:
        run = MainRun(args.skipcat)
        run.run()
        print("Total visits " + str(run.visits) + " times")
        content = "The run starts at: " + str(time) + "\n Takes " + str(
            datetime.datetime.now() - time) + "!\nTotal " + str(run.visits) + " visits\n"
    elif args.lightrun:
        run = MainRun(args.skipcat)
        run.light_run()
        print("Total visits " + str(run.visits) + " times")
        content = "The run starts at: " + str(time) + "\n Takes " + str(
            datetime.datetime.now() - time) + "!\nTotal " + str(run.visits) + " visits\n"
    if args.fight:
        fight = Fight()
        fight.fight()
        print("Total fights " + str(fight.total) + " times")
        content += "The run starts at: " + str(time) + "\n Total " + str(fight.total) + " fights\n"
    print("Complete single run for " + str(datetime.datetime.now() - time) + " seconds!")

    if args.combo:
        combo(args.skipcat)
    send_email(content)
