import argparse
import datetime

from boss_fight import BossFight
from common import print
from email_tools import send_email
from fight import Fight
from running import MainRun
from red_pack import RedPack


def combo(skipcat, gohome, switch):
    r = MainRun(skipcat, gohome, switch)
    f = Fight()
    while True:
        r.light_run()
        f.fight()
        irp = RedPack(1, 7200)
        irp.get_red_pack()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--run", action='store_true', help="Just regular run and visiting")
    parser.add_argument("-rp", "--redpack", action='store_true', help="Get redpack")
    parser.add_argument("-l", "--lightrun", action='store_true', help="Light weight regular run and visiting")
    parser.add_argument("-s", "--switchrun", action='store_true', help="Switch run and visiting")
    parser.add_argument("-f", "--fight", action='store_true', help="Just fight")
    parser.add_argument("-sc", "--skipcat", action='store_true', help="Skip cat grab")
    parser.add_argument("-sa", "--semiauto", action='store_true', help="Semiauto run")
    parser.add_argument("-g", "--gohome", action='store_true', help="Go home directly")
    parser.add_argument("-bf", "--bossfight", action='store_true', help="Combo boss fight")
    parser.add_argument("-c", "--combo", action='store_true', help="Comb of running + fighting + wait for red pack for 2 hours")
    
    args = parser.parse_args()

    content = ""
    time = datetime.datetime.now()
    if args.run:
        run = MainRun(args.skipcat, args.gohome)
        run.run()
        print("Total visits " + str(run.visits) + " times")
        content = "The run starts at: " + str(time) + "\n Takes " + str(
            datetime.datetime.now() - time) + "!\nTotal " + str(run.visits) + " visits\n"
    elif args.lightrun:
        run = MainRun(args.skipcat, args.gohome, args.semiauto)
        run.light_run()
        print("Total visits " + str(run.visits) + " times")
        content = "The run starts at: " + str(time) + "\n Takes " + str(
            datetime.datetime.now() - time) + "!\nTotal " + str(run.visits) + " visits\n"
    elif args.switchrun:
        run = MainRun(args.skipcat, args.gohome, True)
        run.switch_run()
        print("Total visits " + str(run.visits) + " times")
        content = "The run starts at: " + str(time) + "\n Takes " + str(
            datetime.datetime.now() - time) + "!\nTotal " + str(run.visits) + " visits\n"

    if args.bossfight:
        bf = BossFight()
        bf.combo_fight()

    if args.fight:
        fight = Fight()
        fight.fight()
        print("Total fights " + str(fight.total) + " times")
        content += "The run starts at: " + str(time) + "\n Total " + str(fight.total) + " fights\n"
    print("Complete single run for " + str(datetime.datetime.now() - time) + " seconds!")

    if args.redpack:
        rp = RedPack(0)
        rp.get_red_pack()

    if args.combo:
        combo(args.skipcat, args.gohome, args.switchrun)
    send_email(content)
