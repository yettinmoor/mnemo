import os
import pyparsing as pp
import shutil
import tabulate
import time

from datetime import date, datetime
from itertools import zip_longest
from pyparsing import pyparsing_common as common
from random import shuffle
from typing import Iterator, Optional

from card import Card

HIST_FMT = pp.delimited_list(common.integer ^ common.real) \
    + pp.Suppress(pp.line_end) \
    + pp.string_end


class Deck:
    path: str
    cards: list[Card]

    answer_header: str = 'ans'
    cue_headers: list[str] = []

    played_this_round: dict[int, bool]

    def __init__(self, path: str) -> None:
        self.path = os.path.abspath(path)

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

        # assert consistent number of fields
        lengths = set(len(card.cues) for card in self.cards)
        if len(lengths) > 1:
            print('error: badly formatted .mnemo file.')
            print('not all entries have the same number of fields.')
            exit(1)
        if lengths:
            self.number_of_fields = lengths.pop()
        else:
            self.number_of_fields = 0

        if self.cards and self.cards[0].id == 0:
            header_card = self.cards.pop(0)
            self.answer_header = header_card.answer
            self.cue_headers = header_card.cues

        self.played_this_round = {}

    def __repr__(self) -> str:
        return repr(self.cards)

    @property
    def log_path(self) -> str:
        return self.path + '.log'

    # return true if continue, false if exit
    def play(self, card: Card) -> bool:
        print(f'card #{card.id}')
        for header, cue in zip_longest(self.cue_headers, card.cues):
            if cue:
                if header:
                    print(header, end=': ')
                print(cue)

        try:
            if input('> reveal... ') in ['q', 'Q']:
                return False
        except (KeyboardInterrupt, EOFError):
            return False

        if self.answer_header:
            print(self.answer_header, end=': ')
        print(card.answer)

        reply = ''
        while reply.lower() not in ['n', 'y']:
            try:
                reply = input('> ok? [y/n] ').lower()
            except (KeyboardInterrupt, EOFError):
                return False

        correct = reply == 'y'
        if card.update(correct):
            self.played_this_round[card.id] = correct

        self.save_log()

        if card.tick > 0:
            print(
                f'{card.tick} tick(s) until card {"" if card.new else "re"}initialized.')
        else:
            delta = (card.due_date - date.today()).days
            print(f'due again in {delta} days.')

        print()
        time.sleep(1)

        return True

    def save_log(self, path=None):
        if path is None:
            path = self.log_path
        with open(path, mode='w+') as f:
            for card in self.cards:
                f.write(
                    f'{card.id},{card.due},{card.factor:.3f}\n')

    def due_today(self,
                  randomize=False,
                  max_old: Optional[int] = None,
                  max_new: Optional[int] = None) -> Iterator[Card]:

        old_cards = [
            card for card in self.cards if not card.new and card.is_due()]
        old_cards.sort(key=lambda card: card.due)
        if max_old is not None:
            old_cards = old_cards[:max_old]

        while old := [card for card in old_cards if card.tick > 0]:
            yield from old

        new_cards = [card for card in self.cards if card.new]
        if randomize:
            shuffle(new_cards)
        if max_new is not None:
            new_cards = new_cards[:max_new]

        while new := [card for card in new_cards if card.tick > 0]:
            yield from new

    def pretty_print(self, fmt: Optional[str]):
        if fmt is None:
            for card in self.cards:
                print(f'{card.id},{card.answer},{card.due_date},{card.factor}')
        else:
            s = tabulate.tabulate(
                [[card.id, card.answer, card.due_date, card.factor]
                 for card in self.cards],
                tablefmt=fmt)
            print(s)

    def backup_deck(self):
        make_backup(self.path)

    def backup_log(self):
        make_backup(self.log_path)


def make_backup(path: str):
    BACKUP_DIR = '/tmp/mnemo'
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = int(datetime.now().timestamp())
    backup = path.lstrip('/').replace('/', '_')
    backup = os.path.join(BACKUP_DIR, f'{backup}.{timestamp}')
    shutil.copy(path, backup)
