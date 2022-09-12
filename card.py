import pyparsing as pp

from datetime import date, datetime
from pyparsing import pyparsing_common as common
from random import random


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

    def __str__(self) -> str:
        return ' | '.join([str(self.id)] + [self.answer] + self.cues)

    @property
    def due_date(self) -> date:
        return date.fromtimestamp(self.due)

    def is_due(self) -> bool:
        return self.due_date <= date.today() and self.tick > 0

    # returns true if card is done for today
    def update(self, correct: bool) -> bool:
        if self.new and not correct:
            self.tick = Card.INIT_TICKS
        else:
            self.tick -= 1

        if self.tick <= 0:
            self.factor *= Card.POS_FACTOR if correct else Card.NEG_FACTOR
            self.factor = max(self.factor, 1)
            self.factor *= (1 + 0.25 * random())

            if self.due_date < date.today():
                self.due = int(datetime.today().replace(hour=0).timestamp())
            self.due += int(86400 * self.factor)
            return True

        return False


FIELDS = pp.delimited_list(
    pp.CharsNotIn('|'),
    delim='|',
    allow_trailing_delim=True).set_parse_action(lambda ss: [s.strip() for s in ss])

CARD_FMT = common.integer \
    + pp.Char('|').suppress() \
    + FIELDS \
    + pp.line_end.suppress() \
    + pp.string_end
