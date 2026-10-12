import argparse
import datetime

from boss_fight import BossFight
from common import print, challenge_fight
from email_tools import send_email
from fight import Fight
from red_pack import RedPack
from running import MainRun
from star_pick_up import StarPick
from black_market_finder import BlackMarketFinder
from zone_explore import ZoneExplore


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
    parser.add_argument("-c", "--combo", action='store_true',
                        help="Comb of running + fighting + wait for red pack for 2 hours")
    parser.add_argument("-cf", "--challengefight", action='store_true', help="Try to fight challenge until success")
    parser.add_argument("-n", "--niu", action='store_true', help="Run for niu mode")
    parser.add_argument("-sp", "--starpick", action='store_true', help="Star picking")
    parser.add_argument("-bm", "--blackmarket", action='store_true', help="Find black market")
    parser.add_argument("-ri", "--runindex", type=int, default=0, help="Run index")
    parser.add_argument("-ze", "--zoneexplore", action='store_true', help="Zone explore: auto dispatch fleets")
    parser.add_argument("--dry", action='store_true', help="Dry run (detect only, no clicks) for zone explore")
    parser.add_argument("-m", "--monitor", action='store_true',
                        help="Watch the dice run; enter 星际探险 when the dice run out, then zone explore")

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
        run.switch_run(args.runindex)
        print("Total visits " + str(run.visits) + " times")
        content = "The run starts at: " + str(time) + "\n Takes " + str(
            datetime.datetime.now() - time) + "!\nTotal " + str(run.visits) + " visits\n"

    if args.bossfight:
        bf = BossFight()
        bf.combo_fight()

    if args.challengefight:
        challenge_fight()

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

    if args.starpick:
        s = StarPick()
        s.pick_up()
    
    if args.blackmarket:
        bm = BlackMarketFinder()
        bm.find_black_market()

    if args.zoneexplore:
        ZoneExplore(dry_run=args.dry).run()

    if args.monitor:
        ZoneExplore(dry_run=args.dry).monitor()
    
    send_email(content)
