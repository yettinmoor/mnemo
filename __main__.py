import argparse
import os
import sys

from card import Card
from deck import Deck


if __name__ == '__main__':
    ap = argparse.ArgumentParser()

    ap.add_argument('file', help='.mnemo deck file')
    ap.add_argument(
        '-n',
        '--new-cards',
        metavar='cards',
        help='amount of new cards to play (-1 = no limit).',
        type=int,
        action='store',
        default=10)
    ap.add_argument(
        '-a',
        '--add-cards',
        metavar='file',
        help='append new cards to the deck.',
        type=str,
        action='store')
    ap.add_argument(
        '-i',
        '--inspect',
        help='print # of old cards due today and new cards available.',
        action='store_true')
    ap.add_argument(
        '-d',
        '--dump',
        help='print all cards.',
        action='store_true')
    ap.add_argument(
        '--fmt',
        help='dump format',
        action='store')

    args = ap.parse_args()

    if args.new_cards == -1:
        args.new_cards = None

    deck = Deck(args.file)

    if args.inspect:
        due_cards = [card for card in deck.cards if card.is_due()]

        old = sum(1 for card in due_cards if not card.new)
        print(f'{old} old cards due.')

        new = len(due_cards) - old
        if new:
            first_new = next(card for card in due_cards if card.new)
            print(f'{new} new cards available (starting with #{first_new.id}).')
        else:
            print(f'no new cards available.')

    elif args.dump:
        deck.pretty_print(args.fmt)

    elif args.add_cards:
        if deck.cards:
            start_id = max(card.id for card in deck.cards) + 1
        else:
            start_id = 1
        with sys.stdin if args.add_cards == '-' else open(args.add_cards) as f:
            lines = filter(
                lambda line: line.strip() and not line.lstrip().startswith('#'),
                f.readlines())
            add_cards = [Card(f'{i} | ' + line, log_init={})
                         for i, line in enumerate(lines, start=start_id)]

        if not add_cards:
            print('no new cards found.')
        else:
            deck.backup_deck()
            with open(deck.path, 'a') as f:
                for card in add_cards:
                    f.write(str(card) + '\n')
            print(f'appended {len(add_cards)} new cards to {deck.path}.')
            print(f'saved backup to /tmp/mnemo.')

    else:
        # copy a backup of the log to /tmp.
        if os.path.exists(deck.log_path):
            deck.backup_log()

        for card in deck.due_today(max_new=args.new_cards):
            if not deck.play(card):
                break

        print(f'played {len(deck.played_this_round)} cards.')
        failed_cards = [k for k, v in deck.played_this_round.items() if not v]
        if failed_cards:
            print('failed cards:')
            for failed_id in failed_cards:
                card = next(
                    card for card in deck.cards if card.id == failed_id)
                print(f'  #{card.id}: {card.answer}')
