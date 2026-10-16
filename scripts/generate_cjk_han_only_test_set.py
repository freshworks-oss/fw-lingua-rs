#!/usr/bin/env python3
#
# Copyright © 2020-present Peter M. Stahl pemistahl@gmail.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either expressed or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Generates tests/data/cjk_han_only_test_set.tsv.

Chinese words come from segmenting the Chinese test sentences with jieba,
Japanese words are the runs of kanji in the Japanese test data. Each word is
put into one of five classes by its characters, using the sets written by
scripts/generate_cjk_kanji_sets.py:

    chinese_only          only characters Japanese does not use      -> Chinese
    common_with_chinese   shared characters plus Chinese-only ones   -> Chinese
    japanese_only         only kanji that Chinese does not use       -> Japanese
    common_with_japanese  shared characters plus Japanese-only ones  -> Japanese
    common                only characters both languages use         -> None

Real words written only with Japanese-only kanji are rare in the corpus, so
that class is topped up with hand-picked vocabulary, which is checked against
the same character set.

Usage:
    pip install jieba
    python3 scripts/generate_cjk_han_only_test_set.py
"""

import re
from pathlib import Path

import jieba

SAMPLES_PER_CLASS = 200

EXTRA_JAPANESE_ONLY_WORDS = """
経済 経営 経歴 実験 対戦 対処 単価 価値 円満 満塁 労働 啓発 発売 囲碁 娯楽 庁舎 弾薬 徴収 戦闘 払込
拝観 捜査 歓楽 気楽 気絶 県庁 稲穂 総覧 聴覚 脳裏 薬剤 観覧 観戦 読経 譲歩 転売 閲覧 険悪 仏様 覇権
検査 駅舎 黒髪 絶縁 聴衆 脳髄 荘厳 薬価 観衆 読売 転戦 霊験
駅 鉄 円 歯 姉 県 窓 絵 麺 顔 髪 氷 稲 穂 亀 鮎 鰯 蛍 兎 桜 滝 畑 峠 辻 栞 凧 鶏 畳 瀬 霊 呪 粋 雫 頬 樫 榊 梶 椛 栃
竜 剣 姫 嬢 縁 縄 袴 脇 鉢 銭 艶 蔵 薫 裏 塀 斎
""".split()

HAN_WORD = re.compile(r"^[㐀-䶿一-鿿豈-﫿\U00020000-\U0003134f]+$")
HAN_RUN = re.compile(r"[㐀-䶿一-鿿豈-﫿\U00020000-\U0003134f]+")

ROOT = Path(__file__).resolve().parent.parent


def evenly_spaced(words, count):
    words = sorted(words)
    if len(words) <= count:
        return words
    step = len(words) / count
    return [words[int(i * step)] for i in range(count)]


def main():
    jieba.setLogLevel(60)
    data = ROOT / "src" / "data"
    usable = set((data / "japanese_usable_kanji.txt").read_text(encoding="utf-8"))
    unique = set((data / "japanese_unique_kanji.txt").read_text(encoding="utf-8"))

    def classify(word):
        japanese = any(c in unique for c in word)
        chinese = any(c not in usable for c in word)
        shared = any(c in usable and c not in unique for c in word)
        if japanese and chinese:
            raise ValueError(f"{word} contains evidence for both languages")
        if chinese:
            return "common_with_chinese" if shared else "chinese_only"
        if japanese:
            return "common_with_japanese" if shared else "japanese_only"
        return "common"

    testdata = ROOT / "language-models"
    chinese_words = set()
    for line in (testdata / "zh" / "testdata" / "sentences.txt").read_text(encoding="utf-8").splitlines():
        chinese_words.update(w for w in jieba.cut(line.strip()) if HAN_WORD.match(w))
    for line in (testdata / "zh" / "testdata" / "single-words.txt").read_text(encoding="utf-8").splitlines():
        if HAN_WORD.match(line.strip()):
            chinese_words.add(line.strip())

    japanese_words = set()
    for name in ("sentences.txt", "word-pairs.txt", "single-words.txt"):
        text = (testdata / "ja" / "testdata" / name).read_text(encoding="utf-8")
        japanese_words.update(HAN_RUN.findall(text))

    classes = {}
    for origin, words in (("chinese", chinese_words), ("japanese", japanese_words)):
        for word in words:
            classes.setdefault((classify(word), origin), set()).add(word)

    for word in EXTRA_JAPANESE_ONLY_WORDS:
        if classify(word) != "japanese_only":
            raise ValueError(f"{word} is not written with Japanese-only kanji only")
        classes[("japanese_only", "japanese")].add(word)

    expected = {
        "chinese_only": "Chinese",
        "common_with_chinese": "Chinese",
        "japanese_only": "Japanese",
        "common_with_japanese": "Japanese",
        "common": "None",
    }
    rows = []
    for (name, origin), words in sorted(classes.items()):
        # common words come from both corpora, so each origin gets half
        count = SAMPLES_PER_CLASS // 2 if name == "common" else SAMPLES_PER_CLASS
        rows.extend((name, origin, word, expected[name]) for word in evenly_spaced(words, count))

    output = ROOT / "tests" / "data" / "cjk_han_only_test_set.tsv"
    output.parent.mkdir(exist_ok=True)
    with output.open("w", encoding="utf-8") as file:
        file.write("class\torigin\ttext\texpected\n")
        for row in rows:
            file.write("\t".join(row) + "\n")

    counts = {}
    for name, *_ in rows:
        counts[name] = counts.get(name, 0) + 1
    for name, count in sorted(counts.items()):
        print(f"{name:<22} {count}")


if __name__ == "__main__":
    main()
