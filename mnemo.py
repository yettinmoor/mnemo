import argparse
import os
import pyparsing as pp
import shutil
import tabulate
import time

from datetime import date, datetime
from itertools import zip_longest
from pyparsing import pyparsing_common as common
from random import random
from typing import Iterator, Optional

CARD_FMT = common.integer \
    + pp.Suppress('|') \
    + pp.delimited_list(
        pp.CharsNotIn('|'),
        delim='|',
        allow_trailing_delim=True).set_parse_action(lambda ss: [s.strip() for s in ss]) \
    + pp.Suppress(pp.line_end) \
    + pp.string_end

HIST_FMT = pp.delimited_list(common.integer ^ common.real) \
    + pp.Suppress(pp.line_end) \
    + pp.string_end


class Card:
    id: int

    answer: str
    cues: list[str]

    # UNIX timestamp.
    due: int

    # after tick -> 0, due += `factor` days.
    factor: float

    # countdown for this round.
    tick: int

    POS_FACTOR = 2.0
    NEG_FACTOR = 0.5

    INIT_TICKS = 2

    def __init__(self, s, log_init) -> None:
        self.id, self.answer, *self.cues = CARD_FMT.parse_string(s)

        card_init = log_init.get(self.id, {})
        self.due = card_init.get('due', int(datetime.now().timestamp()))
        self.factor = card_init.get('factor', 0)

        self.new = self.factor == 0
        self.tick = Card.INIT_TICKS if self.new else 1
        self.first_correct: Optional[bool] = None

    def __repr__(self) -> str:
        return f'#{self.id}: {self.answer} ({self.factor:.3f}, due {self.due_date})'

    @property
    def due_date(self) -> date:
        return date.fromtimestamp(self.due)

    def is_due(self) -> bool:
        return self.due_date <= date.today() and self.tick > 0

    def update(self, correct: bool):
        if self.first_correct is None:
            self.first_correct = correct

        if correct:
            self.tick -= 1
        else:
            self.tick = Card.INIT_TICKS

        if self.tick <= 0:
            self.factor *= Card.POS_FACTOR if self.first_correct else Card.NEG_FACTOR
            self.factor = max(self.factor, 1)
            self.factor *= (1 + 0.25 * random())

            if self.due_date < date.today():
                self.due = int(datetime.today().replace(hour=0).timestamp())
            self.due += int(86400 * self.factor)


class Deck:
    path: str
    cards: list[Card]

    answer_header: str = 'ans'
    cue_headers: list[str] = []

    def __init__(self, path: str) -> None:
        self.path = path

        log_init = {}
        if os.path.exists(self.log_path):
            with open(self.log_path) as f:
                for line in f.readlines():
                    id, due, factor = HIST_FMT.parse_string(line)
                    log_init[id] = {
                        'due': due,
                        'factor': factor,
                    }

        with open(path) as f:
            self.cards = []
            seen_ids = set()
            for line in f.readlines():
                # ending '\n' creates dummy value for last cue
                card = Card(line.lstrip().removeprefix('#'), log_init)
                if card.id in seen_ids:
                    print(f'error: duplicate id: #{card.id}')
                    exit(1)
                seen_ids.add(card.id)
                if not line.lstrip().startswith('#'):
                    self.cards.append(card)

        if len(set(len(card.cues) for card in self.cards)) > 1:
            print('error: badly formatted .mnemo file.')
            print('not all entries have the same number of fields.')
            exit(1)

        if self.cards and self.cards[0].id == 0:
            header_card = self.cards.pop(0)
            self.answer_header = header_card.answer
            self.cue_headers = header_card.cues

    def __repr__(self) -> str:
        return repr(self.cards)

    @property
    def log_path(self) -> str:
        return self.path + '.log'

    def play(self, card: Card):
        print(f'card #{card.id}')
        for header, cue in zip_longest(self.cue_headers, card.cues):
            if cue:
                if header:
                    print(header, end=': ')
                print(cue)

        try:
            if input('> reveal... ') in ['q', 'Q']:
                exit(0)
        except (KeyboardInterrupt, EOFError):
            exit(0)

        if self.answer_header:
            print(self.answer_header, end=': ')
        print(card.answer)

        reply = ''
        while reply.lower() not in ['n', 'y']:
            try:
                reply = input('> ok? [y/n] ').lower()
            except (KeyboardInterrupt, EOFError):
                exit(0)

        card.update(reply == 'y')

        self.save_log()

        if card.tick > 0:
            print(
                f'{card.tick} tick(s) until card {"" if card.new else "re"}initialized.')
        else:
            delta = (card.due_date - date.today()).days
            print(f'due again in {delta} days.')

        print()
        time.sleep(1)

    def save_log(self, path=None):
        if path is None:
            path = self.log_path
        with open(path, mode='w+') as f:
            for card in self.cards:
                f.write(
                    f'{card.id},{card.due},{card.factor:.3f}\n')

    def due_today(self, max_old: Optional[int] = None, max_new: Optional[int] = None) -> Iterator[Card]:
        old_cards = [
            card for card in self.cards if not card.new and card.is_due()]
        old_cards.sort(key=lambda card: card.due)
        if max_old is not None:
            old_cards = old_cards[:max_old]

        while old := [card for card in old_cards if card.tick > 0]:
            yield from old

        new_cards = [card for card in self.cards if card.new]
        if max_new is not None:
            new_cards = new_cards[:max_new]

        while new := [card for card in new_cards if card.tick > 0]:
            yield from new

    def pretty_print(self, fmt: Optional[str]):
        if fmt is None:
            for card in deck.cards:
                print(f'{card.id},{card.answer},{card.due_date},{card.factor}')
        else:
            s = tabulate.tabulate(
                [[card.id, card.answer, card.due_date, card.factor]
                 for card in deck.cards],
                tablefmt=fmt)
            print(s)


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
    else:
        # copy a backup of the log to /tmp.
        if os.path.exists(deck.log_path):
            timestamp = int(datetime.now().timestamp())
            backup = deck.log_path.replace('/', '_')
            backup = f'/tmp/{backup}.{timestamp}'
            shutil.copy(deck.log_path, backup)

        for card in deck.due_today(max_new=args.new_cards):
            deck.play(card)
