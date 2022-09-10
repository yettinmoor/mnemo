# mnemo

mnemo is a terminal-based flashcard [spaced repetition system](https://en.wikipedia.org/wiki/Spaced_repetition). It is designed as a lightweight, extremely simple alternative to programs like [Anki](https://apps.ankiweb.net/).

Here is a sample of a deck file:

```
$ cat tests/test.mnemo
0 | Capital       | Country    | First letter | Founded
1 | Stockholm     | Sweden     | S            | 1252
2 | Oslo          | Norway     | O            |
3 | Washington DC | USA        | W            | 1791
4 | Antananarivo  | Madagascar | A            |
5 | Mogadishu     | Somalia    | M            |
```

Deck syntax is very simple: fields are separated by `|`. The first field is a numerical unique ID. The second field is the answer to the flashcard. The remaining fields are the cues from which the user must attempt to recall the answer. If the first row has ID 0, its fields are interpreted as field headers.

Because mnemo uses human-readable file formats, it is easy to extend with scripts. For example, using a [Jisho web scraper](https://github.com/yettinmoor/jisho-cli), it is relatively painless to turn:

```
$ cat sentences.txt
時計は[壊滅]だ！
お前はもう[死んでいる]。
[お前]はもう死んでいる。
[時計]は壊滅だ！
```

into:

```
$ ./sentences sentences.txt
 1  | かいめつ, destruction | 時計は[壊滅]だ！
 2  | し, to be dead        | お前はもう[死んでいる]。
 3  | まえ, you             | [お前]はもう死んでいる。
 4  | とけい, clock         | [時計]は壊滅だ！
```

## Tips

Use a tool like [vim-tabular](https://githubcom/godlygeek/tabular) to automatically align by `|`:

```{vimscript}
au BufWritePre *.mnemo :Tabularize /|/
```
