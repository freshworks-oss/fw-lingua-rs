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

"""Replaces Chinese test samples that are identical in Japanese.

Text written only with characters that both Chinese and Japanese use is
detected as Language::Ambiguous, so such lines in
language-models/zh/testdata/single-words.txt and word-pairs.txt do not test
Chinese detection. This script keeps every line that contains a character
Japanese does not use (see src/data/japanese_usable_kanji.txt) and replaces the
others with samples of the same shape that do:

    single-words.txt  single characters from the Chinese test sentences, topped
                      up with the most frequent characters in jieba's
                      dictionary when the sentences run out
    word-pairs.txt    pairs of adjacent characters from the Chinese test
                      sentences, like the existing pairs

The replaced lines remain covered as the "common" class of
tests/data/cjk_han_only_test_set.tsv, where they are expected to be Ambiguous.

Usage:
    pip install jieba
    python3 scripts/update_chinese_testdata.py
"""

import random
import re
from pathlib import Path

import jieba

ROOT = Path(__file__).resolve().parent.parent
TESTDATA = ROOT / "language-models" / "zh" / "testdata"
HAN = re.compile(r"[㐀-䶿一-鿿豈-﫿\U00020000-\U0003134f]")
HAN_RUN = re.compile(r"[㐀-䶿一-鿿豈-﫿\U00020000-\U0003134f]+")
SEED = 20261016


def main():
    usable = set((ROOT / "src" / "data" / "japanese_usable_kanji.txt").read_text(encoding="utf-8"))

    def is_chinese(text):
        return any(HAN.match(c) and c not in usable for c in text)

    sentences = (TESTDATA / "sentences.txt").read_text(encoding="utf-8").splitlines()
    rng = random.Random(SEED)

    def update(file_name, candidates):
        lines = [l for l in (TESTDATA / file_name).read_text(encoding="utf-8").splitlines() if l.strip()]
        present = set(lines)
        candidates = [c for c in dict.fromkeys(candidates) if c not in present]
        replacements = iter(candidates)
        updated, replaced = [], 0
        for line in lines:
            if is_chinese(line):
                updated.append(line)
            else:
                updated.append(next(replacements))
                replaced += 1
        (TESTDATA / file_name).write_text("\n".join(updated) + "\n", encoding="utf-8")
        print(f"{file_name}: kept {len(lines) - replaced}, replaced {replaced}")

    corpus_characters = [c for line in sentences for c in line if HAN.match(c) and c not in usable]
    rng.shuffle(corpus_characters)
    dictionary = Path(jieba.__file__).parent / "dict.txt"
    frequent_characters = [
        word
        for word, frequency in sorted(
            (
                (parts[0], int(parts[1]))
                for parts in (line.split() for line in dictionary.read_text(encoding="utf-8").splitlines())
                if len(parts[0]) == 1
            ),
            key=lambda entry: -entry[1],
        )
        if HAN.match(word) and word not in usable
    ]
    update("single-words.txt", corpus_characters + frequent_characters)

    pairs = [
        run[i : i + 2]
        for line in sentences
        for run in HAN_RUN.findall(line)
        for i in range(len(run) - 1)
        if is_chinese(run[i : i + 2])
    ]
    rng.shuffle(pairs)
    update("word-pairs.txt", pairs)


if __name__ == "__main__":
    main()
